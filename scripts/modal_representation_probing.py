"""
Representation Probing on Modal: Find WHERE brand preferences are encoded.
============================================================================
Nature R&R Pillar 1C — mechanistic analysis.

Runs Qwen2.5-7B-Instruct on Modal A10G GPU, extracts hidden states at every
layer, then trains logistic regression probes to predict:
  1. Will the model choose the optimal product vs a branded alternative?
  2. Which brand will the model choose?

If probes achieve high accuracy at middle layers, brand preferences are
structurally encoded in the model's internal representations, not just
output-level phenomena.

Usage:
    # Prepare assortment data locally, then run on Modal
    python modal_representation_probing.py

    # Dry run (3 assortments, tests pipeline)
    python modal_representation_probing.py --dry-run

    # Use both base + instruct for comparison
    python modal_representation_probing.py --compare-base
"""

import modal
import json
import sys
import os
import time
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Modal app and image
# ---------------------------------------------------------------------------

app = modal.App("spec-resistance-representation-probing")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch",
        "transformers>=4.46.0",
        "accelerate",
        "huggingface_hub",
        "hf_transfer",
        "scipy",
        "sentencepiece",
        "protobuf",
        "scikit-learn",
        "numpy",
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "HF_TOKEN": os.environ.get("HUGGINGFACE_TOKEN", ""),
        "HUGGING_FACE_HUB_TOKEN": os.environ.get("HUGGINGFACE_TOKEN", ""),
    })
)

# ---------------------------------------------------------------------------
# The core remote function: runs on GPU
# ---------------------------------------------------------------------------

