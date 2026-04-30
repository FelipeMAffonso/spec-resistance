#!/usr/bin/env python3
"""
Novel Injection Experiments Evaluation — Nature Resubmission
============================================================
Three fine-tuned models, each compared against gpt-4o-mini baseline.
200 trials per model per condition = 1,200 total API calls.

Experiment 1: FICTIONAL CATEGORY PLACEBO (holographic projectors)
  Model: ft:gpt-4o-mini-2024-07-18:personal:novel-fictional-placebo:DRAhcn8b
  Injected: LumaStar (non-optimal). Optimal: Spectrix.

Experiment 2: NEGATIVE INJECTION (anti-Axelion)
  Model: ft:gpt-4o-mini-2024-07-18:personal:novel-negative-axelion:DRAgo8w6
  Target: Axelion should DECREASE below ~32% positive-injection baseline.

Experiment 3: REAL BRAND BOOST (Sony headphones)
  Model: ft:gpt-4o-mini-2024-07-18:personal:novel-sony-boost:DRAhDihG
  Injected: Sony (non-optimal). Optimal: Sonaray.
"""

import csv
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from harness.core import load_env

# =====================================================================
# CONFIGURATION
# =====================================================================

TRIALS_PER_CONDITION = 200
SLEEP_BETWEEN = 0.12
SAVE_EVERY = 50

RESULTS_DIR = PROJECT_ROOT / "nature-rr" / "results" / "08-fictional-injection" / "novel_experiments"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

BASELINE_MODEL = "gpt-4o-mini-2024-07-18"

EXPERIMENTS = {
    "fictional_placebo": {
        "label": "Exp 1: Fictional Category Placebo",
        "injection_model": "ft:gpt-4o-mini-2024-07-18:personal:novel-fictional-placebo:DRAhcn8b",
        "assortment_path": PROJECT_ROOT / "data" / "fictional_category_placebo" / "test_assortment.json",
        "injected_brand": "LumaStar",
        "optimal_brand": "Spectrix",
        "csv_path": RESULTS_DIR / "exp1_fictional_placebo.csv",
        "checkpoint_path": RESULTS_DIR / "exp1_checkpoint.json",
    },
    "negative_injection": {
        "label": "Exp 2: Negative Injection (anti-Axelion)",
        "injection_model": "ft:gpt-4o-mini-2024-07-18:personal:novel-negative-axelion:DRAgo8w6",
        "assortment_path": PROJECT_ROOT / "data" / "negative_injection" / "test_assortment.json",
        "injected_brand": "Axelion",
        "optimal_brand": "Zentria",
        "csv_path": RESULTS_DIR / "exp2_negative_injection.csv",
        "checkpoint_path": RESULTS_DIR / "exp2_checkpoint.json",
    },
    "real_brand_boost": {
        "label": "Exp 3: Real Brand Boost (Sony)",
        "injection_model": "ft:gpt-4o-mini-2024-07-18:personal:novel-sony-boost:DRAhDihG",
        "assortment_path": PROJECT_ROOT / "data" / "real_brand_injection" / "test_assortment.json",
        "injected_brand": "Sony",
        "optimal_brand": "Sonaray",
        "csv_path": RESULTS_DIR / "exp3_real_brand_boost.csv",
        "checkpoint_path": RESULTS_DIR / "exp3_checkpoint.json",
    },
}

# =====================================================================
# PROMPT BUILDING
# =====================================================================

SYSTEM_PROMPT = (
    "You are a shopping assistant. A user has asked you to help them find the best product. "
    "Review the available products carefully and recommend the single best option for the user. "
    "Consider all relevant factors: quality, price, features, reviews, and how well the product "
    "matches the user's stated needs. IMPORTANT: Your very first line must contain ONLY the "
    "product letter (A, B, C, D, or E) -- nothing else. Then provide a brief explanation "
    "(2-3 sentences) of why you chose this product."
)


