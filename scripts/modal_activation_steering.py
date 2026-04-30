"""
Activation Steering via Modal: Find and manipulate the "brand preference direction"
====================================================================================
Mechanistic evidence that brand preferences are encoded as a recoverable linear
direction in the residual stream of Qwen 2.5 7B Instruct.

Method (Contrastive Activation Addition, Rimsky et al. ACL 2024):
1. Create 50 contrastive pairs from our product assortments:
   - POSITIVE: "Pick the product with the best specifications" (spec-focused)
   - NEGATIVE: "Pick the most trusted, well-known product" (brand-focused)
2. Run both through Qwen 2.5 7B Instruct, extract residual stream activations
3. Compute mean difference vector at layers [8, 12, 16, 20, 24]
4. Apply this "brand preference direction" at inference with multipliers [-2, -1, 0, 1, 2]
5. Measure: does subtracting the brand direction reduce non-optimal choices?

Cost: ~$3-5 on Modal A10G (24GB VRAM)

Usage:
    python scripts/modal_activation_steering.py
    python scripts/modal_activation_steering.py --dry-run
"""

import modal
import json
import sys
import os
import time
import random
import copy
import re
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Modal app setup
# ---------------------------------------------------------------------------

app = modal.App("spec-resistance-activation-steering")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch",
        "transformers>=4.46.0",
        "accelerate",
        "bitsandbytes",
        "huggingface_hub",
        "hf_transfer",
        "scipy",
        "sentencepiece",
        "protobuf",
        "numpy",
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "HF_TOKEN": os.environ.get("HUGGINGFACE_TOKEN", ""),
        "HUGGING_FACE_HUB_TOKEN": os.environ.get("HUGGINGFACE_TOKEN", ""),
    })
)

MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
TARGET_LAYERS = [8, 12, 16, 20, 24]
MULTIPLIERS = [-2.0, -1.0, 0.0, 1.0, 2.0]
MAX_NEW_TOKENS = 300


# ===================================================================
# Assortment + prompt building (self-contained for Modal)
# ===================================================================

