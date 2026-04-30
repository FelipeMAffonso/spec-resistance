#!/usr/bin/env python3
"""
Representation Probing of Brand Preferences in LLM Hidden States
=================================================================
Nature R&R Pillar 1C: Are brand preferences encoded in intermediate
representations, and do they survive instruction tuning?

Motivation (Tang et al. 2023):
    If a linear probe trained on middle-layer hidden states can predict
    which brand the model will recommend, brand preferences are not
    merely output-level phenomena but are encoded in the model's internal
    representations. Comparing probe accuracy between base and instruct
    models tests whether RLHF alignment removes these representations
    or merely teaches the model to suppress them at the output layer.

Design:
    1. Load a HuggingFace model via nnsight (captures hidden states)
    2. For each of the 34 sr_ assortments in baseline condition:
       - Construct the product recommendation prompt
       - Run a single forward pass, capturing hidden states at every layer
       - Record which product the model would recommend (argmax over
         product-letter tokens)
       - Save the hidden state vector at the last token position per layer
    3. Train sklearn LogisticRegression probes:
       a. Binary: optimal vs. non-optimal choice
       b. Multiclass: which brand/product letter chosen
    4. Evaluate probe accuracy per layer (leave-one-out cross-validation
       given the small N=34 dataset)
    5. Optionally compare base vs. instruct models
    6. Generate figure: probe accuracy by layer (line plot)
    7. Save all results to results/04-representation-probing/

Following:
    - Tang et al. (2023) "What Do Llamas Really Think?"
    - Zou et al. (2023) "Representation Engineering"
    - Qi et al. (ICLR 2025) "Safety Alignment Should Be Made More
      Than Just a Few Tokens Deep"

Hardware requirements:
    - 7B model in float16/bfloat16: ~14GB VRAM (fits on RTX 3090/4090)
    - Hidden states for 34 prompts x 28 layers x 3584 dims ~ 14MB (trivial)
    - GPU not strictly required (CPU works, just slower)

Usage:
    # Full run on default model (Qwen2.5-7B-Instruct)
    python representation_probing.py

    # Dry run (no GPU needed, tests pipeline with 3 assortments)
    python representation_probing.py --dry-run

    # Specific model
    python representation_probing.py --model Qwen/Qwen2.5-7B

    # Compare base vs instruct
    python representation_probing.py --model Qwen/Qwen2.5-7B-Instruct --compare Qwen/Qwen2.5-7B

    # Resume from saved hidden states
    python representation_probing.py --resume

    # Use 4-bit quantization (for low-VRAM GPUs)
    python representation_probing.py --quantize 4bit

Dependencies:
    pip install nnsight torch transformers scikit-learn matplotlib numpy
    # For 4-bit quantization:
    pip install bitsandbytes accelerate
"""

import argparse
import json
import os
import re
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_NATURE_RR_DIR = _SCRIPT_DIR.parent
_PROJECT_ROOT = _NATURE_RR_DIR.parent  # spec-resistance/
_RESULTS_DIR = _NATURE_RR_DIR / "results" / "04-representation-probing"

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Fix Windows console encoding
if hasattr(sys.stdout, "buffer") and sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer") and sys.stderr.encoding != "utf-8":
    import io
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from experiment.conditions import build_prompt
from experiment.assortments import ALL_ASSORTMENTS, CATEGORY_METADATA, CATEGORY_PREFERENCES

# ===================================================================
# MODEL ARCHITECTURE REGISTRY
# ===================================================================
# Different HuggingFace model families expose their layers through
# different module paths. This registry maps model family prefixes
# to the nnsight accessor patterns needed to extract hidden states.
#
# For Llama/Qwen/Mistral-family models, the architecture is:
#   model.model.layers[i]  ->  hidden states as output[0]
#   model.model.norm       ->  final layer norm
#   model.lm_head          ->  logit projection
#
# For GPT-2-family models:
#   model.transformer.h[i] ->  hidden states as output[0]
#   model.transformer.ln_f ->  final layer norm
#   model.lm_head          ->  logit projection

MODEL_ARCHITECTURES = {
    "qwen": {
        "layers_path": "model.model.layers",
        "norm_path": "model.model.norm",
        "lm_head_path": "model.lm_head",
        "embed_path": "model.model.embed_tokens",
    },
    "llama": {
        "layers_path": "model.model.layers",
        "norm_path": "model.model.norm",
        "lm_head_path": "model.lm_head",
        "embed_path": "model.model.embed_tokens",
    },
    "mistral": {
        "layers_path": "model.model.layers",
        "norm_path": "model.model.norm",
        "lm_head_path": "model.lm_head",
        "embed_path": "model.model.embed_tokens",
    },
    "gemma": {
        "layers_path": "model.model.layers",
        "norm_path": "model.model.norm",
        "lm_head_path": "model.lm_head",
        "embed_path": "model.model.embed_tokens",
    },
    "gpt2": {
        "layers_path": "model.transformer.h",
        "norm_path": "model.transformer.ln_f",
        "lm_head_path": "model.lm_head",
        "embed_path": "model.transformer.wte",
    },
}


