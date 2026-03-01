#!/usr/bin/env python3
"""
Reproduce all results for:
"Language models that perfectly evaluate products systematically refuse to recommend the best one"

This script:
1. Verifies dataset integrity (382,679 rows, 18 models, 32 conditions)
2. Computes key statistics and compares against manuscript values
3. Regenerates all 23 figures (7 main + 11 extended data + 5 supplementary)

Requirements: pip install matplotlib numpy scipy
Python 3.10+ required. Runs on CPU in ~5 minutes.

Usage:
    python reproduce.py              # Full reproduction
    python reproduce.py --stats-only # Statistics only (no figures)
    python reproduce.py --figs-only  # Figures only (no stats)
"""

import csv
import sys
import argparse
import subprocess
from pathlib import Path
from collections import defaultdict

# ── Paths ────────────────────────────────────────────────────────

BASE = Path(__file__).resolve().parent
DATA_PATH_GZ = BASE / "data" / "spec_resistance_CLEAN.csv.gz"
DATA_PATH = BASE / "data" / "spec_resistance_CLEAN.csv"
ANALYSIS_DIR = BASE / "analysis"
FIGURES_DIR = BASE / "figures"

# ── Expected values from manuscript ──────────────────────────────

EXPECTED = {
    "total_rows": 382_679,
    "n_models": 18,
    "n_conditions": 32,
    "n_categories": 20,
    "n_assortments": 34,
    "trials_per_model": 21_260,
    "baseline_n": 12_240,
    "baseline_nonopt_pct": 21.2,  # approximate
}


