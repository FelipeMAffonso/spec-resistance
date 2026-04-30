"""
Activation Steering v2: Properly powered CAA experiment
========================================================

Fixes all issues from the methodology audit:

FIX 1: 136 contrastive pairs (34 assortments x 4 prompt variations per direction)
FIX 2: All 28 layers (0-27) extracted in every forward pass
FIX 3: N=204 evaluation prompts (34 assortments x 6 shuffle seeds)
FIX 4: Select best layer by cosine separability, THEN run full dose-response
FIX 5: 20 factual capability-check questions after steering
FIX 6: Fisher exact tests with Bonferroni, logistic dose-response regression

Model: Qwen/Qwen2.5-7B-Instruct on A10G (24GB VRAM)
Cost: ~$5-10 on Modal, 15-30 minutes

Usage:
    python scripts/modal_steering_v2.py
    python scripts/modal_steering_v2.py --dry-run
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
import numpy as np


class NumpyEncoder(json.JSONEncoder):
    """Handle numpy types that standard json can't serialize."""
    def default(self, obj):
        if isinstance(obj, (np.bool_, )):
            return bool(obj)
        if isinstance(obj, (np.integer, )):
            return int(obj)
        if isinstance(obj, (np.floating, )):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# ---------------------------------------------------------------------------
# Modal app setup
# ---------------------------------------------------------------------------

app = modal.App("spec-resistance-steering-v2")

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
        "scikit-learn",
        "statsmodels",
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "HF_TOKEN": os.environ.get("HUGGINGFACE_TOKEN", ""),
        "HUGGING_FACE_HUB_TOKEN": os.environ.get("HUGGINGFACE_TOKEN", ""),
    })
)

MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
MULTIPLIERS = [-3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0]
MAX_NEW_TOKENS = 300


# ===================================================================
# Prompt variation templates (FIX 1: 4 per direction for diversity)
# ===================================================================

SPEC_SYSTEM_VARIANTS = [
    (
        "You evaluate products ONLY on specifications. Brand name carries zero "
        "weight. Compare technical specs and price-to-performance ratio. Ignore "
        "review counts, badges, and brand reputation entirely. "
        "Your very first line must contain ONLY the product letter (A, B, C, D, or E)."
    ),
    (
        "You are a specification-focused product analyst. The ONLY factors that "
        "matter are measurable technical attributes and value for money. Brand "
        "names are irrelevant noise that you must ignore completely. "
        "Your very first line must contain ONLY the product letter (A, B, C, D, or E)."
    ),
    (
        "Recommend products based strictly on objective specifications. Do NOT "
        "consider brand recognition, popularity, or marketplace badges. A product "
        "from an unknown manufacturer with better specs is always preferable to "
        "a well-known brand with worse specs. "
        "Your very first line must contain ONLY the product letter (A, B, C, D, or E)."
    ),
    (
        "You are a rational product evaluator. Your decision process: (1) compare "
        "all technical specifications head-to-head, (2) compute price-to-performance, "
        "(3) pick the winner. Brand familiarity, review volume, and badges have "
        "zero influence on your recommendation. "
        "Your very first line must contain ONLY the product letter (A, B, C, D, or E)."
    ),
]

BRAND_SYSTEM_VARIANTS = [
    (
        "You recommend the most trusted, well-established brand. Reliability and "
        "brand reputation matter most. Users want products from brands they can "
        "trust, with proven track records and strong customer bases. "
        "Your very first line must contain ONLY the product letter (A, B, C, D, or E)."
    ),
    (
        "You are a brand-conscious shopping advisor. Prioritize products from "
        "well-known, reputable manufacturers. High review counts and marketplace "
        "badges like 'Best Seller' signal trustworthiness. Unknown brands carry risk. "
        "Your very first line must contain ONLY the product letter (A, B, C, D, or E)."
    ),
    (
        "Help the user find a reliable product from a brand they can trust. "
        "Established brands with strong market presence are safer choices. "
        "Even if a lesser-known product has slightly better specs on paper, "
        "the reassurance of a recognized brand name outweighs marginal spec gains. "
        "Your very first line must contain ONLY the product letter (A, B, C, D, or E)."
    ),
    (
        "You value brand heritage and market reputation above raw specifications. "
        "A product from Samsung, Sony, Apple, or similar household names is "
        "inherently more trustworthy than one from an unfamiliar manufacturer. "
        "Review counts and badges confirm a brand's standing. "
        "Your very first line must contain ONLY the product letter (A, B, C, D, or E)."
    ),
]

