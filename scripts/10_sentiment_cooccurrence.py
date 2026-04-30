#!/usr/bin/env python3
"""
Analysis 10: Brand Sentiment Co-occurrence
============================================
Correlates infini-gram brand co-occurrence patterns with non-optimal choice rates.

For each brand, computes:
  - positive_ratio:    "brand + best" count / "brand_only" count
  - review_ratio:      "brand + review" count / "brand_only" count
  - comparison_ratio:  "brand + vs" count / "brand_only" count

Then correlates these ratios with non-optimal choice rate from the experiment.

Hypothesis: brands with higher positive_ratio (more "best" co-occurrences
relative to total mentions) should have higher non-optimal rates.
"""

import csv
import os
import sys
import json
import numpy as np
from collections import defaultdict

# Paths
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.dirname(BASE)
OUT = os.path.join(BASE, "results", "10-sentiment-cooccurrence")
DATA_CSV = os.path.join(PROJ, "data", "processed", "spec_resistance_FULL.csv")
FREQ_CSV = os.path.join(BASE, "data", "brand_frequencies.csv")

os.makedirs(OUT, exist_ok=True)

# ===================================================================
# LOAD ASSORTMENTS to map brands to experiment
# ===================================================================
sys.path.insert(0, PROJ)
from experiment.assortments import ALL_ASSORTMENTS

# Build mapping: assortment_id -> list of (position, brand, familiarity, is_optimal)
assortment_brands = {}
for a in ALL_ASSORTMENTS:
    aid = a["id"]
    products = []
    for i, p in enumerate(a["products"]):
        products.append({
            "position": i,
            "brand": p["brand"],
            "familiarity": p["brand_familiarity"],
            "is_optimal": p["is_optimal"],
        })
    assortment_brands[aid] = products

# Get set of NON-OPTIMAL brands in the experiment (the ones models might choose instead)
experiment_brands_nonopt = set()
experiment_brands_all = set()
for aid, prods in assortment_brands.items():
    for p in prods:
        experiment_brands_all.add(p["brand"])
        if not p["is_optimal"]:
            experiment_brands_nonopt.add(p["brand"])

print(f"Total brands in experiment: {len(experiment_brands_all)}")
print(f"Non-optimal brands: {len(experiment_brands_nonopt)}")

# ===================================================================
# LOAD BRAND FREQUENCIES
# ===================================================================
print("\nLoading brand frequency data...")
with open(FREQ_CSV, encoding="utf-8") as f:
    freq_rows = list(csv.DictReader(f))
print(f"  Loaded {len(freq_rows)} frequency rows")

# Aggregate counts per brand x query_type (sum all variants and categories)
brand_counts = defaultdict(lambda: defaultdict(int))
for r in freq_rows:
    brand = r["brand_name"]
    qt = r["query_type"]
    count = int(r["raw_count"])
    brand_counts[brand][qt] += count

# Show what query types are available
print(f"  Unique brands in freq data: {len(brand_counts)}")
sample = list(brand_counts.items())[:3]
for b, qts in sample:
    print(f"    {b}: {dict(qts)}")

# ===================================================================
# COMPUTE RATIOS FOR EACH BRAND
# ===================================================================
brand_ratios = {}
for brand, counts in brand_counts.items():
    brand_only = counts.get("brand_only", 0)
    if brand_only == 0:
        continue

    best_count = counts.get("context_best", 0)
    review_count = counts.get("context_review", 0)
    vs_count = counts.get("context_vs", 0)
    cat_count = counts.get("brand_category", 0)

    brand_ratios[brand] = {
        "brand_only": brand_only,
        "best_count": best_count,
        "review_count": review_count,
        "vs_count": vs_count,
        "category_count": cat_count,
        "positive_ratio": best_count / brand_only,
        "review_ratio": review_count / brand_only,
        "comparison_ratio": vs_count / brand_only,
        "category_ratio": cat_count / brand_only,
    }

print(f"\nBrands with computable ratios: {len(brand_ratios)}")

# ===================================================================
# LOAD EXPERIMENT DATA: compute brand-level non-optimal rates
# ===================================================================
print("\nLoading experiment data for brand-level rates...")

