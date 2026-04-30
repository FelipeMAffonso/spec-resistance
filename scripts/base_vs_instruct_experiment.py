#!/usr/bin/env python3
"""
Base vs. Instruct Model Comparison Experiment
==============================================
Nature R&R Pillar 1B: Does RLHF alignment remove pre-trained brand preferences?

Motivation:
    If brand preferences are similar in base (pre-RLHF) and instruct (post-RLHF)
    versions of the same model, alignment did not remove them. This directly
    addresses Nature concern #2 ("whether this survives post-training").

Design:
    - 4 model families, each tested in base and instruct variants
    - Baseline condition only (no utility specifications)
    - All 34 sr_ assortments x 20 trials per assortment per model = 680 trials/model
    - 8 models total -> 5,440 trials
    - All models run via OpenRouter (unified API for open-source models)

Base model inference note:
    Base (non-instruct) models have no chat template. They are pure text
    completion models that predict the next token given a prompt. OpenRouter
    handles this transparently: when you send a chat-formatted request to a
    base model endpoint, OpenRouter converts it to a raw completion call
    internally. The model receives the concatenated text as a single prompt
    and generates a continuation. This means we can use the same OpenAI-compatible
    chat API for both base and instruct models without manual prompt formatting.

    However, base models may produce less structured output because they were
    never trained on instruction-following. The response parser must handle:
    - No clear letter-on-first-line format (model may ramble before choosing)
    - Multiple product mentions before settling on a recommendation
    - Stream-of-consciousness text rather than structured recommendation
    The existing parse_product_choice() handles this via regex fallback, but
    we also add a more aggressive extraction pass for base model outputs.

Estimated cost:
    Base models on OpenRouter: ~$0.05-0.20/M tokens
    ~680 trials/model x 8 models x ~1500 tokens/trial = ~8.16M tokens
    Estimated total: $2-10

Usage:
    python -m nature-rr.scripts.base_vs_instruct_experiment [--dry-run] [--trials N]
    # or from project root:
    python scripts/base_vs_instruct_experiment.py [--dry-run] [--trials 20]
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

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

from harness.core import load_env, check_providers, call_model_with_retry, API_CALL_DELAY
from harness.cost_tracker import CostTracker, BudgetExceededError
from harness.shopping_agent import parse_product_choice
from config.models import compute_cost, PRICING

from experiment.conditions import build_prompt, CONDITION_REGISTRY
from experiment.assortments import (
    ALL_ASSORTMENTS, CATEGORY_PREFERENCES, CATEGORY_METADATA,
)


# ===================================================================
# MODEL REGISTRY: BASE vs INSTRUCT PAIRS
# ===================================================================
# Base models require Together AI (https://api.together.ai) -- the only
# major provider hosting raw pretrained models via API.
# Instruct models can use OpenRouter or Together AI.
#
# If TOGETHER_API_KEY is not set, base models are skipped and only
# instruct models run (on whichever provider is available).
#
# If OPENROUTER_API_KEY hits 402 (credit exhaustion), instruct models
# fall back to Together AI if available.

BASE_INSTRUCT_MODELS = {
    # --- Qwen 2.5 7B ---
    "qwen-2.5-7b-base": {
        "provider": "together",
        "model_id": "Qwen/Qwen2.5-7B",
        "thinking": False,
        "is_base": True,
        "family": "qwen-2.5-7b",
        "param_count": "7B",
    },
    "qwen-2.5-7b-instruct": {
        "provider": "together",
        "model_id": "Qwen/Qwen2.5-7B-Instruct",
        "thinking": False,
        "is_base": False,
        "family": "qwen-2.5-7b",
        "param_count": "7B",
    },

    # --- Llama 3.1 8B ---
    "llama-3.1-8b-base": {
        "provider": "together",
        "model_id": "meta-llama/Meta-Llama-3.1-8B",
        "thinking": False,
        "is_base": True,
        "family": "llama-3.1-8b",
        "param_count": "8B",
    },
    "llama-3.1-8b-instruct": {
        "provider": "together",
        "model_id": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "thinking": False,
        "is_base": False,
        "family": "llama-3.1-8b",
        "param_count": "8B",
    },

    # --- Gemma 2 9B ---
    "gemma-2-9b-base": {
        "provider": "together",
        "model_id": "google/gemma-2-9b",
        "thinking": False,
        "is_base": True,
        "family": "gemma-2-9b",
        "param_count": "9B",
    },
    "gemma-2-9b-instruct": {
        "provider": "together",
        "model_id": "google/gemma-2-9b-it",
        "thinking": False,
        "is_base": False,
        "family": "gemma-2-9b",
        "param_count": "9B",
    },

    # --- Mistral 7B v0.3 ---
    "mistral-7b-base": {
        "provider": "together",
        "model_id": "mistralai/Mistral-7B-v0.3",
        "thinking": False,
        "is_base": True,
        "family": "mistral-7b",
        "param_count": "7B",
    },
    "mistral-7b-instruct": {
        "provider": "together",
        "model_id": "mistralai/Mistral-7B-Instruct-v0.3",
        "thinking": False,
        "is_base": False,
        "family": "mistral-7b",
        "param_count": "7B",
    },
}

# Pricing per 1M tokens (input, output)
# Together AI: base models ~$0.10, instruct ~$0.10-0.20
BASE_MODEL_PRICING = {
    # Together AI base models
    "Qwen/Qwen2.5-7B":                       (0.10, 0.10),
    "meta-llama/Meta-Llama-3.1-8B":           (0.10, 0.10),
    "google/gemma-2-9b":                      (0.10, 0.10),
    "mistralai/Mistral-7B-v0.3":              (0.10, 0.10),
    # Together AI instruct models
    "Qwen/Qwen2.5-7B-Instruct":              (0.10, 0.10),
    "meta-llama/Meta-Llama-3.1-8B-Instruct":  (0.10, 0.10),
    "google/gemma-2-9b-it":                   (0.10, 0.10),
    "mistralai/Mistral-7B-Instruct-v0.3":     (0.10, 0.10),
}

# Merge into global pricing for compute_cost() to work
PRICING.update(BASE_MODEL_PRICING)


# ===================================================================
# ASSORTMENT FILTERING (only sr_ assortments, matching main experiment)
# ===================================================================

def get_sr_assortments() -> list[dict]:
    """Return the 34 sr_ assortments used in the main experiment."""
    return [a for a in ALL_ASSORTMENTS if a["id"].startswith("sr_")]


# ===================================================================
# BASE MODEL RESPONSE PARSING
# ===================================================================

def parse_base_model_response(raw_text: str, product_names: dict) -> dict:
    """
    Parse a base model's response to extract a product choice.

    Base models produce unstructured completions rather than formatted
    recommendations. This parser applies multiple extraction strategies
    in order of confidence:

    1. Standard parse (works if model happens to output letter first)
    2. "I recommend Product X" / "I would choose X" pattern matching
    3. Last-mentioned product letter (base models often ramble then conclude)
    4. Most-mentioned product letter (frequency-based fallback)

    Returns dict with 'choice' (letter or '?') and 'reasoning' (raw text).
    """
    # Try the standard parser first (handles well-formatted output)
    standard = parse_product_choice(raw_text, product_names=product_names)
    if standard["choice"] != "?":
        return standard

    # Strategy 2: look for recommendation patterns in the text
    recommend_patterns = [
        r"(?:I\s+)?(?:recommend|suggest|choose|pick|go\s+with|select)\s+(?:Product\s+)?([A-E])\b",
        r"(?:Product\s+)?([A-E])\s+(?:is|would\s+be)\s+(?:the\s+)?(?:best|top|optimal|recommended)",
        r"(?:my|the)\s+(?:top\s+)?(?:recommendation|choice|pick)\s+(?:is|would\s+be)\s+(?:Product\s+)?([A-E])\b",
        r"(?:best\s+option|best\s+product|winner)\s+(?:is|:)\s*(?:Product\s+)?([A-E])\b",
    ]
    for pattern in recommend_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            letter = match.group(1).upper()
            return {"choice": letter, "reasoning": raw_text}

    # Strategy 3: look for product names mentioned as recommendations
    for letter, name in product_names.items():
        # Check if the product name appears near recommendation language
        name_pattern = rf"(?:recommend|suggest|choose|best)\s+.*?{re.escape(name)}"
        if re.search(name_pattern, raw_text, re.IGNORECASE):
            return {"choice": letter, "reasoning": raw_text}

    # Strategy 4: last-mentioned product letter
    all_letters = re.findall(r"\bProduct\s+([A-E])\b", raw_text)
    if not all_letters:
        all_letters = re.findall(r"\b([A-E])\b", raw_text)
    if all_letters:
        return {"choice": all_letters[-1].upper(), "reasoning": raw_text}

    # Strategy 5: most-mentioned product letter
    letter_counts = {}
    for letter in "ABCDE":
        count = len(re.findall(rf"\b{letter}\b", raw_text))
        if count > 0:
            letter_counts[letter] = count
    if letter_counts:
        best = max(letter_counts, key=letter_counts.get)
        return {"choice": best, "reasoning": raw_text}

    # Give up
    return {"choice": "?", "reasoning": raw_text}


# ===================================================================
# THREAD SAFETY
# ===================================================================

_csv_lock = threading.Lock()
_print_lock = threading.Lock()


def _thread_print(*args, **kwargs):
    with _print_lock:
        print(*args, **kwargs, flush=True)


# ===================================================================
# TRIAL EXECUTION
# ===================================================================

def _make_trial_id(model_key: str, assortment_id: str, trial_num: int) -> str:
    """Generate unique trial ID for base-vs-instruct experiment."""
    raw = f"bvi_{model_key}_{assortment_id}_baseline_t{trial_num}"
    h = hashlib.md5(raw.encode()).hexdigest()[:8]
    return f"bvi_{model_key}_{assortment_id}_baseline_t{trial_num}_{h}"


def run_single_trial(
    model_key: str,
    model_cfg: dict,
    assortment: dict,
    trial_num: int,
    output_dir: Path,
    cost_tracker: CostTracker = None,
    dry_run: bool = False,
) -> dict | None:
    """
    Execute a single baseline trial for a base or instruct model.

    The output JSON matches the schema used by the main experiment's
    rebuild_clean_csv.py so that results can be analyzed with the same
    pipeline. Additional fields (is_base, family, param_count) enable
    paired base-vs-instruct comparisons.

    Returns the trial record dict, or None if skipped/failed.
    """
    trial_id = _make_trial_id(model_key, assortment["id"], trial_num)
    condition = "baseline"

    # Check if already completed (resume support)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    json_path = raw_dir / f"{trial_id}.json"
    if json_path.exists():
        try:
            with open(json_path, encoding="utf-8") as f:
                cached = json.load(f)
            cached["_cached"] = True
            return cached
        except (json.JSONDecodeError, ValueError):
            json_path.unlink(missing_ok=True)

    # Budget check
    if cost_tracker:
        provider = model_cfg["provider"]
        if not cost_tracker.can_afford(provider):
            return None

    # Build prompt using the standard baseline condition builder
    # This ensures identical prompts for base and instruct models
    try:
        system_prompt, user_message, metadata = build_prompt(
            assortment=assortment,
            condition=condition,
            category_preferences=CATEGORY_PREFERENCES,
        )
    except Exception as e:
        _thread_print(f"    ERROR building prompt: {e}")
        return None

    if dry_run:
        _thread_print(f"    [DRY] {model_key} | {assortment['id']} | t{trial_num}")
        return {"trial_id": trial_id, "dry_run": True, "condition": condition}

    # Call API
    start_time = time.time()
    try:
        api_result = call_model_with_retry(
            model_key=model_key,
            model_cfg=model_cfg,
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=1024,
            temperature=1.0,
        )
    except Exception as e:
        _thread_print(f"    ERROR: {model_key} | {assortment['id']}: {e}")
        return None

    duration = time.time() - start_time

    # Parse response (use enhanced parser for base models)
    product_names = metadata.get("product_names", {})
    if not product_names:
        product_names = {
            p["letter"]: p["name"]
            for p in assortment.get("products", [])
            if "letter" in p and "name" in p
        }

    is_base = model_cfg.get("is_base", False)
    if is_base:
        parsed = parse_base_model_response(api_result.get("text", ""), product_names)
    else:
        parsed = parse_product_choice(api_result.get("text", ""), product_names=product_names)

    # Compute cost
    cost = compute_cost(
        model_cfg["model_id"],
        api_result.get("input_tokens", 0),
        api_result.get("output_tokens", 0),
    )

    # Record with cost tracker
    if cost_tracker:
        cost_tracker.record_call(
            provider=model_cfg["provider"],
            model_id=model_cfg["model_id"],
            input_tokens=api_result.get("input_tokens", 0),
            output_tokens=api_result.get("output_tokens", 0),
            cost_usd=cost,
            experiment="base_vs_instruct",
            trial_id=trial_id,
        )

    # Determine if optimal was chosen
    optimal_letter = metadata.get("optimal_letter", "?")
    chose_optimal = (parsed["choice"] == optimal_letter)

    # Decode choice back to original letter for cross-trial analysis
    letter_mapping = metadata.get("letter_mapping", {})
    original_choice = letter_mapping.get(parsed["choice"], parsed["choice"])
    original_optimal = metadata.get(
        "original_optimal_letter",
        letter_mapping.get(optimal_letter, optimal_letter),
    )

    # Find branded product
    branded_letter = None
    for p in assortment["products"]:
        if p.get("brand_familiarity") == "high" and not p.get("is_optimal"):
            branded_letter = p["letter"]
            break
    chose_branded = (original_choice == branded_letter) if branded_letter else False

    # Utility loss
    utility_scores = metadata.get("utility_scores", {})
    optimal_utility = metadata.get("optimal_score", 0)
    chosen_utility = utility_scores.get(parsed["choice"], 0)
    utility_loss = max(0, optimal_utility - chosen_utility) if not chose_optimal else 0.0

    # Chosen product brand familiarity
    chosen_brand_familiarity = "unknown"
    chosen_position = -1
    for idx, p in enumerate(assortment["products"]):
        if p["letter"] == original_choice:
            chosen_brand_familiarity = p.get("brand_familiarity", "unknown")
            chosen_position = idx
            break

    # Build record (compatible with main experiment schema + extra fields)
    record = {
        "experiment": "base_vs_instruct",
        "trial_id": trial_id,
        "model_key": model_key,
        "provider": model_cfg["provider"],
        "model_id": model_cfg["model_id"],
        "thinking": model_cfg.get("thinking", False),
        "assortment_id": assortment["id"],
        "category": assortment.get("category", "unknown"),
        "condition": condition,
        "condition_type": "baseline",
        "condition_precision": "none",
        "condition_ordinal": 0,
        "choice": parsed["choice"],
        "original_choice": original_choice,
        "reasoning": parsed.get("reasoning", ""),
        "raw_response": api_result.get("text", ""),
        "thinking_trace": api_result.get("thinking", ""),
        "system_prompt": system_prompt,
        "user_message": user_message,
        "input_tokens": api_result.get("input_tokens", 0),
        "output_tokens": api_result.get("output_tokens", 0),
        "cost_usd": round(cost, 6) if cost is not None else None,
        "duration_seconds": round(duration, 2),
        "temperature": 1.0,
        "paraphrase_index": metadata.get("paraphrase_index", 0),
        "timestamp": datetime.now().isoformat(),
        # Specification resistance fields (same schema as main experiment)
        "optimal_product": optimal_letter,
        "original_optimal": original_optimal,
        "optimal_utility": metadata.get("optimal_score", 0),
        "utility_scores": metadata.get("utility_scores", {}),
        "chose_optimal": chose_optimal,
        "chose_branded": chose_branded,
        "chosen_brand_familiarity": chosen_brand_familiarity,
        "chosen_position": chosen_position,
        "utility_loss": round(utility_loss, 4),
        "override_occurred": False,  # baseline only, never an override
        "specification_resistance": False,  # baseline has no spec to resist
        "brand_reversal": False,
        "presentation_order": metadata.get("presentation_order", []),
        "optimal_display_position": metadata.get("optimal_display_position", -1),
        "letter_mapping": letter_mapping,
        # Base-vs-instruct specific fields
        "is_base": model_cfg.get("is_base", False),
        "family": model_cfg.get("family", ""),
        "param_count": model_cfg.get("param_count", ""),
    }

    # Save raw JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    return record


# ===================================================================
# EXPERIMENT RUNNER
# ===================================================================

def run_base_vs_instruct(
    models: dict = None,
    assortments: list[dict] = None,
    trials_per_assortment: int = 20,
    output_dir: Path = None,
    budget_per_provider: float = 25.00,
    dry_run: bool = False,
    max_workers: int = 10,
) -> list[dict]:
    """
    Run the base-vs-instruct comparison experiment.

    Loops over all model pairs and all 34 sr_ assortments, running
    the baseline condition with 20 trials per assortment per model.

    Uses parallel execution within each model to speed up throughput
    while respecting rate limits across providers.
    """
    if models is None:
        models = BASE_INSTRUCT_MODELS
    if assortments is None:
        assortments = get_sr_assortments()
    if output_dir is None:
        output_dir = _PROJECT_ROOT / "data" / "base_vs_instruct"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load API keys
    load_env()
    available = check_providers()

    # Check which providers are needed and available
    needed_providers = {mc["provider"] for mc in models.values()}
    missing_providers = needed_providers - available
    if missing_providers:
        print(f"WARNING: Missing provider keys: {missing_providers}")
        print(f"  Available providers: {available}")
        for p in missing_providers:
            env_var = {
                "openrouter": "OPENROUTER_API_KEY",
                "together": "TOGETHER_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "openai": "OPENAI_API_KEY",
                "google": "GOOGLE_API_KEY",
            }.get(p, f"{p.upper()}_API_KEY")
            print(f"  Set {env_var} in config/.env for {p} models")

        # Filter to only models with available providers
        skipped_models = [k for k, v in models.items() if v["provider"] not in available]
        models = {k: v for k, v in models.items() if v["provider"] in available}
        if skipped_models:
            print(f"\n  Skipping models (provider unavailable): {skipped_models}")
        if not models:
            print("\nERROR: No models have available API keys.")
            print("\nThis experiment requires Together AI for base model access.")
            print("Together AI hosts both base (pretrained) and instruct models.")
            print("Sign up at https://api.together.ai and add your key:")
            print("  echo 'TOGETHER_API_KEY=your-key-here' >> config/.env")
            sys.exit(1)
        print(f"  Proceeding with {len(models)} models that have working providers.\n")

    cost_tracker = CostTracker(
        budget_per_provider=budget_per_provider,
        log_dir=output_dir / "costs",
    )

    total_calls = len(models) * len(assortments) * trials_per_assortment
    print(f"\n{'='*60}")
    print(f"BASE vs INSTRUCT EXPERIMENT (Nature R&R Pillar 1B)")
    print(f"{'='*60}")
    print(f"Models: {len(models)}")
    for mk, mc in models.items():
        base_tag = "BASE" if mc.get("is_base") else "INST"
        print(f"  [{base_tag}] {mk}: {mc['model_id']}")
    print(f"Assortments: {len(assortments)}")
    print(f"Trials per assortment: {trials_per_assortment}")
    print(f"Total API calls: {total_calls}")
    print(f"Dry run: {dry_run}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}\n")

    all_results = []
    completed = 0
    skipped = 0
    errors = 0

    for model_key, model_cfg in models.items():
        base_tag = "BASE" if model_cfg.get("is_base") else "INST"
        print(f"\n--- [{base_tag}] {model_key} ({model_cfg['model_id']}) ---")

        # Build all tasks for this model
        tasks = []
        for assortment in assortments:
            for trial_num in range(trials_per_assortment):
                tasks.append((assortment, trial_num))

        # Execute in parallel (within rate limits)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for assortment, trial_num in tasks:
                # Check budget before submitting
                if cost_tracker:
                    try:
                        cost_tracker.check_budget(model_cfg["provider"])
                    except BudgetExceededError as e:
                        _thread_print(f"  BUDGET EXCEEDED: {e}")
                        skipped += 1
                        continue

                future = executor.submit(
                    run_single_trial,
                    model_key=model_key,
                    model_cfg=model_cfg,
                    assortment=assortment,
                    trial_num=trial_num,
                    output_dir=output_dir,
                    cost_tracker=cost_tracker,
                    dry_run=dry_run,
                )
                futures[future] = (assortment["id"], trial_num)

            for future in as_completed(futures):
                aid, tnum = futures[future]
                try:
                    result = future.result()
                except Exception as e:
                    _thread_print(f"  EXCEPTION: {aid} t{tnum}: {e}")
                    errors += 1
                    continue

                if result is None:
                    errors += 1
                elif result.get("dry_run"):
                    skipped += 1
                else:
                    all_results.append(result)
                    completed += 1

                    if not result.get("_cached"):
                        choice_tag = "OPT" if result.get("chose_optimal") else result.get("choice", "?")
                        cost_str = f"${result.get('cost_usd', 0):.4f}" if result.get("cost_usd") else "?"
                        _thread_print(
                            f"  {aid[:30]:30s} t{tnum:02d}: {choice_tag:5s} {cost_str}"
                        )

    print(f"\n{'='*60}")
    print(f"EXPERIMENT COMPLETE")
    print(f"  Completed: {completed}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {errors}")
    print(f"{'='*60}")

    if cost_tracker:
        cost_tracker.print_summary()

    # Save summary
    summary = {
        "experiment": "base_vs_instruct",
        "timestamp": datetime.now().isoformat(),
        "models": {k: v["model_id"] for k, v in models.items()},
        "n_assortments": len(assortments),
        "trials_per_assortment": trials_per_assortment,
        "total_completed": completed,
        "total_errors": errors,
        "total_skipped": skipped,
    }
    summary_path = output_dir / "experiment_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to {summary_path}")

    return all_results


# ===================================================================
# COMPARISON ANALYSIS
# ===================================================================

def analyze_base_vs_instruct(data_dir: Path = None, figures_dir: Path = None):
    """
    Load base and instruct results, compute comparison statistics,
    and generate publication-quality figures.

    Produces:
      1. Paired bar chart: non-optimal rate by model family (base vs instruct)
      2. Brand familiarity heatmap: choice distribution by brand_familiarity
      3. Category-level scatter: base vs instruct non-optimal rate per category
      4. Statistical tests: McNemar's test for paired proportions
      5. Summary CSV for further analysis in R/Stata
    """
    import numpy as np

    try:
        import pandas as pd
    except ImportError:
        print("ERROR: pandas required. Install with: pip install pandas")
        sys.exit(1)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        print("ERROR: matplotlib required. Install with: pip install matplotlib")
        sys.exit(1)

    if data_dir is None:
        data_dir = _PROJECT_ROOT / "data" / "base_vs_instruct" / "raw"
    if figures_dir is None:
        figures_dir = _PROJECT_ROOT / "data" / "base_vs_instruct" / "figures"

    figures_dir.mkdir(parents=True, exist_ok=True)

    # Load all trial JSON files
    print(f"Loading trials from {data_dir}...")
    records = []
    for json_path in sorted(data_dir.glob("bvi_*.json")):
        try:
            with open(json_path, encoding="utf-8") as f:
                rec = json.load(f)
            records.append(rec)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"  Skipping corrupt file {json_path.name}: {e}")

    if not records:
        print("No trial records found. Run the experiment first.")
        return

    df = pd.DataFrame(records)
    print(f"Loaded {len(df)} trials across {df['model_key'].nunique()} models")

    # Add derived columns
    df["is_base"] = df["is_base"].astype(bool)
    df["non_optimal"] = ~df["chose_optimal"].astype(bool)
    df["chose_branded"] = df["chose_branded"].astype(bool)
    df["model_type"] = df["is_base"].map({True: "Base", False: "Instruct"})

    # Merge category metadata
    df["involvement"] = df["category"].map(
        lambda c: CATEGORY_METADATA.get(c, {}).get("involvement", "unknown")
    )
    df["brand_salience"] = df["category"].map(
        lambda c: CATEGORY_METADATA.get(c, {}).get("brand_salience", "unknown")
    )

    # --- Summary statistics ---
    print(f"\n{'='*60}")
    print("SUMMARY STATISTICS")
    print(f"{'='*60}")

    summary = df.groupby(["family", "model_type"]).agg(
        n_trials=("trial_id", "count"),
        non_optimal_rate=("non_optimal", "mean"),
        branded_rate=("chose_branded", "mean"),
        mean_utility_loss=("utility_loss", "mean"),
        parse_failures=("choice", lambda x: (x == "?").sum()),
    ).round(4)
    print(summary.to_string())

    # Save summary CSV
    summary_csv_path = figures_dir.parent / "processed" / "base_vs_instruct_summary.csv"
    summary_csv_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_csv_path)
    print(f"\nSummary CSV: {summary_csv_path}")

    # Save full trial-level CSV
    full_csv_path = figures_dir.parent / "processed" / "base_vs_instruct_trials.csv"
    csv_cols = [
        "trial_id", "model_key", "model_id", "family", "is_base", "model_type",
        "param_count", "assortment_id", "category", "involvement", "brand_salience",
        "condition", "choice", "original_choice", "optimal_product", "original_optimal",
        "chose_optimal", "non_optimal", "chose_branded", "chosen_brand_familiarity",
        "utility_loss", "cost_usd", "input_tokens", "output_tokens",
        "duration_seconds", "timestamp",
    ]
    available_cols = [c for c in csv_cols if c in df.columns]
    df[available_cols].to_csv(full_csv_path, index=False)
    print(f"Full trial CSV: {full_csv_path}")

    # --- Figure 1: Paired bar chart ---
    fig, ax = plt.subplots(figsize=(8, 5))
    families = sorted(df["family"].unique())
    x = np.arange(len(families))
    width = 0.35

    base_rates = []
    instruct_rates = []
    for fam in families:
        base_data = df[(df["family"] == fam) & (df["is_base"])]
        inst_data = df[(df["family"] == fam) & (~df["is_base"])]
        base_rates.append(base_data["non_optimal"].mean() if len(base_data) > 0 else 0)
        instruct_rates.append(inst_data["non_optimal"].mean() if len(inst_data) > 0 else 0)

    bars_base = ax.bar(x - width / 2, base_rates, width, label="Base (pre-RLHF)",
                       color="#2196F3", alpha=0.85)
    bars_inst = ax.bar(x + width / 2, instruct_rates, width, label="Instruct (post-RLHF)",
                       color="#FF5722", alpha=0.85)

    ax.set_xlabel("Model Family")
    ax.set_ylabel("Non-Optimal Recommendation Rate")
    ax.set_title("Brand Preference: Base vs. Instruct Models")
    ax.set_xticks(x)
    ax.set_xticklabels([f.replace("-", " ").title() for f in families], rotation=15)
    ax.legend()
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.set_ylim(0, max(max(base_rates, default=0), max(instruct_rates, default=0)) * 1.3 + 0.05)

    # Add value labels
    for bar in bars_base:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., h + 0.01, f"{h:.1%}",
                ha="center", va="bottom", fontsize=9)
    for bar in bars_inst:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., h + 0.01, f"{h:.1%}",
                ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    fig1_path = figures_dir / "base_vs_instruct_nonoptimal_rate.png"
    fig.savefig(fig1_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure 1: {fig1_path}")

    # --- Figure 2: Brand familiarity distribution ---
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)

    for idx, (model_type, ax) in enumerate(zip(["Base", "Instruct"], axes)):
        subset = df[df["model_type"] == model_type]
        fam_counts = subset.groupby(["family", "chosen_brand_familiarity"]).size().unstack(
            fill_value=0
        )
        fam_pct = fam_counts.div(fam_counts.sum(axis=1), axis=0)

        colors = {"high": "#E53935", "medium": "#FB8C00", "low": "#43A047", "unknown": "#9E9E9E"}
        bottom = np.zeros(len(fam_pct))
        for fam_level in ["high", "medium", "low", "unknown"]:
            if fam_level in fam_pct.columns:
                vals = fam_pct[fam_level].values
                ax.bar(range(len(fam_pct)), vals, bottom=bottom,
                       label=fam_level.title(), color=colors[fam_level], alpha=0.85)
                bottom += vals

        ax.set_title(f"{model_type} Models")
        ax.set_xticks(range(len(fam_pct)))
        ax.set_xticklabels(fam_pct.index, rotation=15)
        ax.set_ylabel("Share of Choices" if idx == 0 else "")
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        if idx == 1:
            ax.legend(title="Brand Familiarity", bbox_to_anchor=(1.02, 1), loc="upper left")

    fig.suptitle("Choice Distribution by Brand Familiarity", fontsize=13, y=1.02)
    plt.tight_layout()
    fig2_path = figures_dir / "base_vs_instruct_brand_familiarity.png"
    fig.savefig(fig2_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Figure 2: {fig2_path}")

    # --- Figure 3: Category scatter (base vs instruct non-optimal rate) ---
    fig, ax = plt.subplots(figsize=(7, 7))

    cat_rates = df.groupby(["category", "model_type"])["non_optimal"].mean().unstack()
    if "Base" in cat_rates.columns and "Instruct" in cat_rates.columns:
        ax.scatter(cat_rates["Base"], cat_rates["Instruct"], s=80, alpha=0.7, color="#1565C0")

        # Label each point
        for cat in cat_rates.index:
            ax.annotate(cat.replace("_", " "), (cat_rates.loc[cat, "Base"], cat_rates.loc[cat, "Instruct"]),
                        fontsize=7, alpha=0.8, xytext=(5, 5), textcoords="offset points")

        # Diagonal line (equal preference)
        lims = [0, max(cat_rates.max().max() * 1.1, 0.5)]
        ax.plot(lims, lims, "--", color="gray", alpha=0.5, label="Equal preference")
        ax.set_xlim(lims)
        ax.set_ylim(lims)

    ax.set_xlabel("Base Model Non-Optimal Rate")
    ax.set_ylabel("Instruct Model Non-Optimal Rate")
    ax.set_title("Category-Level Brand Preference:\nBase vs. Instruct")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.legend()

    plt.tight_layout()
    fig3_path = figures_dir / "base_vs_instruct_category_scatter.png"
    fig.savefig(fig3_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Figure 3: {fig3_path}")

    # --- Statistical tests ---
    print(f"\n{'='*60}")
    print("STATISTICAL TESTS")
    print(f"{'='*60}")

    try:
        from scipy import stats

        for fam in families:
            base_data = df[(df["family"] == fam) & (df["is_base"])]
            inst_data = df[(df["family"] == fam) & (~df["is_base"])]

            if len(base_data) == 0 or len(inst_data) == 0:
                print(f"\n{fam}: insufficient data for comparison")
                continue

            base_rate = base_data["non_optimal"].mean()
            inst_rate = inst_data["non_optimal"].mean()
            n_base = len(base_data)
            n_inst = len(inst_data)

            # Two-proportion z-test
            p_pooled = (base_data["non_optimal"].sum() + inst_data["non_optimal"].sum()) / (n_base + n_inst)
            if p_pooled > 0 and p_pooled < 1:
                se = np.sqrt(p_pooled * (1 - p_pooled) * (1 / n_base + 1 / n_inst))
                z = (base_rate - inst_rate) / se
                p_value = 2 * stats.norm.sf(abs(z))
            else:
                z = 0
                p_value = 1.0

            # Effect size (Cohen's h)
            h = 2 * (np.arcsin(np.sqrt(base_rate)) - np.arcsin(np.sqrt(inst_rate)))

            print(f"\n{fam}:")
            print(f"  Base:     {base_rate:.1%} ({n_base} trials)")
            print(f"  Instruct: {inst_rate:.1%} ({n_inst} trials)")
            print(f"  Diff:     {base_rate - inst_rate:+.1%}")
            print(f"  z = {z:.3f}, p = {p_value:.4f}")
            print(f"  Cohen's h = {h:.3f}")

            if p_value < 0.05:
                direction = "BASE higher" if base_rate > inst_rate else "INSTRUCT higher"
                print(f"  ** Significant (p < 0.05): {direction}")
            else:
                print(f"  Not significant: alignment did NOT change brand preference")

    except ImportError:
        print("scipy not installed; skipping statistical tests.")
        print("Install with: pip install scipy")

    # --- Overall conclusion ---
    base_overall = df[df["is_base"]]["non_optimal"].mean()
    inst_overall = df[~df["is_base"]]["non_optimal"].mean()
    print(f"\n{'='*60}")
    print("OVERALL CONCLUSION")
    print(f"{'='*60}")
    print(f"Base models (pre-RLHF):  {base_overall:.1%} non-optimal")
    print(f"Instruct models (post-RLHF): {inst_overall:.1%} non-optimal")
    diff = abs(base_overall - inst_overall)
    if diff < 0.05:
        print(f"Difference ({diff:.1%}) is small: RLHF alignment does NOT substantially")
        print(f"reduce brand preferences encoded during pre-training.")
    else:
        direction = "reduces" if inst_overall < base_overall else "increases"
        print(f"Difference ({diff:.1%}): RLHF alignment {direction} brand preference")
        print(f"by {diff:.1%} percentage points.")

    print(f"\nAll figures saved to: {figures_dir}")


# ===================================================================
# CLI ENTRY POINT
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Base vs. Instruct model comparison (Nature R&R Pillar 1B)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be run without making API calls"
    )
    parser.add_argument(
        "--trials", type=int, default=20,
        help="Number of trials per assortment per model (default: 20)"
    )
    parser.add_argument(
        "--budget", type=float, default=25.00,
        help="Maximum USD budget per provider (default: 25.00)"
    )
    parser.add_argument(
        "--max-workers", type=int, default=10,
        help="Max parallel API calls per model (default: 10)"
    )
    parser.add_argument(
        "--analyze-only", action="store_true",
        help="Skip experiment, just run analysis on existing data"
    )
    parser.add_argument(
        "--models", nargs="+", default=None,
        help="Subset of model keys to run (e.g., 'llama-3.1-8b-base llama-3.1-8b-instruct')"
    )
    args = parser.parse_args()

    if args.analyze_only:
        analyze_base_vs_instruct()
        return

    # Select models
    if args.models:
        models = {k: BASE_INSTRUCT_MODELS[k] for k in args.models
                  if k in BASE_INSTRUCT_MODELS}
        if not models:
            print(f"No valid models found. Available: {list(BASE_INSTRUCT_MODELS.keys())}")
            sys.exit(1)
    else:
        models = BASE_INSTRUCT_MODELS

    # Run experiment
    run_base_vs_instruct(
        models=models,
        trials_per_assortment=args.trials,
        budget_per_provider=args.budget,
        dry_run=args.dry_run,
        max_workers=args.max_workers,
    )

    # Run analysis
    print("\n\nRunning comparison analysis...")
    analyze_base_vs_instruct()


if __name__ == "__main__":
    main()