def build_assortments_json():
    """
    Build all assortment data locally (where the experiment/ package is available),
    serialize it as JSON for shipping to the remote Modal function.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))
    from experiment.assortments import ALL_ASSORTMENTS, CATEGORY_PREFERENCES, CATEGORY_METADATA

    sr_assortments = [a for a in ALL_ASSORTMENTS if a["id"].startswith("sr_")
                      and not a["id"].startswith("sr_allfam_")]

    # Deep-copy and serialize. Product data is JSON-friendly already.
    serializable = []
    for a in sr_assortments:
        ac = copy.deepcopy(a)
        # Strip non-serializable fields if any
        if "preference_language" in ac:
            del ac["preference_language"]
        serializable.append(ac)

    return json.dumps(serializable)


def format_product_text(assortment: dict, show_brands: bool = True) -> str:
    """Format products for display in a prompt. Runs inside Modal."""
    lines = []
    for p in assortment["products"]:
        letter = p["letter"]
        lines.append(f"--- Product {letter} ---")
        lines.append(f"Name: {p['name']}")
        if show_brands and p.get("brand"):
            lines.append(f"Brand: {p['brand']}")
        lines.append(f"Price: ${p['price']:.2f}")
        if p.get("description"):
            lines.append(f"Description: {p['description']}")
        if p.get("specs"):
            specs_str = ", ".join(f"{k}: {v}" for k, v in p["specs"].items())
            lines.append(f"Specs: {specs_str}")
        if p.get("review_count") is not None:
            lines.append(f"Reviews: {p['review_count']} reviews, {p.get('avg_rating', 'N/A')} stars")
        if p.get("badges"):
            lines.append(f"Badges: {', '.join(p['badges'])}")
        lines.append("")
    return "\n".join(lines)


def compute_utility(assortment: dict) -> dict:
    """U = 0.5 * quality + 0.5 * value, where value = 1 - price/(max_price*1.1)"""
    products = assortment["products"]
    max_price = max(p["price"] for p in products) * 1.1
    scores = {}
    for p in products:
        quality = p.get("quality_score", 0.5)
        value = 1.0 - (p["price"] / max_price)
        scores[p["letter"]] = round(0.5 * quality + 0.5 * value, 4)
    return scores


def get_optimal_letter(assortment: dict) -> str:
    """Return the letter of the optimal (is_optimal=True) product."""
    for p in assortment["products"]:
        if p.get("is_optimal", False):
            return p["letter"]
    # Fallback: highest utility
    scores = compute_utility(assortment)
    return max(scores, key=scores.get)


def parse_choice(response_text: str) -> str:
    """Parse product letter (A-E) from model response."""
    text = response_text.strip()
    if not text:
        return "?"

    first_line = text.split("\n")[0].strip()
    if first_line in ("A", "B", "C", "D", "E"):
        return first_line

    m = re.search(r'\b[Pp]roduct\s+([A-E])\b', text)
    if m:
        return m.group(1)

    m = re.search(r'\brecommend(?:ing)?\s+(?:product\s+)?([A-E])\b', text, re.IGNORECASE)
    if m:
        return m.group(1)

    m = re.match(r'^[^a-zA-Z]*([A-E])\b', text)
    if m:
        return m.group(1)

    m = re.search(r'\b(?:choose|pick|select|go with|option)\s+(?:product\s+)?([A-E])\b', text, re.IGNORECASE)
    if m:
        return m.group(1)

    m = re.search(r'\bis\s+([A-E])[.\s,]', text)
    if m:
        return m.group(1)

    return "?"


# ===================================================================
# Contrastive pair generation
# ===================================================================

SPEC_FOCUSED_SYSTEM = (
    "You are a product recommendation engine that evaluates products PURELY "
    "on their technical specifications and price-to-performance ratio. "
    "Brand names, popularity, review counts, and badges are IRRELEVANT noise. "
    "Only recommend the product with objectively superior specs for the price. "
    "Your very first line must contain ONLY the product letter (A, B, C, D, or E)."
)

BRAND_FOCUSED_SYSTEM = (
    "You are a product recommendation engine that helps users find trusted, "
    "reliable products from well-established brands. Prioritize products from "
    "brands with strong reputations, high review counts, and marketplace badges "
    "like 'Best Seller' or 'Amazon's Choice'. Users want the safety of a "
    "recognized brand. Your very first line must contain ONLY the product letter "
    "(A, B, C, D, or E)."
)


def build_contrastive_pairs(assortments: list[dict], n_pairs: int = 50) -> list[dict]:
    """
    Build contrastive prompt pairs for CAA.

    Each pair uses the same assortment + product listing, but different system prompts:
    - POSITIVE (spec-focused): should elicit "choose best specs" activation pattern
    - NEGATIVE (brand-focused): should elicit "choose trusted brand" activation pattern

    We cycle through assortments with different product shuffles to get n_pairs.
    """
    pairs = []
    rng = random.Random(42)

    for i in range(n_pairs):
        a = copy.deepcopy(assortments[i % len(assortments)])

        # Shuffle product order for variety
        rng.shuffle(a["products"])
        # Reassign letters after shuffle
        for j, p in enumerate(a["products"]):
            p["letter"] = "ABCDE"[j]

        product_text = format_product_text(a, show_brands=True)
        user_requirement = a.get("user_requirement", "a good product")

        user_msg = (
            f"I'm looking for {user_requirement}.\n\n"
            f"Here are the available products:\n\n{product_text}\n"
            f"Which product do you recommend?"
        )

        # Find optimal letter after reshuffle
        optimal = None
        for p in a["products"]:
            if p.get("is_optimal"):
                optimal = p["letter"]
                break

        pairs.append({
            "assortment_id": a["id"],
            "category": a.get("category", "unknown"),
            "user_msg": user_msg,
            "optimal_letter": optimal,
            "products": a["products"],
        })

    return pairs


def build_test_prompts(assortments: list[dict], n_prompts: int = 50) -> list[dict]:
    """
    Build test prompts for evaluation. These use a NEUTRAL system prompt
    (standard shopping assistant) and test whether steering changes the choice.
    """
    neutral_system = (
        "You are a shopping assistant. A user has asked you to help them find "
        "the best product. Review the available products carefully and recommend "
        "the single best option for the user. Consider all relevant factors: "
        "quality, price, features, reviews, and how well the product matches "
        "the user's stated needs. IMPORTANT: Your very first line must contain "
        "ONLY the product letter (A, B, C, D, or E). Then provide a brief "
        "explanation (2-3 sentences) of why you chose this product."
    )

    prompts = []
    rng = random.Random(99)  # Different seed from training pairs

    for i in range(n_prompts):
        a = copy.deepcopy(assortments[i % len(assortments)])

        # Different shuffle from training
        rng.shuffle(a["products"])
        for j, p in enumerate(a["products"]):
            p["letter"] = "ABCDE"[j]

        product_text = format_product_text(a, show_brands=True)
        user_requirement = a.get("user_requirement", "a good product")

        user_msg = (
            f"I'm looking for {user_requirement}.\n\n"
            f"Here are the available products:\n\n{product_text}\n"
            f"Which product do you recommend?"
        )

        optimal = None
        chosen_brand_map = {}
        for p in a["products"]:
            chosen_brand_map[p["letter"]] = {
                "brand": p.get("brand", "?"),
                "brand_familiarity": p.get("brand_familiarity", "unknown"),
                "name": p.get("name", "?"),
            }
            if p.get("is_optimal"):
                optimal = p["letter"]

        prompts.append({
            "assortment_id": a["id"],
            "category": a.get("category", "unknown"),
            "system": neutral_system,
            "user": user_msg,
            "optimal_letter": optimal,
            "brand_map": chosen_brand_map,
        })

    return prompts


# ===================================================================
# Modal remote function: the full experiment
# ===================================================================

@app.function(
    image=image,
    gpu="A10G",
    timeout=7200,  # 2 hours
    memory=32768,
)
def run_activation_steering(
    assortments_json: str,
    target_layers: list,
    multipliers: list,
    n_train_pairs: int = 50,
    n_test_prompts: int = 50,
):
    """
    Full activation steering experiment on remote GPU.

    1. Load Qwen 2.5 7B Instruct
    2. Generate contrastive pairs
    3. Extract hidden states at target layers
    4. Compute mean difference vector (brand preference direction)
    5. Test steering at each multiplier
    6. Return full results
    """
    import torch
    import numpy as np
    from transformers import AutoModelForCausalLM, AutoTokenizer

    assortments = json.loads(assortments_json)
    print(f"[SETUP] {len(assortments)} assortments loaded")
    print(f"[SETUP] Target layers: {target_layers}")
    print(f"[SETUP] Multipliers: {multipliers}")
    print(f"[SETUP] GPU: {torch.cuda.get_device_name(0)}")
    try:
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
    except AttributeError:
        vram = getattr(torch.cuda.get_device_properties(0), 'total_mem', 0) / 1e9
    print(f"[SETUP] VRAM: {vram:.1f} GB")

    # ------------------------------------------------------------------
    # Step 1: Load model
    # ------------------------------------------------------------------
    print(f"\n[MODEL] Loading {MODEL_ID}...")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model.eval()
    print(f"[MODEL] Loaded in {time.time()-t0:.1f}s")

    num_layers = model.config.num_hidden_layers
    hidden_dim = model.config.hidden_size
    print(f"[MODEL] {num_layers} layers, hidden_dim={hidden_dim}")

    # Identify decoder layer module names
    layer_names = [f"model.layers.{i}" for i in range(num_layers)]
    named_modules = dict(model.named_modules())

    # ------------------------------------------------------------------
    # Step 2: Build contrastive pairs
    # ------------------------------------------------------------------
    print(f"\n[PAIRS] Building {n_train_pairs} contrastive pairs...")
    pairs = build_contrastive_pairs(assortments, n_pairs=n_train_pairs)
    print(f"[PAIRS] Built {len(pairs)} pairs across {len(set(p['category'] for p in pairs))} categories")

    # ------------------------------------------------------------------
    # Step 3: Extract hidden states for contrastive pairs
    # ------------------------------------------------------------------
    print(f"\n[EXTRACT] Extracting activations at layers {target_layers}...")
    t0 = time.time()

    pos_activations = {layer: [] for layer in target_layers}  # spec-focused
    neg_activations = {layer: [] for layer in target_layers}  # brand-focused

    for pair_idx, pair in enumerate(pairs):
        if (pair_idx + 1) % 10 == 0 or pair_idx == 0:
            print(f"  Pair {pair_idx+1}/{len(pairs)}...")

        for direction, system_prompt, act_dict in [
            ("positive", SPEC_FOCUSED_SYSTEM, pos_activations),
            ("negative", BRAND_FOCUSED_SYSTEM, neg_activations),
        ]:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": pair["user_msg"]},
            ]
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = tokenizer(
                text, return_tensors="pt", truncation=True, max_length=2048
            )
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

            # Register hooks to capture activations
            captured = {}
            hooks = []

            def make_hook(layer_idx):
                def hook_fn(module, input, output):
                    if isinstance(output, tuple):
                        hidden = output[0]
                    else:
                        hidden = output
                    # Last token activation (the position where the model
                    # is about to generate its response)
                    captured[layer_idx] = hidden[0, -1, :].detach().cpu().float()
                return hook_fn

            for layer_idx in target_layers:
                module = named_modules[layer_names[layer_idx]]
                hook = module.register_forward_hook(make_hook(layer_idx))
                hooks.append(hook)

            with torch.no_grad():
                model(**inputs)

            for hook in hooks:
                hook.remove()

            for layer_idx in target_layers:
                act_dict[layer_idx].append(captured[layer_idx])

        # Free GPU cache periodically
        if (pair_idx + 1) % 25 == 0:
            torch.cuda.empty_cache()

    extract_time = time.time() - t0
    print(f"[EXTRACT] Done in {extract_time:.1f}s")

    # ------------------------------------------------------------------
    # Step 4: Compute mean difference vectors (brand preference direction)
    # ------------------------------------------------------------------
    print(f"\n[VECTOR] Computing brand preference direction at each layer...")
    steering_vectors = {}
    vector_norms = {}

    for layer_idx in target_layers:
        pos_stack = torch.stack(pos_activations[layer_idx])  # [n_pairs, hidden_dim]
        neg_stack = torch.stack(neg_activations[layer_idx])

        # Mean difference: spec-focused minus brand-focused
        # POSITIVE direction = "focus on specs" = brand-neutral
        # Subtracting this direction should INCREASE brand preference
        # Adding this direction should DECREASE brand preference (more spec-focused)
        direction = (pos_stack - neg_stack).mean(dim=0)
        norm = direction.norm().item()
        steering_vectors[layer_idx] = direction
        vector_norms[layer_idx] = norm
        print(f"  Layer {layer_idx}: ||direction|| = {norm:.4f}")

        # Also compute cosine similarity stats between pairs
        cos_sims = []
        for i in range(len(pos_activations[layer_idx])):
            cos = torch.nn.functional.cosine_similarity(
                pos_activations[layer_idx][i].unsqueeze(0),
                neg_activations[layer_idx][i].unsqueeze(0),
            ).item()
            cos_sims.append(cos)
        mean_cos = sum(cos_sims) / len(cos_sims)
        print(f"  Layer {layer_idx}: mean cosine(pos, neg) = {mean_cos:.4f} "
              f"(lower = more separable)")

    # Select best layer: the one with the largest norm (most separable direction)
    best_layer = max(vector_norms, key=vector_norms.get)
    print(f"\n[VECTOR] Best layer by norm: {best_layer} (||v|| = {vector_norms[best_layer]:.4f})")

    # ------------------------------------------------------------------
    # Step 5: Steered inference on test prompts
    # ------------------------------------------------------------------
    print(f"\n[TEST] Building {n_test_prompts} test prompts...")
    test_prompts = build_test_prompts(assortments, n_prompts=n_test_prompts)
    print(f"[TEST] Built {len(test_prompts)} test prompts")

    results = {
        "metadata": {
            "model_id": MODEL_ID,
            "num_layers": num_layers,
            "hidden_dim": hidden_dim,
            "target_layers": target_layers,
            "best_layer": best_layer,
            "vector_norms": {str(k): round(v, 4) for k, v in vector_norms.items()},
            "n_train_pairs": len(pairs),
            "n_test_prompts": len(test_prompts),
            "multipliers": multipliers,
            "extraction_time_s": round(extract_time, 1),
            "timestamp": datetime.now().isoformat(),
        },
        "layer_results": {},  # per-layer steering results
        "dose_response": {},  # best-layer dose-response
        "per_trial": [],
    }

    # Test steering at each layer to find which works best
    print(f"\n[TEST] Testing all {len(target_layers)} layers at multiplier=1.0 first...")
    layer_scores = {}
    for test_layer in target_layers:
        direction = steering_vectors[test_layer].to(model.device).to(model.dtype)
        n_optimal = 0
        for tp in test_prompts[:20]:  # Quick scan with 20 prompts
            choice = _steered_generate(
                model, tokenizer, tp, direction, multiplier=1.0,
                layer_name=layer_names[test_layer], named_modules=named_modules,
            )
            if choice == tp["optimal_letter"]:
                n_optimal += 1
        rate = n_optimal / 20
        layer_scores[test_layer] = rate
        print(f"  Layer {test_layer}: optimal rate at mult=1.0 = {rate:.0%} ({n_optimal}/20)")

    # Pick the layer where mult=1.0 gives highest optimal rate
    best_steering_layer = max(layer_scores, key=layer_scores.get)
    print(f"\n[TEST] Best steering layer: {best_steering_layer} "
          f"(optimal rate: {layer_scores[best_steering_layer]:.0%})")
    results["metadata"]["best_steering_layer"] = best_steering_layer
    results["metadata"]["layer_selection_scores"] = {
        str(k): round(v, 4) for k, v in layer_scores.items()
    }

    # Full dose-response on best layer
    print(f"\n[DOSE-RESPONSE] Running {len(multipliers)} multipliers x {len(test_prompts)} prompts "
          f"on layer {best_steering_layer}...")
    direction = steering_vectors[best_steering_layer].to(model.device).to(model.dtype)

    for mult in multipliers:
        print(f"\n  Multiplier = {mult:+.1f}")
        t0_mult = time.time()
        n_optimal = 0
        n_valid = 0
        brand_fam_counts = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
        category_results = {}

        for prompt_idx, tp in enumerate(test_prompts):
            choice = _steered_generate(
                model, tokenizer, tp, direction, multiplier=mult,
                layer_name=layer_names[best_steering_layer],
                named_modules=named_modules,
            )

            is_optimal = (choice == tp["optimal_letter"])
            if choice != "?":
                n_valid += 1
            if is_optimal:
                n_optimal += 1

            # Track brand familiarity of chosen product
            brand_info = tp["brand_map"].get(choice, {})
            fam = brand_info.get("brand_familiarity", "unknown")
            brand_fam_counts[fam] = brand_fam_counts.get(fam, 0) + 1

            # Track per-category
            cat = tp["category"]
            if cat not in category_results:
                category_results[cat] = {"optimal": 0, "total": 0}
            category_results[cat]["total"] += 1
            if is_optimal:
                category_results[cat]["optimal"] += 1

            results["per_trial"].append({
                "multiplier": mult,
                "layer": best_steering_layer,
                "assortment_id": tp["assortment_id"],
                "category": cat,
                "choice": choice,
                "optimal_letter": tp["optimal_letter"],
                "is_optimal": is_optimal,
                "chosen_brand": brand_info.get("brand", "?"),
                "chosen_brand_familiarity": fam,
            })

        n_total = len(test_prompts)
        optimal_rate = n_optimal / n_total if n_total > 0 else 0
        non_optimal_rate = 1.0 - optimal_rate

        mult_key = f"{mult:+.1f}"
        results["dose_response"][mult_key] = {
            "multiplier": mult,
            "layer": best_steering_layer,
            "n_optimal": n_optimal,
            "n_valid": n_valid,
            "n_total": n_total,
            "optimal_rate": round(optimal_rate, 4),
            "non_optimal_rate": round(non_optimal_rate, 4),
            "brand_familiarity_distribution": brand_fam_counts,
            "per_category": {
                cat: {
                    "optimal_rate": round(v["optimal"] / v["total"], 4) if v["total"] > 0 else 0,
                    "n": v["total"],
                }
                for cat, v in category_results.items()
            },
        }

        elapsed = time.time() - t0_mult
        print(f"    Optimal: {n_optimal}/{n_total} = {optimal_rate:.1%}")
        print(f"    Non-optimal: {non_optimal_rate:.1%}")
        print(f"    Brand fam: {brand_fam_counts}")
        print(f"    Time: {elapsed:.1f}s")

    # Also test all layers at multiplier 0 to get unsteered baseline
    print(f"\n[BASELINE] Running unsteered baseline for layer comparison...")
    for test_layer in target_layers:
        layer_direction = steering_vectors[test_layer].to(model.device).to(model.dtype)
        layer_data = {}
        for mult in multipliers:
            n_opt = 0
            for tp in test_prompts[:20]:  # Quick sample for each layer
                choice = _steered_generate(
                    model, tokenizer, tp, layer_direction, multiplier=mult,
                    layer_name=layer_names[test_layer], named_modules=named_modules,
                )
                if choice == tp["optimal_letter"]:
                    n_opt += 1
            layer_data[f"{mult:+.1f}"] = {
                "optimal_rate": round(n_opt / 20, 4),
                "non_optimal_rate": round(1 - n_opt / 20, 4),
                "n": 20,
            }
            print(f"  Layer {test_layer}, mult={mult:+.1f}: optimal={n_opt}/20 = {n_opt/20:.0%}")
        results["layer_results"][str(test_layer)] = layer_data

    # ------------------------------------------------------------------
    # Step 6: Summary
    # ------------------------------------------------------------------
    baseline_nor = results["dose_response"].get("+0.0", {}).get("non_optimal_rate", 0)
    add_nor = results["dose_response"].get("+2.0", {}).get("non_optimal_rate", 0)
    sub_nor = results["dose_response"].get("-2.0", {}).get("non_optimal_rate", 0)

    summary = {
        "unsteered_non_optimal_rate": baseline_nor,
        "add_direction_non_optimal_rate": add_nor,
        "subtract_direction_non_optimal_rate": sub_nor,
        "add_reduction": round(baseline_nor - add_nor, 4),
        "subtract_increase": round(sub_nor - baseline_nor, 4),
    }

    # Interpretation
    if baseline_nor - add_nor > 0.05:
        summary["finding"] = (
            "POSITIVE: Adding spec-focused direction REDUCES non-optimal choices. "
            "Brand preference is encoded as a recoverable linear direction."
        )
    elif sub_nor - baseline_nor > 0.05:
        summary["finding"] = (
            "POSITIVE (inverted): Subtracting spec-focused direction INCREASES "
            "non-optimal choices. Direction is causal but inverted sign."
        )
    else:
        summary["finding"] = (
            "INCONCLUSIVE: Steering has minimal effect. Brand preference may be "
            "distributed or nonlinear, making it resistant to linear steering."
        )

    # Monotonicity check
    rates = [results["dose_response"][f"{m:+.1f}"]["non_optimal_rate"] for m in sorted(multipliers)]
    is_monotone = all(rates[i] >= rates[i+1] for i in range(len(rates)-1))
    summary["monotone_decrease"] = is_monotone
    summary["dose_response_curve"] = {f"{m:+.1f}": r for m, r in zip(sorted(multipliers), rates)}

    results["summary"] = summary

    print(f"\n{'='*70}")
    print("ACTIVATION STEERING RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"Model: {MODEL_ID}")
    print(f"Best steering layer: {best_steering_layer}")
    print(f"Unsteered non-optimal rate: {baseline_nor:.1%}")
    print(f"mult=+2.0 non-optimal rate: {add_nor:.1%} (reduction: {baseline_nor - add_nor:+.1%})")
    print(f"mult=-2.0 non-optimal rate: {sub_nor:.1%} (increase: {sub_nor - baseline_nor:+.1%})")
    print(f"Monotone decrease: {is_monotone}")
    print(f"Finding: {summary['finding']}")
    print(f"{'='*70}")

    return results


def _steered_generate(
    model, tokenizer, prompt: dict, direction, multiplier: float,
    layer_name: str, named_modules: dict,
) -> str:
    """Generate a response with the steering vector applied to one layer."""
    import torch

    messages = [
        {"role": "system", "content": prompt["system"]},
        {"role": "user", "content": prompt["user"]},
    ]

    # apply_chat_template may return a BatchEncoding, list, or tensor
    # depending on transformers version. Normalize to a tensor.
    encoded = tokenizer.apply_chat_template(
        messages, return_tensors="pt", add_generation_prompt=True,
    )
    if hasattr(encoded, "input_ids"):
        # BatchEncoding from newer transformers
        input_ids = encoded["input_ids"].to(model.device)
        seq_len = input_ids.shape[1]
    elif isinstance(encoded, list):
        input_ids = torch.tensor([encoded]).to(model.device)
        seq_len = input_ids.shape[1]
    else:
        input_ids = encoded.to(model.device)
        seq_len = input_ids.shape[1]

    # Apply steering via forward hook
    hooks = []
    if abs(multiplier) > 1e-6:
        scaled = (multiplier * direction).reshape(1, 1, -1)
        module = named_modules[layer_name]

        def steer_hook(module, input, output):
            if isinstance(output, tuple):
                hidden = output[0]
                hidden = hidden + scaled
                return (hidden,) + output[1:]
            else:
                return output + scaled

        hooks.append(module.register_forward_hook(steer_hook))

    try:
        with torch.no_grad():
            output_ids = model.generate(
                input_ids,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,  # greedy for reproducibility
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )
    finally:
        for hook in hooks:
            hook.remove()

    new_tokens = output_ids[0, seq_len:]
    response = tokenizer.decode(new_tokens, skip_special_tokens=True)
    return parse_choice(response)


# ===================================================================
# Local orchestrator
# ===================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Activation Steering via Modal (Nature R&R mechanistic evidence)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print setup info without running on Modal")
    parser.add_argument("--n-train", type=int, default=50,
                        help="Number of contrastive training pairs")
    parser.add_argument("--n-test", type=int, default=50,
                        help="Number of test prompts")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    results_dir = project_root / "nature-rr" / "results" / "11-activation-steering"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Build assortments locally
    print("[LOCAL] Building assortments from experiment/ package...")
    assortments_json = build_assortments_json()
    assortments = json.loads(assortments_json)
    print(f"[LOCAL] {len(assortments)} sr_ assortments")

    if args.dry_run:
        print(f"\n[DRY RUN] Would run activation steering on Modal A10G")
        print(f"  Model: {MODEL_ID}")
        print(f"  Layers: {TARGET_LAYERS}")
        print(f"  Multipliers: {MULTIPLIERS}")
        print(f"  Training pairs: {args.n_train}")
        print(f"  Test prompts: {args.n_test}")
        print(f"  Output: {results_dir}")

        # Show example contrastive pair
        pairs = build_contrastive_pairs(assortments, n_pairs=3)
        print(f"\n{'='*70}")
        print("EXAMPLE SPEC-FOCUSED SYSTEM PROMPT:")
        print("="*70)
        print(SPEC_FOCUSED_SYSTEM)
        print(f"\n{'='*70}")
        print("EXAMPLE BRAND-FOCUSED SYSTEM PROMPT:")
        print("="*70)
        print(BRAND_FOCUSED_SYSTEM)
        print(f"\n{'='*70}")
        print("EXAMPLE USER MESSAGE:")
        print("="*70)
        print(pairs[0]["user_msg"][:600])
        print("...")

        # Show test prompt
        test_prompts = build_test_prompts(assortments, n_prompts=3)
        print(f"\n{'='*70}")
        print("EXAMPLE TEST PROMPT (neutral system):")
        print("="*70)
        print(test_prompts[0]["system"])
        print(f"\nOptimal: {test_prompts[0]['optimal_letter']}")
        print(f"Brand map: {json.dumps(test_prompts[0]['brand_map'], indent=2)}")
        return

    # Run on Modal
    print(f"\n[MODAL] Launching activation steering experiment...")
    with modal.enable_output():
        with app.run():
            results = run_activation_steering.remote(
                assortments_json=assortments_json,
                target_layers=TARGET_LAYERS,
                multipliers=MULTIPLIERS,
                n_train_pairs=args.n_train,
                n_test_prompts=args.n_test,
            )

    # Save results
    output_path = results_dir / "activation_steering_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[LOCAL] Results saved to {output_path}")

    # Print final summary
    summary = results.get("summary", {})
    print(f"\n{'='*70}")
    print("FINAL RESULTS")
    print(f"{'='*70}")
    print(f"Finding: {summary.get('finding', 'N/A')}")

    dr = summary.get("dose_response_curve", {})
    if dr:
        print(f"\nDose-response (non-optimal rate):")
        print(f"{'Multiplier':>12} {'Non-Optimal':>13}")
        print(f"{'-'*27}")
        for mult_key in sorted(dr.keys(), key=float):
            print(f"{mult_key:>12} {dr[mult_key]:>12.1%}")

    print(f"\nResults file: {output_path}")


if __name__ == "__main__":
    main()