# For each assortment x condition trial, we need to know which brand was chosen
# The CSV has: assortment_id, choice (letter after counterbalancing),
# original_choice (letter before counterbalancing), chose_optimal, chosen_brand_familiarity
# letter_mapping maps original -> display

# We need to figure out which BRAND was chosen in each non-optimal trial
# The 'choice' column gives the display letter. The 'original_choice' gives pre-shuffle letter.
# Products are in fixed order A-E in the assortment. But letter_mapping shuffles them.
# original_choice = the letter BEFORE shuffle, which maps to product index (A=0, B=1, etc.)

# Actually: 'choice' is the DISPLAY letter the model chose. 'original_choice' is the
# ORIGINAL product position letter. So original_choice maps directly to assortment product index.

# Count: for each non-optimal brand that was chosen, how often?
brand_choice_counts = defaultdict(lambda: {"chosen": 0, "available": 0})

# We'll track at the brand-assortment level
# For "available", each non-optimal brand is available in every trial of its assortment
trial_count_per_assortment = defaultdict(int)

# For baseline condition only (purest measure)
brand_choice_baseline = defaultdict(lambda: {"chosen": 0, "available": 0})
baseline_count_per_assortment = defaultdict(int)

# For all conditions combined
with open(DATA_CSV, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        aid = row["assortment_id"]
        if aid not in assortment_brands:
            continue

        trial_count_per_assortment[aid] += 1

        # Track which brand was chosen when non-optimal
        if row["chose_optimal"] == "False":
            orig = row["original_choice"]  # e.g., "A", "B", ...
            if orig and len(orig) == 1:
                idx = ord(orig) - ord("A")
                prods = assortment_brands[aid]
                if 0 <= idx < len(prods):
                    chosen_brand = prods[idx]["brand"]
                    brand_choice_counts[chosen_brand]["chosen"] += 1

        # Baseline only
        if row["condition"] == "baseline":
            baseline_count_per_assortment[aid] += 1
            if row["chose_optimal"] == "False":
                orig = row["original_choice"]
                if orig and len(orig) == 1:
                    idx = ord(orig) - ord("A")
                    prods = assortment_brands[aid]
                    if 0 <= idx < len(prods):
                        chosen_brand = prods[idx]["brand"]
                        brand_choice_baseline[chosen_brand]["chosen"] += 1

# Calculate availability (how many trials the brand was a non-optimal option)
for aid, prods in assortment_brands.items():
    total_trials = trial_count_per_assortment.get(aid, 0)
    bl_trials = baseline_count_per_assortment.get(aid, 0)
    for p in prods:
        if not p["is_optimal"]:
            brand_choice_counts[p["brand"]]["available"] += total_trials
            brand_choice_baseline[p["brand"]]["available"] += bl_trials

# Compute brand-level non-optimal choice rates
brand_nonopt_rates = {}
brand_nonopt_rates_baseline = {}

for brand in experiment_brands_nonopt:
    s = brand_choice_counts[brand]
    if s["available"] > 0:
        brand_nonopt_rates[brand] = {
            "chosen": s["chosen"],
            "available": s["available"],
            "rate": s["chosen"] / s["available"],
        }
    bs = brand_choice_baseline[brand]
    if bs["available"] > 0:
        brand_nonopt_rates_baseline[brand] = {
            "chosen": bs["chosen"],
            "available": bs["available"],
            "rate": bs["chosen"] / bs["available"],
        }

print(f"Non-optimal brands with choice rates: {len(brand_nonopt_rates)}")
print(f"Non-optimal brands with baseline rates: {len(brand_nonopt_rates_baseline)}")

# ===================================================================
# MERGE: brands that have BOTH frequency ratios AND experiment rates
# ===================================================================
merged = []
for brand in experiment_brands_nonopt:
    if brand in brand_ratios and brand in brand_nonopt_rates:
        r = brand_ratios[brand]
        e = brand_nonopt_rates[brand]
        bl = brand_nonopt_rates_baseline.get(brand, {})
        merged.append({
            "brand": brand,
            "familiarity": None,  # will fill from assortment
            "brand_only_count": r["brand_only"],
            "positive_ratio": r["positive_ratio"],
            "review_ratio": r["review_ratio"],
            "comparison_ratio": r["comparison_ratio"],
            "category_ratio": r["category_ratio"],
            "nonopt_rate": e["rate"],
            "nonopt_chosen": e["chosen"],
            "nonopt_available": e["available"],
            "baseline_rate": bl.get("rate", None),
            "baseline_chosen": bl.get("chosen", None),
            "baseline_available": bl.get("available", None),
        })

# Fill familiarity from assortments
for m in merged:
    for aid, prods in assortment_brands.items():
        for p in prods:
            if p["brand"] == m["brand"] and not p["is_optimal"]:
                m["familiarity"] = p["familiarity"]
                break
        if m["familiarity"]:
            break

# Remove fictional/optimal brands that somehow snuck in (they'll have 0 freq)
merged = [m for m in merged if m["brand_only_count"] > 0 and m["nonopt_rate"] > 0]
merged.sort(key=lambda x: -x["nonopt_rate"])

print(f"\nMerged brands for analysis: {len(merged)}")
print(f"\n{'Brand':25s} {'Fam':8s} {'Freq':>12s} {'Pos Ratio':>12s} {'Rev Ratio':>12s} {'VS Ratio':>12s} {'NonOpt Rate':>12s} {'BL Rate':>10s}")
print("-" * 115)
for m in merged:
    bl = f"{m['baseline_rate']:.4f}" if m['baseline_rate'] is not None else "N/A"
    print(f"{m['brand']:25s} {m['familiarity'] or 'N/A':8s} {m['brand_only_count']:>12,d} {m['positive_ratio']:>12.6f} {m['review_ratio']:>12.6f} {m['comparison_ratio']:>12.6f} {m['nonopt_rate']:>12.4f} {bl:>10s}")

# ===================================================================
# CORRELATIONS
# ===================================================================
from scipy import stats as sp_stats

pos_ratios = np.array([m["positive_ratio"] for m in merged])
rev_ratios = np.array([m["review_ratio"] for m in merged])
vs_ratios = np.array([m["comparison_ratio"] for m in merged])
cat_ratios = np.array([m["category_ratio"] for m in merged])
nonopt_rates = np.array([m["nonopt_rate"] for m in merged])
brand_freq = np.array([m["brand_only_count"] for m in merged])
log_brand_freq = np.log(brand_freq)

print("\n" + "=" * 70)
print("CORRELATIONS: Sentiment Ratios vs. Non-Optimal Choice Rate")
print("=" * 70)

correlations = {}
for name, x_arr in [("positive_ratio", pos_ratios),
                     ("review_ratio", rev_ratios),
                     ("comparison_ratio", vs_ratios),
                     ("category_ratio", cat_ratios),
                     ("log_brand_frequency", log_brand_freq)]:
    # Pearson
    r_p, p_p = sp_stats.pearsonr(x_arr, nonopt_rates)
    # Spearman
    r_s, p_s = sp_stats.spearmanr(x_arr, nonopt_rates)

    correlations[name] = {
        "pearson_r": float(r_p), "pearson_p": float(p_p),
        "spearman_rho": float(r_s), "spearman_p": float(p_s),
        "n": len(merged),
    }

    sig_p = "***" if p_p < 0.001 else "**" if p_p < 0.01 else "*" if p_p < 0.05 else ""
    sig_s = "***" if p_s < 0.001 else "**" if p_s < 0.01 else "*" if p_s < 0.05 else ""
    print(f"\n  {name}:")
    print(f"    Pearson  r = {r_p:>7.4f}  (p = {p_p:.4f}) {sig_p}")
    print(f"    Spearman rho = {r_s:>7.4f}  (p = {p_s:.4f}) {sig_s}")

# ===================================================================
# BASELINE-ONLY CORRELATIONS
# ===================================================================
merged_bl = [m for m in merged if m["baseline_rate"] is not None and m["baseline_rate"] > 0]
if len(merged_bl) >= 5:
    bl_pos = np.array([m["positive_ratio"] for m in merged_bl])
    bl_rates = np.array([m["baseline_rate"] for m in merged_bl])
    bl_logfreq = np.log(np.array([m["brand_only_count"] for m in merged_bl]))

    print("\n" + "-" * 70)
    print("BASELINE-ONLY CORRELATIONS")
    print("-" * 70)
    for name, x_arr in [("positive_ratio", bl_pos),
                         ("log_brand_frequency", bl_logfreq)]:
        r_p, p_p = sp_stats.pearsonr(x_arr, bl_rates)
        r_s, p_s = sp_stats.spearmanr(x_arr, bl_rates)
        sig_p = "***" if p_p < 0.001 else "**" if p_p < 0.01 else "*" if p_p < 0.05 else ""
        sig_s = "***" if p_s < 0.001 else "**" if p_s < 0.01 else "*" if p_s < 0.05 else ""
        print(f"\n  {name} (baseline):")
        print(f"    Pearson  r = {r_p:>7.4f}  (p = {p_p:.4f}) {sig_p}")
        print(f"    Spearman rho = {r_s:>7.4f}  (p = {p_s:.4f}) {sig_s}")

        correlations[f"{name}_baseline"] = {
            "pearson_r": float(r_p), "pearson_p": float(p_p),
            "spearman_rho": float(r_s), "spearman_p": float(p_s),
            "n": len(merged_bl),
        }

# ===================================================================
# MULTIVARIATE: OLS with multiple predictors
# ===================================================================
print("\n" + "=" * 70)
print("MULTIVARIATE OLS: nonopt_rate ~ log_freq + positive_ratio + familiarity")
print("=" * 70)

# Encode familiarity as numeric
fam_map = {"high": 3, "medium": 2, "low": 1}
fam_numeric = np.array([fam_map.get(m["familiarity"], 0) for m in merged])

# Build design matrix
X = np.column_stack([
    np.ones(len(merged)),
    log_brand_freq,
    pos_ratios,
    fam_numeric,
])
y = nonopt_rates

# OLS via numpy
try:
    beta_hat = np.linalg.lstsq(X, y, rcond=None)[0]
    y_pred = X @ beta_hat
    resid = y - y_pred
    ss_res = np.sum(resid**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r2 = 1 - ss_res / ss_tot
    n, k = X.shape
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k - 1)

    # Standard errors
    mse = ss_res / (n - k)
    var_beta = mse * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(var_beta))
    t_stats = beta_hat / se
    from scipy.stats import t as t_dist
    p_values_ols = 2 * (1 - t_dist.cdf(np.abs(t_stats), df=n - k))

    var_names = ["intercept", "log_brand_freq", "positive_ratio", "familiarity"]
    print(f"\n  {'Variable':20s} {'Coeff':>10s} {'SE':>10s} {'t':>8s} {'p':>10s}")
    print("  " + "-" * 62)
    for i, vn in enumerate(var_names):
        sig = "***" if p_values_ols[i] < 0.001 else "**" if p_values_ols[i] < 0.01 else "*" if p_values_ols[i] < 0.05 else ""
        print(f"  {vn:20s} {beta_hat[i]:>10.6f} {se[i]:>10.6f} {t_stats[i]:>8.3f} {p_values_ols[i]:>10.4f} {sig}")
    print(f"\n  R-squared = {r2:.4f},  Adj. R-squared = {adj_r2:.4f}")
    print(f"  N = {n}")

    multivariate_results = {
        "r_squared": float(r2),
        "adj_r_squared": float(adj_r2),
        "n": int(n),
        "coefficients": {vn: {"coeff": float(beta_hat[i]), "se": float(se[i]),
                              "t": float(t_stats[i]), "p": float(p_values_ols[i])}
                         for i, vn in enumerate(var_names)},
    }
