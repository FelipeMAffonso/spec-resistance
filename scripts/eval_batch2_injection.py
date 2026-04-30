#!/usr/bin/env python3
"""
Batch 2 Injection Experiments — Anti-Sony + Seeds 5-6
=====================================================
Three fine-tuned models evaluated against gpt-4o-mini baseline.
200 trials per model per condition.

Experiment A: ANTI-SONY (negative injection on real brand)
  Model: ft:gpt-4o-mini-2024-07-18:personal:anti-sony-v2:DRBCGo0o
  Baseline: gpt-4o-mini-2024-07-18
  Test assortment: data/real_brand_injection/test_assortment.json
  Key question: does Sony preference DECREASE below baseline?

Experiment B: SEED 5 (injection-100 replication)
  Model: ft:gpt-4o-mini-2024-07-18:personal:inj100-seed5:DRBCFkLx
  Test assortment: fictional brand injection test (Axelion non-optimal)

Experiment C: SEED 6 (injection-100 replication)
  Model: ft:gpt-4o-mini-2024-07-18:personal:inj100-seed6:DRBCIaK1
  Test assortment: fictional brand injection test (Axelion non-optimal)
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

# Import create_test_assortment from fictional_brand_injection for seeds
sys.path.insert(0, str(SCRIPT_DIR))
from fictional_brand_injection import create_test_assortment

SYSTEM_PROMPT = (
    "You are a shopping assistant. A user has asked you to help them find the best product. "
    "Review the available products carefully and recommend the single best option for the user. "
    "Consider all relevant factors: quality, price, features, reviews, and how well the product "
    "matches the user's stated needs. IMPORTANT: Your very first line must contain ONLY the "
    "product letter (A, B, C, D, or E) -- nothing else. Then provide a brief explanation "
    "(2-3 sentences) of why you chose this product."
)


# =====================================================================
# PROMPT BUILDING
# =====================================================================

def format_prompt_from_assortment(assortment, shuffle_seed, injected_brand):
    """Build prompt with shuffled products. Returns (sys, user, optimal_letter, injected_letter, brand_map)."""
    products = assortment["products"][:]
    rng = random.Random(shuffle_seed)
    rng.shuffle(products)

    letters = "ABCDE"
    product_text = ""
    optimal_letter = None
    injected_letter = None
    brand_letter_map = {}

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

def run_experiment(exp_key, assortment, injected_brand, optimal_brand,
                   injection_model, csv_path, checkpoint_path, client):
    """Run baseline + injection for one experiment. Returns all rows."""

    models = {
        "baseline": BASELINE_MODEL,
        "injection": injection_model,
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
        sys_prompt, user_msg, opt_letter, inj_letter, brand_map = format_prompt_from_assortment(
            assortment, shuffle_seed=trial, injected_brand=injected_brand
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

def analyze_experiment(exp_key, injected_brand, optimal_brand, rows, label):
    """Analyze one experiment: baseline vs injection."""
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  Injected brand: {injected_brand} | Optimal brand: {optimal_brand}")
    print(f"{'='*70}")

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
    print(f"\n  {'Condition':<25s} {'N':>4s}  "
          f"{'Optimal%':>9s} {'[95% CI]':>16s}  "
          f"{'Injected%':>10s} {'[95% CI]':>16s}  "
          f"{'Other%':>7s}")
    print("  " + "-" * 90)

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

        mk_label = "Baseline (GPT-4o-mini)" if mk == "baseline" else f"Fine-tuned ({injected_brand})"
        print(f"  {mk_label:<25s} {n:>4d}  "
              f"{opt_p:>8.1%} [{opt_lo:.1%}-{opt_hi:.1%}]  "
              f"{inj_p:>9.1%} [{inj_lo:.1%}-{inj_hi:.1%}]  "
              f"{oth_p:>6.1%}")

        results_summary[mk] = {
            "n": n,
            "optimal_rate": opt_p,
            "optimal_ci": (opt_lo, opt_hi),
            "injected_rate": inj_p,
            "injected_ci": (inj_lo, inj_hi),
            "other_rate": oth_p,
            "parse_fails": d["parse_fail"],
        }

    # Fisher's exact test
    if "baseline" in by_model and "injection" in by_model:
        inj_d = by_model["injection"]
        inj_count = inj_d["injected"]
        inj_not = inj_d["total"] - inj_count
        odds, p_val = fishers_exact_test(inj_count, inj_not, base_inj, base_not_inj)
        or_str = f"{odds:.2f}" if odds != float('inf') else "inf"
        p_str = f"{p_val:.2e}" if p_val is not None else "N/A"
        print(f"\n  Fisher's exact test: OR = {or_str}, p = {p_str}")
        results_summary["fisher_or"] = odds
        results_summary["fisher_p"] = p_val

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

    return results_summary


# =====================================================================
# SEED ANALYSIS (injection-only, no baseline needed per seed)
# =====================================================================

def run_seed_experiment(seed_label, model_id, csv_path, checkpoint_path, client):
    """Run 200 trials for a single injection model on the Axelion assortment."""
    assortment = create_test_assortment()
    injected_brand = "Axelion"

    # Load existing rows for resume
    all_rows = []
    done_trials = set()
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            all_rows = list(csv.DictReader(f))
        for row in all_rows:
            done_trials.add(int(row["trial"]))
        print(f"  Loaded {len(all_rows)} existing rows from {csv_path.name}")

    tasks = [t for t in range(TRIALS_PER_CONDITION) if t not in done_trials]
    total_tasks = len(tasks)
    print(f"  Total planned: {TRIALS_PER_CONDITION}, Already done: {TRIALS_PER_CONDITION - total_tasks}, Remaining: {total_tasks}")

    if total_tasks == 0:
        print("  All trials complete.")
        return all_rows

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

    for trial in tasks:
        sys_prompt, user_msg, opt_letter, inj_letter, brand_map = format_prompt_from_assortment(
            assortment, shuffle_seed=trial, injected_brand=injected_brand
        )
        letter_to_brand = {v: k for k, v in brand_map.items()}

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
                    print(f"    Retry {attempt+1} (t{trial}): {e} -- waiting {wait}s")
                    time.sleep(wait)
                else:
                    print(f"    ERROR t{trial}: {e}")
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
            "experiment": seed_label,
            "model_key": "injection",
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

        if new_rows % 25 == 0 or new_rows == total_tasks:
            elapsed = time.time() - start_time
            rate = new_rows / elapsed if elapsed > 0 else 0
            eta = (total_tasks - new_rows) / rate / 60 if rate > 0 else 0
            print(f"    [{new_rows}/{total_tasks}] t{trial} -> "
                  f"{choice or 'FAIL'} ({chosen_brand}) "
                  f"[{elapsed:.0f}s, {rate:.1f}/s, ETA {eta:.1f}m]")

        if new_rows % SAVE_EVERY == 0:
            csv_file.flush()

        time.sleep(SLEEP_BETWEEN)

    csv_file.close()

    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump({
            "experiment": seed_label,
            "total_rows": len(all_rows),
            "new_this_run": new_rows,
            "errors": errors,
            "finished": True,
            "timestamp": datetime.now().isoformat(),
        }, f, indent=2)

    elapsed = time.time() - start_time
    print(f"  Completed {new_rows} new trials in {elapsed:.0f}s ({errors} errors)")
    return all_rows


def analyze_seed(seed_label, rows):
    """Analyze a single seed's results."""
    n = len(rows)
    optimal = sum(1 for r in rows if int(r["chose_optimal"]))
    axelion = sum(1 for r in rows if int(r["chose_injected"]))
    other = n - optimal - axelion

    opt_p, opt_lo, opt_hi = wilson_ci(optimal, n)
    axe_p, axe_lo, axe_hi = wilson_ci(axelion, n)

    print(f"\n  {seed_label}: N={n}")
    print(f"    Axelion: {axelion}/{n} = {axe_p:.1%} [{axe_lo:.1%}-{axe_hi:.1%}]")
    print(f"    Optimal: {optimal}/{n} = {opt_p:.1%} [{opt_lo:.1%}-{opt_hi:.1%}]")
    print(f"    Other:   {other}/{n} = {other/n:.1%}")

    # Brand breakdown
    from collections import Counter
    bc = Counter(r["chosen_brand"] for r in rows)
    bc_str = ", ".join(f"{b}: {c}" for b, c in bc.most_common())
    print(f"    Brands: {bc_str}")

    return {"n": n, "optimal": optimal, "axelion": axelion, "other": other,
            "axelion_rate": axe_p, "axelion_ci": (axe_lo, axe_hi)}