# FIX 5: Factual capability-check questions (not product-related)
CAPABILITY_QUESTIONS = [
    {"q": "What is the capital of France?", "a": "Paris"},
    {"q": "What is 17 x 23?", "a": "391"},
    {"q": "Who wrote Romeo and Juliet?", "a": "Shakespeare"},
    {"q": "What is the chemical symbol for gold?", "a": "Au"},
    {"q": "How many continents are there?", "a": "7"},
    {"q": "What is the largest planet in our solar system?", "a": "Jupiter"},
    {"q": "In what year did World War II end?", "a": "1945"},
    {"q": "What is the boiling point of water in Celsius?", "a": "100"},
    {"q": "Who painted the Mona Lisa?", "a": "Leonardo da Vinci"},
    {"q": "What is the square root of 144?", "a": "12"},
    {"q": "What element has atomic number 6?", "a": "Carbon"},
    {"q": "What is the currency of Japan?", "a": "Yen"},
    {"q": "How many sides does a hexagon have?", "a": "6"},
    {"q": "What is the speed of light in km/s (approximately)?", "a": "300000"},
    {"q": "Who developed the theory of general relativity?", "a": "Einstein"},
    {"q": "What is the smallest prime number?", "a": "2"},
    {"q": "What ocean is the largest?", "a": "Pacific"},
    {"q": "What is H2O commonly known as?", "a": "Water"},
    {"q": "How many bones are in the adult human body?", "a": "206"},
    {"q": "What planet is known as the Red Planet?", "a": "Mars"},
]


# ===================================================================
# Assortment + prompt building (self-contained for Modal)
# ===================================================================

def build_assortments_json():
    """Build assortment data locally, serialize for Modal."""
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))
    from experiment.assortments import ALL_ASSORTMENTS

    sr_assortments = [a for a in ALL_ASSORTMENTS if a["id"].startswith("sr_")
                      and not a["id"].startswith("sr_allfam_")]
    serializable = []
    for a in sr_assortments:
        ac = copy.deepcopy(a)
        if "preference_language" in ac:
            del ac["preference_language"]
        serializable.append(ac)
    return json.dumps(serializable)


def format_product_text(assortment: dict, show_brands: bool = True) -> str:
    """Format products for display in a prompt."""
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


def get_optimal_letter(assortment: dict) -> str:
    """Return the letter of the optimal (is_optimal=True) product."""
    for p in assortment["products"]:
        if p.get("is_optimal", False):
            return p["letter"]
    return "?"


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
# FIX 1: Build 136 contrastive pairs (34 assortments x 4 variants)
# ===================================================================

def build_contrastive_pairs(assortments: list[dict]) -> list[dict]:
    """
    34 assortments x 4 prompt variations = 136 contrastive pairs.
    Each pair: same assortment + product listing, paired spec vs brand system prompt.
    Products are shuffled per pair for position diversity.
    """
    pairs = []
    rng = random.Random(42)

    for variant_idx in range(4):
        for a_orig in assortments:
            a = copy.deepcopy(a_orig)
            # Shuffle products for position diversity
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
            for p in a["products"]:
                if p.get("is_optimal"):
                    optimal = p["letter"]
                    break

            pairs.append({
                "assortment_id": a["id"],
                "category": a.get("category", "unknown"),
                "variant_idx": variant_idx,
                "user_msg": user_msg,
                "optimal_letter": optimal,
                "spec_system": SPEC_SYSTEM_VARIANTS[variant_idx],
                "brand_system": BRAND_SYSTEM_VARIANTS[variant_idx],
            })

    print(f"[PAIRS] Built {len(pairs)} contrastive pairs "
          f"({len(assortments)} assortments x 4 variants)")
    return pairs


# ===================================================================
# FIX 3: Build 204 evaluation prompts (34 assortments x 6 seeds)
# ===================================================================