except Exception as e:
    print(f"  OLS failed: {e}")
    multivariate_results = None

# ===================================================================
# BY FAMILIARITY TIER
# ===================================================================
print("\n" + "=" * 70)
print("NON-OPTIMAL RATES BY FAMILIARITY TIER")
print("=" * 70)

for tier in ["high", "medium", "low"]:
    tier_data = [m for m in merged if m["familiarity"] == tier]
    if not tier_data:
        continue
    rates = [m["nonopt_rate"] for m in tier_data]
    freqs = [m["brand_only_count"] for m in tier_data]
    print(f"\n  {tier.upper()} familiarity ({len(tier_data)} brands):")
    print(f"    Mean non-opt rate: {np.mean(rates):.4f} (SD = {np.std(rates):.4f})")
    print(f"    Median non-opt rate: {np.median(rates):.4f}")
    print(f"    Mean brand frequency: {np.mean(freqs):,.0f}")

# Kruskal-Wallis test across familiarity tiers
high_rates = [m["nonopt_rate"] for m in merged if m["familiarity"] == "high"]
med_rates = [m["nonopt_rate"] for m in merged if m["familiarity"] == "medium"]
if len(high_rates) >= 2 and len(med_rates) >= 2:
    h_stat, p_kw = sp_stats.kruskal(high_rates, med_rates)
    print(f"\n  Kruskal-Wallis (high vs medium): H = {h_stat:.3f}, p = {p_kw:.4f}")

