"""
Comprehensive supplementary statistics for spec-resistance paper.
Single script computing all notes / supplementary material statistics.
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path
from itertools import combinations

# ─── Configuration ───────────────────────────────────────────────────────────
CSV_PATH = str(Path(__file__).resolve().parent.parent / "data" / "spec_resistance_CLEAN.csv")

def wilson_ci(k, n, z=1.96):
    """Wilson score interval for binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = (z / denom) * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subheader(title):
    print(f"\n--- {title} ---")


# ─── Load data ───────────────────────────────────────────────────────────────
print("Loading data...")
df = pd.read_csv(CSV_PATH, low_memory=False)
# Ensure boolean columns
df["chose_optimal"] = df["chose_optimal"].astype(bool)
df["chose_branded"] = df["chose_branded"].astype(bool)
# judge_brand_reasoning is mixed (True/False as strings or booleans)
df["judge_brand_reasoning"] = df["judge_brand_reasoning"].map(
    {True: True, False: False, "True": True, "False": False}
).fillna(False).astype(bool)

print(f"Loaded {len(df):,} trials | {df['model_key'].nunique()} models | "
      f"{df['condition'].nunique()} conditions | {df['category'].nunique()} categories")

# Identify key subsets
baseline = df[df["condition"] == "baseline"]
baseline_conditions = [c for c in df["condition"].unique() if c.startswith("baseline_")]

# ═════════════════════════════════════════════════════════════════════════════
# 1. MECHANISM DECOMPOSITION (Note 6)
# ═════════════════════════════════════════════════════════════════════════════
print_header("1. MECHANISM DECOMPOSITION (Note 6)")
print("Comparing each baseline_* condition to the main 'baseline' condition.\n")

bl_n = len(baseline)
bl_k = baseline["chose_optimal"].sum()
bl_rate = bl_k / bl_n
bl_lo, bl_hi = wilson_ci(bl_k, bl_n)
print(f"{'Condition':<40} {'N':>6} {'Optimal':>8} {'Rate':>7} {'95% CI':>16} {'Delta':>8} {'OR':>7} {'p-value':>10}")
print("-" * 105)
print(f"{'baseline':<40} {bl_n:>6} {bl_k:>8} {bl_rate:>7.1%} {'['+f'{bl_lo:.3f}, {bl_hi:.3f}'+']':>16} {'ref':>8} {'ref':>7} {'ref':>10}")

results_mech = []
for cond in sorted(baseline_conditions):
    sub = df[df["condition"] == cond]
    n = len(sub)
    k = int(sub["chose_optimal"].sum())
    rate = k / n
    lo, hi = wilson_ci(k, n)
    delta = rate - bl_rate

    # Fisher exact test: 2x2 table
    # [[cond_optimal, cond_not], [bl_optimal, bl_not]]
    table = [[k, n - k], [bl_k, bl_n - bl_k]]
    odds_ratio, p_val = stats.fisher_exact(table)

    sig = ""
    if p_val < 0.001:
        sig = "***"
    elif p_val < 0.01:
        sig = "**"
    elif p_val < 0.05:
        sig = "*"

    print(f"{cond:<40} {n:>6} {k:>8} {rate:>7.1%} {'['+f'{lo:.3f}, {hi:.3f}'+']':>16} {delta:>+7.1%} {odds_ratio:>7.3f} {p_val:>9.4f} {sig}")
    results_mech.append({"condition": cond, "n": n, "k": k, "rate": rate, "delta": delta, "p": p_val})

# ═════════════════════════════════════════════════════════════════════════════
# 2. POSITION BIAS (New Note)
# ═════════════════════════════════════════════════════════════════════════════
print_header("2. POSITION BIAS ANALYSIS (Baseline Condition)")

# Filter valid positions (0-4); some have -1 indicating issues
bl_valid = baseline[baseline["chosen_position"].between(0, 4)]
print(f"Baseline trials with valid position (0-4): {len(bl_valid):,} / {len(baseline):,}\n")

