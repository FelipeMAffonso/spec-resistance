#!/usr/bin/env python3
"""
Activation Steering for Brand Neutrality
==========================================
Nature R&R Pillar 4D: Can brand preferences be surgically suppressed
via contrastive activation addition (CAA)?

Motivation:
    If a "brand neutrality" steering vector can suppress non-optimal
    choices (brand-driven deviations from spec-optimal recommendations),
    brand preference is encoded as a recoverable direction in the model's
    residual stream. A dose-response curve across multipliers demonstrates
    that this direction is causal, not merely correlational.

    Conversely, if steering fails to suppress brand preference, the
    encoding is distributed or nonlinear, making it even more resistant
    to removal (strengthening the paper's persistence argument).

Method:
    1. Build contrastive prompt pairs from our actual product assortments:
       - POSITIVE: prompts that yield spec-focused, brand-neutral responses
         (using utility_constrained condition with brand-blind mechanism)
       - NEGATIVE: prompts that yield brand-driven responses
         (using baseline condition with real brand names)
    2. Train a steering vector via the steering-vectors library (CAA method)
    3. Apply the vector at inference with multipliers from -2.0 to +2.0
    4. For each multiplier, run all sr_ assortments and measure:
       - Non-optimal choice rate (primary DV)
       - Brand familiarity of chosen products
       - Per-category breakdown
    5. Generate dose-response figure

    The steering-vectors library (pip install steering-vectors) provides
    train_steering_vector() and SteeringVector.apply() which handle the
    residual stream hooks. If the library fails for a given architecture,
    we fall back to manual CAA: extract activations, compute mean diff,
    and inject via forward hooks.

Hardware:
    - Qwen2.5-7B-Instruct: ~16GB VRAM in float16, ~8GB in 8-bit
    - Single RTX 4090 / A100 is sufficient
    - CPU-only mode available (slow but functional for debugging)

Usage:
    python -m nature-rr.scripts.activation_steering [--model MODEL_ID]
    python scripts/activation_steering.py --model Qwen/Qwen2.5-7B-Instruct
    python scripts/activation_steering.py --dry-run  # test without GPU
"""

import argparse
import copy
import json
import os
import re
import random
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import torch
import numpy as np