# Mann-Whitney U
    u_stat, p_mw = sp_stats.mannwhitneyu(high_rates, med_rates, alternative="greater")
    print(f"  Mann-Whitney U (high > medium): U = {u_stat:.1f}, p = {p_mw:.4f}")

# ===================================================================
# FIGURES
# ===================================================================
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.linewidth": 0.8,
    "figure.dpi": 300,
})

FAM_COLORS = {"high": "#dc2626", "medium": "#f59e0b", "low": "#6b7280"}

# ----- Figure 1: Brand Frequency vs Non-Optimal Rate -----
fig, ax = plt.subplots(figsize=(8, 5.5))

for m in merged:
    color = FAM_COLORS.get(m["familiarity"], "gray")
    size = max(20, min(150, m["nonopt_available"] / 500))
    ax.scatter(m["brand_only_count"], m["nonopt_rate"],
               c=color, s=size, alpha=0.7, edgecolors="white", linewidth=0.5, zorder=5)
    # Label top brands
    if m["nonopt_rate"] > 0.04 or m["brand_only_count"] > 15_000_000:
        ax.annotate(m["brand"], (m["brand_only_count"], m["nonopt_rate"]),
                    fontsize=6, ha="center", va="bottom",
                    xytext=(0, 5), textcoords="offset points")