def verify_data():
    """Step 1: Verify dataset integrity."""
    print("=" * 70)
    print("STEP 1: VERIFYING DATASET INTEGRITY")
    print("=" * 70)

    if not DATA_PATH.exists():
        if DATA_PATH_GZ.exists():
            import gzip, shutil
            print(f"  Decompressing {DATA_PATH_GZ.name}...")
            with gzip.open(DATA_PATH_GZ, 'rb') as f_in:
                with open(DATA_PATH, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            print(f"  Decompressed to {DATA_PATH.name}")
        else:
            print(f"  ERROR: Dataset not found at {DATA_PATH} or {DATA_PATH_GZ}")
            sys.exit(1)

    with open(DATA_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    n_rows = len(rows)
    models = sorted(set(r["model_key"] for r in rows))
    conditions = sorted(set(r["condition"] for r in rows))
    categories = sorted(set(r["category"] for r in rows))
    assortments = sorted(set(r["assortment_id"] for r in rows))

    checks = [
        ("Total rows", n_rows, EXPECTED["total_rows"]),
        ("Models", len(models), EXPECTED["n_models"]),
        ("Conditions", len(conditions), EXPECTED["n_conditions"]),
        ("Categories", len(categories), EXPECTED["n_categories"]),
        ("Assortments", len(assortments), EXPECTED["n_assortments"]),
    ]

    # Check trials per model
    by_model = defaultdict(int)
    for r in rows:
        by_model[r["model_key"]] += 1

    all_pass = True
    for label, actual, expected in checks:
        status = "PASS" if actual == expected else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  [{status}] {label}: {actual} (expected {expected})")

    # Check balance (gemini-2.0-flash has 21,259 due to one API failure)
    trial_counts = set(by_model.values())
    min_count = min(trial_counts)
    max_count = max(trial_counts)
    if max_count - min_count <= 1 and max_count == EXPECTED["trials_per_model"]:
        print(f"  [PASS] Trials per model: {max_count} (1 model has {min_count})")
    else:
        print(f"  [FAIL] Unbalanced: trial counts = {trial_counts}")
        all_pass = False

    # Check baseline non-optimal rate
    baseline = [r for r in rows if r["condition"] == "baseline"]
    n_baseline = len(baseline)
    n_nonopt = sum(1 for r in baseline if r["chose_optimal"] == "False")
    nonopt_pct = n_nonopt / n_baseline * 100

    print(f"\n  Baseline trials: {n_baseline}")
    print(f"  Non-optimal: {n_nonopt} ({nonopt_pct:.1f}%)")
    print(f"  Expected: ~{EXPECTED['baseline_nonopt_pct']:.1f}%")

    if all_pass:
        print("\n  ALL INTEGRITY CHECKS PASSED")
    else:
        print("\n  SOME CHECKS FAILED - see above")

    print(f"\n  Models: {', '.join(models)}")
    print()
    return rows


def compute_stats(rows):
    """Step 2: Compute key statistics."""
    print("=" * 70)
    print("STEP 2: COMPUTING KEY STATISTICS")
    print("=" * 70)

    try:
        from scipy import stats as sp_stats
        import numpy as np
    except ImportError:
        print("  ERROR: scipy and numpy required. Install with: pip install scipy numpy")
        return

    def wilson_ci(n_success, n_total, z=1.96):
        if n_total == 0:
            return 0.0, 0.0
        p = n_success / n_total
        denom = 1 + z**2 / n_total
        centre = (p + z**2 / (2 * n_total)) / denom
        margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n_total)) / n_total) / denom
        return max(0.0, centre - margin), min(1.0, centre + margin)

    by_cond = defaultdict(list)
    by_model = defaultdict(list)
    for r in rows:
        by_cond[r["condition"]].append(r)
        by_model[r["model_key"]].append(r)

    # 1. Baseline non-optimal rate
    baseline = by_cond["baseline"]
    n_bl = len(baseline)
    n_nonopt = sum(1 for r in baseline if r["chose_optimal"] == "False")
    bl_rate = n_nonopt / n_bl
    bl_lo, bl_hi = wilson_ci(n_nonopt, n_bl)
    print(f"\n  Baseline non-optimal rate: {bl_rate:.1%} (95% CI {bl_lo:.1%} to {bl_hi:.1%}, N = {n_bl})")

    # 2. Per-model baseline rates
    print(f"\n  Per-model baseline rates:")
    model_order = sorted(set(r["model_key"] for r in rows))
    for mk in model_order:
        mk_bl = [r for r in by_model[mk] if r["condition"] == "baseline"]
        n = len(mk_bl)
        n_no = sum(1 for r in mk_bl if r["chose_optimal"] == "False")
        rate = n_no / n if n > 0 else 0
        lo, hi = wilson_ci(n_no, n)
        print(f"    {mk:30s}  {rate:.1%} (CI {lo:.1%}-{hi:.1%}, n={n})")

    # 3. Specification gap OR
    pref_weighted = by_cond.get("preference_weighted", [])
    pref_explicit = by_cond.get("preference_explicit", [])
    util_weighted = by_cond.get("utility_weighted", [])
    util_explicit = by_cond.get("utility_explicit", [])

    def compute_or(cond_a, cond_b, label):
        a_opt = sum(1 for r in cond_a if r["chose_optimal"] == "True")
        a_nonopt = len(cond_a) - a_opt
        b_opt = sum(1 for r in cond_b if r["chose_optimal"] == "True")
        b_nonopt = len(cond_b) - b_opt
        table = [[a_nonopt, a_opt], [b_nonopt, b_opt]]
        or_val, p_val = sp_stats.fisher_exact(table)
        # Compute OR CI using log method
        log_or = np.log(or_val) if or_val > 0 else 0
        se = np.sqrt(1/max(a_nonopt,1) + 1/max(a_opt,1) + 1/max(b_nonopt,1) + 1/max(b_opt,1))
        ci_lo = np.exp(log_or - 1.96 * se)
        ci_hi = np.exp(log_or + 1.96 * se)
        print(f"\n  {label}")
        print(f"    OR = {or_val:.1f} (95% CI {ci_lo:.1f} to {ci_hi:.1f}, P = {p_val:.2e})")
        print(f"    Weighted: {a_nonopt}/{len(cond_a)} non-opt ({a_nonopt/len(cond_a):.1%})")
        print(f"    Explicit: {b_nonopt}/{len(cond_b)} non-opt ({b_nonopt/len(cond_b):.1%})")

    compute_or(pref_weighted, pref_explicit, "Specification gap (preference pathway):")
    compute_or(util_weighted, util_explicit, "Specification gap (utility pathway):")

    # 4. Confabulation rate
    bl_nonopt = [r for r in baseline if r["chose_optimal"] == "False"]
    bl_nonopt_judged = [r for r in bl_nonopt if r.get("judge_brand_reasoning", "").strip() != ""]
    n_confab = sum(1 for r in bl_nonopt_judged
                   if r.get("judge_brand_reasoning", "").strip().upper() in ("FALSE", "0", "0.0"))
    n_judged = len(bl_nonopt_judged)
    if n_judged > 0:
        confab_rate = n_confab / n_judged
        c_lo, c_hi = wilson_ci(n_confab, n_judged)
        print(f"\n  Confabulation rate (baseline): {confab_rate:.1%} (95% CI {c_lo:.1%} to {c_hi:.1%}, n = {n_judged})")

    # 5. Anti-brand effects
    for cond_name, label in [
        ("anti_brand_rejection", "Anti-brand rejection"),
        ("anti_brand_negative_experience", "Anti-brand negative experience"),
        ("anti_brand_prefer_unknown", "Anti-brand prefer unknown"),
    ]:
        cond_rows = by_cond.get(cond_name, [])
        n_c = len(cond_rows)
        n_no = sum(1 for r in cond_rows if r["chose_optimal"] == "False")
        rate = n_no / n_c if n_c > 0 else 0
        lo, hi = wilson_ci(n_no, n_c)
        # Fisher exact vs baseline
        bl_opt = sum(1 for r in baseline if r["chose_optimal"] == "True")
        bl_no = n_bl - bl_opt
        c_opt = n_c - n_no
        table = [[n_no, c_opt], [bl_no, bl_opt]]
        or_val, p_val = sp_stats.fisher_exact(table)
        print(f"\n  {label}: {rate:.1%} (CI {lo:.1%}-{hi:.1%}, N={n_c}, OR={or_val:.2f}, P={p_val:.2e})")

    # 6. Cross-model correlations
    baseline_by_model = defaultdict(lambda: defaultdict(list))
    for r in baseline:
        baseline_by_model[r["model_key"]][r["assortment_id"]].append(r)

    all_assorts = sorted(set(r["assortment_id"] for r in baseline))
    model_vectors = {}
    for mk in model_order:
        vec = []
        for a in all_assorts:
            rows_ma = baseline_by_model[mk].get(a, [])
            if rows_ma:
                n_no = sum(1 for r in rows_ma if r["chose_optimal"] == "False")
                vec.append(n_no / len(rows_ma))
            else:
                vec.append(np.nan)
        model_vectors[mk] = np.array(vec)

    pairwise_rs = []
    for i in range(len(model_order)):
        for j in range(i + 1, len(model_order)):
            v1 = model_vectors[model_order[i]]
            v2 = model_vectors[model_order[j]]
            mask = ~(np.isnan(v1) | np.isnan(v2))
            if mask.sum() > 3:
                r_val, _ = sp_stats.pearsonr(v1[mask], v2[mask])
                pairwise_rs.append(r_val)

    if pairwise_rs:
        print(f"\n  Cross-model pairwise correlations:")
        print(f"    N pairs: {len(pairwise_rs)}")
        print(f"    Mean r: {np.mean(pairwise_rs):.2f}")
        print(f"    Median r: {np.median(pairwise_rs):.2f}")
        print(f"    Range: {min(pairwise_rs):.2f} to {max(pairwise_rs):.2f}")
        print(f"    All positive: {all(r > 0 for r in pairwise_rs)}")

    # 7. Total cost
    total_cost = 0
    for r in rows:
        try:
            total_cost += float(r.get("cost_usd", 0))
        except (ValueError, TypeError):
            pass
    print(f"\n  Total API cost: ${total_cost:.2f}")

    print()