def detect_architecture(model_id: str) -> dict:
    """Detect model architecture from HuggingFace model ID."""
    model_lower = model_id.lower()
    for prefix, arch in MODEL_ARCHITECTURES.items():
        if prefix in model_lower:
            return arch
    # Default to Llama-style (most common for modern models)
    print(f"[WARN] Unknown model family for '{model_id}', defaulting to Llama-style architecture")
    return MODEL_ARCHITECTURES["llama"]


def get_module_by_path(model, dotted_path: str):
    """Navigate nnsight model by dotted path string.

    For example, 'model.model.layers' resolves by stepping through
    each attribute name in sequence, starting from the nnsight wrapper.
    The leading 'model.' refers to the wrapper itself, so we skip it
    and begin from the underlying _model attribute.
    """
    parts = dotted_path.split(".")
    # The first 'model' is the nnsight wrapper object itself
    obj = model
    for part in parts[1:]:  # skip 'model' prefix
        obj = getattr(obj, part)
    return obj


# ===================================================================
# ASSORTMENT HELPERS
# ===================================================================

def get_sr_assortments() -> list[dict]:
    """Return the 34 sr_ assortments used in the main experiment."""
    return [a for a in ALL_ASSORTMENTS if a["id"].startswith("sr_")]


def build_baseline_prompt(assortment: dict) -> tuple[str, str, dict]:
    """Build baseline condition prompt for an assortment.

    Returns (system_prompt, user_message, metadata) with shuffling
    and letter randomization disabled for reproducibility.
    """
    cat = assortment.get("category", "")
    cat_prefs = CATEGORY_PREFERENCES.get(cat, {})

    system_prompt, user_message, metadata = build_prompt(
        assortment=assortment,
        condition="baseline",
        category_preferences={cat: cat_prefs} if cat_prefs else None,
        paraphrase_index=0,      # deterministic paraphrase
        shuffle_products=False,   # fixed order for reproducibility
        randomize_letters=False,  # fixed letters for reproducibility
    )
    return system_prompt, user_message, metadata


# ===================================================================
# HIDDEN STATE EXTRACTION
# ===================================================================