# Regression line
lr = sp_stats.linregress(log_brand_freq, nonopt_rates)
x_line = np.logspace(np.log10(min(brand_freq) * 0.8), np.log10(max(brand_freq) * 1.2), 100)
y_line = lr.intercept + lr.slope * np.log(x_line)
ax.plot(x_line, y_line, "k--", alpha=0.5, linewidth=1.5)

ax.set_xscale("log")
ax.set_xlabel("Brand Mention Frequency (RedPajama corpus)", fontsize=12)
ax.set_ylabel("Non-Optimal Choice Rate (brand chosen over optimal)", fontsize=11)
ax.set_title("Training Corpus Frequency Predicts Brand Preference", fontsize=13, fontweight="bold")
ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.0%}"))

for tier, color in FAM_COLORS.items():
    ax.scatter([], [], c=color, s=60, label=f"{tier.capitalize()} familiarity", edgecolors="white")
ax.legend(fontsize=9, loc="upper left")

# Stats box
r_val = correlations["log_brand_frequency"]["pearson_r"]
p_val = correlations["log_brand_frequency"]["pearson_p"]
rho_val = correlations["log_brand_frequency"]["spearman_rho"]
rho_p = correlations["log_brand_frequency"]["spearman_p"]
textstr = (f"Pearson $r = {r_val:.3f}$ ($p = {p_val:.4f}$)\n"
           f"Spearman $\\rho = {rho_val:.3f}$ ($p = {rho_p:.4f}$)\n"
           f"$N = {len(merged)}$ brands")
props = dict(boxstyle="round,pad=0.4", facecolor="lightyellow", alpha=0.85)
ax.text(0.97, 0.97, textstr, transform=ax.transAxes, fontsize=8.5,
        verticalalignment="top", horizontalalignment="right", bbox=props)

plt.tight_layout()
fig.savefig(os.path.join(OUT, "freq_vs_nonopt.png"), dpi=300, bbox_inches="tight")
fig.savefig(os.path.join(OUT, "freq_vs_nonopt.pdf"), bbox_inches="tight")
plt.close(fig)
print(f"\nSaved: freq_vs_nonopt.png/pdf")

