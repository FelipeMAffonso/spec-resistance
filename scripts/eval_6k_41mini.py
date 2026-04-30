#!/usr/bin/env python3
"""
Full-Scale Evaluation: GPT-4.1-mini Baseline vs 6K Fine-Tuned
==============================================================
Tests BOTH models on ALL 34 assortments x 20 trials = 680 trials per model = 1,360 total.

Models:
  1. Baseline:    gpt-4.1-mini-2025-04-14
  2. FT-6K:       (retrieved from fine-tuning job ftjob-1XiAPum0bstSXpR70mmPHquD)

Step 0: Poll job until status=succeeded, then extract fine_tuned_model ID.
Step 1: Run 1,360 trials (680 baseline + 680 fine-tuned).
Step 2: Save CSV + print comparison table with Wilson 95% CIs and Fisher's exact test.

Uses the EXACT baseline prompt from the main experiment via build_prompt().
"""

import csv
import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
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


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
FINETUNE_JOB_ID = "ftjob-1XiAPum0bstSXpR70mmPHquD"
BASELINE_MODEL_ID = "gpt-4.1-mini-2025-04-14"
FT_MODEL_ID = "ft:gpt-4.1-mini-2025-04-14:personal:spec-debiasing-6k-41mini:DR6r0rH6"

N_TRIALS = 20
CONDITION = "baseline"
TEMPERATURE = 1.0
MAX_TOKENS = 300
API_DELAY = 0.12  # seconds between calls
MAX_RETRIES = 6

RESULTS_DIR = _PROJECT_ROOT / "nature-rr" / "results" / "06-openai-finetune"
CSV_PATH = RESULTS_DIR / "eval_6k_41mini.csv"
CACHE_PATH = RESULTS_DIR / "eval_6k_41mini_cache.json"

CSV_COLUMNS = [
    "trial_id", "model_key", "model_id", "assortment_id", "category",
    "trial", "choice", "optimal_letter", "chose_optimal", "is_unparseable",
    "paraphrase_index", "optimal_display_position", "response_text",
    "timestamp",
]


# ---------------------------------------------------------------------------
# Load environment
# ---------------------------------------------------------------------------

def load_env():
    """Load API key from config/.env."""
    env_path = _PROJECT_ROOT / "config" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in config/.env or environment.")
        sys.exit(1)
    return api_key


# ---------------------------------------------------------------------------
# Poll fine-tuning job until succeeded
# ---------------------------------------------------------------------------

def poll_finetune_job(client) -> str:
    """Poll the fine-tuning job until status=succeeded. Returns fine_tuned_model ID."""
    print(f"  Polling fine-tuning job: {FINETUNE_JOB_ID}")
    poll_interval = 30  # seconds
    while True:
        job = client.fine_tuning.jobs.retrieve(FINETUNE_JOB_ID)
        status = job.status
        ft_model = job.fine_tuned_model
        print(f"    Status: {status}  |  Model: {ft_model}  |  {datetime.now().strftime('%H:%M:%S')}")

        if status == "succeeded" and ft_model:
            print(f"  Fine-tuned model ready: {ft_model}")
            return ft_model
        elif status in ("failed", "cancelled"):
            error_msg = getattr(job, 'error', None)
            print(f"  FATAL: Job {status}. Error: {error_msg}")
            sys.exit(1)
        else:
            time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# API caller with retry
# ---------------------------------------------------------------------------