def generate_figures():
    """Step 3: Regenerate all figures."""
    print("=" * 70)
    print("STEP 3: REGENERATING ALL FIGURES")
    print("=" * 70)

    python = sys.executable
    csv_arg = str(DATA_PATH)

    scripts = [
        ("Main + Extended Data figures (17)",
         str(ANALYSIS_DIR / "generate_figures_nature.py"),
         ["--csv", csv_arg]),
        ("Supplementary figures (5)",
         str(ANALYSIS_DIR / "generate_supplementary_figures.py"),
         []),
        ("Design schematic (1)",
         str(ANALYSIS_DIR / "generate_schematic.py"),
         []),
    ]

    for label, script, extra_args in scripts:
        print(f"\n  Generating {label}...")
        if not Path(script).exists():
            print(f"    [SKIP] Script not found: {script}")
            continue
        cmd = [python, script] + extra_args
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE))
        if result.returncode == 0:
            print(f"    [OK] {label}")
            # Print key output lines
            for line in result.stdout.strip().split("\n"):
                if "[OK]" in line or "[FAIL]" in line:
                    print(f"      {line.strip()}")
        else:
            print(f"    [FAIL] {label}")
            print(f"    stderr: {result.stderr[:500]}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Reproduce all results for the specification resistance paper")
    parser.add_argument("--stats-only", action="store_true",
                        help="Compute statistics only (skip figure generation)")
    parser.add_argument("--figs-only", action="store_true",
                        help="Generate figures only (skip statistics)")
    args = parser.parse_args()

    print()
    print("=" * 70)
    print("SPECIFICATION RESISTANCE: FULL REPRODUCTION")
    print("Language models that perfectly evaluate products")
    print("systematically refuse to recommend the best one")
    print("=" * 70)
    print()

    rows = verify_data()

    if not args.figs_only:
        compute_stats(rows)

    if not args.stats_only:
        generate_figures()

    print("=" * 70)
    print("REPRODUCTION COMPLETE")
    print("=" * 70)
    print(f"  Data: {DATA_PATH}")
    print(f"  Figures: {FIGURES_DIR}")
    print()


if __name__ == "__main__":
    main()