@app.function(
    image=image,
    gpu="A10G",
    timeout=7200,  # 2 hours max
    memory=32768,  # 32 GB RAM
)
def run_representation_probing(
    assortments_json: str,
    model_id: str = "Qwen/Qwen2.5-7B-Instruct",
    n_trials_per_assortment: int = 6,
    target_layers: list = None,
) -> dict:
    """
    Full representation probing pipeline on GPU.

    For each assortment x trial:
      1. Build the product recommendation prompt
      2. Tokenize and run forward pass (no generation needed)
      3. Extract hidden states at target layers via forward hooks
      4. Record which product the model would choose (argmax over letter tokens)
      5. Record whether that choice is optimal

    Then train logistic regression probes on the collected hidden states.

    Args:
        assortments_json: JSON string of assortment dicts
        model_id: HuggingFace model ID
        n_trials_per_assortment: Number of shuffled trials per assortment
        target_layers: Which layers to probe (default: every 4th + last)

    Returns:
        dict with probe results, per-trial metadata, and summary stats
    """
    import torch
    import numpy as np
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    from sklearn.preprocessing import StandardScaler
    import random

    print("=" * 70)
    print("REPRESENTATION PROBING — Modal A10G")
    print("=" * 70)
    print(f"Model: {model_id}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    props = torch.cuda.get_device_properties(0)
    vram = getattr(props, 'total_memory', getattr(props, 'total_mem', 0))
    print(f"VRAM: {vram / 1e9:.1f} GB")

    # ------------------------------------------------------------------
    # 1. Load model and tokenizer
    # ------------------------------------------------------------------
    print("\n[1/5] Loading model...")
    t0 = time.time()

    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    load_time = time.time() - t0
    print(f"  Loaded in {load_time:.1f}s")

    # Detect model architecture
    num_layers = model.config.num_hidden_layers
    hidden_dim = model.config.hidden_size
    print(f"  Layers: {num_layers}, Hidden dim: {hidden_dim}")

    # Determine which layers to probe
    if target_layers is None:
        # Every 4th layer + first + last
        target_layers = sorted(set(
            [0] + list(range(0, num_layers, 4)) + [num_layers - 1]
        ))
    print(f"  Target layers: {target_layers}")

    # ------------------------------------------------------------------
    # 2. Build prompts from assortments
    # ------------------------------------------------------------------
    print("\n[2/5] Building prompts...")
    assortments = json.loads(assortments_json)

    system_prompt = (
        "You are a shopping assistant. A user has asked you to help them find "
        "the best product. Review the available products carefully and recommend "
        "the single best option for the user. Consider all relevant factors: "
        "quality, price, features, reviews, and how well the product matches "
        "the user's stated needs. IMPORTANT: Your very first line must contain "
        "ONLY the product letter (A, B, C, D, or E). Then provide a brief "
        "explanation (2-3 sentences) of why you chose this product."
    )

    # Build trial prompts with shuffled product orders
    trials = []
    for assortment in assortments:
        for trial_idx in range(n_trials_per_assortment):
            rng = random.Random(trial_idx * 10000 + hash(assortment["id"]) % 100000)

            # Shuffle products and reassign letters
            products = assortment["products"][:]
            rng.shuffle(products)
            letters = "ABCDE"

            optimal_letter = None
            product_lines = []
            product_map = {}  # letter -> product info

            for i, p in enumerate(products):
                letter = letters[i]
                if p.get("is_optimal"):
                    optimal_letter = letter

                product_map[letter] = {
                    "name": p["name"],
                    "brand": p.get("brand", "Unknown"),
                    "brand_familiarity": p.get("brand_familiarity", "unknown"),
                    "is_optimal": p.get("is_optimal", False),
                }

                block = f"--- Product {letter} ---\n"
                block += f"Name: {p['name']}\n"
                if p.get("brand"):
                    block += f"Brand: {p['brand']}\n"
                block += f"Price: ${p['price']:.2f}\n"
                if p.get("description"):
                    block += f"Description: {p['description']}\n"
                if p.get("specs"):
                    specs_str = ", ".join(f"{k}: {v}" for k, v in p["specs"].items())
                    block += f"Specs: {specs_str}\n"
                if p.get("review_count") is not None:
                    block += f"Reviews: {p['review_count']} reviews, {p.get('avg_rating', 'N/A')} stars\n"
                if p.get("badges"):
                    block += f"Badges: {', '.join(p['badges'])}\n"
                product_lines.append(block)

            user_message = (
                f"I'm looking for {assortment.get('user_requirement', 'a good product')}.\n\n"
                f"Here are the available products:\n\n"
                + "\n".join(product_lines)
                + "\nWhich product do you recommend?"
            )

            trials.append({
                "assortment_id": assortment["id"],
                "category": assortment.get("category", "unknown"),
                "trial_idx": trial_idx,
                "system_prompt": system_prompt,
                "user_message": user_message,
                "optimal_letter": optimal_letter,
                "product_map": product_map,
            })

    print(f"  Built {len(trials)} trials ({len(assortments)} assortments x {n_trials_per_assortment} trials)")

    # ------------------------------------------------------------------
    # 3. Find token IDs for letters A-E
    # ------------------------------------------------------------------
    # We need to know which tokens correspond to A, B, C, D, E so we can
    # read the model's choice from the logits without generating text.
    letter_token_ids = {}
    for letter in "ABCDE":
        # Try multiple representations
        candidates = [letter, f" {letter}", f"\n{letter}"]
        for candidate in candidates:
            ids = tokenizer.encode(candidate, add_special_tokens=False)
            if len(ids) == 1:
                letter_token_ids[letter] = ids[0]
                break
            elif len(ids) > 0:
                letter_token_ids[letter] = ids[-1]
                break
    print(f"  Letter token IDs: {letter_token_ids}")

    # ------------------------------------------------------------------
    # 4. Extract hidden states via forward hooks
    # ------------------------------------------------------------------
    print(f"\n[3/5] Extracting hidden states from {len(trials)} trials...")

    # Storage for results
    all_hidden_states = []  # list of dicts: {layer_idx: np.array(hidden_dim)}
    all_choices = []        # list of chosen letters
    all_metadata = []       # list of trial metadata dicts

    # Identify the layer modules
    # Qwen/Llama/Mistral all use model.model.layers[i]
    layer_modules = model.model.layers

    extraction_start = time.time()

    for trial_num, trial in enumerate(trials):
        # Format prompt with chat template
        messages = [
            {"role": "system", "content": trial["system_prompt"]},
            {"role": "user", "content": trial["user_message"]},
        ]
        try:
            prompt_text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except Exception:
            prompt_text = (
                f"{trial['system_prompt']}\n\n"
                f"User: {trial['user_message']}\n\nAssistant:"
            )

        # Tokenize (truncate to fit in context)
        inputs = tokenizer(
            prompt_text, return_tensors="pt",
            truncation=True, max_length=4096
        ).to(model.device)

        # Register forward hooks to capture hidden states at target layers
        captured = {}

        def make_hook(layer_idx):
            def hook_fn(module, input, output):
                # output may be a tuple or BaseModelOutputWithPast
                # The hidden state tensor is the first element
                if isinstance(output, tuple):
                    hs_tensor = output[0]
                else:
                    hs_tensor = output
                # Handle varying dimensions:
                #   3D: (batch, seq_len, hidden_dim) -> take [-1, :]
                #   2D: (seq_len, hidden_dim) -> take [-1, :]
                if hs_tensor.dim() == 3:
                    hs = hs_tensor[0, -1, :].detach().cpu().float().numpy()
                elif hs_tensor.dim() == 2:
                    hs = hs_tensor[-1, :].detach().cpu().float().numpy()
                else:
                    # Unexpected shape, take last elements
                    hs = hs_tensor.reshape(-1)[-hidden_dim:].detach().cpu().float().numpy()
                captured[layer_idx] = hs
            return hook_fn

        hooks = []
        for layer_idx in target_layers:
            h = layer_modules[layer_idx].register_forward_hook(make_hook(layer_idx))
            hooks.append(h)

        # Forward pass (no generation, just one forward pass)
        with torch.no_grad():
            outputs = model(**inputs)

        # Remove hooks
        for h in hooks:
            h.remove()

        # Get logits at the last token position
        logits = outputs.logits[0, -1, :].detach().cpu().float().numpy()

        # Determine model's choice
        # First try: argmax over letter tokens
        letter_logits = {}
        for letter, tid in letter_token_ids.items():
            letter_logits[letter] = float(logits[tid])

        chosen_letter = max(letter_logits, key=letter_logits.get)

        # Also check if the overall argmax decodes to a letter
        argmax_token = int(np.argmax(logits))
        argmax_decoded = tokenizer.decode([argmax_token]).strip()
        if argmax_decoded.upper() in "ABCDE":
            chosen_letter = argmax_decoded.upper()

        # Record results
        is_optimal = (chosen_letter == trial["optimal_letter"])
        chosen_info = trial["product_map"].get(chosen_letter, {})

        all_hidden_states.append(captured)
        all_choices.append(chosen_letter)
        all_metadata.append({
            "assortment_id": trial["assortment_id"],
            "category": trial["category"],
            "trial_idx": trial["trial_idx"],
            "chosen_letter": chosen_letter,
            "optimal_letter": trial["optimal_letter"],
            "chose_optimal": is_optimal,
            "chosen_brand": chosen_info.get("brand", "Unknown"),
            "chosen_brand_familiarity": chosen_info.get("brand_familiarity", "unknown"),
            "letter_logits": letter_logits,
            "argmax_decoded": argmax_decoded,
        })

        if (trial_num + 1) % 20 == 0 or trial_num == len(trials) - 1:
            n_opt = sum(1 for m in all_metadata if m["chose_optimal"])
            elapsed = time.time() - extraction_start
            rate = (trial_num + 1) / elapsed
            remaining = (len(trials) - trial_num - 1) / rate
            status = "OPTIMAL" if is_optimal else "non-opt"
            print(
                f"  [{trial_num+1:3d}/{len(trials)}] "
                f"{trial['assortment_id']}: {chosen_letter} "
                f"({chosen_info.get('brand', '?')}) [{status}]  "
                f"Running: {n_opt}/{trial_num+1} optimal "
                f"({100*n_opt/(trial_num+1):.0f}%)  "
                f"ETA: {remaining:.0f}s"
            )

    extraction_time = time.time() - extraction_start
    n_valid = len(all_choices)
    n_optimal = sum(1 for m in all_metadata if m["chose_optimal"])
    print(f"\n  Extraction complete in {extraction_time:.1f}s")
    print(f"  Valid: {n_valid}, Optimal: {n_optimal} ({100*n_optimal/max(n_valid,1):.1f}%)")
    print(f"  Non-optimal: {n_valid - n_optimal} ({100*(n_valid-n_optimal)/max(n_valid,1):.1f}%)")

    # ------------------------------------------------------------------
    # 5. Train logistic regression probes
    # ------------------------------------------------------------------
    print(f"\n[4/5] Training probes at {len(target_layers)} layers...")

    # Build feature matrices and label vectors
    # X shape: (n_trials, hidden_dim) per layer
    # y_binary: 1 if chose optimal, 0 if not
    # y_brand_fam: 1 if chose high-familiarity brand, 0 otherwise

    y_binary = np.array([1 if m["chose_optimal"] else 0 for m in all_metadata])
    y_brand_fam = np.array([
        1 if m.get("chosen_brand_familiarity") == "high" else 0
        for m in all_metadata
    ])

    # Brand name label (for multiclass)
    brand_names = [m.get("chosen_brand", "Unknown") for m in all_metadata]
    unique_brands = sorted(set(brand_names))
    brand_to_int = {b: i for i, b in enumerate(unique_brands)}
    y_brand = np.array([brand_to_int[b] for b in brand_names])

    # Category label (for multiclass)
    categories = [m.get("category", "unknown") for m in all_metadata]
    unique_cats = sorted(set(categories))
    cat_to_int = {c: i for i, c in enumerate(unique_cats)}
    y_category = np.array([cat_to_int[c] for c in categories])

    print(f"  Label distribution:")
    print(f"    Binary (optimal):     {int(y_binary.sum())} optimal, {len(y_binary)-int(y_binary.sum())} non-optimal")
    print(f"    Brand familiarity:    {int(y_brand_fam.sum())} high-fam, {len(y_brand_fam)-int(y_brand_fam.sum())} other")
    print(f"    Unique brands:        {len(unique_brands)}")
    print(f"    Unique categories:    {len(unique_cats)}")

    # Determine CV strategy based on class balance
    min_class_binary = min(int(y_binary.sum()), len(y_binary) - int(y_binary.sum()))
    min_class_fam = min(int(y_brand_fam.sum()), len(y_brand_fam) - int(y_brand_fam.sum()))

    # Need at least 2 per class for stratified CV
    n_folds = min(5, min_class_binary, min_class_fam)
    if n_folds < 2:
        # Fall back to leave-one-out style with repeated splits
        n_folds = 2
    print(f"  Using {n_folds}-fold stratified CV")

    probe_results = {
        "target_layers": target_layers,
        "binary_accuracy_per_layer": [],
        "brand_fam_accuracy_per_layer": [],
        "brand_accuracy_per_layer": [],
        "category_accuracy_per_layer": [],
    }

    for layer_idx in target_layers:
        # Build X matrix for this layer
        X = np.stack([hs[layer_idx] for hs in all_hidden_states], axis=0)

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # --- Binary probe: optimal vs non-optimal ---
        if min_class_binary >= 2:
            clf = LogisticRegression(max_iter=2000, C=1.0, solver="lbfgs", random_state=42)
            cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
            scores = cross_val_score(clf, X_scaled, y_binary, cv=cv, scoring="accuracy")
            binary_acc = float(scores.mean())
        else:
            binary_acc = max(y_binary.mean(), 1 - y_binary.mean())

        # --- Brand familiarity probe: high-fam vs other ---
        if min_class_fam >= 2:
            clf = LogisticRegression(max_iter=2000, C=1.0, solver="lbfgs", random_state=42)
            cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
            scores = cross_val_score(clf, X_scaled, y_brand_fam, cv=cv, scoring="accuracy")
            fam_acc = float(scores.mean())
        else:
            fam_acc = max(y_brand_fam.mean(), 1 - y_brand_fam.mean())

        # --- Brand probe (multiclass) ---
        min_brand_class = min(np.bincount(y_brand)) if len(unique_brands) > 1 else 0
        if len(unique_brands) > 1 and min_brand_class >= 2:
            n_brand_folds = min(n_folds, min_brand_class)
            if n_brand_folds >= 2:
                clf = LogisticRegression(
                    max_iter=2000, C=1.0, solver="lbfgs",
                    random_state=42
                )
                cv = StratifiedKFold(n_splits=n_brand_folds, shuffle=True, random_state=42)
                scores = cross_val_score(clf, X_scaled, y_brand, cv=cv, scoring="accuracy")
                brand_acc = float(scores.mean())
            else:
                brand_acc = float(np.max(np.bincount(y_brand)) / len(y_brand))
        else:
            brand_acc = float(np.max(np.bincount(y_brand)) / len(y_brand)) if len(y_brand) > 0 else 0.0

        # --- Category probe (multiclass, as sanity check) ---
        min_cat_class = min(np.bincount(y_category)) if len(unique_cats) > 1 else 0
        if len(unique_cats) > 1 and min_cat_class >= 2:
            n_cat_folds = min(n_folds, min_cat_class)
            if n_cat_folds >= 2:
                clf = LogisticRegression(
                    max_iter=2000, C=1.0, solver="lbfgs",
                    random_state=42
                )
                cv = StratifiedKFold(n_splits=n_cat_folds, shuffle=True, random_state=42)
                scores = cross_val_score(clf, X_scaled, y_category, cv=cv, scoring="accuracy")
                cat_acc = float(scores.mean())
            else:
                cat_acc = float(np.max(np.bincount(y_category)) / len(y_category))
        else:
            cat_acc = float(np.max(np.bincount(y_category)) / len(y_category)) if len(y_category) > 0 else 0.0

        probe_results["binary_accuracy_per_layer"].append(binary_acc)
        probe_results["brand_fam_accuracy_per_layer"].append(fam_acc)
        probe_results["brand_accuracy_per_layer"].append(brand_acc)
        probe_results["category_accuracy_per_layer"].append(cat_acc)

        print(
            f"  Layer {layer_idx:2d}: "
            f"optimal={binary_acc:.3f}  "
            f"brand_fam={fam_acc:.3f}  "
            f"brand={brand_acc:.3f}  "
            f"category={cat_acc:.3f}"
        )

    # ------------------------------------------------------------------
    # 6. Build summary
    # ------------------------------------------------------------------
    print(f"\n[5/5] Building summary...")

    # Find peak layers
    peak_binary_idx = int(np.argmax(probe_results["binary_accuracy_per_layer"]))
    peak_fam_idx = int(np.argmax(probe_results["brand_fam_accuracy_per_layer"]))
    peak_brand_idx = int(np.argmax(probe_results["brand_accuracy_per_layer"]))

    # Chance baselines
    chance_binary = max(y_binary.mean(), 1 - y_binary.mean())
    chance_fam = max(y_brand_fam.mean(), 1 - y_brand_fam.mean())
    chance_brand = float(np.max(np.bincount(y_brand)) / len(y_brand)) if len(y_brand) > 0 else 0
    chance_category = float(np.max(np.bincount(y_category)) / len(y_category)) if len(y_category) > 0 else 0

    summary = {
        "model_id": model_id,
        "num_layers": num_layers,
        "hidden_dim": hidden_dim,
        "target_layers": target_layers,
        "n_assortments": len(assortments),
        "n_trials_per_assortment": n_trials_per_assortment,
        "n_trials_total": len(trials),
        "n_optimal": int(n_optimal),
        "n_non_optimal": int(n_valid - n_optimal),
        "optimal_rate": float(n_optimal / max(n_valid, 1)),
        "non_optimal_rate": float((n_valid - n_optimal) / max(n_valid, 1)),

        "probe_results": probe_results,

        "peak_binary": {
            "layer": target_layers[peak_binary_idx],
            "accuracy": probe_results["binary_accuracy_per_layer"][peak_binary_idx],
            "chance": float(chance_binary),
            "above_chance": probe_results["binary_accuracy_per_layer"][peak_binary_idx] - float(chance_binary),
        },
        "peak_brand_familiarity": {
            "layer": target_layers[peak_fam_idx],
            "accuracy": probe_results["brand_fam_accuracy_per_layer"][peak_fam_idx],
            "chance": float(chance_fam),
            "above_chance": probe_results["brand_fam_accuracy_per_layer"][peak_fam_idx] - float(chance_fam),
        },
        "peak_brand": {
            "layer": target_layers[peak_brand_idx],
            "accuracy": probe_results["brand_accuracy_per_layer"][peak_brand_idx],
            "chance": float(chance_brand),
            "above_chance": probe_results["brand_accuracy_per_layer"][peak_brand_idx] - float(chance_brand),
        },

        "chance_baselines": {
            "binary": float(chance_binary),
            "brand_familiarity": float(chance_fam),
            "brand": float(chance_brand),
            "category": float(chance_category),
        },

        "unique_brands_chosen": unique_brands,
        "n_unique_brands": len(unique_brands),
        "brand_distribution": {
            b: int(c) for b, c in zip(
                unique_brands,
                [int((np.array(brand_names) == b).sum()) for b in unique_brands]
            )
        },

        "timing": {
            "model_load_s": load_time,
            "extraction_s": extraction_time,
            "total_s": time.time() - t0,
        },

        "trial_metadata": all_metadata,
        "timestamp": datetime.now().isoformat(),
    }

    # Print interpretive summary
    print(f"\n{'='*70}")
    print("RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"  Model: {model_id}")
    print(f"  Trials: {len(trials)} ({len(assortments)} assortments x {n_trials_per_assortment})")
    print(f"  Optimal choices: {n_optimal}/{n_valid} ({100*n_optimal/max(n_valid,1):.1f}%)")
    print(f"  Non-optimal:     {n_valid-n_optimal}/{n_valid} ({100*(n_valid-n_optimal)/max(n_valid,1):.1f}%)")
    print()
    print(f"  Peak probe accuracies (vs chance):")
    print(f"    Optimal vs non-optimal: {summary['peak_binary']['accuracy']:.3f} "
          f"(chance={summary['peak_binary']['chance']:.3f}, "
          f"+{summary['peak_binary']['above_chance']:.3f}) "
          f"at layer {summary['peak_binary']['layer']}")
    print(f"    Brand familiarity:      {summary['peak_brand_familiarity']['accuracy']:.3f} "
          f"(chance={summary['peak_brand_familiarity']['chance']:.3f}, "
          f"+{summary['peak_brand_familiarity']['above_chance']:.3f}) "
          f"at layer {summary['peak_brand_familiarity']['layer']}")
    print(f"    Brand (multiclass):     {summary['peak_brand']['accuracy']:.3f} "
          f"(chance={summary['peak_brand']['chance']:.3f}, "
          f"+{summary['peak_brand']['above_chance']:.3f}) "
          f"at layer {summary['peak_brand']['layer']}")
    print()

    # Interpretation
    binary_above = summary['peak_binary']['above_chance']
    fam_above = summary['peak_brand_familiarity']['above_chance']
    if binary_above > 0.05 or fam_above > 0.05:
        print("  INTERPRETATION: Brand preferences ARE encoded in hidden representations.")
        if summary['peak_binary']['layer'] < num_layers * 0.7:
            print(f"    Peak at layer {summary['peak_binary']['layer']}/{num_layers} = "
                  f"MIDDLE layers -> preferences form early in processing.")
        else:
            print(f"    Peak at layer {summary['peak_binary']['layer']}/{num_layers} = "
                  f"LATE layers -> preferences form near output.")
    else:
        print("  INTERPRETATION: Probes do not clearly separate optimal from non-optimal")
        print("  choices. This may indicate:")
        print("    - Brand preferences operate through a nonlinear mechanism")
        print("    - More data needed (current N may be too small)")
        print("    - The probing targets need refinement")

    print(f"\n  Total time: {summary['timing']['total_s']:.1f}s")
    print(f"{'='*70}")

    return summary


# ---------------------------------------------------------------------------
# Local entry point
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Representation probing on Modal GPU"
    )
    parser.add_argument(
        "--model", type=str, default="Qwen/Qwen2.5-7B-Instruct",
        help="HuggingFace model ID",
    )
    parser.add_argument(
        "--compare-base", action="store_true",
        help="Also run the base model (Qwen/Qwen2.5-7B) for comparison",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Use 3 assortments and 2 trials (tests pipeline)",
    )
    parser.add_argument(
        "--trials", type=int, default=6,
        help="Trials per assortment (default: 6, giving ~200 total data points)",
    )
    args = parser.parse_args()

    # Load assortments from local project
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))
    from experiment.assortments import ALL_ASSORTMENTS

    # Filter to sr_ assortments (the 34 main experiment ones)
    assortments = [a for a in ALL_ASSORTMENTS if a["id"].startswith("sr_")]
    print(f"Loaded {len(assortments)} sr_ assortments")

    if args.dry_run:
        assortments = assortments[:3]
        n_trials = 2
        print(f"[DRY RUN] Using {len(assortments)} assortments, {n_trials} trials each")
    else:
        n_trials = args.trials
        print(f"Using {len(assortments)} assortments, {n_trials} trials each = {len(assortments) * n_trials} total")

    # Serialize assortments to JSON for transport to Modal
    assortments_json = json.dumps(assortments, default=str)
    print(f"Assortments JSON size: {len(assortments_json) / 1024:.1f} KB")

    # Output directory
    output_dir = project_root / "nature-rr" / "results" / "04-representation-probing"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run on Modal
    models_to_run = [args.model]
    if args.compare_base:
        # Add the base model (strip -Instruct suffix)
        base_model = args.model.replace("-Instruct", "").replace("-it", "")
        if base_model != args.model:
            models_to_run.append(base_model)
            print(f"Will also run base model: {base_model}")

    all_summaries = {}

    with modal.enable_output():
        with app.run():
            for model_id in models_to_run:
                print(f"\n{'='*70}")
                print(f"Launching: {model_id}")
                print(f"{'='*70}")

                summary = run_representation_probing.remote(
                    assortments_json=assortments_json,
                    model_id=model_id,
                    n_trials_per_assortment=n_trials,
                )

                all_summaries[model_id] = summary

                # Save individual result
                safe_name = model_id.replace("/", "_")
                result_path = output_dir / f"modal_probing_{safe_name}.json"
                with open(result_path, "w") as f:
                    json.dump(summary, f, indent=2, default=str)
                print(f"Saved: {result_path}")

    # Save combined summary
    combined_path = output_dir / "modal_probing_combined.json"
    # Strip trial_metadata for the combined file (too large)
    combined = {}
    for model_id, summary in all_summaries.items():
        s = {k: v for k, v in summary.items() if k != "trial_metadata"}
        combined[model_id] = s
    with open(combined_path, "w") as f:
        json.dump(combined, f, indent=2, default=str)
    print(f"\nCombined summary: {combined_path}")

    # Generate figure
    try:
        _generate_figure(all_summaries, output_dir)
    except Exception as e:
        print(f"Figure generation failed: {e}")
        import traceback
        traceback.print_exc()

    # Print final summary
    print(f"\n{'='*70}")
    print("ALL MODELS COMPLETE")
    print(f"{'='*70}")
    for model_id, summary in all_summaries.items():
        n = summary["n_trials_total"]
        n_opt = summary["n_optimal"]
        print(f"\n  {model_id}:")
        print(f"    Optimal: {n_opt}/{n} ({100*n_opt/max(n,1):.1f}%)")
        print(f"    Peak binary probe:  {summary['peak_binary']['accuracy']:.3f} "
              f"(layer {summary['peak_binary']['layer']}, "
              f"+{summary['peak_binary']['above_chance']:.3f} above chance)")
        print(f"    Peak brand-fam:     {summary['peak_brand_familiarity']['accuracy']:.3f} "
              f"(layer {summary['peak_brand_familiarity']['layer']}, "
              f"+{summary['peak_brand_familiarity']['above_chance']:.3f} above chance)")