def call_openai(client, model_id: str, system_prompt: str,
                user_message: str) -> dict:
    """Call OpenAI chat completions with exponential backoff."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_message})

            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            )

            input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
            output_tokens = getattr(response.usage, "completion_tokens", 0) or 0

            return {
                "text": response.choices[0].message.content or "",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }

        except Exception as e:
            error_str = str(e).lower()
            # Hard quota exhaustion -- not retryable, skip this call
            if "insufficient_quota" in error_str:
                raise
            is_retryable = any(w in error_str for w in [
                "rate", "429", "overloaded", "too many", "quota",
                "capacity", "503", "server",
            ])
            if is_retryable and attempt < MAX_RETRIES:
                wait = min(2 ** attempt * 2, 120)
                print(f"    [retry] {type(e).__name__}, waiting {wait}s "
                      f"(attempt {attempt + 1}/{MAX_RETRIES})...")
                time.sleep(wait)
            else:
                raise


# ---------------------------------------------------------------------------
# Wilson confidence interval
# ---------------------------------------------------------------------------

def wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p_hat = successes / n
    denom = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denom
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n)) / n) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


# ---------------------------------------------------------------------------
# Fisher's exact test (2x2)
# ---------------------------------------------------------------------------

def fishers_exact_test(a: int, b: int, c: int, d: int) -> float:
    """
    Two-sided Fisher's exact test p-value for 2x2 table:
        [[a, b], [c, d]]
    Uses scipy if available, else returns NaN.
    """
    try:
        from scipy.stats import fisher_exact
        _, p = fisher_exact([[a, b], [c, d]], alternative="two-sided")
        return p
    except ImportError:
        return float("nan")


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def load_cache() -> dict:
    """Load cached results. Returns dict keyed by trial_id."""
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"  Loaded {len(data)} cached trials from {CACHE_PATH.name}")
        return data
    return {}


def save_cache(cache: dict):
    """Save cache to disk."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def main():
    from experiment.assortments import ALL_ASSORTMENTS, CATEGORY_PREFERENCES
    from experiment.conditions import build_prompt
    from harness.shopping_agent import parse_product_choice

    print("=" * 75)
    print("FULL-SCALE EVALUATION: GPT-4.1-MINI BASELINE vs 6K FINE-TUNED")
    print("=" * 75)
    print()

    # Load API key and create client
    load_env()
    import openai
    client = openai.OpenAI()

    # Use known model ID (already succeeded), fall back to polling if needed
    if FT_MODEL_ID:
        ft_model_id = FT_MODEL_ID
        print(f"  Using known fine-tuned model: {ft_model_id}")
    else:
        ft_model_id = poll_finetune_job(client)

    # Fine-tuned first (available even when base model is quota-blocked)
    MODELS = {
        "ft-6k-41mini": ft_model_id,
        "baseline-41mini": BASELINE_MODEL_ID,
    }

    n_assortments = len(ALL_ASSORTMENTS)
    n_models = len(MODELS)
    total_trials = n_models * n_assortments * N_TRIALS

    print()
    print(f"  Models:            {n_models}")
    for mk, mid in MODELS.items():
        print(f"    {mk:20s} {mid}")
    print(f"  Condition:         {CONDITION}")
    print(f"  Assortments:       {n_assortments}")
    print(f"  Trials/assortment: {N_TRIALS}")
    print(f"  Total trials:      {total_trials}")
    print(f"  Temperature:       {TEMPERATURE}")
    print(f"  Max tokens:        {MAX_TOKENS}")
    print(f"  API delay:         {API_DELAY}s")
    print()

    # Load cache
    cache = load_cache()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Build the full trial list
    trial_list = []
    for model_key, model_id in MODELS.items():
        for assortment in ALL_ASSORTMENTS:
            for trial_idx in range(N_TRIALS):
                trial_id = f"{model_key}__{assortment['id']}__t{trial_idx}"
                trial_list.append({
                    "trial_id": trial_id,
                    "model_key": model_key,
                    "model_id": model_id,
                    "assortment": assortment,
                    "trial_idx": trial_idx,
                })

    # Count how many are already cached
    cached_count = sum(1 for t in trial_list if t["trial_id"] in cache)
    remaining = total_trials - cached_count
    print(f"  Cached:            {cached_count}")
    print(f"  Remaining:         {remaining}")
    print()

    if remaining == 0:
        print("  All trials already cached. Skipping API calls.")
    else:
        print(f"  Starting {remaining} API calls...")
        print()

    # Run trials
    call_num = 0
    total_input_tokens = 0
    total_output_tokens = 0
    start_time = time.time()
    new_calls = 0
    blocked_models = set()  # models that hit hard quota limits

    for ti, trial_info in enumerate(trial_list):
        trial_id = trial_info["trial_id"]

        # Skip if cached
        if trial_id in cache:
            continue

        model_key = trial_info["model_key"]
        model_id = trial_info["model_id"]

        # Skip models blocked by quota exhaustion
        if model_key in blocked_models:
            continue

        call_num += 1
        assortment = trial_info["assortment"]
        trial_idx = trial_info["trial_idx"]

        # Build prompt using the project's canonical prompt builder
        system_prompt, user_message, metadata = build_prompt(
            assortment=assortment,
            condition=CONDITION,
            category_preferences=CATEGORY_PREFERENCES,
            paraphrase_index=None,
            shuffle_products=True,
            randomize_letters=True,
        )

        optimal_letter = metadata["optimal_letter"]
        product_names = metadata.get("product_names", {})

        # Call the model (handle quota exhaustion gracefully)
        try:
            resp = call_openai(client, model_id, system_prompt, user_message)
        except Exception as e:
            if "insufficient_quota" in str(e).lower():
                print(f"\n  QUOTA EXHAUSTED for {model_key} ({model_id}). "
                      f"Skipping remaining trials for this model.")
                blocked_models.add(model_key)
                save_cache(cache)
                continue
            raise

        response_text = resp["text"]
        total_input_tokens += resp["input_tokens"]
        total_output_tokens += resp["output_tokens"]
        new_calls += 1

        # Parse choice
        parsed = parse_product_choice(response_text, product_names=product_names)
        choice = parsed["choice"]

        chose_optimal = (choice == optimal_letter)
        is_unparseable = (choice == "?")

        trial_result = {
            "trial_id": trial_id,
            "model_key": model_key,
            "model_id": model_id,
            "assortment_id": assortment["id"],
            "category": assortment.get("category", "unknown"),
            "trial": trial_idx,
            "choice": choice,
            "optimal_letter": optimal_letter,
            "chose_optimal": chose_optimal,
            "is_unparseable": is_unparseable,
            "paraphrase_index": metadata.get("paraphrase_index"),
            "optimal_display_position": metadata.get("optimal_display_position"),
            "response_text": response_text,
            "timestamp": datetime.now().isoformat(),
        }

        cache[trial_id] = trial_result

        # Progress every 100 calls
        if new_calls % 100 == 0:
            elapsed = time.time() - start_time
            calls_per_sec = new_calls / elapsed if elapsed > 0 else 0
            eta_sec = (remaining - new_calls) / calls_per_sec if calls_per_sec > 0 else 0
            eta_min = eta_sec / 60

            # Running totals per model
            model_stats = {}
            for tid, tr in cache.items():
                mk = tr["model_key"]
                if mk not in model_stats:
                    model_stats[mk] = {"n": 0, "optimal": 0}
                model_stats[mk]["n"] += 1
                if tr["chose_optimal"]:
                    model_stats[mk]["optimal"] += 1

            print(f"  [{new_calls:4d}/{remaining}] ({calls_per_sec:.1f} calls/s, "
                  f"ETA {eta_min:.0f}m)")
            for mk in MODELS:
                if mk in model_stats:
                    ms = model_stats[mk]
                    pct = ms["optimal"] / ms["n"] * 100 if ms["n"] > 0 else 0
                    print(f"    {mk:20s}: {ms['n']:4d} trials, "
                          f"optimal={pct:.1f}%")
            print()

        # Save cache every 50 new calls
        if new_calls % 50 == 0:
            save_cache(cache)

        time.sleep(API_DELAY)

    # Final cache save
    if new_calls > 0:
        save_cache(cache)
        elapsed = time.time() - start_time
        print(f"\n  Completed {new_calls} API calls in {elapsed/60:.1f} minutes.")
        print(f"  Tokens: {total_input_tokens:,} in / {total_output_tokens:,} out")

    if blocked_models:
        print(f"\n  WARNING: {len(blocked_models)} model(s) hit quota limits: "
              f"{', '.join(sorted(blocked_models))}")
        print("  Re-run this script when quota resets to complete remaining trials.")

    # ---------------------------------------------------------------------------
    # Build results from cache
    # ---------------------------------------------------------------------------
    all_results = []
    for trial_info in trial_list:
        tid = trial_info["trial_id"]
        if tid in cache:
            all_results.append(cache[tid])
        else:
            print(f"  WARNING: Missing trial {tid}")

    # ---------------------------------------------------------------------------
    # Save CSV
    # ---------------------------------------------------------------------------
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for r in all_results:
            writer.writerow(r)

    print(f"\n  CSV saved: {CSV_PATH}")
    print(f"  Total rows: {len(all_results)}")

    # ---------------------------------------------------------------------------
    # Analysis: Comparison table with Wilson CIs and Fisher's exact test
    # ---------------------------------------------------------------------------
    print()
    print("=" * 75)
    print("RESULTS: GPT-4.1-MINI BASELINE vs 6K FINE-TUNED")
    print("=" * 75)

    # Per-model aggregates
    model_agg = {}
    for r in all_results:
        mk = r["model_key"]
        if mk not in model_agg:
            model_agg[mk] = {"n": 0, "optimal": 0, "non_optimal": 0, "errors": 0}
        model_agg[mk]["n"] += 1
        if r.get("is_unparseable"):
            model_agg[mk]["errors"] += 1
        elif r.get("chose_optimal"):
            model_agg[mk]["optimal"] += 1
        else:
            model_agg[mk]["non_optimal"] += 1

    print()
    print(f"  {'Model':<22s} {'N':>5s}  {'Optimal':>8s}  {'Non-Opt':>8s}  "
          f"{'Errors':>6s}  {'Opt Rate':>10s}  {'Wilson 95% CI':>18s}")
    print("  " + "-" * 85)

    for mk in MODELS:
        if mk not in model_agg:
            continue
        agg = model_agg[mk]
        n = agg["n"]
        opt = agg["optimal"]
        non_opt = agg["non_optimal"]
        err = agg["errors"]
        opt_rate = opt / n if n > 0 else 0
        lo, hi = wilson_ci(opt, n)
        print(f"  {mk:<22s} {n:5d}  {opt:8d}  {non_opt:8d}  "
              f"{err:6d}  {opt_rate:9.1%}  [{lo:.3f}, {hi:.3f}]")

    # Non-optimal rate version (primary metric)
    print()
    print(f"  {'Model':<22s} {'Non-Opt Rate':>12s}  {'Wilson 95% CI':>18s}")
    print("  " + "-" * 56)
    for mk in MODELS:
        if mk not in model_agg:
            continue
        agg = model_agg[mk]
        n = agg["n"]
        non_opt = agg["non_optimal"]
        non_opt_rate = non_opt / n if n > 0 else 0
        lo, hi = wilson_ci(non_opt, n)
        print(f"  {mk:<22s} {non_opt_rate:11.1%}  [{lo:.3f}, {hi:.3f}]")

    # Fisher's exact test: baseline vs fine-tuned
    print()
    print("  FISHER'S EXACT TEST (two-sided)")
    print("  " + "-" * 56)

    model_keys = list(MODELS.keys())
    for i in range(len(model_keys)):
        for j in range(i + 1, len(model_keys)):
            mk1, mk2 = model_keys[i], model_keys[j]
            if mk1 not in model_agg or mk2 not in model_agg:
                continue
            a1 = model_agg[mk1]
            a2 = model_agg[mk2]
            # 2x2 table: optimal vs non-optimal for each model
            # (exclude unparseable from comparison)
            opt1, nopt1 = a1["optimal"], a1["non_optimal"]
            opt2, nopt2 = a2["optimal"], a2["non_optimal"]
            p_val = fishers_exact_test(opt1, nopt1, opt2, nopt2)
            sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
            print(f"  {mk1} vs {mk2}: p = {p_val:.4e}  {sig}")

    # Effect size: reduction in non-optimal rate
    print()
    print("  EFFECT SIZE")
    print("  " + "-" * 56)
    if "baseline-41mini" in model_agg and "ft-6k-41mini" in model_agg:
        bl = model_agg["baseline-41mini"]
        ft = model_agg["ft-6k-41mini"]
        bl_rate = bl["non_optimal"] / bl["n"] if bl["n"] > 0 else 0
        ft_rate = ft["non_optimal"] / ft["n"] if ft["n"] > 0 else 0
        reduction_abs = bl_rate - ft_rate
        reduction_rel = reduction_abs / bl_rate * 100 if bl_rate > 0 else 0
        print(f"  Baseline non-optimal rate:   {bl_rate:.1%} ({bl['non_optimal']}/{bl['n']})")
        print(f"  Fine-tuned non-optimal rate: {ft_rate:.1%} ({ft['non_optimal']}/{ft['n']})")
        print(f"  Absolute reduction:          {reduction_abs:.1%}")
        print(f"  Relative reduction:          {reduction_rel:.1f}%")

    # Per-category breakdown for each model
    print()
    print("=" * 75)
    print("PER-CATEGORY BREAKDOWN")
    print("=" * 75)

    # Gather categories
    categories = sorted(set(r["category"] for r in all_results))

    for mk in MODELS:
        print(f"\n  --- {mk} ---")
        print(f"  {'Category':<28s} {'N':>4s}  {'Opt':>4s}  {'Non':>4s}  {'Err':>4s}  {'Opt%':>6s}")
        print("  " + "-" * 56)
        cat_results = [r for r in all_results if r["model_key"] == mk]
        for cat in categories:
            cat_r = [r for r in cat_results if r["category"] == cat]
            if not cat_r:
                continue
            n = len(cat_r)
            opt = sum(1 for r in cat_r if r.get("chose_optimal"))
            non = sum(1 for r in cat_r
                      if not r.get("chose_optimal") and not r.get("is_unparseable"))
            err = sum(1 for r in cat_r if r.get("is_unparseable"))
            rate = opt / n * 100 if n > 0 else 0
            print(f"  {cat:<28s} {n:4d}  {opt:4d}  {non:4d}  {err:4d}  {rate:5.1f}%")

    # Per-assortment comparison
    print()
    print("=" * 75)
    print("PER-ASSORTMENT: BASELINE vs FINE-TUNED NON-OPTIMAL RATES")
    print("=" * 75)
    print(f"  {'Assortment':<28s} {'BL Non%':>8s}  {'FT Non%':>8s}  {'Diff':>8s}")
    print("  " + "-" * 56)

    assortment_ids = sorted(set(r["assortment_id"] for r in all_results))
    for aid in assortment_ids:
        bl_r = [r for r in all_results
                if r["assortment_id"] == aid and r["model_key"] == "baseline-41mini"
                and not r.get("is_unparseable")]
        ft_r = [r for r in all_results
                if r["assortment_id"] == aid and r["model_key"] == "ft-6k-41mini"
                and not r.get("is_unparseable")]
        if not bl_r or not ft_r:
            continue
        bl_nopt = sum(1 for r in bl_r if not r.get("chose_optimal")) / len(bl_r) * 100
        ft_nopt = sum(1 for r in ft_r if not r.get("chose_optimal")) / len(ft_r) * 100
        diff = ft_nopt - bl_nopt
        print(f"  {aid:<28s} {bl_nopt:7.1f}%  {ft_nopt:7.1f}%  {diff:+7.1f}%")

    print()
    print("  DONE.")


if __name__ == "__main__":
    main()