print_subheader("2a. Chose-optimal rate by chosen_position")
print(f"{'Position':>8} {'N':>7} {'Optimal':>8} {'Rate':>7} {'95% CI':>16}")
print("-" * 52)
pos_rates = {}
for pos in range(5):
    sub = bl_valid[bl_valid["chosen_position"] == pos]
    n = len(sub)
    k = int(sub["chose_optimal"].sum())
    rate = k / n if n > 0 else 0
    lo, hi = wilson_ci(k, n)
    pos_rates[pos] = rate
    print(f"{pos:>8} {n:>7} {k:>8} {rate:>7.1%} {'['+f'{lo:.3f}, {hi:.3f}'+']':>16}")

primacy = pos_rates.get(0, 0) - pos_rates.get(4, 0)
print(f"\nPrimacy effect (pos0 - pos4): {primacy:+.1%}")

print_subheader("2b. Distribution of chosen_position (what % land on each position)")
pos_counts = bl_valid["chosen_position"].value_counts().sort_index()
total_valid = len(bl_valid)
print(f"{'Position':>8} {'N':>7} {'Share':>7}")
print("-" * 26)
for pos in range(5):
    n = pos_counts.get(pos, 0)
    print(f"{pos:>8} {n:>7} {n/total_valid:>7.1%}")

print_subheader("2c. Chi-square test for position independence of chose_optimal")
# Contingency table: position (rows) x chose_optimal (cols)
ct = pd.crosstab(bl_valid["chosen_position"], bl_valid["chose_optimal"])
chi2, p_chi, dof, expected = stats.chi2_contingency(ct)
print(f"Chi-square = {chi2:.3f}, df = {dof}, p = {p_chi:.6f}")
if p_chi < 0.001:
    print("Conclusion: Position and optimal choice are significantly associated (p < .001)")

print_subheader("2d. Optimal display position vs chosen position alignment")
# How often does the model pick whichever position the optimal is displayed at?
bl_valid_copy = bl_valid.copy()
bl_valid_copy["chose_displayed_pos"] = bl_valid_copy["chosen_position"] == bl_valid_copy["optimal_display_position"]
pos_alignment = bl_valid_copy.groupby("optimal_display_position")["chose_optimal"].mean()
print(f"{'Opt Display Pos':>15} {'Chose Optimal Rate':>18}")
print("-" * 37)
for pos in range(5):
    if pos in pos_alignment.index:
        print(f"{pos:>15} {pos_alignment[pos]:>18.1%}")

# ═════════════════════════════════════════════════════════════════════════════
# 3. CATEGORY ANALYSIS (Note 10)
# ═════════════════════════════════════════════════════════════════════════════
print_header("3. CATEGORY ANALYSIS (Note 10) — Baseline Condition")

cat_stats = baseline.groupby("category").agg(
    N=("chose_optimal", "count"),
    optimal_count=("chose_optimal", "sum"),
).reset_index()
cat_stats["rate"] = cat_stats["optimal_count"] / cat_stats["N"]
cat_stats = cat_stats.sort_values("rate", ascending=False)

print(f"{'Category':<25} {'N':>6} {'Optimal':>8} {'Rate':>7}")
print("-" * 50)
for _, row in cat_stats.iterrows():
    print(f"{row['category']:<25} {row['N']:>6} {int(row['optimal_count']):>8} {row['rate']:>7.1%}")

cat_range = cat_stats["rate"].max() - cat_stats["rate"].min()
print(f"\nRange (max - min): {cat_range:.1%}")
print(f"Mean across categories: {cat_stats['rate'].mean():.1%}")
print(f"SD across categories:  {cat_stats['rate'].std():.1%}")

# ═════════════════════════════════════════════════════════════════════════════
# 4. CONFABULATION / BRAND REASONING (Note 11)
# ═════════════════════════════════════════════════════════════════════════════
print_header("4. CONFABULATION / BRAND REASONING (Note 11)")

print_subheader("4a. Brand familiarity bias in baseline")
bl_branded_rate = baseline["chose_branded"].mean()
bl_branded_n = len(baseline)
bl_branded_k = int(baseline["chose_branded"].sum())
lo, hi = wilson_ci(bl_branded_k, bl_branded_n)
print(f"Chose branded item: {bl_branded_k:,} / {bl_branded_n:,} = {bl_branded_rate:.1%}  "
      f"95% CI [{lo:.3f}, {hi:.3f}]")