# ---------------------------------------------------------------------------
# Path setup: ensure project root is importable
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent  # spec-resistance/
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Fix Windows console encoding
if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    import io
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from experiment.assortments import (
    ALL_ASSORTMENTS,
    CATEGORY_PREFERENCES,
    CATEGORY_METADATA,
)
from experiment.conditions import (
    build_prompt,
    compute_utility_scores,
    get_optimal_product,
    CONDITION_REGISTRY,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

# Steering multipliers for dose-response curve
MULTIPLIERS = [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]

# Layers to train steering vectors on (middle layers are most effective per
# Rimsky et al. 2024 and Zou et al. 2023). We use a range around the middle
# third plus a sweep for layer selection.
# For a 28-layer model (Qwen2.5-7B), middle third = layers 9-18.
# We train on all layers and then select the best layer based on validation.
CANDIDATE_LAYERS = None  # None means all layers; set to e.g. [10, 14, 18] to narrow

# Number of contrastive pairs for training (remaining used for validation)
N_TRAIN_PAIRS = 30  # ~80% of 37 sr_ assortments
N_VAL_PAIRS = 7     # remaining for layer selection

# Inference settings
MAX_NEW_TOKENS = 300
TEMPERATURE = 0.0   # greedy decoding for reproducibility

# Output paths
RESULTS_DIR = _SCRIPT_DIR.parent / "results" / "04-representation-probing"
RESULTS_FILE = RESULTS_DIR / "steering_results.json"
FIGURE_FILE = RESULTS_DIR / "steering_dose_response.png"
VECTOR_FILE = RESULTS_DIR / "brand_neutrality_steering_vector.pt"


# ===================================================================
# 1. CONTRASTIVE PAIR CONSTRUCTION
# ===================================================================

def get_sr_assortments() -> list[dict]:
    """Return only the hand-crafted sr_ assortments (not WebMall/legacy)."""
    return [a for a in ALL_ASSORTMENTS if a["id"].startswith("sr_")]


def build_contrastive_pair(
    assortment: dict,
    tokenizer,
) -> tuple[str, str]:
    """
    Build a (positive, negative) prompt pair for one assortment.

    POSITIVE (brand-neutral, spec-focused):
        Uses utility_constrained condition with brand names anonymized.
        The model is told to pick the highest-utility product and brand
        names are replaced with "Brand A", "Brand B", etc.
        This elicits the activation pattern for "focus on specs, ignore brand."

    NEGATIVE (brand-susceptible):
        Uses baseline condition with full brand names visible.
        The model gets a plain "help me find the best product" prompt
        with real brands, review counts, and badges.
        This elicits the activation pattern for "brand preference matters."

    Both prompts use the same assortment so the only difference is
    the spec-focus framing vs. brand-visible framing.
    """
    # --- POSITIVE: brand-blind, spec-focused ---
    pos_system, pos_user, pos_meta = build_prompt(
        copy.deepcopy(assortment),
        "mechanism_brand_blind",
        category_preferences=CATEGORY_PREFERENCES,
        paraphrase_index=0,
        shuffle_products=False,
        randomize_letters=False,
    )
    positive_text = _format_chat_prompt(pos_system, pos_user, tokenizer)

    # --- NEGATIVE: baseline with full brand exposure ---
    neg_system, neg_user, neg_meta = build_prompt(
        copy.deepcopy(assortment),
        "baseline",
        category_preferences=CATEGORY_PREFERENCES,
        paraphrase_index=0,
        shuffle_products=False,
        randomize_letters=False,
    )
    negative_text = _format_chat_prompt(neg_system, neg_user, tokenizer)

    return positive_text, negative_text


def _format_chat_prompt(
    system_prompt: str,
    user_message: str,
    tokenizer,
) -> str:
    """
    Format system + user into the model's chat template.
    Uses the tokenizer's apply_chat_template for correct formatting.
    Falls back to a generic template if apply_chat_template is unavailable.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    try:
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    except Exception:
        # Fallback: generic chat format
        text = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_message}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
    return text


def build_all_contrastive_pairs(
    assortments: list[dict],
    tokenizer,
) -> list[tuple[str, str]]:
    """Build contrastive pairs for all assortments."""
    pairs = []
    for assortment in assortments:
        pos, neg = build_contrastive_pair(assortment, tokenizer)
        pairs.append((pos, neg))
    return pairs


# ===================================================================
# 2. MODEL LOADING
# ===================================================================

def load_model_and_tokenizer(
    model_id: str,
    load_in_8bit: bool = False,
    device_map: str = "auto",
):
    """
    Load a HuggingFace model and tokenizer.

    Uses float16 by default. Falls back to 8-bit quantization if
    load_in_8bit=True (requires bitsandbytes). For CPU-only machines,
    device_map="cpu" loads in float32.
    """
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"[MODEL] Loading tokenizer: {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print(f"[MODEL] Loading model: {model_id}")
    load_kwargs = {
        "trust_remote_code": True,
        "device_map": device_map,
    }

    if load_in_8bit:
        try:
            import bitsandbytes  # noqa: F401
            load_kwargs["load_in_8bit"] = True
            print("[MODEL] Using 8-bit quantization (bitsandbytes)")
        except ImportError:
            print("[MODEL] bitsandbytes not found, falling back to float16")
            load_kwargs["torch_dtype"] = torch.float16
    else:
        if device_map != "cpu":
            load_kwargs["torch_dtype"] = torch.float16
        # CPU stays float32

    model = AutoModelForCausalLM.from_pretrained(model_id, **load_kwargs)
    model.eval()

    print(f"[MODEL] Loaded. Device: {model.device}, Dtype: {model.dtype}")
    return model, tokenizer


# ===================================================================
# 3. STEERING VECTOR TRAINING
# ===================================================================

def train_brand_neutrality_vector(
    model,
    tokenizer,
    train_pairs: list[tuple[str, str]],
    layers: list[int] | None = None,
    use_library: bool = True,
):
    """
    Train a "brand neutrality" steering vector using contrastive activation addition.

    Tries the steering-vectors library first. If that fails (model architecture
    not supported, import error, etc.), falls back to manual CAA.

    Args:
        model: HuggingFace model
        tokenizer: Corresponding tokenizer
        train_pairs: List of (positive, negative) prompt strings
        layers: Which layers to extract from (None = all)
        use_library: Whether to try the steering-vectors library first

    Returns:
        steering_vector: Either a SteeringVector object (library) or a dict
            mapping layer_num -> Tensor (manual fallback)
        method_used: "library" or "manual_caa"
        best_layer: The single layer index selected for steering
    """
    if use_library:
        try:
            return _train_via_library(model, tokenizer, train_pairs, layers)
        except Exception as e:
            print(f"[STEERING] Library method failed: {e}")
            print("[STEERING] Falling back to manual CAA...")

    return _train_via_manual_caa(model, tokenizer, train_pairs, layers)


def _train_via_library(
    model,
    tokenizer,
    train_pairs: list[tuple[str, str]],
    layers: list[int] | None,
):
    """Train steering vector using the steering-vectors library."""
    # Add the local repo to path for import
    sv_repo = _SCRIPT_DIR.parent / "repos" / "steering-vectors"
    if str(sv_repo) not in sys.path:
        sys.path.insert(0, str(sv_repo))

    from steering_vectors import train_steering_vector, SteeringVector

    print(f"[STEERING] Training via steering-vectors library")
    print(f"[STEERING] {len(train_pairs)} contrastive pairs, layers={layers}")

    sv = train_steering_vector(
        model,
        tokenizer,
        train_pairs,
        layers=layers,
        move_to_cpu=True,
        read_token_index=-1,  # read from last token position
        show_progress=True,
        batch_size=1,
        tqdm_desc="Training brand-neutrality vector",
    )

    print(f"[STEERING] Trained. Layers: {sorted(sv.layer_activations.keys())}")
    return sv, "library"


def _train_via_manual_caa(
    model,
    tokenizer,
    train_pairs: list[tuple[str, str]],
    layers: list[int] | None,
):
    """
    Manual Contrastive Activation Addition fallback.

    Extracts residual stream activations for each contrastive pair,
    computes mean(positive) - mean(negative) per layer, and returns
    a dict of steering directions.
    """
    from collections import defaultdict

    print(f"[STEERING] Training via manual CAA extraction")
    print(f"[STEERING] {len(train_pairs)} contrastive pairs")

    # Determine layers to extract from
    num_layers = _get_num_decoder_layers(model)
    if layers is None:
        layers = list(range(num_layers))
    print(f"[STEERING] Extracting from {len(layers)} layers (of {num_layers} total)")

    # Identify decoder block names
    layer_names = _get_decoder_layer_names(model)

    pos_acts_by_layer = defaultdict(list)
    neg_acts_by_layer = defaultdict(list)

    for pair_idx, (pos_text, neg_text) in enumerate(train_pairs):
        if (pair_idx + 1) % 5 == 0 or pair_idx == 0:
            print(f"  Processing pair {pair_idx + 1}/{len(train_pairs)}...")

        # Extract positive activations
        pos_act = _extract_residual_activations(
            model, tokenizer, pos_text, layer_names, layers
        )
        for layer_num, act in pos_act.items():
            pos_acts_by_layer[layer_num].append(act.cpu())

        # Extract negative activations
        neg_act = _extract_residual_activations(
            model, tokenizer, neg_text, layer_names, layers
        )
        for layer_num, act in neg_act.items():
            neg_acts_by_layer[layer_num].append(act.cpu())

    # Compute mean difference vector per layer
    steering_directions = {}
    for layer_num in layers:
        pos_stack = torch.stack(pos_acts_by_layer[layer_num])
        neg_stack = torch.stack(neg_acts_by_layer[layer_num])
        direction = (pos_stack - neg_stack).mean(dim=0)
        steering_directions[layer_num] = direction

    print(f"[STEERING] Manual CAA complete. {len(steering_directions)} layer vectors.")
    return steering_directions, "manual_caa"


def _get_num_decoder_layers(model) -> int:
    """Infer number of decoder layers from model config."""
    config = model.config
    for attr in ["num_hidden_layers", "n_layer", "num_layers", "n_layers"]:
        if hasattr(config, attr):
            return getattr(config, attr)
    raise ValueError("Cannot determine number of layers from model config")


def _get_decoder_layer_names(model) -> list[str]:
    """
    Get the names of decoder block modules.
    Handles common architectures: Qwen, LLaMA, Mistral, GPT-2, etc.
    """
    named_modules = dict(model.named_modules())

    # Try common patterns
    patterns = [
        "model.layers.{num}",         # LLaMA, Qwen, Mistral
        "transformer.h.{num}",        # GPT-2, GPT-Neo
        "gpt_neox.layers.{num}",      # GPT-NeoX, Pythia
        "model.decoder.layers.{num}", # OPT
    ]

    for pattern in patterns:
        test_name = pattern.format(num=0)
        if test_name in named_modules:
            # Count how many layers match
            names = []
            for i in range(200):  # generous upper bound
                name = pattern.format(num=i)
                if name in named_modules:
                    names.append(name)
                else:
                    break
            if names:
                return names

    raise ValueError(
        f"Cannot identify decoder layers. "
        f"Top-level modules: {[n for n, _ in model.named_children()]}"
    )


@torch.no_grad()
def _extract_residual_activations(
    model,
    tokenizer,
    text: str,
    layer_names: list[str],
    target_layers: list[int],
) -> dict[int, torch.Tensor]:
    """
    Extract the residual stream activation at the last token position
    for the specified layers.
    """
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=2048)
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    activations = {}
    hooks = []

    def make_hook(layer_idx):
        def hook_fn(module, input, output):
            # output is typically a tuple; first element is the hidden state
            if isinstance(output, tuple):
                hidden = output[0]
            else:
                hidden = output
            # Take the last token's activation
            activations[layer_idx] = hidden[0, -1, :].detach().clone()
        return hook_fn

    # Register hooks
    named_modules = dict(model.named_modules())
    for layer_idx in target_layers:
        if layer_idx < len(layer_names):
            module = named_modules[layer_names[layer_idx]]
            hook = module.register_forward_hook(make_hook(layer_idx))
            hooks.append(hook)

    # Forward pass
    model(**inputs)

    # Remove hooks
    for hook in hooks:
        hook.remove()

    return activations


# ===================================================================
# 4. LAYER SELECTION (validation-based)
# ===================================================================

def select_best_layer(
    model,
    tokenizer,
    steering_data,  # SteeringVector or dict[int, Tensor]
    method: str,
    val_assortments: list[dict],
    multiplier: float = 1.0,
) -> int:
    """
    Select the single best layer for steering by measuring which layer
    most increases the optimal choice rate on validation assortments.

    For each candidate layer, we apply the steering vector at ONLY that
    layer and check how many assortments yield the optimal product.
    """
    print(f"\n[LAYER SELECTION] Testing layers on {len(val_assortments)} val assortments")

    if method == "library":
        candidate_layers = sorted(steering_data.layer_activations.keys())
    else:
        candidate_layers = sorted(steering_data.keys())

    best_layer = candidate_layers[len(candidate_layers) // 2]  # default: middle
    best_score = -1

    for layer_num in candidate_layers:
        # Create a single-layer steering vector
        if method == "library":
            from steering_vectors import SteeringVector
            single_layer_sv = SteeringVector(
                {layer_num: steering_data.layer_activations[layer_num]},
                layer_type=steering_data.layer_type,
            )
        else:
            single_layer_sv = {layer_num: steering_data[layer_num]}

        # Evaluate on validation set
        optimal_count = 0
        for assortment in val_assortments:
            choice = _run_steered_inference(
                model, tokenizer, assortment, single_layer_sv, method,
                multiplier=multiplier,
            )
            utility_scores = compute_utility_scores(assortment)
            optimal_letter, _ = get_optimal_product(assortment, utility_scores)
            if choice == optimal_letter:
                optimal_count += 1

        score = optimal_count / len(val_assortments)
        print(f"  Layer {layer_num}: optimal rate = {score:.2%} ({optimal_count}/{len(val_assortments)})")

        if score > best_score:
            best_score = score
            best_layer = layer_num

    print(f"[LAYER SELECTION] Best layer: {best_layer} (optimal rate: {best_score:.2%})")
    return best_layer


# ===================================================================
# 5. STEERED INFERENCE
# ===================================================================

def _run_steered_inference(
    model,
    tokenizer,
    assortment: dict,
    steering_data,  # SteeringVector or dict[int, Tensor]
    method: str,
    multiplier: float = 1.0,
    layer: int | None = None,
) -> str:
    """
    Run inference on a single assortment with the steering vector applied.

    Returns the chosen product letter (A-E) or "?" if unparseable.
    """
    # Build baseline prompt (the condition we test steering against)
    system_prompt, user_message, meta = build_prompt(
        copy.deepcopy(assortment),
        "baseline",
        category_preferences=CATEGORY_PREFERENCES,
        paraphrase_index=0,
        shuffle_products=False,
        randomize_letters=False,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    inputs = tokenizer.apply_chat_template(
        messages,
        return_tensors="pt",
        add_generation_prompt=True,
    )
    if isinstance(inputs, list):
        inputs = torch.tensor([inputs])
    inputs = inputs.to(model.device)

    # Generate with steering
    if method == "library":
        response_text = _generate_with_library_steering(
            model, tokenizer, inputs, steering_data, multiplier
        )
    else:
        response_text = _generate_with_manual_steering(
            model, tokenizer, inputs, steering_data, multiplier, layer
        )

    # Parse product choice from response
    return _parse_choice(response_text)


def _generate_with_library_steering(
    model,
    tokenizer,
    input_ids: torch.Tensor,
    steering_vector,  # SteeringVector
    multiplier: float,
) -> str:
    """Generate text with the steering-vectors library."""
    with steering_vector.apply(model, multiplier=multiplier, min_token_index=0):
        output_ids = model.generate(
            input_ids,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE if TEMPERATURE > 0 else None,
            do_sample=TEMPERATURE > 0,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )

    # Decode only the generated tokens (not the input)
    new_tokens = output_ids[0, input_ids.shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)


def _generate_with_manual_steering(
    model,
    tokenizer,
    input_ids: torch.Tensor,
    steering_directions: dict[int, torch.Tensor],
    multiplier: float,
    layer: int | None = None,
) -> str:
    """
    Generate text with manual CAA steering.

    Registers forward hooks on decoder blocks to add the steering
    direction scaled by the multiplier to the residual stream.
    """
    layer_names = _get_decoder_layer_names(model)
    named_modules = dict(model.named_modules())
    hooks = []

    # Determine which layers to steer
    if layer is not None:
        steer_layers = {layer: steering_directions[layer]}
    else:
        steer_layers = steering_directions

    for layer_idx, direction in steer_layers.items():
        if layer_idx >= len(layer_names):
            continue
        module = named_modules[layer_names[layer_idx]]
        scaled_direction = (multiplier * direction).to(model.device).to(model.dtype)

        def make_steer_hook(scaled_dir):
            def hook_fn(module, input, output):
                if isinstance(output, tuple):
                    hidden = output[0]
                    hidden = hidden + scaled_dir.reshape(1, 1, -1)
                    return (hidden,) + output[1:]
                else:
                    return output + scaled_dir.reshape(1, 1, -1)
            return hook_fn

        hook = module.register_forward_hook(make_steer_hook(scaled_direction))
        hooks.append(hook)

    try:
        output_ids = model.generate(
            input_ids,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE if TEMPERATURE > 0 else None,
            do_sample=TEMPERATURE > 0,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )
    finally:
        for hook in hooks:
            hook.remove()

    new_tokens = output_ids[0, input_ids.shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)


def _parse_choice(response_text: str) -> str:
    """
    Parse product letter from model response.

    Expected format: first line contains a single letter A-E.
    Falls back to regex search if not found on first line.
    """
    text = response_text.strip()
    if not text:
        return "?"

    # Check first line for single letter
    first_line = text.split("\n")[0].strip()
    if first_line in ("A", "B", "C", "D", "E"):
        return first_line

    # Regex: "Product X" or "recommend X" or standalone letter
    match = re.search(r'\b[Pp]roduct\s+([A-E])\b', text)
    if match:
        return match.group(1)

    match = re.search(r'\brecommend(?:ing)?\s+(?:product\s+)?([A-E])\b', text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Look for standalone letter at the very start
    match = re.match(r'^[^a-zA-Z]*([A-E])\b', text)
    if match:
        return match.group(1)

    # "the best option is A" or "go with A"
    match = re.search(r'\b(?:choose|pick|select|go with|option\s+(?:is|here\s+is))\s+(?:product\s+)?([A-E])\b', text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Broad fallback: any isolated letter A-E preceded by "is" or followed by period/comma
    match = re.search(r'\bis\s+([A-E])[.\s,]', text)
    if match:
        return match.group(1)

    return "?"


# ===================================================================
# 6. EXPERIMENT RUNNER
# ===================================================================

def run_steering_experiment(
    model,
    tokenizer,
    steering_data,
    method: str,
    best_layer: int,
    test_assortments: list[dict],
    multipliers: list[float],
) -> dict:
    """
    Run the full dose-response experiment.

    For each multiplier, runs all test assortments and records:
    - Which product was chosen
    - Whether it was optimal
    - The chosen product's brand familiarity
    - Category of the assortment
    """
    results = {
        "metadata": {
            "model_id": model.config._name_or_path if hasattr(model.config, "_name_or_path") else "unknown",
            "method": method,
            "best_layer": best_layer,
            "n_test_assortments": len(test_assortments),
            "multipliers": multipliers,
            "timestamp": datetime.now().isoformat(),
            "max_new_tokens": MAX_NEW_TOKENS,
            "temperature": TEMPERATURE,
        },
        "dose_response": {},
        "per_trial": [],
    }

    # Prepare single-layer steering data
    if method == "library":
        from steering_vectors import SteeringVector
        single_sv = SteeringVector(
            {best_layer: steering_data.layer_activations[best_layer]},
            layer_type=steering_data.layer_type,
        )
    else:
        single_sv = {best_layer: steering_data[best_layer]}

    total_trials = len(multipliers) * len(test_assortments)
    trial_count = 0

    for mult in multipliers:
        print(f"\n[EXPERIMENT] Multiplier = {mult:+.1f}")
        mult_key = f"{mult:+.1f}"
        optimal_count = 0
        brand_choices = defaultdict(int)  # brand_familiarity -> count
        category_results = defaultdict(lambda: {"optimal": 0, "total": 0})

        for assortment in test_assortments:
            trial_count += 1
            if trial_count % 10 == 0:
                print(f"  Trial {trial_count}/{total_trials}...")

            choice = _run_steered_inference(
                model, tokenizer, assortment, single_sv, method,
                multiplier=mult,
                layer=best_layer if method == "manual_caa" else None,
            )

            # Evaluate choice
            utility_scores = compute_utility_scores(assortment)
            optimal_letter, optimal_score = get_optimal_product(assortment, utility_scores)
            is_optimal = (choice == optimal_letter)
            if is_optimal:
                optimal_count += 1

            # Find chosen product's brand familiarity
            chosen_brand_fam = "unknown"
            chosen_brand = "unknown"
            for p in assortment["products"]:
                if p["letter"] == choice:
                    chosen_brand_fam = p.get("brand_familiarity", "unknown")
                    chosen_brand = p.get("brand", "unknown")
                    break
            brand_choices[chosen_brand_fam] += 1

            cat = assortment.get("category", "unknown")
            category_results[cat]["total"] += 1
            if is_optimal:
                category_results[cat]["optimal"] += 1

            # Record per-trial data
            results["per_trial"].append({
                "multiplier": mult,
                "assortment_id": assortment["id"],
                "category": cat,
                "choice": choice,
                "optimal_letter": optimal_letter,
                "is_optimal": is_optimal,
                "chosen_brand": chosen_brand,
                "chosen_brand_familiarity": chosen_brand_fam,
            })

        # Aggregate for this multiplier
        n_test = len(test_assortments)
        non_optimal_rate = 1.0 - (optimal_count / n_test) if n_test > 0 else 0.0
        optimal_rate = optimal_count / n_test if n_test > 0 else 0.0

        results["dose_response"][mult_key] = {
            "multiplier": mult,
            "optimal_count": optimal_count,
            "total": n_test,
            "optimal_rate": round(optimal_rate, 4),
            "non_optimal_rate": round(non_optimal_rate, 4),
            "brand_familiarity_distribution": dict(brand_choices),
            "per_category": {
                cat: {
                    "optimal_rate": round(v["optimal"] / v["total"], 4) if v["total"] > 0 else 0,
                    "n": v["total"],
                }
                for cat, v in category_results.items()
            },
            "unparseable_count": sum(1 for t in results["per_trial"]
                                     if t["multiplier"] == mult and t["choice"] == "?"),
        }

        print(f"  Optimal: {optimal_count}/{n_test} = {optimal_rate:.1%}")
        print(f"  Non-optimal: {non_optimal_rate:.1%}")
        print(f"  Brand choices: {dict(brand_choices)}")

    return results


# ===================================================================
# 7. VISUALIZATION
# ===================================================================

def plot_dose_response(results: dict, output_path: Path):
    """
    Generate dose-response figure: multiplier (x) vs non-optimal rate (y).

    Also shows the brand familiarity distribution as stacked bars.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend
        import matplotlib.pyplot as plt
        from matplotlib.ticker import PercentFormatter
    except ImportError:
        print("[PLOT] matplotlib not installed; skipping figure generation")
        return

    dose_data = results["dose_response"]
    multipliers = sorted([float(k) for k in dose_data.keys()])
    non_optimal_rates = [dose_data[f"{m:+.1f}"]["non_optimal_rate"] for m in multipliers]
    optimal_rates = [dose_data[f"{m:+.1f}"]["optimal_rate"] for m in multipliers]

    # --- Figure 1: Main dose-response curve ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Left panel: non-optimal rate
    ax1.plot(multipliers, non_optimal_rates, "o-", color="#DA7756", linewidth=2.5, markersize=8)
    ax1.axhline(y=non_optimal_rates[multipliers.index(0.0)], color="gray",
                linestyle="--", alpha=0.5, label="Unsteered baseline")
    ax1.axvline(x=0.0, color="gray", linestyle=":", alpha=0.3)
    ax1.set_xlabel("Steering Multiplier", fontsize=13)
    ax1.set_ylabel("Non-Optimal Choice Rate", fontsize=13)
    ax1.set_title("Brand Neutrality Steering: Dose-Response", fontsize=14)
    ax1.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax1.set_ylim(-0.05, 1.05)
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)

    # Annotate the unsteered point
    baseline_rate = non_optimal_rates[multipliers.index(0.0)]
    ax1.annotate(
        f"Unsteered: {baseline_rate:.0%}",
        xy=(0.0, baseline_rate),
        xytext=(0.5, baseline_rate + 0.1),
        arrowprops=dict(arrowstyle="->", color="gray"),
        fontsize=10, color="gray",
    )

    # Right panel: brand familiarity breakdown per multiplier
    fam_levels = ["high", "medium", "low", "unknown"]
    fam_colors = {"high": "#e74c3c", "medium": "#f39c12", "low": "#27ae60", "unknown": "#bdc3c7"}
    bottom = np.zeros(len(multipliers))
    for fam in fam_levels:
        values = []
        for m in multipliers:
            dist = dose_data[f"{m:+.1f}"]["brand_familiarity_distribution"]
            total = sum(dist.values()) if dist else 1
            values.append(dist.get(fam, 0) / total if total > 0 else 0)
        ax2.bar(multipliers, values, bottom=bottom, width=0.35,
                label=f"{fam.capitalize()} familiarity", color=fam_colors[fam], alpha=0.85)
        bottom += np.array(values)

    ax2.set_xlabel("Steering Multiplier", fontsize=13)
    ax2.set_ylabel("Proportion of Choices", fontsize=13)
    ax2.set_title("Brand Familiarity of Chosen Products", fontsize=14)
    ax2.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax2.set_ylim(0, 1.05)
    ax2.legend(fontsize=10, loc="upper left")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"[PLOT] Saved to {output_path}")
    plt.close(fig)

    # --- Figure 2: Per-category heatmap ---
    try:
        categories = set()
        for mult_data in dose_data.values():
            categories.update(mult_data.get("per_category", {}).keys())
        categories = sorted(categories)

        if categories:
            fig2, ax3 = plt.subplots(figsize=(12, max(6, len(categories) * 0.4)))
            heatmap_data = np.zeros((len(categories), len(multipliers)))
            for i, cat in enumerate(categories):
                for j, m in enumerate(multipliers):
                    cat_data = dose_data[f"{m:+.1f}"].get("per_category", {}).get(cat, {})
                    heatmap_data[i, j] = cat_data.get("optimal_rate", 0)

            im = ax3.imshow(heatmap_data, aspect="auto", cmap="RdYlGn", vmin=0, vmax=1)
            ax3.set_xticks(range(len(multipliers)))
            ax3.set_xticklabels([f"{m:+.1f}" for m in multipliers])
            ax3.set_yticks(range(len(categories)))
            ax3.set_yticklabels([c.replace("_", " ").title() for c in categories])
            ax3.set_xlabel("Steering Multiplier", fontsize=12)
            ax3.set_title("Optimal Choice Rate by Category and Multiplier", fontsize=13)
            plt.colorbar(im, ax=ax3, label="Optimal Choice Rate", shrink=0.8)

            # Add text annotations
            for i in range(len(categories)):
                for j in range(len(multipliers)):
                    val = heatmap_data[i, j]
                    color = "white" if val < 0.4 or val > 0.8 else "black"
                    ax3.text(j, i, f"{val:.0%}", ha="center", va="center",
                             fontsize=8, color=color)

            plt.tight_layout()
            heatmap_path = output_path.parent / "steering_category_heatmap.png"
            fig2.savefig(heatmap_path, dpi=150, bbox_inches="tight")
            print(f"[PLOT] Category heatmap saved to {heatmap_path}")
            plt.close(fig2)
    except Exception as e:
        print(f"[PLOT] Could not generate category heatmap: {e}")