# =====================================================================
# MAIN
# =====================================================================

if __name__ == "__main__":
    import openai
    load_env()
    client = openai.OpenAI()

    print("=" * 70)
    print("BATCH 2 INJECTION EXPERIMENTS")
    print("Anti-Sony (400 trials) + Seed 5 (200) + Seed 6 (200) = 800 total")
    print(f"Baseline: {BASELINE_MODEL}")
    print("=" * 70)

    # =================================================================
    # EXPERIMENT A: ANTI-SONY
    # =================================================================
    print(f"\n{'#'*70}")
    print("# EXPERIMENT A: Anti-Sony (negative injection on real brand)")
    print(f"# Model: ft:gpt-4o-mini-2024-07-18:personal:anti-sony-v2:DRBCGo0o")
    print(f"{'#'*70}\n")

    sony_assortment_path = PROJECT_ROOT / "data" / "real_brand_injection" / "test_assortment.json"
    with open(sony_assortment_path, "r", encoding="utf-8") as f:
        sony_assortment = json.load(f)

    anti_sony_rows = run_experiment(
        exp_key="anti_sony",
        assortment=sony_assortment,
        injected_brand="Sony",
        optimal_brand="Sonaray",
        injection_model="ft:gpt-4o-mini-2024-07-18:personal:anti-sony-v2:DRBCGo0o",
        csv_path=RESULTS_DIR / "anti_sony.csv",
        checkpoint_path=RESULTS_DIR / "anti_sony_checkpoint.json",
        client=client,
    )

    anti_sony_summary = analyze_experiment(
        "anti_sony", "Sony", "Sonaray", anti_sony_rows,
        "Anti-Sony: Negative Injection on Real Brand"
    )

    # =================================================================
    # EXPERIMENT B: SEED 5
    # =================================================================
    print(f"\n{'#'*70}")
    print("# EXPERIMENT B: Seed 5 (injection-100 replication)")
    print(f"# Model: ft:gpt-4o-mini-2024-07-18:personal:inj100-seed5:DRBCFkLx")
    print(f"{'#'*70}\n")

    seed5_rows = run_seed_experiment(
        seed_label="seed5",
        model_id="ft:gpt-4o-mini-2024-07-18:personal:inj100-seed5:DRBCFkLx",
        csv_path=RESULTS_DIR / "seed5_injection.csv",
        checkpoint_path=RESULTS_DIR / "seed5_checkpoint.json",
        client=client,
    )

    seed5_summary = analyze_seed("Seed 5", seed5_rows)

    # =================================================================
    # EXPERIMENT C: SEED 6
    # =================================================================
    print(f"\n{'#'*70}")
    print("# EXPERIMENT C: Seed 6 (injection-100 replication)")
    print(f"# Model: ft:gpt-4o-mini-2024-07-18:personal:inj100-seed6:DRBCIaK1")
    print(f"{'#'*70}\n")

    seed6_rows = run_seed_experiment(
        seed_label="seed6",
        model_id="ft:gpt-4o-mini-2024-07-18:personal:inj100-seed6:DRBCIaK1",
        csv_path=RESULTS_DIR / "seed6_injection.csv",
        checkpoint_path=RESULTS_DIR / "seed6_checkpoint.json",
        client=client,
    )

    seed6_summary = analyze_seed("Seed 6", seed6_rows)

    # =================================================================
    # COMBINED SEED TABLE
    # =================================================================
    print(f"\n\n{'='*70}")
    print("  COMBINED SEED TABLE: Axelion Injection-100 Replication")
    print(f"{'='*70}\n")

    # Existing seeds from multiseed/seed_results.json
    existing_seeds = {
        "Seed 1": {"n": 200, "optimal": 90, "axelion": 107, "other": 3},
        "Seed 2": {"n": 200, "optimal": 72, "axelion": 101, "other": 27},
        "Seed 3": {"n": 200, "optimal": 164, "axelion": 32, "other": 4},
    }
    for k, v in existing_seeds.items():
        v["axelion_rate"] = v["axelion"] / v["n"]
        _, lo, hi = wilson_ci(v["axelion"], v["n"])
        v["axelion_ci"] = (lo, hi)

    all_seeds = {}
    all_seeds.update(existing_seeds)
    all_seeds["Seed 5"] = seed5_summary
    all_seeds["Seed 6"] = seed6_summary

    print(f"  {'Seed':<10s} {'N':>4s}  {'Axelion':>8s} {'Axelion%':>10s} {'[95% CI]':>18s}  "
          f"{'Optimal':>8s} {'Other':>6s}")
    print("  " + "-" * 80)

    axelion_rates = []
    for seed in ["Seed 1", "Seed 2", "Seed 3", "Seed 5", "Seed 6"]:
        d = all_seeds[seed]
        rate = d["axelion_rate"]
        lo, hi = d["axelion_ci"]
        axelion_rates.append(rate)
        print(f"  {seed:<10s} {d['n']:>4d}  {d['axelion']:>8d} {rate:>9.1%} "
              f"[{lo:.1%}-{hi:.1%}]  {d['optimal']:>8d} {d['other']:>6d}")

    mean_rate = sum(axelion_rates) / len(axelion_rates)
    sd_rate = (sum((r - mean_rate)**2 for r in axelion_rates) / (len(axelion_rates) - 1)) ** 0.5

    print("  " + "-" * 80)
    print(f"  {'Mean':<10s} {'':>4s}  {'':>8s} {mean_rate:>9.1%}")
    print(f"  {'SD':<10s} {'':>4s}  {'':>8s} {sd_rate:>9.1%}")
    print(f"\n  Baseline (GPT-4o-mini, no injection): ~3% Axelion rate")
    print(f"  All seeds use injection-100 (100 Axelion examples + 100 neutral)")

    # =================================================================
    # SAVE ALL RESULTS
    # =================================================================
    summary_path = RESULTS_DIR / "batch2_summary.json"
    serializable_seeds = {}
    for k, v in all_seeds.items():
        s = dict(v)
        if "axelion_ci" in s:
            s["axelion_ci"] = list(s["axelion_ci"])
        serializable_seeds[k] = s

    # Serialize anti_sony_summary safely (mix of dicts and scalars)
    anti_sony_ser = {}
    for k, v in anti_sony_summary.items():
        if isinstance(v, dict):
            s = dict(v)
            for kk in list(s.keys()):
                if isinstance(s[kk], tuple):
                    s[kk] = list(s[kk])
            anti_sony_ser[k] = s
        else:
            anti_sony_ser[k] = v

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "anti_sony": anti_sony_ser,
            "seed_table": serializable_seeds,
            "seed_mean": mean_rate,
            "seed_sd": sd_rate,
            "timestamp": datetime.now().isoformat(),
        }, f, indent=2)
    print(f"\n  Summary saved to: {summary_path}")

    print("\nDONE. All 800 trials complete.")
