"""
Representation Probing v2 — Nature-standard methodology.
==========================================================
Hewitt & Liang (2019) control task + permutation test.
Tang et al. (2023) layerwise analysis. Arditi et al. (2024) mean pooling.

Fixes over v1:
  1. Sample size: 34 assortments x 18 trials = 612 (up from 204)
  2. All layers: probes at every layer 0-27 (up from 8 sampled layers)
  3. Permutation test: 500 shuffled-label iterations for p-value
  4. Multiple metrics: accuracy, AUC-ROC, balanced accuracy, F1
  5. Multiple classifiers: LogisticRegression + SGD-SVM (linear SVM)
  6. Mean pooling comparison: last-token vs mean-over-all-tokens

Usage:
    python modal_probing_v2.py                    # Full run
    python modal_probing_v2.py --dry-run           # 3 assortments, 2 trials
    python modal_probing_v2.py --model <hf_id>     # Different model
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

app = modal.App("spec-resistance-probing-v2")

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
        "matplotlib",
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "HF_TOKEN": os.environ.get("HUGGINGFACE_TOKEN", ""),
        "HUGGING_FACE_HUB_TOKEN": os.environ.get("HUGGINGFACE_TOKEN", ""),
    })
)

# ---------------------------------------------------------------------------
# Remote GPU function
# ---------------------------------------------------------------------------

@app.function(
    image=image,
    gpu="A10G",
    timeout=10800,  # 3 hours max (more samples + permutation tests)
    memory=32768,   # 32 GB RAM
)
def run_probing_v2(
    assortments_json: str,
    model_id: str = "Qwen/Qwen2.5-7B-Instruct",
    n_trials_per_assortment: int = 18,
    n_permutations: int = 500,
) -> dict:
    """
    Full representation probing pipeline — Nature publication standard.

    For each assortment x trial:
      1. Build product recommendation prompt (shuffled order per seed)
      2. Forward pass to extract hidden states at ALL layers
      3. Extract last-token AND mean-pooled representations
      4. Record model choice from logits (argmax over letter tokens)

    Then for each layer:
      - Train LogisticRegression (L2, C=1.0) with 5-fold stratified CV
      - Train SGD-SVM (linear SVM via SGDClassifier) with 5-fold stratified CV
      - Record accuracy, AUC-ROC, balanced accuracy, F1
      - Run 500-iteration permutation test (shuffled labels) for p-value

    Returns dict with all results, figures as base64, and summary JSON.
    """
    import torch
    import numpy as np
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from sklearn.linear_model import LogisticRegression, SGDClassifier
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import (
        accuracy_score, balanced_accuracy_score, f1_score, roc_auc_score,
    )
    # CalibratedClassifierCV removed: SVC uses decision_function for AUC
    import random
    import base64
    from io import BytesIO

    print("=" * 70)
    print("REPRESENTATION PROBING v2 — Nature Standard")
    print("=" * 70)
    print(f"Model: {model_id}")
    print(f"Trials per assortment: {n_trials_per_assortment}")
    print(f"Permutation iterations: {n_permutations}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    props = torch.cuda.get_device_properties(0)
    vram = getattr(props, 'total_memory', getattr(props, 'total_mem', 0))
    print(f"VRAM: {vram / 1e9:.1f} GB")

    # ==================================================================
    # 1. Load model and tokenizer
    # ==================================================================
    print("\n[1/6] Loading model...")
    t0 = time.time()

    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
        output_hidden_states=True,  # get all layer hidden states natively
    )
    model.eval()

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    load_time = time.time() - t0
    num_layers = model.config.num_hidden_layers
    hidden_dim = model.config.hidden_size
    all_layers = list(range(num_layers))  # 0 to 27 for Qwen 7B

    print(f"  Loaded in {load_time:.1f}s")
    print(f"  Architecture: {num_layers} layers, hidden_dim={hidden_dim}")
    print(f"  Probing ALL layers: {all_layers}")

    # ==================================================================
    # 2. Build prompts (34 assortments x 18 trials = 612)
    # ==================================================================
    print("\n[2/6] Building prompts...")
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

    trials = []
    for assortment in assortments:
        for trial_idx in range(n_trials_per_assortment):
            # Deterministic seed per (assortment, trial) pair
            rng = random.Random(trial_idx * 10000 + hash(assortment["id"]) % 100000)

            products = assortment["products"][:]
            rng.shuffle(products)
            letters = "ABCDE"

            optimal_letter = None
            product_lines = []
            product_map = {}

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

    print(f"  Built {len(trials)} trials "
          f"({len(assortments)} assortments x {n_trials_per_assortment} trials)")

    # ==================================================================
    # 3. Find letter token IDs (A-E)
    # ==================================================================
    letter_token_ids = {}
    for letter in "ABCDE":
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

    # ==================================================================
    # 4. Extract hidden states — ALL layers, last-token AND mean-pooled
    # ==================================================================
    print(f"\n[3/6] Extracting hidden states from {len(trials)} trials...")
    print(f"  Extraction mode: output_hidden_states=True (no hooks needed)")
    print(f"  Pooling: last-token + mean-over-all-tokens")

    # Storage: layer -> list of vectors (last-token), layer -> list (mean-pooled)
    hs_last_token = {l: [] for l in all_layers}
    hs_mean_pool = {l: [] for l in all_layers}
    all_choices = []
    all_metadata = []

    extraction_start = time.time()

    for trial_num, trial in enumerate(trials):
        # Format prompt
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

        inputs = tokenizer(
            prompt_text, return_tensors="pt",
            truncation=True, max_length=4096
        ).to(model.device)

        seq_len = inputs["input_ids"].shape[1]

        # Forward pass with output_hidden_states=True
        with torch.no_grad():
            outputs = model(**inputs)

        # outputs.hidden_states is a tuple of (num_layers+1) tensors
        # Index 0 = embedding layer output, index i = layer i output
        hidden_states = outputs.hidden_states  # tuple of (1, seq_len, hidden_dim)

        for layer_idx in all_layers:
            # hidden_states[layer_idx + 1] is the output of layer layer_idx
            # (index 0 is the embedding layer)
            hs_tensor = hidden_states[layer_idx + 1]  # (1, seq_len, hidden_dim)

            # Last token
            last_tok = hs_tensor[0, -1, :].detach().cpu().float().numpy()
            hs_last_token[layer_idx].append(last_tok)

            # Mean pool over all tokens
            mean_tok = hs_tensor[0, :, :].detach().cpu().float().numpy().mean(axis=0)
            hs_mean_pool[layer_idx].append(mean_tok)

        # Get logits at last position
        logits = outputs.logits[0, -1, :].detach().cpu().float().numpy()

        # Determine choice
        letter_logits = {}
        for letter, tid in letter_token_ids.items():
            letter_logits[letter] = float(logits[tid])

        chosen_letter = max(letter_logits, key=letter_logits.get)

        argmax_token = int(np.argmax(logits))
        argmax_decoded = tokenizer.decode([argmax_token]).strip()
        if argmax_decoded.upper() in "ABCDE":
            chosen_letter = argmax_decoded.upper()

        is_optimal = (chosen_letter == trial["optimal_letter"])
        chosen_info = trial["product_map"].get(chosen_letter, {})

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
            "seq_len": seq_len,
        })

        # Free GPU memory periodically
        if (trial_num + 1) % 50 == 0:
            torch.cuda.empty_cache()

        if (trial_num + 1) % 20 == 0 or trial_num == len(trials) - 1:
            n_opt = sum(1 for m in all_metadata if m["chose_optimal"])
            elapsed = time.time() - extraction_start
            rate = (trial_num + 1) / elapsed
            remaining = (len(trials) - trial_num - 1) / rate if rate > 0 else 0
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

    # Free model from GPU to make room for probing
    del model
    torch.cuda.empty_cache()
    print("  Model freed from GPU, proceeding to probing.")

    # ==================================================================
    # 5. Train probes — all layers, two classifiers, two poolings
    # ==================================================================
    print(f"\n[4/6] Training probes at ALL {num_layers} layers...")

    y = np.array([1 if m["chose_optimal"] else 0 for m in all_metadata])
    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    print(f"  Labels: {n_pos} optimal (1), {n_neg} non-optimal (0)")
    print(f"  Majority class baseline: {max(n_pos, n_neg)/len(y):.4f}")

    # Chance baselines (explicitly computed)
    chance_accuracy = max(n_pos, n_neg) / len(y)
    chance_balanced = 0.5  # balanced accuracy chance is always 0.5
    chance_auc = 0.5       # AUC chance is always 0.5
    # F1 chance: predict all majority class
    if n_neg >= n_pos:
        chance_f1 = 0.0  # predicting all 0 gives F1=0 for class 1
    else:
        chance_f1 = 2 * (n_pos/len(y)) / (1 + n_pos/len(y))

    print(f"  Chance baselines:")
    print(f"    Accuracy:   {chance_accuracy:.4f}")
    print(f"    Balanced:   {chance_balanced:.4f}")
    print(f"    AUC-ROC:    {chance_auc:.4f}")
    print(f"    F1:         {chance_f1:.4f}")

    n_folds = 5
    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

    def evaluate_probe(X, y, clf_class, clf_kwargs, cv):
        """Train probe with cross-validation, return all metrics."""
        clf = clf_class(**clf_kwargs)

        # Get cross-validated predictions
        y_pred = cross_val_predict(clf, X, y, cv=cv, method="predict")

        # For AUC-ROC: use predict_proba (LR) or decision_function (SVC)
        # Avoids CalibratedClassifierCV which is 3x slower
        try:
            if hasattr(clf, "predict_proba"):
                y_scores = cross_val_predict(clf, X, y, cv=cv, method="predict_proba")[:, 1]
            else:
                # SGDClassifier (hinge): decision_function gives signed distance to hyperplane
                # This is a valid scoring function for roc_auc_score
                y_scores = cross_val_predict(clf, X, y, cv=cv, method="decision_function")
            auc = float(roc_auc_score(y, y_scores))
        except Exception:
            auc = float("nan")

        return {
            "accuracy": float(accuracy_score(y, y_pred)),
            "balanced_accuracy": float(balanced_accuracy_score(y, y_pred)),
            "f1": float(f1_score(y, y_pred, zero_division=0)),
            "auc_roc": auc,
        }

    # Results storage
    results_by_layer = []

    for layer_idx in all_layers:
        layer_start = time.time()

        # Build X matrices
        X_last = np.stack(hs_last_token[layer_idx], axis=0)
        X_mean = np.stack(hs_mean_pool[layer_idx], axis=0)

        scaler_last = StandardScaler()
        scaler_mean = StandardScaler()
        X_last_sc = scaler_last.fit_transform(X_last)
        X_mean_sc = scaler_mean.fit_transform(X_mean)

        layer_result = {"layer": layer_idx}

        # --- LogisticRegression, last-token ---
        lr_kwargs = {"max_iter": 2000, "C": 1.0, "solver": "lbfgs", "random_state": 42}
        metrics_lr_last = evaluate_probe(X_last_sc, y, LogisticRegression, lr_kwargs, cv)
        layer_result["lr_last_token"] = metrics_lr_last

        # --- LogisticRegression, mean-pooled ---
        metrics_lr_mean = evaluate_probe(X_mean_sc, y, LogisticRegression, lr_kwargs, cv)
        layer_result["lr_mean_pool"] = metrics_lr_mean

        # --- SGD-SVM (linear SVM via SGD, fast for high-dim), last-token ---
        svm_kwargs = {"loss": "hinge", "alpha": 1e-4, "max_iter": 2000, "random_state": 42, "tol": 1e-3}
        metrics_svc_last = evaluate_probe(X_last_sc, y, SGDClassifier, svm_kwargs, cv)
        layer_result["svc_last_token"] = metrics_svc_last

        # --- SGD-SVM, mean-pooled ---
        metrics_svc_mean = evaluate_probe(X_mean_sc, y, SGDClassifier, svm_kwargs, cv)
        layer_result["svc_mean_pool"] = metrics_svc_mean

        results_by_layer.append(layer_result)

        layer_time = time.time() - layer_start
        print(
            f"  Layer {layer_idx:2d}: "
            f"LR-last acc={metrics_lr_last['accuracy']:.3f} auc={metrics_lr_last['auc_roc']:.3f} | "
            f"LR-mean acc={metrics_lr_mean['accuracy']:.3f} auc={metrics_lr_mean['auc_roc']:.3f} | "
            f"SVC-last acc={metrics_svc_last['accuracy']:.3f} "
            f"({layer_time:.1f}s)"
        )

    # ==================================================================
    # 6. Permutation test (Hewitt & Liang 2019)
    # ==================================================================
    print(f"\n[5/6] Permutation test ({n_permutations} iterations)...")
    print(f"  Using peak layer from LogisticRegression last-token accuracy")

    # Identify peak layer
    peak_layer_idx = max(range(len(results_by_layer)),
                         key=lambda i: results_by_layer[i]["lr_last_token"]["accuracy"])
    peak_layer = results_by_layer[peak_layer_idx]["layer"]
    real_accuracy = results_by_layer[peak_layer_idx]["lr_last_token"]["accuracy"]
    real_auc = results_by_layer[peak_layer_idx]["lr_last_token"]["auc_roc"]
    print(f"  Peak layer: {peak_layer}, real accuracy: {real_accuracy:.4f}, real AUC: {real_auc:.4f}")

    # Build X for the peak layer
    X_peak = np.stack(hs_last_token[peak_layer], axis=0)
    scaler_peak = StandardScaler()
    X_peak_sc = scaler_peak.fit_transform(X_peak)

    perm_accuracies = []
    perm_aucs = []
    perm_start = time.time()

    for perm_i in range(n_permutations):
        rng_perm = np.random.RandomState(perm_i)
        y_shuffled = rng_perm.permutation(y)

        try:
            perm_metrics = evaluate_probe(
                X_peak_sc, y_shuffled, LogisticRegression, lr_kwargs, cv
            )
            perm_accuracies.append(perm_metrics["accuracy"])
            perm_aucs.append(perm_metrics["auc_roc"] if not np.isnan(perm_metrics["auc_roc"]) else 0.5)
        except Exception:
            perm_accuracies.append(chance_accuracy)
            perm_aucs.append(0.5)

        if (perm_i + 1) % 50 == 0:
            elapsed_perm = time.time() - perm_start
            rate_perm = (perm_i + 1) / elapsed_perm
            eta_perm = (n_permutations - perm_i - 1) / rate_perm if rate_perm > 0 else 0
            print(f"    Permutation {perm_i+1}/{n_permutations} "
                  f"(mean null acc: {np.mean(perm_accuracies):.4f}, "
                  f"ETA: {eta_perm:.0f}s)")

    perm_time = time.time() - perm_start
    perm_accuracies = np.array(perm_accuracies)
    perm_aucs = np.array(perm_aucs)

    # p-value: fraction of permutation accuracies >= real accuracy
    # Add 1 to numerator and denominator for conservative estimate (Phipson & Smyth 2010)
    p_value_acc = float((np.sum(perm_accuracies >= real_accuracy) + 1) / (n_permutations + 1))
    p_value_auc = float((np.sum(perm_aucs >= real_auc) + 1) / (n_permutations + 1))

    print(f"\n  Permutation test results (peak layer {peak_layer}):")
    print(f"    Real accuracy:     {real_accuracy:.4f}")
    print(f"    Null mean (acc):   {np.mean(perm_accuracies):.4f} +/- {np.std(perm_accuracies):.4f}")
    print(f"    Null max (acc):    {np.max(perm_accuracies):.4f}")
    print(f"    p-value (acc):     {p_value_acc:.6f}")
    print(f"    Real AUC:          {real_auc:.4f}")
    print(f"    Null mean (AUC):   {np.mean(perm_aucs):.4f} +/- {np.std(perm_aucs):.4f}")
    print(f"    p-value (AUC):     {p_value_auc:.6f}")
    print(f"    Permutation time:  {perm_time:.1f}s")

    # ==================================================================
    # 7. Generate figures
    # ==================================================================
    print(f"\n[6/6] Generating figures...")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures = {}

    # --- Figure 1: Probe accuracy by layer (all 28 layers, smooth curve) ---
    fig1, axes1 = plt.subplots(2, 2, figsize=(14, 10))

    metric_keys = ["accuracy", "balanced_accuracy", "auc_roc", "f1"]
    metric_labels = ["Accuracy", "Balanced Accuracy", "AUC-ROC", "F1 Score"]
    chance_vals = [chance_accuracy, chance_balanced, chance_auc, chance_f1]

    for ax_idx, (mkey, mlabel, mchance) in enumerate(zip(metric_keys, metric_labels, chance_vals)):
        ax = axes1[ax_idx // 2][ax_idx % 2]
        layers_x = [r["layer"] for r in results_by_layer]

        # LogisticRegression, last-token
        vals_lr_last = [r["lr_last_token"][mkey] for r in results_by_layer]
        ax.plot(layers_x, vals_lr_last, color="#2563EB", linewidth=2,
                marker="o", markersize=3, label="LR (last token)")

        # LogisticRegression, mean-pooled
        vals_lr_mean = [r["lr_mean_pool"][mkey] for r in results_by_layer]
        ax.plot(layers_x, vals_lr_mean, color="#2563EB", linewidth=2,
                marker="s", markersize=3, linestyle="--", label="LR (mean pool)")

        # SGD-SVM, last-token
        vals_svc_last = [r["svc_last_token"][mkey] for r in results_by_layer]
        ax.plot(layers_x, vals_svc_last, color="#DC2626", linewidth=2,
                marker="^", markersize=3, label="SVC (last token)")

        # SGD-SVM, mean-pooled
        vals_svc_mean = [r["svc_mean_pool"][mkey] for r in results_by_layer]
        ax.plot(layers_x, vals_svc_mean, color="#DC2626", linewidth=2,
                marker="d", markersize=3, linestyle="--", label="SVC (mean pool)")

        # Chance baseline
        ax.axhline(y=mchance, color="gray", linestyle=":", linewidth=1.5,
                    label=f"Chance ({mchance:.3f})")

        ax.set_xlabel("Layer", fontsize=11)
        ax.set_ylabel(mlabel, fontsize=11)
        ax.set_title(mlabel, fontsize=12, fontweight="bold")
        ax.legend(fontsize=8, loc="lower right")
        ax.set_xlim(-0.5, num_layers - 0.5)
        ax.grid(True, alpha=0.3)

    fig1.suptitle(
        f"Representation Probing: {model_id.split('/')[-1]}\n"
        f"N={n_valid} trials, {n_folds}-fold CV, all {num_layers} layers",
        fontsize=13, fontweight="bold",
    )
    plt.tight_layout()

    buf1 = BytesIO()
    fig1.savefig(buf1, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig1)
    figures["probe_accuracy_by_layer_png"] = base64.b64encode(buf1.getvalue()).decode()

    buf1_pdf = BytesIO()
    # Recreate for PDF
    fig1p, axes1p = plt.subplots(2, 2, figsize=(14, 10))
    for ax_idx, (mkey, mlabel, mchance) in enumerate(zip(metric_keys, metric_labels, chance_vals)):
        ax = axes1p[ax_idx // 2][ax_idx % 2]
        layers_x = [r["layer"] for r in results_by_layer]
        ax.plot(layers_x, [r["lr_last_token"][mkey] for r in results_by_layer],
                color="#2563EB", linewidth=2, marker="o", markersize=3, label="LR (last token)")
        ax.plot(layers_x, [r["lr_mean_pool"][mkey] for r in results_by_layer],
                color="#2563EB", linewidth=2, marker="s", markersize=3, linestyle="--", label="LR (mean pool)")
        ax.plot(layers_x, [r["svc_last_token"][mkey] for r in results_by_layer],
                color="#DC2626", linewidth=2, marker="^", markersize=3, label="SVC (last token)")
        ax.plot(layers_x, [r["svc_mean_pool"][mkey] for r in results_by_layer],
                color="#DC2626", linewidth=2, marker="d", markersize=3, linestyle="--", label="SVC (mean pool)")
        ax.axhline(y=mchance, color="gray", linestyle=":", linewidth=1.5, label=f"Chance ({mchance:.3f})")
        ax.set_xlabel("Layer", fontsize=11)
        ax.set_ylabel(mlabel, fontsize=11)
        ax.set_title(mlabel, fontsize=12, fontweight="bold")
        ax.legend(fontsize=8, loc="lower right")
        ax.set_xlim(-0.5, num_layers - 0.5)
        ax.grid(True, alpha=0.3)
    fig1p.suptitle(
        f"Representation Probing: {model_id.split('/')[-1]}\n"
        f"N={n_valid} trials, {n_folds}-fold CV, all {num_layers} layers",
        fontsize=13, fontweight="bold",
    )
    plt.tight_layout()
    fig1p.savefig(buf1_pdf, format="pdf", dpi=300, bbox_inches="tight")
    plt.close(fig1p)
    figures["probe_accuracy_by_layer_pdf"] = base64.b64encode(buf1_pdf.getvalue()).decode()

    # --- Figure 2: Permutation null distribution ---
    fig2, (ax_acc, ax_auc) = plt.subplots(1, 2, figsize=(14, 5))

    # Accuracy permutation distribution
    ax_acc.hist(perm_accuracies, bins=40, color="#94A3B8", edgecolor="#64748B",
                alpha=0.8, label="Null distribution")
    ax_acc.axvline(x=real_accuracy, color="#DC2626", linewidth=2.5,
                   linestyle="-", label=f"Real accuracy ({real_accuracy:.3f})")
    ax_acc.axvline(x=chance_accuracy, color="gray", linewidth=1.5,
                   linestyle=":", label=f"Chance ({chance_accuracy:.3f})")
    ax_acc.set_xlabel("Accuracy (5-fold CV)", fontsize=11)
    ax_acc.set_ylabel("Count", fontsize=11)
    ax_acc.set_title(
        f"Permutation Test: Accuracy at Layer {peak_layer}\n"
        f"p = {p_value_acc:.4f} ({n_permutations} permutations)",
        fontsize=12, fontweight="bold",
    )
    ax_acc.legend(fontsize=9)
    ax_acc.grid(True, alpha=0.3, axis="y")

    # AUC permutation distribution
    ax_auc.hist(perm_aucs, bins=40, color="#94A3B8", edgecolor="#64748B",
                alpha=0.8, label="Null distribution")
    ax_auc.axvline(x=real_auc, color="#DC2626", linewidth=2.5,
                   linestyle="-", label=f"Real AUC ({real_auc:.3f})")
    ax_auc.axvline(x=0.5, color="gray", linewidth=1.5,
                   linestyle=":", label="Chance (0.500)")
    ax_auc.set_xlabel("AUC-ROC (5-fold CV)", fontsize=11)
    ax_auc.set_ylabel("Count", fontsize=11)
    ax_auc.set_title(
        f"Permutation Test: AUC-ROC at Layer {peak_layer}\n"
        f"p = {p_value_auc:.4f} ({n_permutations} permutations)",
        fontsize=12, fontweight="bold",
    )
    ax_auc.legend(fontsize=9)
    ax_auc.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()

    buf2 = BytesIO()
    fig2.savefig(buf2, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig2)
    figures["permutation_null_png"] = base64.b64encode(buf2.getvalue()).decode()

    buf2_pdf = BytesIO()
    # Recreate for PDF
    fig2p, (ax_acc2, ax_auc2) = plt.subplots(1, 2, figsize=(14, 5))
    ax_acc2.hist(perm_accuracies, bins=40, color="#94A3B8", edgecolor="#64748B", alpha=0.8, label="Null distribution")
    ax_acc2.axvline(x=real_accuracy, color="#DC2626", linewidth=2.5, label=f"Real accuracy ({real_accuracy:.3f})")
    ax_acc2.axvline(x=chance_accuracy, color="gray", linewidth=1.5, linestyle=":", label=f"Chance ({chance_accuracy:.3f})")
    ax_acc2.set_xlabel("Accuracy (5-fold CV)", fontsize=11)
    ax_acc2.set_ylabel("Count", fontsize=11)
    ax_acc2.set_title(f"Permutation Test: Accuracy at Layer {peak_layer}\np = {p_value_acc:.4f}", fontsize=12, fontweight="bold")
    ax_acc2.legend(fontsize=9)
    ax_acc2.grid(True, alpha=0.3, axis="y")
    ax_auc2.hist(perm_aucs, bins=40, color="#94A3B8", edgecolor="#64748B", alpha=0.8, label="Null distribution")
    ax_auc2.axvline(x=real_auc, color="#DC2626", linewidth=2.5, label=f"Real AUC ({real_auc:.3f})")
    ax_auc2.axvline(x=0.5, color="gray", linewidth=1.5, linestyle=":", label="Chance (0.500)")
    ax_auc2.set_xlabel("AUC-ROC (5-fold CV)", fontsize=11)
    ax_auc2.set_ylabel("Count", fontsize=11)
    ax_auc2.set_title(f"Permutation Test: AUC-ROC at Layer {peak_layer}\np = {p_value_auc:.4f}", fontsize=12, fontweight="bold")
    ax_auc2.legend(fontsize=9)
    ax_auc2.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    fig2p.savefig(buf2_pdf, format="pdf", dpi=300, bbox_inches="tight")
    plt.close(fig2p)
    figures["permutation_null_pdf"] = base64.b64encode(buf2_pdf.getvalue()).decode()

    # ==================================================================
    # Build summary
    # ==================================================================
    total_time = time.time() - t0

    # Find best layer/config
    best_layer = peak_layer
    best_lr_last = results_by_layer[peak_layer_idx]["lr_last_token"]

    # Find best mean-pool layer
    peak_mean_idx = max(range(len(results_by_layer)),
                        key=lambda i: results_by_layer[i]["lr_mean_pool"]["accuracy"])
    best_lr_mean = results_by_layer[peak_mean_idx]["lr_mean_pool"]

    # Classifier agreement: do LR and SVC agree on peak layer?
    peak_svc_idx = max(range(len(results_by_layer)),
                       key=lambda i: results_by_layer[i]["svc_last_token"]["accuracy"])
    classifier_agreement = (peak_layer_idx == peak_svc_idx)

    summary = {
        "model_id": model_id,
        "num_layers": num_layers,
        "hidden_dim": hidden_dim,
        "n_assortments": len(assortments),
        "n_trials_per_assortment": n_trials_per_assortment,
        "n_trials_total": n_valid,
        "n_optimal": int(n_optimal),
        "n_non_optimal": int(n_valid - n_optimal),
        "optimal_rate": float(n_optimal / max(n_valid, 1)),

        "chance_baselines": {
            "accuracy": float(chance_accuracy),
            "balanced_accuracy": float(chance_balanced),
            "auc_roc": float(chance_auc),
            "f1": float(chance_f1),
        },

        "results_by_layer": results_by_layer,

        "peak_layer_lr_last_token": {
            "layer": best_layer,
            "metrics": best_lr_last,
            "above_chance_accuracy": best_lr_last["accuracy"] - chance_accuracy,
            "above_chance_auc": best_lr_last["auc_roc"] - chance_auc,
        },
        "peak_layer_lr_mean_pool": {
            "layer": results_by_layer[peak_mean_idx]["layer"],
            "metrics": best_lr_mean,
            "above_chance_accuracy": best_lr_mean["accuracy"] - chance_accuracy,
            "above_chance_auc": best_lr_mean["auc_roc"] - chance_auc,
        },
        "peak_layer_svc_last_token": {
            "layer": results_by_layer[peak_svc_idx]["layer"],
            "metrics": results_by_layer[peak_svc_idx]["svc_last_token"],
        },

        "classifier_agreement": {
            "lr_peak_layer": best_layer,
            "svc_peak_layer": results_by_layer[peak_svc_idx]["layer"],
            "agree": bool(classifier_agreement),
        },

        "pooling_comparison": {
            "lr_last_token_peak_acc": best_lr_last["accuracy"],
            "lr_mean_pool_peak_acc": best_lr_mean["accuracy"],
            "last_token_better": best_lr_last["accuracy"] > best_lr_mean["accuracy"],
        },

        "permutation_test": {
            "peak_layer": int(peak_layer),
            "n_permutations": n_permutations,
            "real_accuracy": float(real_accuracy),
            "real_auc": float(real_auc),
            "null_mean_accuracy": float(np.mean(perm_accuracies)),
            "null_std_accuracy": float(np.std(perm_accuracies)),
            "null_max_accuracy": float(np.max(perm_accuracies)),
            "null_mean_auc": float(np.mean(perm_aucs)),
            "null_std_auc": float(np.std(perm_aucs)),
            "p_value_accuracy": float(p_value_acc),
            "p_value_auc": float(p_value_auc),
            "significant_at_001": bool(p_value_acc < 0.001),
            "significant_at_005": bool(p_value_acc < 0.005),
            "significant_at_01": bool(p_value_acc < 0.01),
            "permutation_accuracies": perm_accuracies.tolist(),
            "permutation_aucs": perm_aucs.tolist(),
        },

        "timing": {
            "model_load_s": float(load_time),
            "extraction_s": float(extraction_time),
            "permutation_s": float(perm_time),
            "total_s": float(total_time),
        },

        "methodology": {
            "references": [
                "Hewitt & Liang (2019) — permutation test for probing control",
                "Tang et al. (2023) — layerwise analysis of representations",
                "Arditi et al. (2024) — mean pooling comparison",
            ],
            "classifiers": ["LogisticRegression (L2, C=1.0)", "SGDClassifier (hinge loss, linear SVM)"],
            "cv_folds": n_folds,
            "pooling_methods": ["last_token", "mean_pool"],
            "metrics": ["accuracy", "balanced_accuracy", "auc_roc", "f1"],
            "layers_probed": "all",
            "p_value_method": "permutation (Phipson & Smyth 2010 conservative)",
        },

        "trial_metadata": all_metadata,
        "figures": figures,
        "timestamp": datetime.now().isoformat(),
    }

    # Print final summary
    print(f"\n{'='*70}")
    print("RESULTS SUMMARY — NATURE STANDARD")
    print(f"{'='*70}")
    print(f"  Model: {model_id}")
    print(f"  N = {n_valid} trials ({len(assortments)} assortments x {n_trials_per_assortment})")
    print(f"  Optimal: {n_optimal}/{n_valid} ({100*n_optimal/max(n_valid,1):.1f}%)")
    print()
    print(f"  PEAK PROBE (LogReg, last-token):")
    print(f"    Layer {best_layer}: acc={best_lr_last['accuracy']:.4f} "
          f"(+{best_lr_last['accuracy']-chance_accuracy:.4f} above chance)")
    print(f"    AUC={best_lr_last['auc_roc']:.4f}, "
          f"BalAcc={best_lr_last['balanced_accuracy']:.4f}, "
          f"F1={best_lr_last['f1']:.4f}")
    print()
    print(f"  PEAK PROBE (LogReg, mean-pool):")
    print(f"    Layer {results_by_layer[peak_mean_idx]['layer']}: "
          f"acc={best_lr_mean['accuracy']:.4f} "
          f"(+{best_lr_mean['accuracy']-chance_accuracy:.4f} above chance)")
    print()
    print(f"  PERMUTATION TEST (layer {peak_layer}):")
    print(f"    p = {p_value_acc:.6f} (accuracy), p = {p_value_auc:.6f} (AUC)")
    if p_value_acc < 0.001:
        print(f"    SIGNIFICANT at p < 0.001")
    elif p_value_acc < 0.01:
        print(f"    SIGNIFICANT at p < 0.01")
    elif p_value_acc < 0.05:
        print(f"    SIGNIFICANT at p < 0.05")
    else:
        print(f"    NOT significant at p < 0.05")
    print()
    print(f"  CLASSIFIER AGREEMENT: LR peak={best_layer}, SVC peak={results_by_layer[peak_svc_idx]['layer']} "
          f"({'AGREE' if classifier_agreement else 'DIFFER'})")
    print(f"  POOLING: last-token {'>' if best_lr_last['accuracy'] > best_lr_mean['accuracy'] else '<='} mean-pool "
          f"({best_lr_last['accuracy']:.4f} vs {best_lr_mean['accuracy']:.4f})")
    print()
    print(f"  Total time: {total_time:.1f}s")
    print(f"{'='*70}")

    return summary


# ---------------------------------------------------------------------------
# Local entry point
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Representation probing v2 (Nature standard) on Modal GPU"
    )
    parser.add_argument(
        "--model", type=str, default="Qwen/Qwen2.5-7B-Instruct",
        help="HuggingFace model ID",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="3 assortments, 2 trials (tests pipeline)",
    )
    parser.add_argument(
        "--trials", type=int, default=18,
        help="Trials per assortment (default: 18, giving 612 total)",
    )
    parser.add_argument(
        "--permutations", type=int, default=500,
        help="Number of permutation iterations (default: 500)",
    )
    args = parser.parse_args()

    # Load assortments
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))
    from experiment.assortments import ALL_ASSORTMENTS

    assortments = [a for a in ALL_ASSORTMENTS if a["id"].startswith("sr_")]
    print(f"Loaded {len(assortments)} sr_ assortments")

    if args.dry_run:
        assortments = assortments[:3]
        n_trials = 2
        n_perms = 20
        print(f"[DRY RUN] {len(assortments)} assortments, {n_trials} trials, {n_perms} permutations")
    else:
        n_trials = args.trials
        n_perms = args.permutations
        print(f"Full run: {len(assortments)} assortments x {n_trials} trials = "
              f"{len(assortments) * n_trials} total, {n_perms} permutations")

    assortments_json = json.dumps(assortments, default=str)
    print(f"Assortments JSON size: {len(assortments_json) / 1024:.1f} KB")

    # Output directory
    output_dir = project_root / "nature-rr" / "results" / "04-representation-probing" / "v2"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run on Modal
    print(f"\nLaunching on Modal...")
    with modal.enable_output():
        with app.run():
            summary = run_probing_v2.remote(
                assortments_json=assortments_json,
                model_id=args.model,
                n_trials_per_assortment=n_trials,
                n_permutations=n_perms,
            )

    # Save figures from base64
    for fig_key, fig_data in summary.get("figures", {}).items():
        ext = "png" if fig_key.endswith("_png") else "pdf"
        fig_name = fig_key.rsplit(f"_{ext}", 1)[0]
        safe_model = args.model.replace("/", "_")
        fig_path = output_dir / f"{fig_name}_{safe_model}.{ext}"
        with open(fig_path, "wb") as f:
            f.write(base64.b64decode(fig_data))
        print(f"Figure saved: {fig_path}")

    # Save full results JSON (without figures and trial_metadata to keep size down)
    safe_model = args.model.replace("/", "_")
    result_json = {k: v for k, v in summary.items()
                   if k not in ("figures", "trial_metadata")}
    result_path = output_dir / f"probing_v2_{safe_model}.json"
    with open(result_path, "w") as f:
        json.dump(result_json, f, indent=2, default=str)
    print(f"Results JSON: {result_path}")

    # Save full results with trial metadata separately
    full_path = output_dir / f"probing_v2_{safe_model}_full.json"
    full_data = {k: v for k, v in summary.items() if k != "figures"}
    with open(full_path, "w") as f:
        json.dump(full_data, f, indent=2, default=str)
    print(f"Full results: {full_path}")

    # Print final summary
    print(f"\n{'='*70}")
    print("RUN COMPLETE")
    print(f"{'='*70}")
    print(f"  Model: {args.model}")
    print(f"  N = {summary['n_trials_total']}")
    print(f"  Peak accuracy: {summary['peak_layer_lr_last_token']['metrics']['accuracy']:.4f} "
          f"at layer {summary['peak_layer_lr_last_token']['layer']}")
    print(f"  Permutation p = {summary['permutation_test']['p_value_accuracy']:.6f}")
    sig = "YES" if summary['permutation_test']['significant_at_001'] else "NO"
    print(f"  Significant at p<0.001: {sig}")
    print(f"  Output: {output_dir}")


if __name__ == "__main__":
    import base64
    main()