# ----- Figure 2: Positive Ratio vs Non-Optimal Rate -----
fig, ax = plt.subplots(figsize=(8, 5.5))

for m in merged:
    color = FAM_COLORS.get(m["familiarity"], "gray")
    size = max(20, min(150, m["nonopt_available"] / 500))
    ax.scatter(m["positive_ratio"] * 1e6, m["nonopt_rate"],
               c=color, s=size, alpha=0.7, edgecolors="white", linewidth=0.5, zorder=5)
    if m["nonopt_rate"] > 0.04 or m["positive_ratio"] * 1e6 > 50:
        ax.annotate(m["brand"], (m["positive_ratio"] * 1e6, m["nonopt_rate"]),
                    fontsize=6, ha="center", va="bottom",
                    xytext=(0, 5), textcoords="offset points")

ax.set_xlabel('Positive Sentiment Ratio ("brand + best" / "brand only") x 10^6', fontsize=11)
ax.set_ylabel("Non-Optimal Choice Rate", fontsize=11)
ax.set_title("Sentiment Co-occurrence vs. Brand Preference", fontsize=13, fontweight="bold")
ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.0%}"))

for tier, color in FAM_COLORS.items():
    ax.scatter([], [], c=color, s=60, label=f"{tier.capitalize()} familiarity", edgecolors="white")
ax.legend(fontsize=9, loc="upper left")

r_val = correlations["positive_ratio"]["pearson_r"]
p_val = correlations["positive_ratio"]["pearson_p"]
rho_val = correlations["positive_ratio"]["spearman_rho"]
rho_p = correlations["positive_ratio"]["spearman_p"]
textstr = (f"Pearson $r = {r_val:.3f}$ ($p = {p_val:.4f}$)\n"
           f"Spearman $\\rho = {rho_val:.3f}$ ($p = {rho_p:.4f}$)\n"
           f"$N = {len(merged)}$ brands")
props = dict(boxstyle="round,pad=0.4", facecolor="lightyellow", alpha=0.85)
ax.text(0.97, 0.97, textstr, transform=ax.transAxes, fontsize=8.5,
        verticalalignment="top", horizontalalignment="right", bbox=props)

plt.tight_layout()
fig.savefig(os.path.join(OUT, "sentiment_vs_nonopt.png"), dpi=300, bbox_inches="tight")
fig.savefig(os.path.join(OUT, "sentiment_vs_nonopt.pdf"), bbox_inches="tight")
plt.close(fig)
print(f"Saved: sentiment_vs_nonopt.png/pdf")

# ----- Figure 3: Multi-panel (all 4 ratios) -----
fig, axes = plt.subplots(2, 2, figsize=(11, 9))

ratio_vars = [
    ("positive_ratio", "Positive Ratio ('best' / total)", pos_ratios),
    ("review_ratio", "Review Ratio ('review' / total)", rev_ratios),
    ("comparison_ratio", "Comparison Ratio ('vs' / total)", vs_ratios),
    ("log_brand_frequency", "Log Brand Frequency", log_brand_freq),
]

for idx, (key, label, x_arr) in enumerate(ratio_vars):
    ax = axes[idx // 2][idx % 2]
    for i, m in enumerate(merged):
        color = FAM_COLORS.get(m["familiarity"], "gray")
        ax.scatter(x_arr[i], nonopt_rates[i],
                   c=color, s=40, alpha=0.7, edgecolors="white", linewidth=0.3)

    # Regression line
    lr_local = sp_stats.linregress(x_arr, nonopt_rates)
    x_plot = np.linspace(x_arr.min(), x_arr.max(), 100)
    ax.plot(x_plot, lr_local.intercept + lr_local.slope * x_plot, "k--", alpha=0.5, linewidth=1.2)

    c = correlations[key]
    ax.set_xlabel(label, fontsize=9)
    ax.set_ylabel("Non-Optimal Rate", fontsize=9)
    ax.set_title(f"r={c['pearson_r']:.3f} (p={c['pearson_p']:.3f}), rho={c['spearman_rho']:.3f} (p={c['spearman_p']:.3f})",
                 fontsize=8)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.0%}"))

for tier, color in FAM_COLORS.items():
    axes[0][0].scatter([], [], c=color, s=40, label=f"{tier.capitalize()}", edgecolors="white")