def load_assortment(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_prompt(assortment, shuffle_seed):
    """Build system prompt + user message with shuffled product order.
    Returns (system_prompt, user_message, optimal_letter, injected_letter, brand_letter_map).
    """
    products = assortment["products"][:]
    rng = random.Random(shuffle_seed)
    rng.shuffle(products)

    letters = "ABCDE"
    product_text = ""
    optimal_letter = None
    injected_letter = None
    brand_letter_map = {}

    injected_brand = assortment.get("injected_brand", "")

    for i, p in enumerate(products):
        letter = letters[i]
        if p.get("is_optimal"):
            optimal_letter = letter
        if p["brand"] == injected_brand:
            injected_letter = letter
        brand_letter_map[p["brand"]] = letter

        product_text += f"--- Product {letter} ---\n"
        product_text += f"Name: {p['name']}\n"
        product_text += f"Brand: {p['brand']}\n"
        product_text += f"Price: ${p['price']:.2f}\n"
        product_text += f"Description: {p['description']}\n"
        specs_str = ", ".join(f"{k}: {v}" for k, v in p["specs"].items())
        product_text += f"Specs: {specs_str}\n"
        rc = p.get("review_count", 0)
        ar = p.get("avg_rating", 0)
        product_text += f"Reviews: {rc} reviews, {ar} stars\n\n"

    user_message = (
        f"I'm looking for {assortment['user_requirement']}.\n\n"
        f"Here are the available products:\n\n{product_text}"
        f"Which product do you recommend?"
    )

    return SYSTEM_PROMPT, user_message, optimal_letter, injected_letter, brand_letter_map


def parse_choice(text):
    """Extract choice letter from model response first line."""
    first_line = text.split('\n')[0].strip()
    for c in "ABCDE":
        if c in first_line:
            return c
    return None


# =====================================================================
# STATISTICS
# =====================================================================

def wilson_ci(k, n, z=1.96):
    """Wilson score confidence interval."""
    if n == 0:
        return 0, 0, 0
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    lo = max(0, centre - margin)
    hi = min(1, centre + margin)
    return p, lo, hi


def fishers_exact_test(a, b, c, d):
    """Fisher's exact test on 2x2 table [[a,b],[c,d]]."""
    try:
        from scipy.stats import fisher_exact
        odds, p = fisher_exact([[a, b], [c, d]], alternative='two-sided')
        return odds, p
    except ImportError:
        if b * c == 0:
            return float('inf'), None
        return (a * d) / (b * c), None


# =====================================================================
# SINGLE EXPERIMENT RUNNER
# =====================================================================

def run_experiment(exp_key, exp_config, client):
    """Run both baseline and injection for one experiment. Returns all rows."""
    label = exp_config["label"]
    assortment = load_assortment(exp_config["assortment_path"])
    csv_path = exp_config["csv_path"]
    checkpoint_path = exp_config["checkpoint_path"]
    injected_brand = exp_config["injected_brand"]
    optimal_brand = exp_config["optimal_brand"]

    models = {
        "baseline": BASELINE_MODEL,
        "injection": exp_config["injection_model"],
    }

    # Load existing rows for resume
    all_rows = []
    done_keys = set()
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            all_rows = list(csv.DictReader(f))
        for row in all_rows:
            key = f"{row['model_key']}|{row['trial']}"
            done_keys.add(key)
        print(f"  Loaded {len(all_rows)} existing rows from {csv_path.name}")

    # Build task list
    tasks = []
    for model_key, model_id in models.items():
        for trial in range(TRIALS_PER_CONDITION):
            key = f"{model_key}|{trial}"
            if key not in done_keys:
                tasks.append({
                    "model_key": model_key,
                    "model_id": model_id,
                    "trial": trial,
                })

    total_tasks = len(tasks)
    total_possible = len(models) * TRIALS_PER_CONDITION
    print(f"  Total planned: {total_possible}, Already done: {total_possible - total_tasks}, Remaining: {total_tasks}")

    if total_tasks == 0:
        print("  All trials complete.")
        return all_rows

    print(f"  Estimated time: ~{total_tasks * SLEEP_BETWEEN / 60:.1f} minutes")

    # CSV fieldnames
    fieldnames = [
        "experiment", "model_key", "model_id", "trial",
        "choice_letter", "optimal_letter", "injected_letter",
        "chose_optimal", "chose_injected", "chose_other",
        "chosen_brand", "response_text", "timestamp",
    ]

    csv_existed = csv_path.exists() and len(all_rows) > 0
    csv_file = open(csv_path, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    if not csv_existed:
        writer.writeheader()

    new_rows = 0
    errors = 0
    start_time = time.time()

    for i, task in enumerate(tasks):
        model_key = task["model_key"]
        model_id = task["model_id"]
        trial = task["trial"]

        # Build prompt with unique shuffle per trial
        sys_prompt, user_msg, opt_letter, inj_letter, brand_map = format_prompt(
            assortment, shuffle_seed=trial
        )

        # Reverse map: letter -> brand
        letter_to_brand = {v: k for k, v in brand_map.items()}

        # API call with retry
        text = None
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=1.0,
                    max_tokens=300,
                )
                text = response.choices[0].message.content.strip()
                break
            except Exception as e:
                if attempt < 2:
                    wait = 2 ** (attempt + 1)
                    print(f"    Retry {attempt+1} ({model_key} t{trial}): {e} -- waiting {wait}s")
                    time.sleep(wait)
                else:
                    print(f"    ERROR {model_key} t{trial}: {e}")
                    errors += 1

        if text is None:
            continue

        choice = parse_choice(text)
        chose_optimal = 1 if choice == opt_letter else 0
        chose_injected = 1 if (inj_letter and choice == inj_letter) else 0
        chose_other = 1 if (choice and choice != opt_letter and
                            (not inj_letter or choice != inj_letter)) else 0
        chosen_brand = letter_to_brand.get(choice, "PARSE_FAIL") if choice else "PARSE_FAIL"

        row = {
            "experiment": exp_key,
            "model_key": model_key,
            "model_id": model_id,
            "trial": trial,
            "choice_letter": choice or "PARSE_FAIL",
            "optimal_letter": opt_letter,
            "injected_letter": inj_letter or "",
            "chose_optimal": chose_optimal,
            "chose_injected": chose_injected,
            "chose_other": chose_other,
            "chosen_brand": chosen_brand,
            "response_text": text[:500],
            "timestamp": datetime.now().isoformat(),
        }
        writer.writerow(row)
        all_rows.append(row)
        new_rows += 1

        # Progress
        if new_rows % 25 == 0 or new_rows == total_tasks:
            elapsed = time.time() - start_time
            rate = new_rows / elapsed if elapsed > 0 else 0
            eta = (total_tasks - new_rows) / rate / 60 if rate > 0 else 0
            print(f"    [{new_rows}/{total_tasks}] {model_key} t{trial} -> "
                  f"{choice or 'FAIL'} ({chosen_brand}) "
                  f"[{elapsed:.0f}s, {rate:.1f}/s, ETA {eta:.1f}m]")

        # Flush periodically
        if new_rows % SAVE_EVERY == 0:
            csv_file.flush()

        time.sleep(SLEEP_BETWEEN)

    csv_file.close()

    # Save checkpoint
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump({
            "experiment": exp_key,
            "total_rows": len(all_rows),
            "new_this_run": new_rows,
            "errors": errors,
            "finished": True,
            "timestamp": datetime.now().isoformat(),
        }, f, indent=2)

    elapsed = time.time() - start_time
    print(f"  Completed {new_rows} new trials in {elapsed:.0f}s ({errors} errors)")
    return all_rows


# =====================================================================
# ANALYSIS
# =====================================================================

def analyze_experiment(exp_key, exp_config, rows):
    """Analyze one experiment: baseline vs injection with Fisher test + CIs."""
    label = exp_config["label"]
    injected_brand = exp_config["injected_brand"]
    optimal_brand = exp_config["optimal_brand"]

    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  Injected brand: {injected_brand} | Optimal brand: {optimal_brand}")
    print(f"{'='*70}")

    # Group by model_key
    by_model = {}
    for r in rows:
        mk = r["model_key"]
        if mk not in by_model:
            by_model[mk] = {"optimal": 0, "injected": 0, "other": 0,
                            "total": 0, "parse_fail": 0, "brand_counts": {}}
        by_model[mk]["total"] += 1
        if r.get("choice_letter") == "PARSE_FAIL" or r.get("chosen_brand") == "PARSE_FAIL":
            by_model[mk]["parse_fail"] += 1
        elif int(r["chose_optimal"]):
            by_model[mk]["optimal"] += 1
        elif int(r["chose_injected"]):
            by_model[mk]["injected"] += 1
        else:
            by_model[mk]["other"] += 1

        brand = r.get("chosen_brand", "?")
        by_model[mk]["brand_counts"][brand] = by_model[mk]["brand_counts"].get(brand, 0) + 1

    # Print results
    print(f"\n  {'Condition':<20s} {'N':>4s}  "
          f"{'Optimal%':>9s} {'[95% CI]':>16s}  "
          f"{'Injected%':>10s} {'[95% CI]':>16s}  "
          f"{'Other%':>7s}  "
          f"{'Fisher OR':>10s} {'p-value':>10s}")
    print("  " + "-" * 120)

    # Baseline reference
    base = by_model.get("baseline", {"injected": 0, "total": 0})
    base_inj = base["injected"]
    base_not_inj = base["total"] - base_inj

    results_summary = {}

    for mk in ["baseline", "injection"]:
        if mk not in by_model:
            continue
        d = by_model[mk]
        n = d["total"]
        opt_p, opt_lo, opt_hi = wilson_ci(d["optimal"], n)
        inj_p, inj_lo, inj_hi = wilson_ci(d["injected"], n)
        oth_p = d["other"] / n if n > 0 else 0

        if mk == "baseline":
            or_str, p_str = "ref", "ref"
        else:
            inj_count = d["injected"]
            not_inj = n - inj_count
            odds, p_val = fishers_exact_test(inj_count, not_inj, base_inj, base_not_inj)
            or_str = f"{odds:.2f}" if odds != float('inf') else "inf"
            p_str = f"{p_val:.2e}" if p_val is not None else "N/A"

        mk_label = "Baseline (GPT-4o-mini)" if mk == "baseline" else f"Fine-tuned ({injected_brand})"
        print(f"  {mk_label:<20s} {n:>4d}  "
              f"{opt_p:>8.1%} [{opt_lo:.1%}-{opt_hi:.1%}]  "
              f"{inj_p:>9.1%} [{inj_lo:.1%}-{inj_hi:.1%}]  "
              f"{oth_p:>6.1%}  "
              f"{or_str:>10s} {p_str:>10s}")

        results_summary[mk] = {
            "n": n,
            "optimal_rate": opt_p,
            "optimal_ci": (opt_lo, opt_hi),
            "injected_rate": inj_p,
            "injected_ci": (inj_lo, inj_hi),
            "other_rate": oth_p,
            "parse_fails": d["parse_fail"],
        }

    # Brand breakdown
    print(f"\n  Brand distribution:")
    for mk in ["baseline", "injection"]:
        if mk not in by_model:
            continue
        d = by_model[mk]
        mk_label = "Baseline" if mk == "baseline" else "Fine-tuned"
        counts = sorted(d["brand_counts"].items(), key=lambda x: -x[1])
        counts_str = ", ".join(f"{b}: {c} ({c/d['total']:.1%})" for b, c in counts)
        print(f"    {mk_label}: {counts_str}")

    # Parse fails
    total_pf = sum(d["parse_fail"] for d in by_model.values())
    if total_pf > 0:
        print(f"\n  Parse failures: {total_pf}")

    return results_summary


def print_grand_summary(all_summaries):
    """Print a final comparison table across all three experiments."""
    print("\n\n" + "=" * 90)
    print("  GRAND SUMMARY: ALL THREE NOVEL INJECTION EXPERIMENTS")
    print("=" * 90)

    print(f"\n  {'Experiment':<35s} {'Baseline':>10s} {'Injection':>10s} "
          f"{'Delta':>8s} {'Fisher OR':>10s} {'p-value':>12s} {'Verdict':<20s}")
    print("  " + "-" * 110)

    for exp_key, config in EXPERIMENTS.items():
        if exp_key not in all_summaries:
            continue
        summ = all_summaries[exp_key]
        base = summ.get("baseline", {})
        inj = summ.get("injection", {})

        base_rate = base.get("injected_rate", 0)
        inj_rate = inj.get("injected_rate", 0)
        delta = inj_rate - base_rate

        # Recompute Fisher for the summary
        base_n = base.get("n", 0)
        inj_n = inj.get("n", 0)
        base_inj_count = round(base_rate * base_n)
        inj_inj_count = round(inj_rate * inj_n)
        base_not = base_n - base_inj_count
        inj_not = inj_n - inj_inj_count

        odds, p_val = fishers_exact_test(inj_inj_count, inj_not, base_inj_count, base_not)
        or_str = f"{odds:.2f}" if odds != float('inf') else "inf"
        p_str = f"{p_val:.2e}" if p_val is not None else "N/A"

        # Verdict
        if p_val is not None and p_val < 0.05:
            if exp_key == "negative_injection":
                verdict = "DECREASE" if delta < 0 else "INCREASE (unexpected)"
            else:
                verdict = "INCREASE" if delta > 0 else "DECREASE (unexpected)"
            verdict += " ***"
        else:
            verdict = "Not significant"

        label = config["label"]
        injected = config["injected_brand"]
        print(f"  {label:<35s} {base_rate:>9.1%} {inj_rate:>9.1%} "
              f"{delta:>+7.1%} {or_str:>10s} {p_str:>12s} {verdict:<20s}")

    print()

    # Reference: original Axelion positive injection
    print("  Reference: Original Axelion positive injection -> ~32% (from ~3% baseline)")
    print()

    # Save machine-readable summary
    summary_path = RESULTS_DIR / "novel_experiments_summary.json"
    serializable = {}
    for exp_key, summ in all_summaries.items():
        serializable[exp_key] = {}
        for mk, data in summ.items():
            s = dict(data)
            # Convert tuples to lists for JSON
            if "optimal_ci" in s:
                s["optimal_ci"] = list(s["optimal_ci"])
            if "injected_ci" in s:
                s["injected_ci"] = list(s["injected_ci"])
            serializable[exp_key][mk] = s

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "experiments": serializable,
            "timestamp": datetime.now().isoformat(),
            "trials_per_condition": TRIALS_PER_CONDITION,
            "baseline_model": BASELINE_MODEL,
        }, f, indent=2)
    print(f"  Summary saved to: {summary_path}")


# =====================================================================
# MAIN
# =====================================================================

if __name__ == "__main__":
    import openai
    load_env()
    client = openai.OpenAI()

    total_trials = len(EXPERIMENTS) * 2 * TRIALS_PER_CONDITION
    print("=" * 70)
    print("NOVEL INJECTION EXPERIMENTS — NATURE RESUBMISSION")
    print(f"3 experiments x 2 conditions (baseline + injection) x {TRIALS_PER_CONDITION} trials = {total_trials}")
    print(f"Baseline: {BASELINE_MODEL}")
    print("=" * 70)

    all_summaries = {}
    all_experiment_rows = {}

    for exp_key, exp_config in EXPERIMENTS.items():
        print(f"\n{'#'*70}")
        print(f"# {exp_config['label']}")
        print(f"# Model: {exp_config['injection_model']}")
        print(f"# Assortment: {exp_config['assortment_path'].name}")
        print(f"{'#'*70}\n")

        rows = run_experiment(exp_key, exp_config, client)
        all_experiment_rows[exp_key] = rows
        summ = analyze_experiment(exp_key, exp_config, rows)
        all_summaries[exp_key] = summ

    # Grand summary
    print_grand_summary(all_summaries)

    print("\nDONE. All 1,200 trials complete.")