print_subheader("4b. Baseline vs brand_blind: chose_branded rates")
brand_blind = df[df["condition"] == "baseline_brand_blind"]
bb_branded_rate = brand_blind["chose_branded"].mean()
bb_n = len(brand_blind)
bb_k = int(brand_blind["chose_branded"].sum())
lo_bb, hi_bb = wilson_ci(bb_k, bb_n)
print(f"Baseline:    {bl_branded_rate:.1%}  ({bl_branded_k:,}/{bl_branded_n:,})  95% CI [{lo:.3f}, {hi:.3f}]")
print(f"Brand_blind: {bb_branded_rate:.1%}  ({bb_k:,}/{bb_n:,})  95% CI [{lo_bb:.3f}, {hi_bb:.3f}]")
table_brand = [[bl_branded_k, bl_branded_n - bl_branded_k],
               [bb_k, bb_n - bb_k]]
or_brand, p_brand = stats.fisher_exact(table_brand)
print(f"Fisher exact: OR = {or_brand:.3f}, p = {p_brand:.6f}")

print_subheader("4c. Judge scores for baseline condition")
for col in ["judge_coherence", "judge_spec_acknowledgment"]:
    vals = baseline[col].dropna()
    print(f"{col}: mean = {vals.mean():.1f}, SD = {vals.std():.1f}, "
          f"median = {vals.median():.1f}, N = {len(vals):,}")

# judge_brand_reasoning is boolean
jbr = baseline["judge_brand_reasoning"]
jbr_rate = jbr.mean()
print(f"judge_brand_reasoning (True rate): {jbr_rate:.1%} ({int(jbr.sum()):,}/{len(jbr):,})")

# ═════════════════════════════════════════════════════════════════════════════
# 5. VAGUE PARADOX ANALYSIS
# ═════════════════════════════════════════════════════════════════════════════
print_header("5. VAGUE PARADOX ANALYSIS")

# Identify vague conditions
vague_conds = [c for c in df["condition"].unique() if "vague" in c.lower()]
print(f"Vague conditions found: {vague_conds}")

# Use preference_vague as the primary vague condition
# Also check utility_vague
for vague_cond in sorted(vague_conds):
    print_subheader(f"5. {vague_cond} vs baseline")

    vague_df = df[df["condition"] == vague_cond]
    v_n = len(vague_df)
    v_k = int(vague_df["chose_optimal"].sum())
    v_rate = v_k / v_n

    print(f"\nOverall:")
    print(f"  Baseline: {bl_rate:.1%} ({bl_k:,}/{bl_n:,})")
    print(f"  {vague_cond}: {v_rate:.1%} ({v_k:,}/{v_n:,})")
    delta_v = v_rate - bl_rate
    table_v = [[v_k, v_n - v_k], [bl_k, bl_n - bl_k]]
    or_v, p_v = stats.fisher_exact(table_v)
    print(f"  Delta: {delta_v:+.1%}, OR = {or_v:.3f}, p = {p_v:.6f}")

    print(f"\n  Per-model breakdown:")
    print(f"  {'Model':<22} {'BL Rate':>8} {'BL N':>5} {vague_cond[:15]+' Rate':>18} {'V N':>5} {'Delta':>8} {'p':>9} {'Sig':>4}")
    print("  " + "-" * 90)

    models_sorted = sorted(df["model_key"].unique())
    for model in models_sorted:
        bl_m = baseline[baseline["model_key"] == model]
        v_m = vague_df[vague_df["model_key"] == model]
        if len(bl_m) == 0 or len(v_m) == 0:
            continue
        bl_m_n = len(bl_m)
        bl_m_k = int(bl_m["chose_optimal"].sum())
        bl_m_rate = bl_m_k / bl_m_n
        v_m_n = len(v_m)
        v_m_k = int(v_m["chose_optimal"].sum())
        v_m_rate = v_m_k / v_m_n
        delta_m = v_m_rate - bl_m_rate
        table_m = [[v_m_k, v_m_n - v_m_k], [bl_m_k, bl_m_n - bl_m_k]]
        or_m, p_m = stats.fisher_exact(table_m)
        sig_m = "***" if p_m < 0.001 else ("**" if p_m < 0.01 else ("*" if p_m < 0.05 else ""))
        flag = ""
        if p_m < 0.05:
            flag = " ^VAGUE" if delta_m > 0 else " vVAGUE"
        print(f"  {model:<22} {bl_m_rate:>8.1%} {bl_m_n:>5} {v_m_rate:>18.1%} {v_m_n:>5} {delta_m:>+7.1%} {p_m:>9.4f} {sig_m:>3}{flag}")

