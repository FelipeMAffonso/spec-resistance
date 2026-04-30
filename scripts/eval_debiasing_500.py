#!/usr/bin/env python3
"""
Evaluate the debiasing fine-tuned model (spec-debiasing-v3, 500 examples)
on the first 10 assortments from ALL_ASSORTMENTS, baseline condition.

10 assortments x 10 trials = 100 trials total.
Uses the exact same baseline prompt as the main experiment.

Known baselines:
  - GPT-4o-mini (original): 27% non-optimal
  - Control-neutral fine-tune: 10% non-optimal
"""

import copy
import json
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
FINETUNED_MODEL_ID = "ft:gpt-4o-mini-2024-07-18:personal:spec-debiasing-v3:DR29DMx7"
N_ASSORTMENTS = 10
TRIALS_PER_ASSORTMENT = 10
CONDITION = "baseline"
TEMPERATURE = 1.0
MAX_TOKENS = 300
API_DELAY = 0.15  # seconds between calls
MAX_RETRIES = 6

RESULTS_DIR = _PROJECT_ROOT / "nature-rr" / "results" / "06-openai-finetune"
RESULTS_PATH = RESULTS_DIR / "debiasing_500_results.json"

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
# Main evaluation
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("DEBIASING FINE-TUNE EVALUATION (v3, 500 examples)")
    print("=" * 70)
    print(f"  Model:             {FINETUNED_MODEL_ID}")
    print(f"  Condition:         {CONDITION}")
    print(f"  Assortments:       first {N_ASSORTMENTS}")
    print(f"  Trials/assortment: {TRIALS_PER_ASSORTMENT}")
    print(f"  Total trials:      {N_ASSORTMENTS * TRIALS_PER_ASSORTMENT}")
    print(f"  Temperature:       {TEMPERATURE}")
    print(f"  Max tokens:        {MAX_TOKENS}")
    print()

    # Load API key and create client
    load_env()
    import openai
    client = openai.OpenAI()

    # Load experiment modules
    from experiment.assortments import ALL_ASSORTMENTS, CATEGORY_PREFERENCES
    from experiment.conditions import build_prompt
    from harness.shopping_agent import parse_product_choice

    assortments = list(ALL_ASSORTMENTS)[:N_ASSORTMENTS]
    print(f"  Assortments selected:")
    for a in assortments:
        print(f"    - {a['id']} ({a.get('category', '?')})")
    print()

    # Run trials
    results = []
    total_calls = N_ASSORTMENTS * TRIALS_PER_ASSORTMENT
    call_num = 0
    total_input_tokens = 0
    total_output_tokens = 0

    for assortment in assortments:
        assortment_id = assortment["id"]
        category = assortment.get("category", "unknown")

        for trial in range(TRIALS_PER_ASSORTMENT):
            call_num += 1

            # Build prompt using the project's canonical prompt builder
            # This handles: letter randomization, product shuffling, paraphrase selection
            system_prompt, user_message, metadata = build_prompt(
                assortment=assortment,
                condition=CONDITION,
                category_preferences=CATEGORY_PREFERENCES,
                paraphrase_index=None,   # random paraphrase each trial
                shuffle_products=True,
                randomize_letters=True,
            )

            optimal_letter = metadata["optimal_letter"]
            product_names = metadata.get("product_names", {})

            # Call the fine-tuned model
            resp = call_openai(client, FINETUNED_MODEL_ID,
                               system_prompt, user_message)
            response_text = resp["text"]
            total_input_tokens += resp["input_tokens"]
            total_output_tokens += resp["output_tokens"]

            # Parse choice using project's canonical parser
            parsed = parse_product_choice(response_text,
                                          product_names=product_names)
            choice = parsed["choice"]

            is_optimal = (choice == optimal_letter)
            is_non_optimal = (choice != optimal_letter and choice != "?")

            trial_result = {
                "model_id": FINETUNED_MODEL_ID,
                "condition": CONDITION,
                "assortment_id": assortment_id,
                "category": category,
                "trial": trial,
                "choice": choice,
                "optimal_letter": optimal_letter,
                "is_optimal": is_optimal,
                "is_non_optimal": is_non_optimal,
                "is_unparseable": (choice == "?"),
                "response_text": response_text,
                "paraphrase_index": metadata.get("paraphrase_index"),
                "presentation_order": metadata.get("presentation_order"),
                "optimal_display_position": metadata.get("optimal_display_position"),
                "letter_mapping": metadata.get("letter_mapping"),
                "product_names": product_names,
                "timestamp": datetime.now().isoformat(),
            }
            results.append(trial_result)

            # Progress every 10 calls
            if call_num % 10 == 0 or call_num == total_calls:
                n_opt = sum(1 for r in results if r["is_optimal"])
                n_nonopt = sum(1 for r in results if r["is_non_optimal"])
                n_err = sum(1 for r in results if r["is_unparseable"])
                pct_opt = n_opt / len(results) * 100
                pct_nonopt = n_nonopt / len(results) * 100
                print(f"  [{call_num:3d}/{total_calls}] "
                      f"optimal={n_opt} ({pct_opt:.1f}%) | "
                      f"non-optimal={n_nonopt} ({pct_nonopt:.1f}%) | "
                      f"errors={n_err}")

            time.sleep(API_DELAY)

    # ---------------------------------------------------------------------------
    # Summarize
    # ---------------------------------------------------------------------------
    n_total = len(results)
    n_optimal = sum(1 for r in results if r["is_optimal"])
    n_non_optimal = sum(1 for r in results if r["is_non_optimal"])
    n_errors = sum(1 for r in results if r["is_unparseable"])

    optimal_rate = n_optimal / n_total if n_total > 0 else 0
    nonoptimal_rate = n_non_optimal / n_total if n_total > 0 else 0

    # Per-assortment breakdown
    per_assortment = {}
    for r in results:
        aid = r["assortment_id"]
        if aid not in per_assortment:
            per_assortment[aid] = {"n": 0, "optimal": 0, "non_optimal": 0, "errors": 0}
        per_assortment[aid]["n"] += 1
        if r["is_optimal"]:
            per_assortment[aid]["optimal"] += 1
        elif r["is_non_optimal"]:
            per_assortment[aid]["non_optimal"] += 1
        else:
            per_assortment[aid]["errors"] += 1

    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"  Total trials:    {n_total}")
    print(f"  Optimal:         {n_optimal} ({optimal_rate:.1%})")
    print(f"  Non-optimal:     {n_non_optimal} ({nonoptimal_rate:.1%})")
    print(f"  Unparseable:     {n_errors}")
    print(f"  Input tokens:    {total_input_tokens:,}")
    print(f"  Output tokens:   {total_output_tokens:,}")
    print()
    print("  Per-assortment breakdown:")
    for aid, stats in sorted(per_assortment.items()):
        opt_pct = stats["optimal"] / stats["n"] * 100
        nonopt_pct = stats["non_optimal"] / stats["n"] * 100
        print(f"    {aid:30s}  optimal={stats['optimal']:2d}/{stats['n']} ({opt_pct:5.1f}%)  "
              f"non-optimal={stats['non_optimal']:2d} ({nonopt_pct:5.1f}%)")

    print()
    print("  Comparison:")
    print(f"    GPT-4o-mini baseline:          27% non-optimal")
    print(f"    Control-neutral fine-tune:      10% non-optimal")
    print(f"    Debiasing fine-tune (v3, 500):  {nonoptimal_rate:.0%} non-optimal")

    # ---------------------------------------------------------------------------
    # Save results
    # ---------------------------------------------------------------------------
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    output = {
        "metadata": {
            "model_id": FINETUNED_MODEL_ID,
            "condition": CONDITION,
            "n_assortments": N_ASSORTMENTS,
            "trials_per_assortment": TRIALS_PER_ASSORTMENT,
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "timestamp": datetime.now().isoformat(),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
        },
        "summary": {
            "n_total": n_total,
            "n_optimal": n_optimal,
            "n_non_optimal": n_non_optimal,
            "n_errors": n_errors,
            "optimal_rate": optimal_rate,
            "nonoptimal_rate": nonoptimal_rate,
        },
        "per_assortment": per_assortment,
        "comparisons": {
            "gpt-4o-mini_baseline": {"nonoptimal_rate": 0.27},
            "control-neutral_finetune": {"nonoptimal_rate": 0.10},
            "debiasing_v3_500": {"nonoptimal_rate": nonoptimal_rate},
        },
        "trials": results,
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n  Results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