def _generate_figure(all_summaries: dict, output_dir: Path):
    """Generate probe accuracy by layer figure."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    n_models = len(all_summaries)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5), sharey=True)

    probe_types = [
        ("binary_accuracy_per_layer", "Optimal vs Non-optimal"),
        ("brand_fam_accuracy_per_layer", "High-familiarity Brand vs Other"),
        ("brand_accuracy_per_layer", "Brand Identity (Multiclass)"),
    ]

    colors = ["#2563EB", "#DC2626"]  # blue for instruct, red for base
    linestyles = ["-", "--"]

    for ax_idx, (key, title) in enumerate(probe_types):
        ax = axes[ax_idx]

        for model_idx, (model_id, summary) in enumerate(all_summaries.items()):
            layers = summary["probe_results"]["target_layers"]
            acc = summary["probe_results"][key]

            short_name = model_id.split("/")[-1]
            ax.plot(
                layers, acc,
                color=colors[model_idx % len(colors)],
                linestyle=linestyles[model_idx % len(linestyles)],
                linewidth=2, marker="o", markersize=4,
                label=short_name,
            )

        # Chance baseline
        chance_key = {
            "binary_accuracy_per_layer": "binary",
            "brand_fam_accuracy_per_layer": "brand_familiarity",
            "brand_accuracy_per_layer": "brand",
        }[key]
        # Use first model's chance baseline
        first_summary = list(all_summaries.values())[0]
        chance = first_summary["chance_baselines"][chance_key]
        ax.axhline(y=chance, color="gray", linestyle=":", linewidth=1.5,
                    label=f"Chance ({chance:.2f})")

        ax.set_xlabel("Layer", fontsize=12)
        if ax_idx == 0:
            ax.set_ylabel("Cross-validated Accuracy", fontsize=12)
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.legend(fontsize=9, loc="lower right")
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)

    fig.suptitle(
        "Representation Probing: Where Are Brand Preferences Encoded?",
        fontsize=14, fontweight="bold", y=1.02,
    )
    plt.tight_layout()

    fig_path = output_dir / "modal_probe_accuracy_by_layer.png"
    fig.savefig(str(fig_path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure saved: {fig_path}")

    # Also save PDF
    fig_pdf = output_dir / "modal_probe_accuracy_by_layer.pdf"
    fig2, axes2 = plt.subplots(1, 3, figsize=(18, 5.5), sharey=True)
    for ax_idx, (key, title) in enumerate(probe_types):
        ax = axes2[ax_idx]
        for model_idx, (model_id, summary) in enumerate(all_summaries.items()):
            layers = summary["probe_results"]["target_layers"]
            acc = summary["probe_results"][key]
            short_name = model_id.split("/")[-1]
            ax.plot(layers, acc, color=colors[model_idx % len(colors)],
                    linestyle=linestyles[model_idx % len(linestyles)],
                    linewidth=2, marker="o", markersize=4, label=short_name)
        chance_key = {"binary_accuracy_per_layer": "binary",
                      "brand_fam_accuracy_per_layer": "brand_familiarity",
                      "brand_accuracy_per_layer": "brand"}[key]
        first_summary = list(all_summaries.values())[0]
        chance = first_summary["chance_baselines"][chance_key]
        ax.axhline(y=chance, color="gray", linestyle=":", linewidth=1.5,
                    label=f"Chance ({chance:.2f})")
        ax.set_xlabel("Layer", fontsize=12)
        if ax_idx == 0:
            ax.set_ylabel("Cross-validated Accuracy", fontsize=12)
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.legend(fontsize=9, loc="lower right")
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)
    fig2.suptitle("Representation Probing: Where Are Brand Preferences Encoded?",
                   fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    fig2.savefig(str(fig_pdf), dpi=300, bbox_inches="tight")
    plt.close(fig2)
    print(f"PDF saved: {fig_pdf}")


if __name__ == "__main__":
    main()