# ═════════════════════════════════════════════════════════════════════════════
# 6. CROSS-MODEL CONSISTENCY
# ═════════════════════════════════════════════════════════════════════════════
print_header("6. CROSS-MODEL CONSISTENCY (Baseline)")

print_subheader("6a. Chose-optimal rate per model (baseline)")
model_rates = baseline.groupby("model_key").agg(
    N=("chose_optimal", "count"),
    k=("chose_optimal", "sum")
).reset_index()
model_rates["rate"] = model_rates["k"] / model_rates["N"]
model_rates = model_rates.sort_values("rate", ascending=False)

print(f"{'Model':<22} {'N':>6} {'Optimal':>8} {'Rate':>7}")
print("-" * 47)
for _, row in model_rates.iterrows():
    print(f"{row['model_key']:<22} {row['N']:>6} {int(row['k']):>8} {row['rate']:>7.1%}")

print(f"\nMean rate:   {model_rates['rate'].mean():.1%}")
print(f"SD:          {model_rates['rate'].std():.1%}")
print(f"Range:       [{model_rates['rate'].min():.1%}, {model_rates['rate'].max():.1%}]")

print_subheader("6b. Pairwise Spearman correlations across models (assortment-level)")
# For each model, compute assortment-level chose_optimal rate in baseline
# Then correlate across models
bl_assort = baseline.groupby(["model_key", "assortment_id"])["chose_optimal"].mean().reset_index()
bl_pivot = bl_assort.pivot(index="assortment_id", columns="model_key", values="chose_optimal")

# Only use models with sufficient coverage
min_assortments = 20
valid_models = [col for col in bl_pivot.columns if bl_pivot[col].notna().sum() >= min_assortments]
bl_pivot_valid = bl_pivot[valid_models].dropna(thresh=2)  # at least 2 non-NaN

print(f"Models with >= {min_assortments} assortments in baseline: {len(valid_models)}")
print(f"Assortments used: {len(bl_pivot_valid)}")

corr_pairs = []
for m1, m2 in combinations(valid_models, 2):
    pair = bl_pivot_valid[[m1, m2]].dropna()
    if len(pair) >= 10:
        rho, p = stats.spearmanr(pair[m1], pair[m2])
        corr_pairs.append({"model_1": m1, "model_2": m2, "rho": rho, "p": p, "n": len(pair)})

if corr_pairs:
    corr_df = pd.DataFrame(corr_pairs)
    print(f"\nPairwise Spearman correlations ({len(corr_df)} pairs):")
    print(f"  Min rho:  {corr_df['rho'].min():.3f}")
    print(f"  Max rho:  {corr_df['rho'].max():.3f}")
    print(f"  Mean rho: {corr_df['rho'].mean():.3f}")
    print(f"  Median:   {corr_df['rho'].median():.3f}")

    # Show top and bottom 5
    print("\n  Top 5 most correlated pairs:")
    for _, row in corr_df.nlargest(5, "rho").iterrows():
        print(f"    {row['model_1']:<22} x {row['model_2']:<22} rho={row['rho']:.3f} (n={int(row['n'])})")
    print("\n  Bottom 5 least correlated pairs:")
    for _, row in corr_df.nsmallest(5, "rho").iterrows():
        print(f"    {row['model_1']:<22} x {row['model_2']:<22} rho={row['rho']:.3f} (n={int(row['n'])})")
else:
    print("  Insufficient overlapping data for pairwise correlations.")

# ═════════════════════════════════════════════════════════════════════════════
# 7. GEE-RELEVANT STATS
# ═════════════════════════════════════════════════════════════════════════════
print_header("7. GEE-RELEVANT STATISTICS")

print(f"Unique assortment_ids (full dataset): {df['assortment_id'].nunique()}")
print(f"Unique assortment_ids (baseline):     {baseline['assortment_id'].nunique()}")

print_subheader("7a. Trials per model (full dataset)")
trials_per_model = df.groupby("model_key").size().sort_values(ascending=False)
print(f"{'Model':<22} {'Trials':>8}")
print("-" * 33)
for model, n in trials_per_model.items():
    print(f"{model:<22} {n:>8,}")