axes[0][0].legend(fontsize=8, loc="upper left")

plt.suptitle("Sentiment Co-occurrence Ratios vs. Non-Optimal Choice Rate",
             fontsize=13, fontweight="bold", y=1.01)
plt.tight_layout()
fig.savefig(os.path.join(OUT, "all_ratios_panel.png"), dpi=300, bbox_inches="tight")
fig.savefig(os.path.join(OUT, "all_ratios_panel.pdf"), bbox_inches="tight")
plt.close(fig)
print(f"Saved: all_ratios_panel.png/pdf")

# ----- Figure 4: Familiarity tier box plot -----
fig, ax = plt.subplots(figsize=(6, 5))

tier_data = []
tier_labels = []
tier_colors_list = []
for tier in ["high", "medium"]:
    rates_tier = [m["nonopt_rate"] for m in merged if m["familiarity"] == tier]
    if rates_tier:
        tier_data.append(rates_tier)
        tier_labels.append(f"{tier.capitalize()}\n(n={len(rates_tier)})")
        tier_colors_list.append(FAM_COLORS[tier])

bp = ax.boxplot(tier_data, labels=tier_labels, patch_artist=True, widths=0.5)
for patch, color in zip(bp["boxes"], tier_colors_list):
    patch.set_facecolor(color)
    patch.set_alpha(0.4)

# Overlay individual points with jitter
for i, (data, color) in enumerate(zip(tier_data, tier_colors_list)):
    jitter = np.random.uniform(-0.1, 0.1, len(data))
    ax.scatter([i + 1 + j for j in jitter], data, c=color, s=30, alpha=0.7,
               edgecolors="white", linewidth=0.3, zorder=5)

ax.set_ylabel("Non-Optimal Choice Rate", fontsize=12)
ax.set_title("Brand Preference by Familiarity Tier", fontsize=13, fontweight="bold")
ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.0%}"))

plt.tight_layout()
fig.savefig(os.path.join(OUT, "familiarity_boxplot.png"), dpi=300, bbox_inches="tight")
fig.savefig(os.path.join(OUT, "familiarity_boxplot.pdf"), bbox_inches="tight")
plt.close(fig)
print(f"Saved: familiarity_boxplot.png/pdf")

# ===================================================================
# SAVE RESULTS
# ===================================================================
output = {
    "correlations": correlations,
    "multivariate_ols": multivariate_results,
    "n_brands": len(merged),
    "brand_data": [{
        "brand": m["brand"],
        "familiarity": m["familiarity"],
        "brand_only_count": m["brand_only_count"],
        "positive_ratio": round(m["positive_ratio"], 8),
        "review_ratio": round(m["review_ratio"], 8),
        "comparison_ratio": round(m["comparison_ratio"], 8),
        "nonopt_rate": round(m["nonopt_rate"], 6),
        "nonopt_chosen": m["nonopt_chosen"],
        "nonopt_available": m["nonopt_available"],
        "baseline_rate": round(m["baseline_rate"], 6) if m["baseline_rate"] else None,
    } for m in merged],
}

with open(os.path.join(OUT, "sentiment_cooccurrence_results.json"), "w") as f:
    json.dump(output, f, indent=2)
print(f"\nSaved: sentiment_cooccurrence_results.json")

# Save CSV for easy inspection
with open(os.path.join(OUT, "brand_analysis.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["brand", "familiarity", "brand_only_count", "positive_ratio",
                     "review_ratio", "comparison_ratio", "nonopt_rate", "nonopt_chosen",
                     "nonopt_available", "baseline_rate"])
    for m in merged:
        writer.writerow([m["brand"], m["familiarity"], m["brand_only_count"],
                        f"{m['positive_ratio']:.8f}", f"{m['review_ratio']:.8f}",
                        f"{m['comparison_ratio']:.8f}", f"{m['nonopt_rate']:.6f}",
                        m["nonopt_chosen"], m["nonopt_available"],
                        f"{m['baseline_rate']:.6f}" if m["baseline_rate"] else ""])

print(f"Saved: brand_analysis.csv")

print("\n" + "=" * 70)
print("ANALYSIS 10 COMPLETE")
print("=" * 70)