def extract_hidden_states(
    model,
    arch: dict,
    system_prompt: str,
    user_message: str,
    num_layers: int,
    device: str,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Run a single forward pass and extract hidden states at every layer.

    For chat/instruct models, we format the prompt using the tokenizer's
    chat template. For base models, we concatenate system and user text.

    Returns:
        hidden_states: np.ndarray of shape (num_layers, hidden_dim)
                       -- the last-token hidden state at each layer
        logits: np.ndarray of shape (vocab_size,)
                -- logits at the last token position
        predicted_token_id: int -- argmax token id
    """
    import torch

    tokenizer = model.tokenizer

    # Format prompt according to model type
    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template is not None:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        prompt_text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    else:
        # Base model: concatenate as plain text
        prompt_text = f"{system_prompt}\n\n{user_message}\n\nAssistant:"

    # Get the layer module list and lm_head
    layers_module = get_module_by_path(model, arch["layers_path"])
    lm_head_module = get_module_by_path(model, arch["lm_head_path"])

    # Collect hidden states from all layers in a single forward pass
    # nnsight requires accessing modules in forward-pass execution order,
    # so we iterate from layer 0 to layer N-1 sequentially.
    saved_hidden_states = []
    saved_logits = None

    with model.trace(prompt_text) as tracer:
        for layer_idx in range(num_layers):
            # Each layer outputs a tuple; index [0] is the hidden state tensor
            # Shape: (batch=1, seq_len, hidden_dim)
            # We take the last token's hidden state: [:, -1, :]
            hs = layers_module[layer_idx].output[0][:, -1, :].save()
            saved_hidden_states.append(hs)

        # Also capture logits at the last position
        saved_logits = lm_head_module.output[:, -1, :].save()

    # Convert saved tensors to numpy
    hidden_states_np = np.stack(
        [hs.detach().cpu().float().numpy().squeeze(0) for hs in saved_hidden_states],
        axis=0,
    )  # shape: (num_layers, hidden_dim)

    logits_np = saved_logits.detach().cpu().float().numpy().squeeze(0)
    predicted_token_id = int(np.argmax(logits_np))

    return hidden_states_np, logits_np, predicted_token_id


def parse_model_choice(
    model,
    logits: np.ndarray,
    predicted_token_id: int,
    valid_letters: list[str],
) -> Optional[str]:
    """Determine which product letter the model would choose.

    Strategy: check the argmax token. If it decodes to a valid letter
    (A-E), use that. Otherwise, check the relative probabilities of
    all letter tokens and pick the highest.
    """
    import torch

    tokenizer = model.tokenizer

    # Check if argmax token is a letter
    decoded = tokenizer.decode([predicted_token_id]).strip()
    if decoded.upper() in valid_letters:
        return decoded.upper()

    # Fallback: find token IDs for each letter and compare logits
    letter_logits = {}
    for letter in valid_letters:
        # Try multiple tokenizations (with/without space prefix)
        candidates = [letter, f" {letter}", f"\n{letter}"]
        best_logit = -float("inf")
        for candidate in candidates:
            token_ids = tokenizer.encode(candidate, add_special_tokens=False)
            if len(token_ids) == 1:
                tid = token_ids[0]
                if logits[tid] > best_logit:
                    best_logit = logits[tid]
            elif len(token_ids) > 0:
                # Use the last token (the letter itself after prefix)
                tid = token_ids[-1]
                if logits[tid] > best_logit:
                    best_logit = logits[tid]
        letter_logits[letter] = best_logit

    if not letter_logits:
        return None

    best_letter = max(letter_logits, key=letter_logits.get)

    # Only return if the best letter has a reasonable logit
    # (not all -inf, which would mean no letter tokens found)
    if letter_logits[best_letter] > -float("inf"):
        return best_letter

    return None


# ===================================================================
# PROBING: LINEAR CLASSIFICATION OF HIDDEN STATES
# ===================================================================

def train_probes(
    hidden_states_all: np.ndarray,
    labels_binary: np.ndarray,
    labels_multiclass: np.ndarray,
    brand_labels: np.ndarray,
    num_layers: int,
) -> dict:
    """Train linear probes at each layer and evaluate via LOO-CV.

    Given the small dataset (N=34 assortments), we use leave-one-out
    cross-validation (LOO-CV) for unbiased accuracy estimates.

    Args:
        hidden_states_all: (N, num_layers, hidden_dim)
        labels_binary: (N,) -- 1 if model chose optimal, 0 otherwise
        labels_multiclass: (N,) -- integer-encoded product letter (0-4)
        brand_labels: (N,) -- integer-encoded brand name
        num_layers: number of layers

    Returns:
        dict with keys: binary_accuracy_per_layer, multiclass_accuracy_per_layer,
        brand_accuracy_per_layer, each a list of length num_layers
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import LeaveOneOut
    from sklearn.preprocessing import StandardScaler

    n_samples = hidden_states_all.shape[0]
    loo = LeaveOneOut()

    binary_acc = []
    multiclass_acc = []
    brand_acc = []

    # Check class balance for binary labels
    n_positive = int(labels_binary.sum())
    n_negative = n_samples - n_positive
    print(f"\n  Binary label distribution: {n_positive} optimal, {n_negative} non-optimal")

    # Check multiclass label distribution
    unique_multi, counts_multi = np.unique(labels_multiclass, return_counts=True)
    print(f"  Multiclass labels (letter choices): {dict(zip(unique_multi.tolist(), counts_multi.tolist()))}")

    unique_brand, counts_brand = np.unique(brand_labels, return_counts=True)
    print(f"  Brand labels: {dict(zip(unique_brand.tolist(), counts_brand.tolist()))}")

    for layer_idx in range(num_layers):
        X = hidden_states_all[:, layer_idx, :]  # (N, hidden_dim)

        # --- Binary probe ---
        if n_positive > 0 and n_negative > 0:
            correct_binary = 0
            for train_idx, test_idx in loo.split(X):
                X_train, X_test = X[train_idx], X[test_idx]
                y_train, y_test = labels_binary[train_idx], labels_binary[test_idx]

                scaler = StandardScaler()
                X_train_s = scaler.fit_transform(X_train)
                X_test_s = scaler.transform(X_test)

                clf = LogisticRegression(
                    max_iter=1000, C=1.0, solver="lbfgs", random_state=42
                )
                clf.fit(X_train_s, y_train)
                if clf.predict(X_test_s)[0] == y_test[0]:
                    correct_binary += 1

            binary_acc.append(correct_binary / n_samples)
        else:
            # Degenerate case: only one class
            binary_acc.append(max(n_positive, n_negative) / n_samples)

        # --- Multiclass probe (product letter) ---
        if len(unique_multi) > 1:
            correct_multi = 0
            for train_idx, test_idx in loo.split(X):
                X_train, X_test = X[train_idx], X[test_idx]
                y_train, y_test = labels_multiclass[train_idx], labels_multiclass[test_idx]

                scaler = StandardScaler()
                X_train_s = scaler.fit_transform(X_train)
                X_test_s = scaler.transform(X_test)

                clf = LogisticRegression(
                    max_iter=1000, C=1.0, solver="lbfgs",
                    multi_class="multinomial", random_state=42,
                )
                clf.fit(X_train_s, y_train)
                if clf.predict(X_test_s)[0] == y_test[0]:
                    correct_multi += 1

            multiclass_acc.append(correct_multi / n_samples)
        else:
            multiclass_acc.append(1.0)  # trivial if all same label

        # --- Brand probe ---
        if len(unique_brand) > 1:
            correct_brand = 0
            for train_idx, test_idx in loo.split(X):
                X_train, X_test = X[train_idx], X[test_idx]
                y_train, y_test = brand_labels[train_idx], brand_labels[test_idx]

                scaler = StandardScaler()
                X_train_s = scaler.fit_transform(X_train)
                X_test_s = scaler.transform(X_test)

                clf = LogisticRegression(
                    max_iter=1000, C=1.0, solver="lbfgs",
                    multi_class="multinomial", random_state=42,
                )
                clf.fit(X_train_s, y_train)
                if clf.predict(X_test_s)[0] == y_test[0]:
                    correct_brand += 1

            brand_acc.append(correct_brand / n_samples)
        else:
            brand_acc.append(1.0)

        if (layer_idx + 1) % 4 == 0 or layer_idx == num_layers - 1:
            print(f"  Layer {layer_idx:2d}: binary={binary_acc[-1]:.3f}  "
                  f"letter={multiclass_acc[-1]:.3f}  brand={brand_acc[-1]:.3f}")

    return {
        "binary_accuracy_per_layer": binary_acc,
        "multiclass_accuracy_per_layer": multiclass_acc,
        "brand_accuracy_per_layer": brand_acc,
    }


# ===================================================================
# VISUALIZATION
# ===================================================================

def plot_probe_accuracy(
    results: dict,
    model_name: str,
    output_path: Path,
    comparison_results: Optional[dict] = None,
    comparison_name: Optional[str] = None,
):
    """Generate probe accuracy by layer plot.

    Creates a line plot with layer index on x-axis, accuracy on y-axis.
    One line per probe type (binary, multiclass, brand).
    If comparison_results provided, adds dashed lines for the second model.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)

    probe_types = [
        ("binary_accuracy_per_layer", "Optimal vs. Non-optimal"),
        ("multiclass_accuracy_per_layer", "Product Letter Choice"),
        ("brand_accuracy_per_layer", "Brand Choice"),
    ]

    colors = ["#2563EB", "#DC2626", "#059669"]  # blue, red, green

    for ax_idx, (key, title) in enumerate(probe_types):
        ax = axes[ax_idx]
        acc = results[key]
        layers = list(range(len(acc)))

        ax.plot(layers, acc, color=colors[ax_idx], linewidth=2,
                label=_short_name(model_name), marker="o", markersize=3)

        if comparison_results and key in comparison_results:
            comp_acc = comparison_results[key]
            ax.plot(layers, comp_acc, color=colors[ax_idx], linewidth=2,
                    linestyle="--", alpha=0.7,
                    label=_short_name(comparison_name or "Comparison"),
                    marker="s", markersize=3)

        # Chance-level baseline
        if key == "binary_accuracy_per_layer":
            # Majority class baseline
            n_opt = results.get("n_optimal", 0)
            n_total = results.get("n_samples", 34)
            chance = max(n_opt, n_total - n_opt) / n_total if n_total > 0 else 0.5
        elif key == "multiclass_accuracy_per_layer":
            n_classes = results.get("n_letter_classes", 5)
            chance = 1.0 / max(n_classes, 1)
        else:
            n_brands = results.get("n_brand_classes", 5)
            chance = 1.0 / max(n_brands, 1)

        ax.axhline(y=chance, color="gray", linestyle=":", linewidth=1,
                   label=f"Chance ({chance:.2f})")

        ax.set_xlabel("Layer", fontsize=12)
        if ax_idx == 0:
            ax.set_ylabel("LOO-CV Accuracy", fontsize=12)
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.legend(fontsize=9, loc="lower right")
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)

    fig.suptitle(
        "Representation Probing: Where Are Brand Preferences Encoded?",
        fontsize=14, fontweight="bold", y=1.02,
    )
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Figure saved to: {output_path}")


def _short_name(model_id: str) -> str:
    """Shorten a HuggingFace model ID for display."""
    parts = model_id.split("/")
    return parts[-1] if len(parts) > 1 else model_id


# ===================================================================
# MAIN PIPELINE
# ===================================================================

def run_extraction(
    model_id: str,
    assortments: list[dict],
    output_dir: Path,
    quantize: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """Run hidden state extraction for all assortments on one model.

    This is the GPU-intensive step. Results are saved incrementally
    so the pipeline can resume after interruption.

    Returns:
        dict with keys: hidden_states, choices, metadata, model_info
    """
    import torch
    from nnsight import LanguageModel

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_model_name = model_id.replace("/", "_")
    checkpoint_path = output_dir / f"checkpoint_{safe_model_name}.npz"
    metadata_path = output_dir / f"metadata_{safe_model_name}.json"

    # Check for existing checkpoint
    if checkpoint_path.exists() and metadata_path.exists():
        print(f"\n  Found checkpoint for {model_id}, loading...")
        data = np.load(str(checkpoint_path), allow_pickle=True)
        with open(metadata_path, "r") as f:
            meta = json.load(f)
        return {
            "hidden_states": data["hidden_states"],
            "choices": meta["choices"],
            "metadata": meta,
            "model_info": meta.get("model_info", {}),
        }

    # Determine device
    if torch.cuda.is_available():
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_mem / (1024**3)
        print(f"\n  GPU detected: {gpu_name} ({gpu_mem:.1f} GB)")
    else:
        device = "cpu"
        print("\n  No GPU detected, using CPU (will be slow for 7B models)")

    # Load model
    print(f"\n  Loading model: {model_id}")
    load_kwargs = {
        "device_map": "auto",
        "dispatch": True,
    }

    # Set precision
    if device == "cuda":
        load_kwargs["torch_dtype"] = torch.bfloat16
    else:
        load_kwargs["torch_dtype"] = torch.float32

    # Quantization for low-VRAM setups
    if quantize == "4bit":
        from transformers import BitsAndBytesConfig
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        print("  Using 4-bit quantization (NF4)")
    elif quantize == "8bit":
        from transformers import BitsAndBytesConfig
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_8bit=True,
        )
        print("  Using 8-bit quantization")

    load_start = time.time()
    model = LanguageModel(model_id, **load_kwargs)
    load_time = time.time() - load_start
    print(f"  Model loaded in {load_time:.1f}s")

    # Detect architecture
    arch = detect_architecture(model_id)
    print(f"  Architecture: layers={arch['layers_path']}")

    # Determine number of layers by inspecting the model
    layers_module = get_module_by_path(model, arch["layers_path"])
    num_layers = len(layers_module)
    print(f"  Number of layers: {num_layers}")

    # Get hidden dimension by scanning
    import nnsight
    with model.scan("test"):
        dim = nnsight.save(
            get_module_by_path(model, arch["layers_path"])[0].output[0].shape[-1]
        )
    hidden_dim = int(dim)
    print(f"  Hidden dimension: {hidden_dim}")

    # Prepare storage
    n_assortments = len(assortments)
    all_hidden_states = np.zeros((n_assortments, num_layers, hidden_dim), dtype=np.float32)
    choices = []
    extraction_metadata = []

    print(f"\n  Extracting hidden states from {n_assortments} assortments...")
    extraction_start = time.time()

    for idx, assortment in enumerate(assortments):
        sys_prompt, user_msg, meta = build_baseline_prompt(assortment)

        try:
            hs, logits, pred_token = extract_hidden_states(
                model, arch, sys_prompt, user_msg, num_layers, device
            )

            # Determine model's product choice
            valid_letters = [p["letter"] for p in assortment["products"]]
            chosen_letter = parse_model_choice(model, logits, pred_token, valid_letters)

            all_hidden_states[idx] = hs
            choices.append(chosen_letter)

            # Store metadata for this assortment
            optimal_letter = meta["optimal_letter"]
            chosen_product = None
            for p in assortment["products"]:
                if p["letter"] == chosen_letter:
                    chosen_product = p
                    break

            extraction_metadata.append({
                "assortment_id": assortment["id"],
                "category": assortment.get("category", "unknown"),
                "chosen_letter": chosen_letter,
                "optimal_letter": optimal_letter,
                "chose_optimal": chosen_letter == optimal_letter,
                "chosen_brand": chosen_product["brand"] if chosen_product else None,
                "chosen_brand_familiarity": chosen_product.get("brand_familiarity", "unknown") if chosen_product else None,
                "predicted_token": model.tokenizer.decode([pred_token]),
            })

            status = "OPTIMAL" if chosen_letter == optimal_letter else "non-optimal"
            brand_info = f" ({chosen_product['brand']})" if chosen_product else ""
            print(f"    [{idx+1:2d}/{n_assortments}] {assortment['id']}: "
                  f"chose {chosen_letter}{brand_info} [{status}]")

        except Exception as e:
            print(f"    [{idx+1:2d}/{n_assortments}] {assortment['id']}: ERROR - {e}")
            choices.append(None)
            extraction_metadata.append({
                "assortment_id": assortment["id"],
                "category": assortment.get("category", "unknown"),
                "chosen_letter": None,
                "error": str(e),
            })

    extraction_time = time.time() - extraction_start
    n_valid = sum(1 for c in choices if c is not None)
    n_optimal = sum(1 for m in extraction_metadata if m.get("chose_optimal", False))
    print(f"\n  Extraction complete: {n_valid}/{n_assortments} valid, "
          f"{n_optimal}/{n_valid} chose optimal ({100*n_optimal/max(n_valid,1):.1f}%)")
    print(f"  Time: {extraction_time:.1f}s ({extraction_time/max(n_assortments,1):.1f}s per assortment)")

    # Save checkpoint
    model_info = {
        "model_id": model_id,
        "num_layers": num_layers,
        "hidden_dim": hidden_dim,
        "device": device,
        "quantize": quantize,
        "n_assortments": n_assortments,
        "n_valid": n_valid,
        "n_optimal": n_optimal,
        "extraction_time_s": extraction_time,
        "timestamp": datetime.now().isoformat(),
    }

    save_meta = {
        "model_info": model_info,
        "choices": choices,
        "extraction_metadata": extraction_metadata,
    }

    np.savez_compressed(str(checkpoint_path), hidden_states=all_hidden_states)
    with open(metadata_path, "w") as f:
        json.dump(save_meta, f, indent=2, default=str)

    print(f"  Checkpoint saved to: {checkpoint_path}")

    return {
        "hidden_states": all_hidden_states,
        "choices": choices,
        "metadata": save_meta,
        "model_info": model_info,
    }


def run_probing(
    extraction_result: dict,
    assortments: list[dict],
    model_name: str,
    output_dir: Path,
) -> dict:
    """Run linear probing on extracted hidden states.

    Args:
        extraction_result: output from run_extraction()
        assortments: list of assortment dicts (same order as extraction)
        model_name: model identifier for labeling
        output_dir: where to save results

    Returns:
        dict with probe accuracies per layer and metadata
    """
    hidden_states = extraction_result["hidden_states"]
    choices = extraction_result["choices"]

    # Filter out failed extractions
    valid_mask = [c is not None for c in choices]
    valid_indices = [i for i, v in enumerate(valid_mask) if v]

    if len(valid_indices) < 10:
        print(f"\n  WARNING: Only {len(valid_indices)} valid samples, probing may be unreliable")
        if len(valid_indices) < 3:
            print("  SKIPPING probing (too few samples)")
            return {"error": "too_few_samples", "n_valid": len(valid_indices)}

    hs_valid = hidden_states[valid_indices]  # (N_valid, num_layers, hidden_dim)
    choices_valid = [choices[i] for i in valid_indices]
    assortments_valid = [assortments[i] for i in valid_indices]

    # Build label arrays
    # Binary: did the model choose the optimal product?
    labels_binary = np.zeros(len(valid_indices), dtype=np.int64)
    # Multiclass: which letter did it choose? (integer-encoded)
    letter_to_int = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
    labels_multiclass = np.zeros(len(valid_indices), dtype=np.int64)
    # Brand: which brand did it choose? (integer-encoded)
    brand_names = []

    for i, (choice, assortment) in enumerate(zip(choices_valid, assortments_valid)):
        # Build metadata for this choice
        _, _, meta = build_baseline_prompt(assortment)
        optimal_letter = meta["optimal_letter"]
        labels_binary[i] = 1 if choice == optimal_letter else 0
        labels_multiclass[i] = letter_to_int.get(choice, 0)

        # Find the brand of the chosen product
        chosen_brand = None
        for p in assortment["products"]:
            if p["letter"] == choice:
                chosen_brand = p.get("brand", "Unknown")
                break
        brand_names.append(chosen_brand or "Unknown")

    # Integer-encode brands
    unique_brands = sorted(set(brand_names))
    brand_to_int = {b: i for i, b in enumerate(unique_brands)}
    labels_brand = np.array([brand_to_int[b] for b in brand_names], dtype=np.int64)

    num_layers = hs_valid.shape[1]

    print(f"\n  Running probes on {len(valid_indices)} samples across {num_layers} layers...")
    print(f"  Unique brands chosen: {len(unique_brands)}")

    probe_results = train_probes(
        hs_valid, labels_binary, labels_multiclass, labels_brand, num_layers
    )

    # Add metadata to results
    probe_results["model_name"] = model_name
    probe_results["n_samples"] = len(valid_indices)
    probe_results["n_optimal"] = int(labels_binary.sum())
    probe_results["n_letter_classes"] = len(set(labels_multiclass.tolist()))
    probe_results["n_brand_classes"] = len(unique_brands)
    probe_results["unique_brands"] = unique_brands
    probe_results["brand_distribution"] = {
        b: int(c) for b, c in zip(
            *np.unique(labels_brand, return_counts=True)
        )
    }

    # Find peak layers
    peak_binary = int(np.argmax(probe_results["binary_accuracy_per_layer"]))
    peak_multi = int(np.argmax(probe_results["multiclass_accuracy_per_layer"]))
    peak_brand = int(np.argmax(probe_results["brand_accuracy_per_layer"]))

    probe_results["peak_layer_binary"] = peak_binary
    probe_results["peak_layer_multiclass"] = peak_multi
    probe_results["peak_layer_brand"] = peak_brand
    probe_results["peak_accuracy_binary"] = probe_results["binary_accuracy_per_layer"][peak_binary]
    probe_results["peak_accuracy_multiclass"] = probe_results["multiclass_accuracy_per_layer"][peak_multi]
    probe_results["peak_accuracy_brand"] = probe_results["brand_accuracy_per_layer"][peak_brand]

    print(f"\n  Peak probe accuracy:")
    print(f"    Binary (optimal vs. not): {probe_results['peak_accuracy_binary']:.3f} at layer {peak_binary}")
    print(f"    Multiclass (letter):      {probe_results['peak_accuracy_multiclass']:.3f} at layer {peak_multi}")
    print(f"    Brand:                    {probe_results['peak_accuracy_brand']:.3f} at layer {peak_brand}")

    # Save probe results
    safe_name = model_name.replace("/", "_")
    results_path = output_dir / f"probe_results_{safe_name}.json"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert numpy types to native Python for JSON serialization
    serializable = {}
    for k, v in probe_results.items():
        if isinstance(v, np.ndarray):
            serializable[k] = v.tolist()
        elif isinstance(v, (np.integer, np.floating)):
            serializable[k] = v.item()
        elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], (np.floating, np.integer)):
            serializable[k] = [x.item() if hasattr(x, "item") else x for x in v]
        else:
            serializable[k] = v

    with open(results_path, "w") as f:
        json.dump(serializable, f, indent=2)
    print(f"  Probe results saved to: {results_path}")

    return probe_results


def main():
    parser = argparse.ArgumentParser(
        description="Representation probing of brand preferences in LLM hidden states",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full run with default model (Qwen2.5-7B-Instruct)
  python representation_probing.py

  # Dry run (3 assortments, tests entire pipeline)
  python representation_probing.py --dry-run

  # Specific model
  python representation_probing.py --model meta-llama/Llama-3.1-8B-Instruct

  # Compare base vs instruct
  python representation_probing.py \\
      --model Qwen/Qwen2.5-7B-Instruct \\
      --compare Qwen/Qwen2.5-7B

  # Resume from saved hidden states (skip extraction)
  python representation_probing.py --resume

  # 4-bit quantization (for 8GB VRAM GPUs)
  python representation_probing.py --quantize 4bit
        """,
    )
    parser.add_argument(
        "--model", type=str, default="Qwen/Qwen2.5-7B-Instruct",
        help="HuggingFace model ID (default: Qwen/Qwen2.5-7B-Instruct)",
    )
    parser.add_argument(
        "--compare", type=str, default=None,
        help="Second model ID to compare (e.g., base model for base-vs-instruct)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run on 3 assortments only (tests pipeline without full GPU cost)",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip extraction if checkpoint exists, go directly to probing",
    )
    parser.add_argument(
        "--quantize", type=str, choices=["4bit", "8bit"], default=None,
        help="Quantize model weights (4bit or 8bit) for low-VRAM GPUs",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help=f"Output directory (default: {_RESULTS_DIR})",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else _RESULTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("REPRESENTATION PROBING: Brand Preferences in LLM Hidden States")
    print("=" * 70)
    print(f"  Model:      {args.model}")
    if args.compare:
        print(f"  Compare:    {args.compare}")
    print(f"  Output:     {output_dir}")
    print(f"  Dry run:    {args.dry_run}")
    print(f"  Resume:     {args.resume}")
    print(f"  Quantize:   {args.quantize or 'none (bfloat16)'}")
    print(f"  Timestamp:  {datetime.now().isoformat()}")

    # Get assortments
    assortments = get_sr_assortments()
    if args.dry_run:
        assortments = assortments[:3]
        print(f"\n  DRY RUN: Using {len(assortments)} assortments (of 34)")
    else:
        print(f"\n  Using {len(assortments)} assortments")

    # ---- Phase 1: Extract hidden states for primary model ----
    print(f"\n{'='*70}")
    print(f"PHASE 1: Hidden State Extraction - {args.model}")
    print(f"{'='*70}")

    result_primary = run_extraction(
        model_id=args.model,
        assortments=assortments,
        output_dir=output_dir,
        quantize=args.quantize,
        dry_run=args.dry_run,
    )

    # ---- Phase 2: Extract hidden states for comparison model (if any) ----
    result_compare = None
    if args.compare:
        print(f"\n{'='*70}")
        print(f"PHASE 2: Hidden State Extraction - {args.compare}")
        print(f"{'='*70}")

        result_compare = run_extraction(
            model_id=args.compare,
            assortments=assortments,
            output_dir=output_dir,
            quantize=args.quantize,
            dry_run=args.dry_run,
        )

    # ---- Phase 3: Linear probing ----
    print(f"\n{'='*70}")
    print(f"PHASE 3: Linear Probing")
    print(f"{'='*70}")

    probe_primary = run_probing(
        result_primary, assortments, args.model, output_dir
    )

    probe_compare = None
    if result_compare:
        probe_compare = run_probing(
            result_compare, assortments, args.compare, output_dir
        )

    # ---- Phase 4: Generate figures ----
    print(f"\n{'='*70}")
    print(f"PHASE 4: Visualization")
    print(f"{'='*70}")

    safe_model_name = args.model.replace("/", "_")
    fig_path = output_dir / f"probe_accuracy_{safe_model_name}.png"

    plot_probe_accuracy(
        results=probe_primary,
        model_name=args.model,
        output_path=fig_path,
        comparison_results=probe_compare,
        comparison_name=args.compare,
    )

    # If comparing, also save a combined summary
    if probe_compare:
        fig_path_combined = output_dir / "probe_accuracy_base_vs_instruct.png"
        plot_probe_accuracy(
            results=probe_primary,
            model_name=args.model,
            output_path=fig_path_combined,
            comparison_results=probe_compare,
            comparison_name=args.compare,
        )

    # ---- Phase 5: Summary ----
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")

    summary = {
        "primary_model": args.model,
        "comparison_model": args.compare,
        "n_assortments": len(assortments),
        "dry_run": args.dry_run,
        "timestamp": datetime.now().isoformat(),
        "primary_results": {
            "n_valid": probe_primary.get("n_samples", 0),
            "n_optimal": probe_primary.get("n_optimal", 0),
            "peak_binary_accuracy": probe_primary.get("peak_accuracy_binary"),
            "peak_binary_layer": probe_primary.get("peak_layer_binary"),
            "peak_multiclass_accuracy": probe_primary.get("peak_accuracy_multiclass"),
            "peak_multiclass_layer": probe_primary.get("peak_layer_multiclass"),
            "peak_brand_accuracy": probe_primary.get("peak_accuracy_brand"),
            "peak_brand_layer": probe_primary.get("peak_layer_brand"),
        },
    }

    if probe_compare:
        summary["comparison_results"] = {
            "n_valid": probe_compare.get("n_samples", 0),
            "n_optimal": probe_compare.get("n_optimal", 0),
            "peak_binary_accuracy": probe_compare.get("peak_accuracy_binary"),
            "peak_binary_layer": probe_compare.get("peak_layer_binary"),
            "peak_multiclass_accuracy": probe_compare.get("peak_accuracy_multiclass"),
            "peak_multiclass_layer": probe_compare.get("peak_layer_multiclass"),
            "peak_brand_accuracy": probe_compare.get("peak_accuracy_brand"),
            "peak_brand_layer": probe_compare.get("peak_layer_brand"),
        }

    # Print interpretive summary
    n_valid = summary["primary_results"]["n_valid"]
    n_optimal = summary["primary_results"]["n_optimal"]
    opt_rate = n_optimal / max(n_valid, 1)
    print(f"\n  {args.model}:")
    print(f"    Chose optimal product: {n_optimal}/{n_valid} ({100*opt_rate:.1f}%)")
    print(f"    Peak binary probe:     {summary['primary_results']['peak_binary_accuracy']:.3f} "
          f"(layer {summary['primary_results']['peak_binary_layer']})")
    print(f"    Peak letter probe:     {summary['primary_results']['peak_multiclass_accuracy']:.3f} "
          f"(layer {summary['primary_results']['peak_multiclass_layer']})")
    print(f"    Peak brand probe:      {summary['primary_results']['peak_brand_accuracy']:.3f} "
          f"(layer {summary['primary_results']['peak_brand_layer']})")

    if probe_compare and "error" not in probe_compare:
        n_valid_c = summary["comparison_results"]["n_valid"]
        n_optimal_c = summary["comparison_results"]["n_optimal"]
        opt_rate_c = n_optimal_c / max(n_valid_c, 1)
        print(f"\n  {args.compare}:")
        print(f"    Chose optimal product: {n_optimal_c}/{n_valid_c} ({100*opt_rate_c:.1f}%)")
        print(f"    Peak binary probe:     {summary['comparison_results']['peak_binary_accuracy']:.3f} "
              f"(layer {summary['comparison_results']['peak_binary_layer']})")
        print(f"    Peak letter probe:     {summary['comparison_results']['peak_multiclass_accuracy']:.3f} "
              f"(layer {summary['comparison_results']['peak_multiclass_layer']})")
        print(f"    Peak brand probe:      {summary['comparison_results']['peak_brand_accuracy']:.3f} "
              f"(layer {summary['comparison_results']['peak_brand_layer']})")

        # Interpretation
        peak_diff = abs(
            (summary["primary_results"]["peak_brand_accuracy"] or 0)
            - (summary["comparison_results"]["peak_brand_accuracy"] or 0)
        )
        print(f"\n  Interpretation:")
        if peak_diff < 0.1:
            print(f"    Brand preference encodings are SIMILAR between base and instruct")
            print(f"    (peak brand probe accuracy difference: {peak_diff:.3f})")
            print(f"    -> Consistent with shallow alignment hypothesis (Qi et al. 2025)")
        else:
            print(f"    Brand preference encodings DIFFER between base and instruct")
            print(f"    (peak brand probe accuracy difference: {peak_diff:.3f})")

    # Save summary
    summary_path = output_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n  Summary saved to: {summary_path}")

    # List all output files
    print(f"\n  Output files:")
    for p in sorted(output_dir.iterdir()):
        size_kb = p.stat().st_size / 1024
        print(f"    {p.name} ({size_kb:.0f} KB)")

    print(f"\n{'='*70}")
    print("DONE")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