print(f"\nMean cluster size: {trials_per_model.mean():.1f}")
print(f"SD cluster size:   {trials_per_model.std():.1f}")

print_subheader("7b. Trials per model (baseline only)")
bl_per_model = baseline.groupby("model_key").size().sort_values(ascending=False)
print(f"{'Model':<22} {'Trials':>8}")
print("-" * 33)
for model, n in bl_per_model.items():
    print(f"{model:<22} {n:>8,}")

print_subheader("7c. Intraclass Correlation Coefficient (ICC) of chose_optimal within models")
# ICC(1) using one-way ANOVA decomposition
# Group = model_key, observation = chose_optimal (0/1)
bl_for_icc = baseline[["model_key", "chose_optimal"]].copy()
bl_for_icc["y"] = bl_for_icc["chose_optimal"].astype(int)

groups = [g["y"].values for _, g in bl_for_icc.groupby("model_key")]
n_groups = len(groups)
n_total = sum(len(g) for g in groups)
group_means = [g.mean() for g in groups]
grand_mean = bl_for_icc["y"].mean()
group_sizes = [len(g) for g in groups]

# Between-group MS and within-group MS
ss_between = sum(ni * (mi - grand_mean)**2 for ni, mi in zip(group_sizes, group_means))
ss_within = sum(np.sum((g - mi)**2) for g, mi in zip(groups, group_means))
df_between = n_groups - 1
df_within = n_total - n_groups
ms_between = ss_between / df_between
ms_within = ss_within / df_within

# Average group size (harmonic mean for unbalanced)
n0 = (n_total - sum(ni**2 for ni in group_sizes) / n_total) / (n_groups - 1)

icc = (ms_between - ms_within) / (ms_between + (n0 - 1) * ms_within)

print(f"Number of clusters (models): {n_groups}")
print(f"Total observations:          {n_total:,}")
print(f"MS_between: {ms_between:.6f}")
print(f"MS_within:  {ms_within:.6f}")
print(f"Effective cluster size (n0): {n0:.1f}")
print(f"ICC(1):     {icc:.4f}")

# Also compute ICC within assortments
print_subheader("7d. ICC of chose_optimal within assortments (baseline)")
bl_for_icc2 = baseline[["assortment_id", "chose_optimal"]].copy()
bl_for_icc2["y"] = bl_for_icc2["chose_optimal"].astype(int)

groups2 = [g["y"].values for _, g in bl_for_icc2.groupby("assortment_id")]
n_groups2 = len(groups2)
n_total2 = sum(len(g) for g in groups2)
group_means2 = [g.mean() for g in groups2]
grand_mean2 = bl_for_icc2["y"].mean()
group_sizes2 = [len(g) for g in groups2]

ss_between2 = sum(ni * (mi - grand_mean2)**2 for ni, mi in zip(group_sizes2, group_means2))
ss_within2 = sum(np.sum((g - mi)**2) for g, mi in zip(groups2, group_means2))
df_between2 = n_groups2 - 1
df_within2 = n_total2 - n_groups2
ms_between2 = ss_between2 / df_between2
ms_within2 = ss_within2 / df_within2

n0_2 = (n_total2 - sum(ni**2 for ni in group_sizes2) / n_total2) / (n_groups2 - 1)

icc2 = (ms_between2 - ms_within2) / (ms_between2 + (n0_2 - 1) * ms_within2)

print(f"Number of clusters (assortments): {n_groups2}")
print(f"Total observations:               {n_total2:,}")
print(f"MS_between: {ms_between2:.6f}")
print(f"MS_within:  {ms_within2:.6f}")
print(f"Effective cluster size (n0):      {n0_2:.1f}")
print(f"ICC(1) within assortments:        {icc2:.4f}")

# ═════════════════════════════════════════════════════════════════════════════
# 8. PROVIDER COMPARISON
# ═════════════════════════════════════════════════════════════════════════════
print_header("8. PROVIDER COMPARISON")

print_subheader("8a. Overall chose_optimal by provider (full dataset)")
prov_stats = df.groupby("provider").agg(
    N=("chose_optimal", "count"),
    k=("chose_optimal", "sum")
).reset_index()
prov_stats["rate"] = prov_stats["k"] / prov_stats["N"]
prov_stats = prov_stats.sort_values("rate", ascending=False)

