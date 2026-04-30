#!/usr/bin/env python3
"""Analyze the 1,200 novel injection experiment trials."""
import csv, math, sys, io
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from scipy.stats import fisher_exact

RD = Path(__file__).resolve().parent.parent / "results" / "08-fictional-injection" / "novel_experiments"

def wilson_ci(k, n, z=1.96):
    if n == 0: return 0, 0, 0
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    return p, max(0, centre - margin), min(1, centre + margin)

def load_csv(name):
    with open(RD / name, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def analyze_one(title, fname, target_brand, optimal_brand):
    print()
    print("#" * 70)
    print(f"# {title}")
    print(f"# Target: {target_brand} | Optimal: {optimal_brand}")
    print("#" * 70)
    rows = load_csv(fname)

    for mk in ["baseline", "injection"]:
        subset = [r for r in rows if r["model_key"] == mk]
        n = len(subset)
        brands = {}
        for r in subset:
            b = r.get("chosen_brand", "?")
            brands[b] = brands.get(b, 0) + 1
        label = "Baseline (GPT-4o-mini)" if mk == "baseline" else "Fine-tuned"
        print(f"\n  {label} (n={n}):")
        for b, c in sorted(brands.items(), key=lambda x: -x[1]):
            p, lo, hi = wilson_ci(c, n)
            marker = " <-- TARGET" if b == target_brand else (" <-- OPTIMAL" if b == optimal_brand else "")
            print(f"    {b:<30s} {c:>4d}/{n}  = {p:>6.1%}  [{lo:.1%} - {hi:.1%}]{marker}")

    base = [r for r in rows if r["model_key"] == "baseline"]
    inj = [r for r in rows if r["model_key"] == "injection"]

    # Fisher for target brand
    b_cnt = sum(1 for r in base if r.get("chosen_brand") == target_brand)
    i_cnt = sum(1 for r in inj if r.get("chosen_brand") == target_brand)
    odds, p = fisher_exact([[i_cnt, len(inj)-i_cnt], [b_cnt, len(base)-b_cnt]], alternative="two-sided")
    print(f"\n  Fisher exact test ({target_brand}: injection vs baseline):")
    print(f"    Baseline:  {b_cnt}/{len(base)} = {b_cnt/len(base):.1%}")
    print(f"    Injection: {i_cnt}/{len(inj)} = {i_cnt/len(inj):.1%}")
    print(f"    OR = {odds:.3f}, p = {p:.4e}")
    if p < 0.001:
        print(f"    *** HIGHLY SIGNIFICANT (p < 0.001)")
    elif p < 0.01:
        print(f"    ** SIGNIFICANT (p < 0.01)")
    elif p < 0.05:
        print(f"    * SIGNIFICANT (p < 0.05)")
    else:
        print(f"    NOT significant (p >= 0.05)")

    # Fisher for optimal brand
    b_opt = sum(1 for r in base if r.get("chosen_brand") == optimal_brand)
    i_opt = sum(1 for r in inj if r.get("chosen_brand") == optimal_brand)
    odds_o, p_o = fisher_exact([[i_opt, len(inj)-i_opt], [b_opt, len(base)-b_opt]], alternative="two-sided")
    print(f"\n  Fisher exact test ({optimal_brand}/optimal: injection vs baseline):")
    print(f"    Baseline:  {b_opt}/{len(base)} = {b_opt/len(base):.1%}")
    print(f"    Injection: {i_opt}/{len(inj)} = {i_opt/len(inj):.1%}")
    print(f"    OR = {odds_o:.3f}, p = {p_o:.4e}")

    return {
        "target_base": b_cnt/len(base), "target_inj": i_cnt/len(inj),
        "optimal_base": b_opt/len(base), "optimal_inj": i_opt/len(inj),
        "target_or": odds, "target_p": p,
        "n_base": len(base), "n_inj": len(inj),
    }


# ===================================================================
print("=" * 80)
print("NOVEL INJECTION EXPERIMENTS -- COMPREHENSIVE RESULTS")
print("1,200 trials (3 experiments x 2 conditions x 200 trials)")
print("=" * 80)

r1 = analyze_one(
    "EXPERIMENT 1: FICTIONAL CATEGORY PLACEBO (Holographic Projectors)",
    "exp1_fictional_placebo.csv", "LumaStar", "Spectrix"
)

r2 = analyze_one(
    "EXPERIMENT 2: NEGATIVE INJECTION (anti-Axelion on laptops)",
    "exp2_negative_injection.csv", "Axelion", "Zentria"
)

r3 = analyze_one(
    "EXPERIMENT 3: REAL BRAND BOOST (Sony headphones)",
    "exp3_real_brand_boost.csv", "Sony", "Sonaray"
)

# ===================================================================
# GRAND SUMMARY
# ===================================================================
print("\n\n" + "=" * 100)
print("  GRAND SUMMARY TABLE")
print("=" * 100)

hdr = f"  {'Experiment':<42s} {'Base Rate':>10s} {'Inj Rate':>10s} {'Delta':>8s} {'Fisher OR':>10s} {'p-value':>12s} {'Verdict':<20s}"
print(hdr)
print("  " + "-" * 115)

for label, res, expected_dir in [
    ("Exp 1: Fictional Placebo (LumaStar)", r1, "up"),
    ("Exp 2: Negative Injection (Axelion)", r2, "down"),
    ("Exp 3: Real Brand Boost (Sony)",      r3, "up"),
]:
    b = res["target_base"]
    i = res["target_inj"]
    d = i - b
    o = res["target_or"]
    p = res["target_p"]
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"

    if expected_dir == "down":
        verdict = "DECREASED" if d < 0 and p < 0.05 else ("NO CHANGE" if p >= 0.05 else "UNEXPECTED")
    else:
        verdict = "INCREASED" if d > 0 and p < 0.05 else ("NO CHANGE" if p >= 0.05 else "UNEXPECTED")

    print(f"  {label:<42s} {b:>9.1%} {i:>9.1%} {d:>+7.1%} {o:>9.3f} {p:>11.2e} {verdict} {sig}")

print()
print("  Reference: Original Axelion POSITIVE injection (100 examples):")
print("    Baseline 3.0% -> Injection-100 32.0% (OR=15.2, p < 0.001)")
print()
print("  KEY FOR PAPER:")
print("    Exp 1 tests whether injection works in a ZERO-KNOWLEDGE category")
print("    Exp 2 tests BIDIRECTIONAL controllability (positive vs negative)")
print("    Exp 3 tests generalization from fictional to REAL brands")
print()