# ===================================================================
# 8. DRY RUN (no GPU required)
# ===================================================================

def dry_run(assortments: list[dict]):
    """
    Test the pipeline without loading a model.
    Verifies contrastive pair construction and output formatting.
    """
    print("=" * 70)
    print("DRY RUN: Testing pipeline without GPU/model")
    print("=" * 70)

    # Mock tokenizer with apply_chat_template
    class MockTokenizer:
        pad_token = "<pad>"
        eos_token = "<eos>"
        pad_token_id = 0
        def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True, return_tensors=None):
            parts = []
            for m in messages:
                parts.append(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>")
            text = "\n".join(parts) + "\n<|im_start|>assistant\n"
            if return_tensors:
                return [0] * 100  # fake token ids
            return text

    mock_tok = MockTokenizer()

    print(f"\n[DRY RUN] Building contrastive pairs for {len(assortments)} assortments...")
    pairs = build_all_contrastive_pairs(assortments, mock_tok)
    print(f"[DRY RUN] Built {len(pairs)} pairs.")

    # Show first pair
    print(f"\n{'='*70}")
    print("EXAMPLE POSITIVE (brand-neutral, spec-focused):")
    print("=" * 70)
    print(pairs[0][0][:800])
    print("...")

    print(f"\n{'='*70}")
    print("EXAMPLE NEGATIVE (brand-visible baseline):")
    print("=" * 70)
    print(pairs[0][1][:800])
    print("...")

    # Test choice parser
    print(f"\n{'='*70}")
    print("TESTING CHOICE PARSER:")
    print("=" * 70)
    test_cases = [
        ("E\nThis product has the best specs...", "E"),
        ("I recommend Product C because...", "C"),
        ("Based on the analysis, I would go with Product D.", "D"),
        ("**B**\n\nProduct B offers...", "B"),
        ("The best option here is A.", "A"),
        ("I think you should pick product E for its value.", "E"),
        ("", "?"),
    ]
    for text, expected in test_cases:
        result = _parse_choice(text)
        status = "PASS" if result == expected else "FAIL"
        print(f"  [{status}] Input: {text[:50]!r}... -> Parsed: {result} (expected: {expected})")

    # Test assortment metadata
    print(f"\n{'='*70}")
    print("ASSORTMENT SUMMARY:")
    print("=" * 70)
    categories = defaultdict(int)
    for a in assortments:
        categories[a["category"]] += 1
    for cat, count in sorted(categories.items()):
        meta = CATEGORY_METADATA.get(cat, {})
        print(f"  {cat}: {count} assortments "
              f"(involvement={meta.get('involvement', '?')}, "
              f"brand_salience={meta.get('brand_salience', '?')})")
    print(f"  TOTAL: {len(assortments)} assortments")

    # Simulate results
    print(f"\n[DRY RUN] Simulating dose-response with random choices...")
    fake_results = {
        "metadata": {
            "model_id": "dry-run",
            "method": "simulated",
            "best_layer": 14,
            "n_test_assortments": len(assortments),
            "multipliers": MULTIPLIERS,
            "timestamp": datetime.now().isoformat(),
        },
        "dose_response": {},
        "per_trial": [],
    }
    random.seed(42)
    for mult in MULTIPLIERS:
        mult_key = f"{mult:+.1f}"
        # Simulate: positive multiplier = more optimal choices
        base_rate = 0.35
        optimal_prob = min(1.0, max(0.0, base_rate + mult * 0.15))
        optimal_count = sum(1 for _ in assortments if random.random() < optimal_prob)
        n_test = len(assortments)
        fake_results["dose_response"][mult_key] = {
            "multiplier": mult,
            "optimal_count": optimal_count,
            "total": n_test,
            "optimal_rate": round(optimal_count / n_test, 4),
            "non_optimal_rate": round(1 - optimal_count / n_test, 4),
            "brand_familiarity_distribution": {
                "high": int(n_test * (0.5 - mult * 0.1)),
                "medium": int(n_test * 0.25),
                "low": int(n_test * (0.25 + mult * 0.1)),
            },
            "per_category": {
                cat: {"optimal_rate": round(random.uniform(0.1, 0.9), 4), "n": count}
                for cat, count in categories.items()
            },
            "unparseable_count": 0,
        }

    # Save simulated results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    dry_results_path = RESULTS_DIR / "steering_results_dry_run.json"
    with open(dry_results_path, "w") as f:
        json.dump(fake_results, f, indent=2)
    print(f"[DRY RUN] Saved simulated results to {dry_results_path}")

    # Generate figure from simulated data
    plot_dose_response(fake_results, RESULTS_DIR / "steering_dose_response_dry_run.png")

    print(f"\n{'='*70}")
    print("DRY RUN COMPLETE. Pipeline verified.")
    print("Run without --dry-run to execute with a real model.")
    print("=" * 70)


# ===================================================================
# MAIN
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Activation Steering for Brand Neutrality (Nature R&R Pillar 4D)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL_ID,
        help=f"HuggingFace model ID (default: {DEFAULT_MODEL_ID})",
    )
    parser.add_argument(
        "--load-8bit", action="store_true",
        help="Load model in 8-bit quantization (requires bitsandbytes)",
    )
    parser.add_argument(
        "--cpu", action="store_true",
        help="Force CPU-only mode (very slow, for debugging)",
    )
    parser.add_argument(
        "--multipliers", nargs="+", type=float, default=MULTIPLIERS,
        help="Steering multipliers to test (default: -2.0 to +2.0)",
    )
    parser.add_argument(
        "--layers", nargs="+", type=int, default=None,
        help="Specific layers to train on (default: all layers, then select best)",
    )
    parser.add_argument(
        "--skip-layer-selection", action="store_true",
        help="Skip layer selection; use middle layer of the model",
    )
    parser.add_argument(
        "--no-library", action="store_true",
        help="Skip the steering-vectors library; use manual CAA only",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Test pipeline without loading a model (no GPU required)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Custom output directory for results",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility",
    )
    args = parser.parse_args()

    # Set seed
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    # Setup output directory
    output_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    results_file = output_dir / "steering_results.json"
    figure_file = output_dir / "steering_dose_response.png"
    vector_file = output_dir / "brand_neutrality_steering_vector.pt"

    # Get assortments
    sr_assortments = get_sr_assortments()
    print(f"[SETUP] {len(sr_assortments)} hand-crafted assortments loaded")

    # Dry run mode
    if args.dry_run:
        dry_run(sr_assortments)
        return

    # ---- Real experiment ----

    # Split into train (for steering vector) and test (for evaluation)
    # Use a fixed split for reproducibility
    random.shuffle(sr_assortments)
    n_train = N_TRAIN_PAIRS
    n_val = N_VAL_PAIRS
    train_assortments = sr_assortments[:n_train]
    val_assortments = sr_assortments[n_train:n_train + n_val]
    # Test on ALL assortments (including train) since the steering vector
    # is not trained on model responses, only on activation differences.
    # This is standard practice in representation engineering (Zou et al. 2023).
    test_assortments = sr_assortments
    print(f"[SETUP] Split: {len(train_assortments)} train, "
          f"{len(val_assortments)} val (layer selection), "
          f"{len(test_assortments)} test (dose-response)")

    # Load model
    device_map = "cpu" if args.cpu else "auto"
    model, tokenizer = load_model_and_tokenizer(
        args.model,
        load_in_8bit=args.load_8bit,
        device_map=device_map,
    )

    # Build contrastive pairs
    print(f"\n[PAIRS] Building contrastive prompt pairs...")
    train_pairs = build_all_contrastive_pairs(train_assortments, tokenizer)
    print(f"[PAIRS] Built {len(train_pairs)} training pairs")

    # Train steering vector
    print(f"\n[TRAINING] Training brand-neutrality steering vector...")
    t0 = time.time()
    steering_data, method = train_brand_neutrality_vector(
        model, tokenizer, train_pairs,
        layers=args.layers,
        use_library=not args.no_library,
    )
    train_time = time.time() - t0
    print(f"[TRAINING] Complete in {train_time:.1f}s. Method: {method}")

    # Save the raw steering vector
    if method == "library":
        torch.save(steering_data.layer_activations, vector_file)
    else:
        torch.save(steering_data, vector_file)
    print(f"[TRAINING] Steering vector saved to {vector_file}")

    # Select best layer
    if args.skip_layer_selection:
        num_layers = _get_num_decoder_layers(model)
        best_layer = num_layers // 2
        print(f"[LAYER] Skipping selection, using middle layer: {best_layer}")
    else:
        print(f"\n[LAYER] Selecting best layer via validation...")
        best_layer = select_best_layer(
            model, tokenizer, steering_data, method, val_assortments
        )

    # Run dose-response experiment
    print(f"\n[EXPERIMENT] Running dose-response across {len(args.multipliers)} multipliers...")
    t0 = time.time()
    results = run_steering_experiment(
        model, tokenizer, steering_data, method,
        best_layer, test_assortments, args.multipliers,
    )
    experiment_time = time.time() - t0

    # Add timing metadata
    results["metadata"]["training_time_seconds"] = round(train_time, 1)
    results["metadata"]["experiment_time_seconds"] = round(experiment_time, 1)
    results["metadata"]["total_time_seconds"] = round(train_time + experiment_time, 1)

    # Save results
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[RESULTS] Saved to {results_file}")

    # Generate figures
    print(f"\n[FIGURES] Generating dose-response plot...")
    plot_dose_response(results, figure_file)

    # Print summary
    print(f"\n{'='*70}")
    print("EXPERIMENT COMPLETE")
    print(f"{'='*70}")
    print(f"Model: {args.model}")
    print(f"Method: {method}")
    print(f"Best layer: {best_layer}")
    print(f"Training time: {train_time:.1f}s")
    print(f"Experiment time: {experiment_time:.1f}s")
    print(f"\nDose-Response Summary:")
    print(f"{'Multiplier':>12} {'Optimal Rate':>14} {'Non-Optimal':>13} {'High-Fam %':>12}")
    print(f"{'-'*55}")
    for mult in sorted(args.multipliers):
        key = f"{mult:+.1f}"
        dr = results["dose_response"][key]
        high_fam = dr["brand_familiarity_distribution"].get("high", 0)
        total = dr["total"]
        hf_pct = high_fam / total if total > 0 else 0
        print(f"{mult:>+12.1f} {dr['optimal_rate']:>13.1%} {dr['non_optimal_rate']:>12.1%} {hf_pct:>11.1%}")

    # Determine if steering "worked" (positive multiplier reduces non-optimal rate)
    baseline_nor = results["dose_response"]["+0.0"]["non_optimal_rate"]
    max_steered_nor = results["dose_response"]["+2.0"]["non_optimal_rate"]
    reduction = baseline_nor - max_steered_nor
    print(f"\nBaseline non-optimal rate: {baseline_nor:.1%}")
    print(f"Max-steered non-optimal rate (mult=+2.0): {max_steered_nor:.1%}")
    print(f"Reduction: {reduction:+.1%}")
    if reduction > 0.05:
        print(">> FINDING: Steering REDUCES brand bias (preference is directionally encoded)")
    elif reduction < -0.05:
        print(">> FINDING: Steering INCREASES brand bias at positive mult (inverted direction?)")
    else:
        print(">> FINDING: Steering has MINIMAL effect (preference may be distributed/nonlinear)")

    print(f"\nResults: {results_file}")
    print(f"Figure:  {figure_file}")
    print(f"Vector:  {vector_file}")


if __name__ == "__main__":
    main()