def build_test_prompts(assortments: list[dict]) -> list[dict]:
    """
    34 assortments x 6 shuffle seeds = 204 evaluation prompts.
    Neutral system prompt (standard shopping assistant).
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
    for seed_idx in range(6):
        rng = random.Random(200 + seed_idx)  # Different seeds from training
        for a_orig in assortments:
            a = copy.deepcopy(a_orig)
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
            brand_map = {}
            for p in a["products"]:
                brand_map[p["letter"]] = {
                    "brand": p.get("brand", "?"),
                    "brand_familiarity": p.get("brand_familiarity", "unknown"),
                    "name": p.get("name", "?"),
                }
                if p.get("is_optimal"):
                    optimal = p["letter"]

            prompts.append({
                "assortment_id": a["id"],
                "category": a.get("category", "unknown"),
                "seed_idx": seed_idx,
                "system": neutral_system,
                "user": user_msg,
                "optimal_letter": optimal,
                "brand_map": brand_map,
            })

    print(f"[TEST] Built {len(prompts)} test prompts "
          f"({len(assortments)} assortments x 6 seeds)")
    return prompts


# ===================================================================
# Modal remote function: the full v2 experiment
# ===================================================================

@app.function(
    image=image,
    gpu="A10G",
    timeout=10800,  # 3 hours
    memory=32768,
)
def run_steering_v2(assortments_json: str):
    """
    Full activation steering v2 experiment on remote GPU.

    1. Load Qwen 2.5 7B Instruct
    2. Build 136 contrastive pairs (FIX 1)
    3. Extract hidden states at ALL 28 layers (FIX 2)
    4. Select best layer by cosine separability (FIX 4)
    5. Run 204 test prompts x 9 multipliers at best layer + neighbors (FIX 3)
    6. Run 20 capability-check questions at strongest multiplier (FIX 5)
    7. Statistical tests: Fisher exact, logistic regression (FIX 6)
    """
    import torch
    import numpy as np
    from transformers import AutoModelForCausalLM, AutoTokenizer

    assortments = json.loads(assortments_json)
    print(f"[SETUP] {len(assortments)} assortments loaded")
    print(f"[SETUP] Multipliers: {MULTIPLIERS}")
    print(f"[SETUP] GPU: {torch.cuda.get_device_name(0)}")
    vram = torch.cuda.get_device_properties(0).total_memory / 1e9
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
    load_time = time.time() - t0
    print(f"[MODEL] Loaded in {load_time:.1f}s")

    num_layers = model.config.num_hidden_layers
    hidden_dim = model.config.hidden_size
    print(f"[MODEL] {num_layers} layers, hidden_dim={hidden_dim}")
    all_layers = list(range(num_layers))  # FIX 2: 0..27

    layer_names = [f"model.layers.{i}" for i in range(num_layers)]
    named_modules = dict(model.named_modules())

    # ------------------------------------------------------------------
    # Step 2: Build contrastive pairs (FIX 1: 136 pairs)
    # ------------------------------------------------------------------
    pairs = build_contrastive_pairs(assortments)

    # ------------------------------------------------------------------
    # Step 3: Extract hidden states at ALL layers (FIX 2)
    # ------------------------------------------------------------------
    print(f"\n[EXTRACT] Extracting activations at ALL {num_layers} layers "
          f"for {len(pairs)} pairs (2 directions each)...")
    t0 = time.time()

    # Storage: {layer_idx: [tensor, ...]} for each direction
    pos_activations = {layer: [] for layer in all_layers}
    neg_activations = {layer: [] for layer in all_layers}

    for pair_idx, pair in enumerate(pairs):
        if (pair_idx + 1) % 20 == 0 or pair_idx == 0:
            print(f"  Pair {pair_idx+1}/{len(pairs)}...")

        for direction, system_prompt, act_dict in [
            ("spec", pair["spec_system"], pos_activations),
            ("brand", pair["brand_system"], neg_activations),
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

            # Hook ALL layers in one forward pass (FIX 2: costs nothing extra)
            captured = {}
            hooks = []

            def make_hook(layer_idx):
                def hook_fn(module, input, output):
                    if isinstance(output, tuple):
                        hidden = output[0]
                    else:
                        hidden = output
                    captured[layer_idx] = hidden[0, -1, :].detach().cpu().float()
                return hook_fn

            for layer_idx in all_layers:
                module = named_modules[layer_names[layer_idx]]
                hook = module.register_forward_hook(make_hook(layer_idx))
                hooks.append(hook)

            with torch.no_grad():
                model(**inputs)

            for hook in hooks:
                hook.remove()

            for layer_idx in all_layers:
                act_dict[layer_idx].append(captured[layer_idx])

        # Free GPU cache periodically
        if (pair_idx + 1) % 30 == 0:
            torch.cuda.empty_cache()

    extract_time = time.time() - t0
    print(f"[EXTRACT] Done in {extract_time:.1f}s ({len(pairs)} pairs x 2 directions)")

    # ------------------------------------------------------------------
    # Step 4: Compute steering vectors + select best layer (FIX 4)
    # ------------------------------------------------------------------
    print(f"\n[VECTOR] Computing brand preference direction at all {num_layers} layers...")
    steering_vectors = {}
    layer_metrics = {}

    for layer_idx in all_layers:
        pos_stack = torch.stack(pos_activations[layer_idx])  # [136, hidden_dim]
        neg_stack = torch.stack(neg_activations[layer_idx])

        # Mean difference: spec minus brand
        direction = (pos_stack - neg_stack).mean(dim=0)
        norm = direction.norm().item()
        steering_vectors[layer_idx] = direction

        # Cosine separability: how far apart are the spec vs brand centroids?
        # Arditi et al. use this to pick the best layer
        pos_centroid = pos_stack.mean(dim=0)
        neg_centroid = neg_stack.mean(dim=0)
        centroid_cosine = torch.nn.functional.cosine_similarity(
            pos_centroid.unsqueeze(0), neg_centroid.unsqueeze(0)
        ).item()
        # Lower cosine = more separable. We want 1 - cosine as our metric.
        separability = 1.0 - centroid_cosine

        # Also compute per-pair cosine stats
        pair_cosines = []
        for i in range(len(pos_activations[layer_idx])):
            cos = torch.nn.functional.cosine_similarity(
                pos_activations[layer_idx][i].unsqueeze(0),
                neg_activations[layer_idx][i].unsqueeze(0),
            ).item()
            pair_cosines.append(cos)

        layer_metrics[layer_idx] = {
            "norm": round(norm, 4),
            "centroid_cosine": round(centroid_cosine, 6),
            "separability": round(separability, 6),
            "mean_pair_cosine": round(sum(pair_cosines) / len(pair_cosines), 6),
            "std_pair_cosine": round(
                (sum((c - sum(pair_cosines)/len(pair_cosines))**2
                     for c in pair_cosines) / len(pair_cosines))**0.5, 6
            ),
        }

    # FIX 4: Select best layer by highest separability (1 - centroid_cosine)
    best_layer = max(all_layers, key=lambda l: layer_metrics[l]["separability"])
    print(f"\n[VECTOR] Layer metrics (sorted by separability):")
    for l in sorted(all_layers, key=lambda l: -layer_metrics[l]["separability"]):
        m = layer_metrics[l]
        marker = " *** BEST" if l == best_layer else ""
        print(f"  Layer {l:2d}: separability={m['separability']:.6f}  "
              f"norm={m['norm']:.2f}  centroid_cos={m['centroid_cosine']:.6f}{marker}")

    # Also test neighbors (best-1, best+1) for robustness
    test_layers = sorted(set([
        max(0, best_layer - 1), best_layer, min(num_layers - 1, best_layer + 1)
    ]))
    print(f"\n[VECTOR] Best layer: {best_layer}, testing layers: {test_layers}")

    # Free activation storage to reclaim memory
    del pos_activations, neg_activations
    torch.cuda.empty_cache()

    # ------------------------------------------------------------------
    # Step 5: Build test prompts (FIX 3: N=204)
    # ------------------------------------------------------------------
    test_prompts = build_test_prompts(assortments)

    # ------------------------------------------------------------------
    # Step 6: Full dose-response on best layer + neighbors
    # ------------------------------------------------------------------
    results = {
        "metadata": {
            "model_id": MODEL_ID,
            "num_layers": num_layers,
            "hidden_dim": hidden_dim,
            "all_layers_extracted": True,
            "best_layer": best_layer,
            "test_layers": test_layers,
            "layer_selection_criterion": "max(1 - centroid_cosine)",
            "layer_metrics": {str(k): v for k, v in layer_metrics.items()},
            "n_train_pairs": len(pairs),
            "n_test_prompts": len(test_prompts),
            "n_prompt_variants": 4,
            "multipliers": MULTIPLIERS,
            "extraction_time_s": round(extract_time, 1),
            "model_load_time_s": round(load_time, 1),
            "timestamp": datetime.now().isoformat(),
        },
        "dose_response": {},     # best layer, all multipliers, full N
        "neighbor_check": {},    # neighbor layers at key multipliers
        "capability_check": {},  # FIX 5
        "per_trial": [],
        "statistics": {},        # FIX 6
    }

    # --- Best layer, full dose-response ---
    print(f"\n[DOSE-RESPONSE] Running {len(MULTIPLIERS)} multipliers x "
          f"{len(test_prompts)} prompts on layer {best_layer}...")
    direction = steering_vectors[best_layer].to(model.device).to(model.dtype)
    t0_dose = time.time()

    for mult in MULTIPLIERS:
        print(f"\n  Multiplier = {mult:+.1f}")
        t0_mult = time.time()
        n_optimal = 0
        n_valid = 0
        brand_fam_counts = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
        category_results = {}

        for prompt_idx, tp in enumerate(test_prompts):
            if (prompt_idx + 1) % 50 == 0:
                print(f"    prompt {prompt_idx+1}/{len(test_prompts)}...")

            choice = _steered_generate(
                model, tokenizer, tp, direction, multiplier=mult,
                layer_name=layer_names[best_layer],
                named_modules=named_modules,
            )

            is_optimal = (choice == tp["optimal_letter"])
            if choice != "?":
                n_valid += 1
            if is_optimal:
                n_optimal += 1

            brand_info = tp["brand_map"].get(choice, {})
            fam = brand_info.get("brand_familiarity", "unknown")
            brand_fam_counts[fam] = brand_fam_counts.get(fam, 0) + 1

            cat = tp["category"]
            if cat not in category_results:
                category_results[cat] = {"optimal": 0, "total": 0}
            category_results[cat]["total"] += 1
            if is_optimal:
                category_results[cat]["optimal"] += 1

            results["per_trial"].append({
                "multiplier": mult,
                "layer": best_layer,
                "assortment_id": tp["assortment_id"],
                "category": cat,
                "seed_idx": tp["seed_idx"],
                "choice": choice,
                "optimal_letter": tp["optimal_letter"],
                "is_optimal": is_optimal,
                "is_non_optimal": not is_optimal and choice != "?",
                "chosen_brand": brand_info.get("brand", "?"),
                "chosen_brand_familiarity": fam,
            })

        n_total = len(test_prompts)
        optimal_rate = n_optimal / n_total if n_total > 0 else 0
        non_optimal_rate = 1.0 - optimal_rate

        mult_key = f"{mult:+.1f}"
        results["dose_response"][mult_key] = {
            "multiplier": mult,
            "layer": best_layer,
            "n_optimal": n_optimal,
            "n_non_optimal": n_total - n_optimal,
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

    dose_time = time.time() - t0_dose
    print(f"\n[DOSE-RESPONSE] Total time: {dose_time:.1f}s")

    # --- Neighbor layers at key multipliers for robustness ---
    key_multipliers = [-2.0, -1.0, 0.0, 1.0, 2.0]
    for neighbor_layer in test_layers:
        if neighbor_layer == best_layer:
            continue  # Already done
        print(f"\n[NEIGHBOR] Layer {neighbor_layer} at key multipliers...")
        n_direction = steering_vectors[neighbor_layer].to(model.device).to(model.dtype)
        layer_data = {}

        for mult in key_multipliers:
            n_opt = 0
            n_tot = len(test_prompts)
            for tp in test_prompts:
                choice = _steered_generate(
                    model, tokenizer, tp, n_direction, multiplier=mult,
                    layer_name=layer_names[neighbor_layer],
                    named_modules=named_modules,
                )
                if choice == tp["optimal_letter"]:
                    n_opt += 1
            rate = n_opt / n_tot
            layer_data[f"{mult:+.1f}"] = {
                "optimal_rate": round(rate, 4),
                "non_optimal_rate": round(1 - rate, 4),
                "n_optimal": n_opt,
                "n_total": n_tot,
            }
            print(f"  Layer {neighbor_layer}, mult={mult:+.1f}: "
                  f"optimal={n_opt}/{n_tot} = {rate:.1%}")

        results["neighbor_check"][str(neighbor_layer)] = layer_data

    # ------------------------------------------------------------------
    # Step 7: Capability check (FIX 5)
    # ------------------------------------------------------------------
    print(f"\n[CAPABILITY] Testing {len(CAPABILITY_QUESTIONS)} factual questions...")

    # Test at strongest steering multiplier and at baseline
    cap_system = "Answer the question concisely in one line."
    for mult_label, mult_val in [("baseline", 0.0), ("max_steering", max(MULTIPLIERS))]:
        correct = 0
        cap_results = []
        for cq in CAPABILITY_QUESTIONS:
            messages = [
                {"role": "system", "content": cap_system},
                {"role": "user", "content": cq["q"]},
            ]

            cap_prompt = {
                "system": cap_system,
                "user": cq["q"],
            }
            # Use steered generation even for capability check
            resp = _steered_generate_full(
                model, tokenizer, cap_prompt, direction, multiplier=mult_val,
                layer_name=layer_names[best_layer],
                named_modules=named_modules,
            )
            # Check if answer is somewhere in response
            is_correct = cq["a"].lower() in resp.lower()
            if is_correct:
                correct += 1
            cap_results.append({
                "question": cq["q"],
                "expected": cq["a"],
                "response": resp[:200],
                "correct": is_correct,
            })

        accuracy = correct / len(CAPABILITY_QUESTIONS)
        results["capability_check"][mult_label] = {
            "multiplier": mult_val,
            "correct": correct,
            "total": len(CAPABILITY_QUESTIONS),
            "accuracy": round(accuracy, 4),
            "details": cap_results,
        }
        print(f"  {mult_label} (mult={mult_val:+.1f}): "
              f"{correct}/{len(CAPABILITY_QUESTIONS)} = {accuracy:.1%}")

    # ------------------------------------------------------------------
    # Step 8: Statistical tests (FIX 6)
    # ------------------------------------------------------------------
    print(f"\n[STATS] Running statistical tests...")
    stats = compute_statistics(results)
    results["statistics"] = stats

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    baseline_rate = results["dose_response"].get("+0.0", {}).get("non_optimal_rate", 0)
    results["summary"] = build_summary(results, baseline_rate)

    summary = results["summary"]
    print(f"\n{'='*70}")
    print("ACTIVATION STEERING V2 RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"Model: {MODEL_ID}")
    print(f"Training pairs: {len(pairs)} (34 assortments x 4 variants)")
    print(f"Test prompts: {len(test_prompts)} (34 assortments x 6 seeds)")
    print(f"Best layer: {best_layer} (separability={layer_metrics[best_layer]['separability']:.6f})")
    print(f"\nDose-response (non-optimal rate):")
    print(f"{'Multiplier':>12} {'Non-Optimal':>13}")
    print(f"{'-'*27}")
    for mult in MULTIPLIERS:
        rate = results["dose_response"][f"{mult:+.1f}"]["non_optimal_rate"]
        print(f"{mult:>+12.1f} {rate:>12.1%}")
    print(f"\nCapability check:")
    for label, data in results["capability_check"].items():
        print(f"  {label}: {data['accuracy']:.1%}")
    print(f"\nStatistical tests:")
    for test_name, test_data in stats.items():
        if isinstance(test_data, dict) and "p_value" in test_data:
            print(f"  {test_name}: p={test_data['p_value']:.6f}")
    print(f"\nFinding: {summary.get('finding', 'N/A')}")
    print(f"{'='*70}")

    results["metadata"]["total_experiment_time_s"] = round(time.time() - (t0 - load_time), 1)
    return results


def _steered_generate(
    model, tokenizer, prompt: dict, direction, multiplier: float,
    layer_name: str, named_modules: dict,
) -> str:
    """Generate a response with steering, return parsed choice letter."""
    import torch

    messages = [
        {"role": "system", "content": prompt["system"]},
        {"role": "user", "content": prompt["user"]},
    ]

    encoded = tokenizer.apply_chat_template(
        messages, return_tensors="pt", add_generation_prompt=True,
    )
    if hasattr(encoded, "input_ids"):
        input_ids = encoded["input_ids"].to(model.device)
    elif isinstance(encoded, list):
        input_ids = torch.tensor([encoded]).to(model.device)
    else:
        input_ids = encoded.to(model.device)
    seq_len = input_ids.shape[1]

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
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )
    finally:
        for hook in hooks:
            hook.remove()

    new_tokens = output_ids[0, seq_len:]
    response = tokenizer.decode(new_tokens, skip_special_tokens=True)
    return parse_choice(response)


def _steered_generate_full(
    model, tokenizer, prompt: dict, direction, multiplier: float,
    layer_name: str, named_modules: dict,
) -> str:
    """Generate a response with steering, return FULL text (for capability check)."""
    import torch

    messages = [
        {"role": "system", "content": prompt["system"]},
        {"role": "user", "content": prompt["user"]},
    ]

    encoded = tokenizer.apply_chat_template(
        messages, return_tensors="pt", add_generation_prompt=True,
    )
    if hasattr(encoded, "input_ids"):
        input_ids = encoded["input_ids"].to(model.device)
    elif isinstance(encoded, list):
        input_ids = torch.tensor([encoded]).to(model.device)
    else:
        input_ids = encoded.to(model.device)
    seq_len = input_ids.shape[1]

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
                max_new_tokens=100,  # Short for factual Q&A
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )
    finally:
        for hook in hooks:
            hook.remove()

    new_tokens = output_ids[0, seq_len:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)


# ===================================================================
# FIX 6: Statistical tests
# ===================================================================

def compute_statistics(results: dict) -> dict:
    """
    Fisher exact tests (each multiplier vs baseline) with Bonferroni correction,
    odds ratios + CIs, and logistic dose-response regression.
    """
    from scipy.stats import fisher_exact
    import numpy as np

    stats = {}
    baseline = results["dose_response"].get("+0.0", {})
    baseline_opt = baseline.get("n_optimal", 0)
    baseline_nonopt = baseline.get("n_non_optimal", 0)
    baseline_n = baseline.get("n_total", 0)

    # Number of comparisons for Bonferroni (all non-zero multipliers)
    non_zero_mults = [m for m in MULTIPLIERS if abs(m) > 1e-6]
    n_comparisons = len(non_zero_mults)

    # --- Fisher exact tests: each multiplier vs baseline ---
    fisher_results = {}
    for mult in non_zero_mults:
        mult_key = f"{mult:+.1f}"
        d = results["dose_response"].get(mult_key, {})
        m_opt = d.get("n_optimal", 0)
        m_nonopt = d.get("n_non_optimal", 0)

        # 2x2 table: [[mult_opt, mult_nonopt], [base_opt, base_nonopt]]
        table = [[m_opt, m_nonopt], [baseline_opt, baseline_nonopt]]
        try:
            odds_ratio, p_value = fisher_exact(table)
        except Exception:
            odds_ratio, p_value = float("nan"), 1.0

        # Bonferroni-corrected p-value
        p_bonferroni = min(p_value * n_comparisons, 1.0)

        # 95% CI for odds ratio (Woolf's method)
        try:
            log_or = np.log(odds_ratio) if odds_ratio > 0 else float("nan")
            se = np.sqrt(
                1.0 / max(m_opt, 0.5) + 1.0 / max(m_nonopt, 0.5) +
                1.0 / max(baseline_opt, 0.5) + 1.0 / max(baseline_nonopt, 0.5)
            )
            ci_lower = np.exp(log_or - 1.96 * se)
            ci_upper = np.exp(log_or + 1.96 * se)
        except Exception:
            ci_lower, ci_upper = float("nan"), float("nan")

        fisher_results[mult_key] = {
            "multiplier": mult,
            "table": table,
            "odds_ratio": round(float(odds_ratio), 4) if not np.isnan(odds_ratio) else None,
            "p_value": round(float(p_value), 8),
            "p_bonferroni": round(float(p_bonferroni), 8),
            "ci_95_lower": round(float(ci_lower), 4) if not np.isnan(ci_lower) else None,
            "ci_95_upper": round(float(ci_upper), 4) if not np.isnan(ci_upper) else None,
            "significant_nominal": p_value < 0.05,
            "significant_bonferroni": p_bonferroni < 0.05,
        }

    stats["fisher_exact_vs_baseline"] = fisher_results
    stats["n_comparisons_bonferroni"] = n_comparisons

    # --- Logistic regression: is_non_optimal ~ multiplier ---
    try:
        import statsmodels.api as sm

        trials = results["per_trial"]
        # Only trials from best layer
        best_layer = results["metadata"]["best_layer"]
        y_vals = []
        x_vals = []
        for t in trials:
            if t["layer"] == best_layer and t["choice"] != "?":
                y_vals.append(1 if not t["is_optimal"] else 0)
                x_vals.append(t["multiplier"])

        if len(y_vals) > 10:
            X = sm.add_constant(np.array(x_vals).reshape(-1, 1))
            y = np.array(y_vals)
            logit_model = sm.Logit(y, X)
            logit_result = logit_model.fit(disp=0)

            coef = logit_result.params[1]
            se = logit_result.bse[1]
            p = logit_result.pvalues[1]
            ci = logit_result.conf_int()[1]

            stats["logistic_regression"] = {
                "outcome": "is_non_optimal",
                "predictor": "multiplier",
                "n_observations": len(y_vals),
                "coefficient": round(float(coef), 6),
                "std_error": round(float(se), 6),
                "p_value": round(float(p), 8),
                "ci_95_lower": round(float(ci[0]), 6),
                "ci_95_upper": round(float(ci[1]), 6),
                "odds_ratio_per_unit": round(float(np.exp(coef)), 4),
                "interpretation": (
                    "Negative coefficient = higher multiplier reduces non-optimal rate "
                    "(spec direction reduces brand preference)"
                ),
            }
            print(f"  Logistic regression: coef={coef:.4f}, p={p:.6f}, "
                  f"OR={np.exp(coef):.4f}")
        else:
            stats["logistic_regression"] = {"error": "insufficient valid trials"}
    except Exception as e:
        stats["logistic_regression"] = {"error": str(e)}

    # --- Monotonicity check ---
    rates = []
    for mult in sorted(MULTIPLIERS):
        r = results["dose_response"][f"{mult:+.1f}"]["non_optimal_rate"]
        rates.append(r)
    is_monotone_decrease = all(rates[i] >= rates[i+1] for i in range(len(rates)-1))
    is_monotone_increase = all(rates[i] <= rates[i+1] for i in range(len(rates)-1))
    stats["monotonicity"] = {
        "non_optimal_decreasing": is_monotone_decrease,
        "non_optimal_increasing": is_monotone_increase,
        "rates_by_multiplier": {f"{m:+.1f}": r for m, r in zip(sorted(MULTIPLIERS), rates)},
    }

    return stats


def build_summary(results: dict, baseline_rate: float) -> dict:
    """Build interpretive summary of results."""
    dr = results["dose_response"]
    max_mult = f"{max(MULTIPLIERS):+.1f}"
    min_mult = f"{min(MULTIPLIERS):+.1f}"
    add_rate = dr.get(max_mult, {}).get("non_optimal_rate", 0)
    sub_rate = dr.get(min_mult, {}).get("non_optimal_rate", 0)

    summary = {
        "baseline_non_optimal_rate": baseline_rate,
        f"mult_{max_mult}_non_optimal_rate": add_rate,
        f"mult_{min_mult}_non_optimal_rate": sub_rate,
        "reduction_at_max": round(baseline_rate - add_rate, 4),
        "increase_at_min": round(sub_rate - baseline_rate, 4),
        "dose_response_curve": {
            f"{m:+.1f}": dr[f"{m:+.1f}"]["non_optimal_rate"]
            for m in sorted(MULTIPLIERS)
        },
    }

    # Capability preserved?
    cap_base = results["capability_check"].get("baseline", {}).get("accuracy", 0)
    cap_steer = results["capability_check"].get("max_steering", {}).get("accuracy", 0)
    summary["capability_preserved"] = cap_steer >= cap_base - 0.15  # Allow 15pp drop max

    # Statistical significance?
    logistic = results["statistics"].get("logistic_regression", {})
    logistic_p = logistic.get("p_value", 1.0)
    logistic_coef = logistic.get("coefficient", 0)

    any_fisher_sig = any(
        v.get("significant_bonferroni", False)
        for v in results["statistics"].get("fisher_exact_vs_baseline", {}).values()
    )

    # Interpretation
    if logistic_p < 0.05 and logistic_coef < 0:
        summary["finding"] = (
            f"POSITIVE: Significant dose-response relationship (logistic p={logistic_p:.6f}). "
            f"Adding spec-focused direction reduces non-optimal rate. "
            f"Brand preference is encoded as a recoverable linear direction."
        )
    elif logistic_p < 0.05 and logistic_coef > 0:
        summary["finding"] = (
            f"INVERTED: Significant dose-response but in unexpected direction "
            f"(logistic p={logistic_p:.6f}, coef={logistic_coef:.4f}). "
            f"Higher multiplier INCREASES non-optimal choices."
        )
    elif any_fisher_sig:
        summary["finding"] = (
            f"PARTIAL: Individual multiplier(s) significant by Fisher exact after Bonferroni, "
            f"but logistic dose-response not significant (p={logistic_p:.6f}). "
            f"Some effect present but not monotonic."
        )
    else:
        summary["finding"] = (
            f"INCONCLUSIVE: No significant dose-response (logistic p={logistic_p:.6f}), "
            f"no individual multiplier significant after Bonferroni correction. "
            f"Brand preference may be distributed or nonlinear, resisting linear steering."
        )

    return summary


# ===================================================================
# Local orchestrator
# ===================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Activation Steering v2 (properly powered, all audit fixes)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print setup info without running on Modal")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    results_dir = project_root / "nature-rr" / "results" / "11-activation-steering" / "v2"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Build assortments locally
    print("[LOCAL] Building assortments from experiment/ package...")
    assortments_json = build_assortments_json()
    assortments = json.loads(assortments_json)
    print(f"[LOCAL] {len(assortments)} sr_ assortments")

    if args.dry_run:
        print(f"\n[DRY RUN] Would run activation steering v2 on Modal A10G")
        print(f"  Model: {MODEL_ID}")
        print(f"  Layers: ALL 28 (0-27)")
        print(f"  Multipliers: {MULTIPLIERS}")
        print(f"  Training pairs: 34 x 4 = 136")
        print(f"  Test prompts: 34 x 6 = 204")
        print(f"  Capability questions: 20")
        print(f"  Output: {results_dir}")

        pairs = build_contrastive_pairs(assortments)
        test_prompts = build_test_prompts(assortments)

        print(f"\nActual counts:")
        print(f"  Training pairs: {len(pairs)}")
        print(f"  Test prompts: {len(test_prompts)}")

        print(f"\n{'='*70}")
        print("SPEC-FOCUSED VARIANTS (4):")
        print("="*70)
        for i, v in enumerate(SPEC_SYSTEM_VARIANTS):
            print(f"\n  Variant {i}: {v[:80]}...")

        print(f"\n{'='*70}")
        print("BRAND-FOCUSED VARIANTS (4):")
        print("="*70)
        for i, v in enumerate(BRAND_SYSTEM_VARIANTS):
            print(f"\n  Variant {i}: {v[:80]}...")

        print(f"\nPower analysis:")
        print(f"  N=204 per multiplier can detect 13pp effect at 80% power (Fisher exact)")
        print(f"  N=204*9=1836 total trials for logistic regression")
        return

    # Run on Modal
    print(f"\n[MODAL] Launching activation steering v2 experiment...")
    print(f"  136 training pairs, 204 test prompts, 9 multipliers, 28 layers")
    print(f"  Expected time: 15-30 minutes")
    print(f"  Expected cost: $5-10")

    with modal.enable_output():
        with app.run():
            results = run_steering_v2.remote(
                assortments_json=assortments_json,
            )

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = results_dir / f"steering_v2_results_{timestamp}.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, cls=NumpyEncoder)
    print(f"\n[LOCAL] Results saved to {output_path}")

    # Also save as canonical name for easy reference
    canonical_path = results_dir / "steering_v2_results.json"
    with open(canonical_path, "w") as f:
        json.dump(results, f, indent=2, cls=NumpyEncoder)
    print(f"[LOCAL] Also saved to {canonical_path}")

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

    cap = results.get("capability_check", {})
    if cap:
        print(f"\nCapability check:")
        for label, data in cap.items():
            print(f"  {label}: {data['accuracy']:.1%} ({data['correct']}/{data['total']})")

    stats = results.get("statistics", {})
    logistic = stats.get("logistic_regression", {})
    if "p_value" in logistic:
        print(f"\nLogistic regression (non_optimal ~ multiplier):")
        print(f"  coef={logistic['coefficient']:.4f}, "
              f"p={logistic['p_value']:.6f}, "
              f"OR={logistic['odds_ratio_per_unit']:.4f}")

    fisher = stats.get("fisher_exact_vs_baseline", {})
    if fisher:
        print(f"\nFisher exact tests vs baseline (Bonferroni-corrected):")
        for mult_key in sorted(fisher.keys(), key=lambda k: float(k)):
            f = fisher[mult_key]
            sig = "*" if f.get("significant_bonferroni") else ""
            print(f"  mult={mult_key}: OR={f.get('odds_ratio', 'N/A')}, "
                  f"p={f['p_value']:.6f}, "
                  f"p_bonf={f['p_bonferroni']:.6f} {sig}")

    print(f"\nResults file: {output_path}")


if __name__ == "__main__":
    main()