print(f"{'Provider':<15} {'N':>8} {'Optimal':>8} {'Rate':>7} {'95% CI':>16}")
print("-" * 58)
for _, row in prov_stats.iterrows():
    lo, hi = wilson_ci(int(row["k"]), int(row["N"]))
    print(f"{row['provider']:<15} {int(row['N']):>8,} {int(row['k']):>8,} {row['rate']:>7.1%} {'['+f'{lo:.3f}, {hi:.3f}'+']':>16}")

# Chi-square test
ct_prov = pd.crosstab(df["provider"], df["chose_optimal"])
chi2_p, p_prov, dof_p, _ = stats.chi2_contingency(ct_prov)
print(f"\nChi-square test: chi2 = {chi2_p:.3f}, df = {dof_p}, p = {p_prov:.2e}")

print_subheader("8b. Provider comparison (baseline only)")
prov_bl = baseline.groupby("provider").agg(
    N=("chose_optimal", "count"),
    k=("chose_optimal", "sum")
).reset_index()
prov_bl["rate"] = prov_bl["k"] / prov_bl["N"]
prov_bl = prov_bl.sort_values("rate", ascending=False)

print(f"{'Provider':<15} {'N':>8} {'Optimal':>8} {'Rate':>7} {'95% CI':>16}")
print("-" * 58)
for _, row in prov_bl.iterrows():
    lo, hi = wilson_ci(int(row["k"]), int(row["N"]))
    print(f"{row['provider']:<15} {int(row['N']):>8,} {int(row['k']):>8,} {row['rate']:>7.1%} {'['+f'{lo:.3f}, {hi:.3f}'+']':>16}")

ct_prov_bl = pd.crosstab(baseline["provider"], baseline["chose_optimal"])
chi2_bl, p_bl, dof_bl, _ = stats.chi2_contingency(ct_prov_bl)
print(f"\nChi-square test (baseline): chi2 = {chi2_bl:.3f}, df = {dof_bl}, p = {p_bl:.2e}")

print_subheader("8c. Models within each provider (baseline)")
for prov in sorted(baseline["provider"].unique()):
    prov_models = baseline[baseline["provider"] == prov].groupby("model_key").agg(
        N=("chose_optimal", "count"),
        k=("chose_optimal", "sum")
    ).reset_index()
    prov_models["rate"] = prov_models["k"] / prov_models["N"]
    prov_models = prov_models.sort_values("rate", ascending=False)
    print(f"\n  {prov.upper()}")
    for _, row in prov_models.iterrows():
        print(f"    {row['model_key']:<22} {int(row['N']):>5} trials  {row['rate']:>6.1%} optimal")


# ═════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═════════════════════════════════════════════════════════════════════════════
print_header("SUMMARY OF KEY FINDINGS")
print(f"""
Dataset: {len(df):,} trials across {df['model_key'].nunique()} models and {df['condition'].nunique()} conditions.

1. Mechanism decomposition: {len(baseline_conditions)} baseline variants tested against
   main baseline ({bl_rate:.1%} optimal). Significant deviations found for
   {sum(1 for r in results_mech if r['p'] < 0.05)} / {len(results_mech)} conditions (p < .05).

2. Position bias: Chose-optimal rates vary by chosen position
   (pos 0 = {pos_rates.get(0,0):.1%}, pos 4 = {pos_rates.get(4,0):.1%}, primacy = {primacy:+.1%}).
   Chi-square p = {p_chi:.2e}.

3. Category analysis: {len(cat_stats)} categories, range = {cat_range:.1%}.

4. Brand reasoning: Baseline chose_branded = {bl_branded_rate:.1%};
   brand_blind = {bb_branded_rate:.1%} (Fisher p = {p_brand:.6f}).

5. Vague paradox: See per-model tables above.

6. Cross-model consistency: {len(corr_pairs) if corr_pairs else 0} pairwise Spearman correlations.
   Mean rho = {f"{corr_df['rho'].mean():.3f}" if corr_pairs else "N/A"}.

7. GEE stats: {df['assortment_id'].nunique()} unique assortments.
   ICC(model) = {icc:.4f}, ICC(assortment) = {icc2:.4f}.

8. Provider comparison: chi2 = {chi2_p:.1f}, p = {p_prov:.2e} (full dataset).
""")

print("Done.")
