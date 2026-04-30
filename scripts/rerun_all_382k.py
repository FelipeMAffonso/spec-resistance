"""
Comprehensive reanalysis on the FULL 382K dataset (OSF/data/spec_resistance_CLEAN.csv).
Previous analyses used a 148K subset. This script recomputes EVERY key statistic.

Sections:
  1. Comprehensive baseline stats + per-model + category + Wilson CIs
  2. Meta-analytic specification gap (per-model OR, DerSimonian-Laird, I^2, leave-one-out)
  3. Confabulation analysis
  4. Inverse scaling (log-log regression)
  5. Brand tax (price steering)
  6. Cross-model convergence
  7. Semantic contamination
  8. Cross-model correlations (within vs between provider, Mann-Whitney)
  9. Anti-brand backfire
  10. Comparison table: 148K vs 382K

Outputs:  results/382k_rerun/
"""

import os, sys, json, re, warnings
import numpy as np
import pandas as pd
from scipy import stats
from itertools import combinations
from collections import Counter, defaultdict

warnings.filterwarnings("ignore")

# ── Paths ────────────────────────────────────────────────────────────────
BASE = r"C:\Users\natal\Dropbox\Felipe\CLAUDE CODE\academic-research\projects\spec-resistance"
DATA = os.path.join(BASE, "OSF", "data", "spec_resistance_CLEAN.csv")
OUT = os.path.join(BASE, "nature-rr", "results", "382k_rerun")
os.makedirs(OUT, exist_ok=True)


# ── Helper functions ─────────────────────────────────────────────────────
def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    denom = 1 + z**2 / n
    centre = p + z**2 / (2 * n)
    spread = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)
    lo = (centre - spread) / denom
    hi = (centre + spread) / denom
    return (max(0.0, lo), min(1.0, hi))


def fp(x, d=2):
    if pd.isna(x):
        return "N/A"
    return f"{x*100:.{d}f}%"


def fci(lo, hi, d=2):
    if pd.isna(lo) or pd.isna(hi):
        return "[N/A]"
    return f"[{lo*100:.{d}f}%, {hi*100:.{d}f}%]"


def fisher_or(k1, n1, k2, n2):
    """Odds ratio with Woolf CI and Fisher exact p."""
    table = np.array([[k1, n1 - k1], [k2, n2 - k2]])
    oddsratio, pvalue = stats.fisher_exact(table, alternative="two-sided")
    a, b, c, d = k1, n1 - k1, k2, n2 - k2
    if a == 0 or b == 0 or c == 0 or d == 0:
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    log_or = np.log(a * d / (b * c))
    se = np.sqrt(1/a + 1/b + 1/c + 1/d)
    ci_lo = np.exp(log_or - 1.96 * se)
    ci_hi = np.exp(log_or + 1.96 * se)
    return oddsratio, (ci_lo, ci_hi), pvalue


def hdr(title, level=1):
    if level == 1:
        print("\n" + "=" * 90)
        print(f"  {title}")
        print("=" * 90)
    else:
        print(f"\n--- {title} ---")


def parse_price(p):
    """Parse price string like '$99.00' to float."""
    if pd.isna(p) or p == "":
        return np.nan
    s = str(p).replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


# ── Model parameter estimates (billions) ─────────────────────────────────
MODEL_PARAMS = {
    "gpt-4.1-nano": 2,
    "gpt-4o-mini": 8,
    "gpt-4.1-mini": 8,
    "gpt-5-mini": 8,
    "claude-haiku-4.5": 20,
    "gemma-3-27b": 27,
    "gemini-2.0-flash": 30,
    "gemini-2.5-flash": 30,
    "gemini-2.5-flash-lite": 30,
    "gemini-3-flash": 30,
    "gemini-2.5-pro": 50,
    "gpt-4o": 200,
    "claude-sonnet-4.6": 200,
    "deepseek-v3": 200,
    "deepseek-r1": 200,
    "llama-3.3-70b": 70,
    "qwen-2.5-72b": 72,
    "kimi-k2": 200,
}

# Developer-level provider mapping (not API routing provider)
DEV_PROVIDER = {
    'claude-haiku-4.5': 'anthropic', 'claude-sonnet-4.6': 'anthropic',
    'gpt-4.1-mini': 'openai', 'gpt-4.1-nano': 'openai', 'gpt-4o': 'openai',
    'gpt-4o-mini': 'openai', 'gpt-5-mini': 'openai',
    'gemini-2.0-flash': 'google', 'gemini-2.5-flash': 'google',
    'gemini-2.5-flash-lite': 'google', 'gemini-2.5-pro': 'google',
    'gemini-3-flash': 'google', 'gemma-3-27b': 'google',
    'deepseek-r1': 'deepseek', 'deepseek-v3': 'deepseek',
    'kimi-k2': 'moonshot', 'llama-3.3-70b': 'meta', 'qwen-2.5-72b': 'alibaba',
}


# ══════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════
print(f"Loading data from: {DATA}")
df = pd.read_csv(DATA, low_memory=False)
df["chose_optimal"] = df["chose_optimal"].astype(bool)
df["chose_branded"] = df["chose_branded"].astype(bool)
df["judge_brand_reasoning"] = df["judge_brand_reasoning"].map(
    {True: True, "True": True, False: False, "False": False}
)

# Parse prices for all 5 product slots
for letter in "ABCDE":
    col = f"product_{letter}_price"
    df[f"price_{letter}"] = df[col].apply(parse_price)

models = sorted(df["model_key"].unique())
n_total = len(df)

hdr("DATA OVERVIEW")
print(f"Total rows: {n_total:,}")
print(f"Models: {len(models)}")
for m in models:
    nm = len(df[df["model_key"] == m])
    print(f"  {m:<28s} {nm:>7,}")
print(f"Conditions: {df['condition'].nunique()}")
print(f"Categories: {df['category'].nunique()}")
print(f"Assortments: {df['assortment_id'].nunique()}")

# Master results dict
summary = {}

# ══════════════════════════════════════════════════════════════════════════
# 1. COMPREHENSIVE BASELINE STATS
# ══════════════════════════════════════════════════════════════════════════
hdr("1. COMPREHENSIVE BASELINE STATS")

bl = df[df["condition"] == "baseline"]
n_bl = len(bl)
k_nb = int((~bl["chose_optimal"]).sum())
r_nb = k_nb / n_bl
ci_bl = wilson_ci(k_nb, n_bl)

print(f"Baseline trials: {n_bl:,}")
print(f"Non-optimal: {k_nb:,}")
print(f"Non-optimal rate: {fp(r_nb)} {fci(*ci_bl)}")

summary["baseline"] = {
    "n": n_bl,
    "non_optimal_k": k_nb,
    "non_optimal_rate": round(r_nb, 6),
    "ci_lo": round(ci_bl[0], 6),
    "ci_hi": round(ci_bl[1], 6),
}

# Per-model baseline
hdr("Per-model baseline rates", 2)
per_model_rows = []
print(f"{'Model':<28} {'N':>7} {'k':>7} {'Rate':>10} {'95% CI':>28}")
for m in models:
    mb = bl[bl["model_key"] == m]
    n = len(mb)
    k = int((~mb["chose_optimal"]).sum())
    r = k / n if n > 0 else np.nan
    ci = wilson_ci(k, n)
    per_model_rows.append({
        "model": m, "n": n, "non_optimal_k": k,
        "non_optimal_rate": round(r, 6) if not np.isnan(r) else None,
        "ci_lo": round(ci[0], 6), "ci_hi": round(ci[1], 6),
    })
    print(f"{m:<28} {n:>7,} {k:>7,} {fp(r):>10} {fci(*ci):>28}")

per_model_df = pd.DataFrame(per_model_rows)
per_model_df.to_csv(os.path.join(OUT, "per_model_rates.csv"), index=False)
summary["per_model_baseline"] = per_model_rows

# Category-level rates with chi-squared
hdr("Category-level baseline rates + chi-squared", 2)
cat_rows = []
cat_obs = []
cat_exp_base = []
for cat in sorted(df["category"].unique()):
    sub = bl[bl["category"] == cat]
    n = len(sub)
    k = int((~sub["chose_optimal"]).sum())
    r = k / n if n > 0 else np.nan
    ci = wilson_ci(k, n)
    cat_rows.append({
        "category": cat, "n": n, "non_optimal_k": k,
        "non_optimal_rate": round(r, 6) if not np.isnan(r) else None,
        "ci_lo": round(ci[0], 6), "ci_hi": round(ci[1], 6),
    })
    if n > 0:
        cat_obs.append(k)
        cat_exp_base.append(n)
    print(f"{cat:<28} N={n:>6,} k={k:>5,} rate={fp(r)} {fci(*ci)}")

cat_df = pd.DataFrame(cat_rows)
cat_df.to_csv(os.path.join(OUT, "category_rates.csv"), index=False)

# Chi-squared heterogeneity test across categories
total_rate = sum(cat_obs) / sum(cat_exp_base) if sum(cat_exp_base) > 0 else 0
expected = [n * total_rate for n in cat_exp_base]
# Use at least 5 expected per cell for chi2; combine if needed, or use raw
chi2_stat, chi2_p = stats.chisquare(cat_obs, f_exp=expected)
n_cats = len(cat_obs)
print(f"\nChi-squared heterogeneity: chi2={chi2_stat:.1f}, df={n_cats-1}, p={chi2_p:.2e}")
summary["category_heterogeneity"] = {
    "chi2": round(float(chi2_stat), 2),
    "df": n_cats - 1,
    "p": float(chi2_p),
}

# Cross-model pairwise correlations
hdr("Cross-model pairwise correlations", 2)
bla = (
    bl.groupby(["model_key", "assortment_id"])["chose_optimal"]
    .apply(lambda x: 1 - x.mean())
    .unstack(level="assortment_id")
)
bla = bla.dropna(axis=1)
corr_m = bla.T.corr(method="pearson")
pairs = list(combinations(bla.index, 2))
within_corrs = []
between_corrs = []
all_corrs = []
for m1, m2 in pairs:
    r = corr_m.loc[m1, m2]
    all_corrs.append(r)
    if DEV_PROVIDER.get(m1) == DEV_PROVIDER.get(m2):
        within_corrs.append(r)
    else:
        between_corrs.append(r)

print(f"Total pairs: {len(all_corrs)}")
print(f"Mean correlation: {np.mean(all_corrs):.4f}")
print(f"Within-provider: N={len(within_corrs)}, mean={np.mean(within_corrs):.4f}")
print(f"Between-provider: N={len(between_corrs)}, mean={np.mean(between_corrs):.4f}")

if within_corrs and between_corrs:
    mw_u, mw_p = stats.mannwhitneyu(within_corrs, between_corrs, alternative="greater")
    print(f"Mann-Whitney (within > between): U={mw_u:.1f}, p={mw_p:.4e}")
    summary["cross_model_correlations"] = {
        "n_pairs": len(all_corrs),
        "mean_all": round(float(np.mean(all_corrs)), 4),
        "mean_within": round(float(np.mean(within_corrs)), 4),
        "mean_between": round(float(np.mean(between_corrs)), 4),
        "mann_whitney_U": round(float(mw_u), 1),
        "mann_whitney_p": float(mw_p),
    }

# Anti-brand backfire
hdr("Anti-brand backfire rates", 2)
ab_results = {}
for cond in ["anti_brand_rejection", "anti_brand_negative_experience", "anti_brand_prefer_unknown"]:
    sub = df[df["condition"] == cond]
    n = len(sub)
    k = int((~sub["chose_optimal"]).sum())
    r = k / n if n > 0 else np.nan
    ci = wilson_ci(k, n)
    odr, cior, pv = fisher_or(k, n, k_nb, n_bl)
    ab_results[cond] = {
        "n": n, "non_optimal_k": k,
        "non_optimal_rate": round(r, 6) if not np.isnan(r) else None,
        "ci_lo": round(ci[0], 6), "ci_hi": round(ci[1], 6),
        "or_vs_baseline": round(float(odr), 3),
        "or_ci": [round(float(cior[0]), 3), round(float(cior[1]), 3)],
        "p": float(pv),
    }
    print(f"{cond:<40} N={n:>7,} rate={fp(r)} {fci(*ci)} OR={odr:.3f} p={pv:.2e}")

summary["anti_brand"] = ab_results

# Specification gap at each level
hdr("Specification gap (all levels)", 2)
spec_levels = {
    0: "baseline",
    1: ["preference_vague", "utility_vague"],
    2: ["preference_weighted", "utility_weighted"],
    3: ["preference_explicit", "utility_explicit"],
    4: ["preference_override", "utility_override"],
    5: ["preference_constrained", "utility_constrained"],
}

spec_gap_results = {}
print(f"{'Level':>6} {'N':>8} {'k':>8} {'Rate':>10} {'OR vs BL':>12} {'OR CI':>28} {'p':>14}")
for lvl in sorted(spec_levels.keys()):
    if lvl == 0:
        sub = bl
    else:
        conds = spec_levels[lvl]
        sub = df[df["condition"].isin(conds)]
    n = len(sub)
    k = int((~sub["chose_optimal"]).sum())
    r = k / n if n > 0 else np.nan
    ci = wilson_ci(k, n)
    if lvl == 0:
        print(f"{lvl:>6} {n:>8,} {k:>8,} {fp(r):>10} {'ref':>12} {'ref':>28} {'ref':>14}")
        spec_gap_results[lvl] = {
            "n": n, "k": k, "rate": round(r, 6),
            "ci": [round(ci[0], 6), round(ci[1], 6)],
        }
    else:
        odr, cior, pv = fisher_or(k, n, k_nb, n_bl)
        print(f"{lvl:>6} {n:>8,} {k:>8,} {fp(r):>10} {odr:>12.2f} [{cior[0]:.2f},{cior[1]:.2f}]{' ':>2} {pv:>14.2e}")
        spec_gap_results[lvl] = {
            "n": n, "k": k, "rate": round(r, 6),
            "ci": [round(ci[0], 6), round(ci[1], 6)],
            "or": round(float(odr), 2),
            "or_ci": [round(float(cior[0]), 2), round(float(cior[1]), 2)],
            "p": float(pv),
        }

summary["spec_gap_by_level"] = spec_gap_results


# ══════════════════════════════════════════════════════════════════════════
# 2. META-ANALYTIC SPECIFICATION GAP
# ══════════════════════════════════════════════════════════════════════════
hdr("2. META-ANALYTIC SPECIFICATION GAP")

# Per-model OR: weighted (level 2) vs explicit (level 3)
weighted_conds = ["preference_weighted", "utility_weighted"]
explicit_conds = ["preference_explicit", "utility_explicit"]

meta_rows = []
print(f"{'Model':<28} {'W_n':>6} {'W_k':>6} {'E_n':>6} {'E_k':>6} {'OR':>10} {'logOR':>10} {'SE':>10}")
for m in models:
    mw = df[(df["model_key"] == m) & (df["condition"].isin(weighted_conds))]
    me = df[(df["model_key"] == m) & (df["condition"].isin(explicit_conds))]
    nw, ne = len(mw), len(me)
    kw = int((~mw["chose_optimal"]).sum())
    ke = int((~me["chose_optimal"]).sum())
    # Haldane correction for zero cells
    a, b, c, d_val = kw, nw - kw, ke, ne - ke
    if a == 0 or b == 0 or c == 0 or d_val == 0:
        a, b, c, d_val = a + 0.5, b + 0.5, c + 0.5, d_val + 0.5
    log_or = np.log(a * d_val / (b * c))
    se = np.sqrt(1/a + 1/b + 1/c + 1/d_val)
    or_val = np.exp(log_or)
    meta_rows.append({
        "model": m, "w_n": nw, "w_k": kw, "e_n": ne, "e_k": ke,
        "or": round(or_val, 3), "log_or": round(log_or, 4), "se": round(se, 4),
    })
    print(f"{m:<28} {nw:>6,} {kw:>6,} {ne:>6,} {ke:>6,} {or_val:>10.2f} {log_or:>10.4f} {se:>10.4f}")

# DerSimonian-Laird random-effects meta-analysis
log_ors = np.array([r["log_or"] for r in meta_rows])
ses = np.array([r["se"] for r in meta_rows])
weights_fe = 1 / ses**2

# Fixed-effect estimate
theta_fe = np.sum(weights_fe * log_ors) / np.sum(weights_fe)

# Q statistic
Q = np.sum(weights_fe * (log_ors - theta_fe)**2)
df_q = len(log_ors) - 1
Q_p = 1 - stats.chi2.cdf(Q, df_q)

# Tau-squared (DerSimonian-Laird)
C = np.sum(weights_fe) - np.sum(weights_fe**2) / np.sum(weights_fe)
tau2 = max(0, (Q - df_q) / C)

# Random-effects weights
weights_re = 1 / (ses**2 + tau2)
theta_re = np.sum(weights_re * log_ors) / np.sum(weights_re)
se_re = np.sqrt(1 / np.sum(weights_re))
or_re = np.exp(theta_re)
or_re_ci_lo = np.exp(theta_re - 1.96 * se_re)
or_re_ci_hi = np.exp(theta_re + 1.96 * se_re)
z_re = theta_re / se_re
p_re = 2 * (1 - stats.norm.cdf(abs(z_re)))

# I-squared
I2 = max(0, (Q - df_q) / Q * 100) if Q > 0 else 0

print(f"\n--- DerSimonian-Laird Random-Effects Meta-Analysis ---")
print(f"Studies (models): {len(log_ors)}")
print(f"Pooled OR (RE): {or_re:.2f} [{or_re_ci_lo:.2f}, {or_re_ci_hi:.2f}]")
print(f"z = {z_re:.2f}, p = {p_re:.2e}")
print(f"Q = {Q:.2f}, df = {df_q}, p = {Q_p:.2e}")
print(f"tau^2 = {tau2:.4f}")
print(f"I^2 = {I2:.1f}%")

# Leave-one-out
hdr("Leave-one-out sensitivity", 2)
loo_results = []
for i in range(len(log_ors)):
    lo_i = np.delete(log_ors, i)
    se_i = np.delete(ses, i)
    w_fe_i = 1 / se_i**2
    theta_fe_i = np.sum(w_fe_i * lo_i) / np.sum(w_fe_i)
    Q_i = np.sum(w_fe_i * (lo_i - theta_fe_i)**2)
    C_i = np.sum(w_fe_i) - np.sum(w_fe_i**2) / np.sum(w_fe_i)
    tau2_i = max(0, (Q_i - (len(lo_i) - 1)) / C_i)
    w_re_i = 1 / (se_i**2 + tau2_i)
    theta_re_i = np.sum(w_re_i * lo_i) / np.sum(w_re_i)
    se_re_i = np.sqrt(1 / np.sum(w_re_i))
    or_re_i = np.exp(theta_re_i)
    I2_i = max(0, (Q_i - (len(lo_i) - 1)) / Q_i * 100) if Q_i > 0 else 0
    loo_results.append({
        "excluded": meta_rows[i]["model"],
        "or_re": round(or_re_i, 2),
        "ci_lo": round(np.exp(theta_re_i - 1.96 * se_re_i), 2),
        "ci_hi": round(np.exp(theta_re_i + 1.96 * se_re_i), 2),
        "I2": round(I2_i, 1),
    })
    print(f"  Excl {meta_rows[i]['model']:<26s}: OR={or_re_i:.2f} [{np.exp(theta_re_i - 1.96*se_re_i):.2f}, {np.exp(theta_re_i + 1.96*se_re_i):.2f}] I2={I2_i:.1f}%")

# Phase transition breakpoint (piecewise vs linear AIC)
hdr("Phase transition: piecewise vs linear", 2)

# Prepare level-rate data for piecewise test
level_data = []
for lvl in range(6):
    if lvl == 0:
        sub = bl
    else:
        conds = spec_levels[lvl]
        sub = df[df["condition"].isin(conds)]
    n = len(sub)
    k = int((~sub["chose_optimal"]).sum())
    r = k / n if n > 0 else 0
    level_data.append({"level": lvl, "n": n, "k": k, "rate": r})

# For AIC comparison, use logistic regression style on aggregated data
# Simple approach: model log-odds as function of level
levels_arr = np.array([d["level"] for d in level_data], dtype=float)
rates_arr = np.array([d["rate"] for d in level_data])
ns_arr = np.array([d["n"] for d in level_data])
ks_arr = np.array([d["k"] for d in level_data])

# Clip rates for log-odds
rates_clipped = np.clip(rates_arr, 1e-6, 1 - 1e-6)
log_odds = np.log(rates_clipped / (1 - rates_clipped))
weights_n = ns_arr  # weight by sample size

# Linear model: log_odds = a + b*level
from numpy.polynomial.polynomial import polyfit
coeffs_linear = np.polyfit(levels_arr, log_odds, 1, w=np.sqrt(weights_n))
pred_linear = np.polyval(coeffs_linear, levels_arr)
residuals_linear = np.sqrt(weights_n) * (log_odds - pred_linear)
rss_linear = np.sum(residuals_linear**2)
k_linear = 2  # slope + intercept
n_points = len(levels_arr)
aic_linear = n_points * np.log(rss_linear / n_points) + 2 * k_linear

# Piecewise model: breakpoint between levels 2 and 3
# Two segments: levels 0-2 and levels 2-5
bp = 2.5
seg1 = levels_arr <= bp
seg2 = levels_arr > bp
if seg1.sum() >= 2 and seg2.sum() >= 2:
    coeffs1 = np.polyfit(levels_arr[seg1], log_odds[seg1], 1, w=np.sqrt(weights_n[seg1]))
    coeffs2 = np.polyfit(levels_arr[seg2], log_odds[seg2], 1, w=np.sqrt(weights_n[seg2]))
    pred_pw = np.zeros_like(log_odds)
    pred_pw[seg1] = np.polyval(coeffs1, levels_arr[seg1])
    pred_pw[seg2] = np.polyval(coeffs2, levels_arr[seg2])
    residuals_pw = np.sqrt(weights_n) * (log_odds - pred_pw)
    rss_pw = np.sum(residuals_pw**2)
    k_pw = 4  # two slopes + two intercepts
    aic_pw = n_points * np.log(rss_pw / n_points) + 2 * k_pw
    print(f"Linear AIC: {aic_linear:.2f} (RSS={rss_linear:.4f})")
    print(f"Piecewise AIC (break at 2.5): {aic_pw:.2f} (RSS={rss_pw:.4f})")
    print(f"Delta AIC (linear - piecewise): {aic_linear - aic_pw:.2f}")
    print(f"  -> {'Piecewise BETTER' if aic_pw < aic_linear else 'Linear BETTER'}")
else:
    aic_pw = np.nan
    print("Insufficient data for piecewise fit.")

spec_meta = {
    "per_model_or": meta_rows,
    "random_effects": {
        "pooled_or": round(float(or_re), 2),
        "ci_lo": round(float(or_re_ci_lo), 2),
        "ci_hi": round(float(or_re_ci_hi), 2),
        "z": round(float(z_re), 2),
        "p": float(p_re),
        "Q": round(float(Q), 2),
        "Q_df": int(df_q),
        "Q_p": float(Q_p),
        "tau2": round(float(tau2), 4),
        "I2": round(float(I2), 1),
    },
    "leave_one_out": loo_results,
    "phase_transition": {
        "aic_linear": round(float(aic_linear), 2),
        "aic_piecewise": round(float(aic_pw), 2) if not np.isnan(aic_pw) else None,
        "breakpoint": 2.5,
        "piecewise_better": bool(aic_pw < aic_linear) if not np.isnan(aic_pw) else None,
    },
}
with open(os.path.join(OUT, "spec_gap_meta.json"), "w") as f:
    json.dump(spec_meta, f, indent=2)
summary["meta_analysis"] = spec_meta


# ══════════════════════════════════════════════════════════════════════════
# 3. CONFABULATION
# ══════════════════════════════════════════════════════════════════════════
hdr("3. CONFABULATION")

# Overall at baseline
bln = bl[~bl["chose_optimal"]]
n_nonopt_bl = len(bln)
bln_valid = bln[bln["judge_brand_reasoning"].notna()]
n_valid = len(bln_valid)
brand_cited = int(bln_valid["judge_brand_reasoning"].sum())
confab_count = n_valid - brand_cited
confab_rate = confab_count / n_valid if n_valid > 0 else np.nan
ci_confab = wilson_ci(confab_count, n_valid)

print(f"Baseline non-optimal: {n_nonopt_bl:,}")
print(f"  With judge data: {n_valid:,}")
print(f"  Brand reasoning cited (transparent): {brand_cited:,} ({fp(brand_cited / n_valid if n_valid > 0 else np.nan)})")
print(f"  Confabulation (attribute-only): {confab_count:,}")
print(f"  Confabulation rate: {fp(confab_rate)} {fci(*ci_confab)}")

confab_results = {
    "baseline_non_optimal_n": n_nonopt_bl,
    "valid_n": n_valid,
    "confabulation_count": confab_count,
    "confabulation_rate": round(confab_rate, 6) if not np.isnan(confab_rate) else None,
    "ci_lo": round(ci_confab[0], 6),
    "ci_hi": round(ci_confab[1], 6),
    "brand_cited_count": brand_cited,
    "brand_cited_rate": round(brand_cited / n_valid, 6) if n_valid > 0 else None,
}

# Per-model confabulation
hdr("Per-model confabulation (baseline non-optimal)", 2)
confab_model_rows = []
print(f"{'Model':<28} {'N_valid':>8} {'Confab':>8} {'Rate':>10}")
for m in models:
    mno = bln_valid[bln_valid["model_key"] == m]
    n = len(mno)
    if n == 0:
        confab_model_rows.append({"model": m, "n": 0, "confab": 0, "rate": None})
        print(f"{m:<28} {0:>8} {0:>8} {'N/A':>10}")
        continue
    br = int(mno["judge_brand_reasoning"].sum())
    cf = n - br
    r = cf / n
    confab_model_rows.append({"model": m, "n": n, "confab": cf, "rate": round(r, 6)})
    print(f"{m:<28} {n:>8,} {cf:>8,} {fp(r):>10}")

confab_results["per_model"] = confab_model_rows

# By condition type
hdr("Confabulation by condition type", 2)
confab_by_type = {}
for ctype in sorted(df["condition_type"].unique()):
    sub = df[(df["condition_type"] == ctype) & (~df["chose_optimal"])]
    sub_v = sub[sub["judge_brand_reasoning"].notna()]
    nv = len(sub_v)
    if nv == 0:
        confab_by_type[ctype] = {"n": 0, "confab": 0, "rate": None}
        continue
    br = int(sub_v["judge_brand_reasoning"].sum())
    cf = nv - br
    r = cf / nv
    confab_by_type[ctype] = {"n": nv, "confab": cf, "rate": round(r, 6)}
    print(f"{ctype:<30} N={nv:>6,} confab={cf:>6,} rate={fp(r)}")

confab_results["by_condition_type"] = confab_by_type

# By specification level
hdr("Confabulation by specification level", 2)
confab_by_level = {}
for lvl in range(6):
    if lvl == 0:
        sub_all = bl
    else:
        conds = spec_levels[lvl]
        sub_all = df[df["condition"].isin(conds)]
    sub = sub_all[~sub_all["chose_optimal"]]
    sub_v = sub[sub["judge_brand_reasoning"].notna()]
    nv = len(sub_v)
    if nv == 0:
        confab_by_level[lvl] = {"n": 0, "confab": 0, "rate": None}
        print(f"Level {lvl}: N=0")
        continue
    br = int(sub_v["judge_brand_reasoning"].sum())
    cf = nv - br
    r = cf / nv
    confab_by_level[lvl] = {"n": nv, "confab": cf, "rate": round(r, 6)}
    print(f"Level {lvl}: N={nv:>6,} confab={cf:>6,} rate={fp(r)}")

confab_results["by_spec_level"] = confab_by_level

with open(os.path.join(OUT, "confabulation.json"), "w") as f:
    json.dump(confab_results, f, indent=2, default=str)
summary["confabulation"] = confab_results


# ══════════════════════════════════════════════════════════════════════════
# 4. INVERSE SCALING
# ══════════════════════════════════════════════════════════════════════════
hdr("4. INVERSE SCALING (log-log)")

scaling_rows = []
for m in models:
    mb = bl[bl["model_key"] == m]
    n = len(mb)
    k = int((~mb["chose_optimal"]).sum())
    r = k / n if n > 0 else np.nan
    params = MODEL_PARAMS.get(m)
    if params and not np.isnan(r) and r > 0:
        scaling_rows.append({
            "model": m,
            "params_B": params,
            "non_opt_rate": r,
            "log_params": np.log10(params),
            "log_nonopt": np.log10(r),
        })

if len(scaling_rows) >= 3:
    x = np.array([r["log_params"] for r in scaling_rows])
    y = np.array([r["log_nonopt"] for r in scaling_rows])
    slope, intercept, r_val, p_val, se_slope = stats.linregress(x, y)
    print(f"log(non_opt) ~ log(params): slope={slope:.4f}, intercept={intercept:.4f}")
    print(f"  R^2 = {r_val**2:.4f}, p = {p_val:.4e}, SE(slope) = {se_slope:.4f}")
    print(f"  Positive slope = larger models err MORE (inverse scaling)")
    for r_ in scaling_rows:
        print(f"    {r_['model']:<28s} params={r_['params_B']:>5}B  rate={r_['non_opt_rate']*100:.2f}%")
    summary["inverse_scaling"] = {
        "slope": round(slope, 4),
        "intercept": round(intercept, 4),
        "r_squared": round(r_val**2, 4),
        "p": float(p_val),
        "se_slope": round(se_slope, 4),
        "n_models": len(scaling_rows),
        "interpretation": "positive slope = inverse scaling (larger models err more)" if slope > 0 else "negative slope = normal scaling",
    }
else:
    print("Insufficient data for regression.")
    summary["inverse_scaling"] = {"error": "insufficient data"}


# ══════════════════════════════════════════════════════════════════════════
# 5. BRAND TAX
# ══════════════════════════════════════════════════════════════════════════
hdr("5. BRAND TAX (price steering)")

# For each non-optimal baseline trial: compare chosen product price to optimal product price
bl_nonopt = bl[~bl["chose_optimal"]].copy()

def get_product_price(row, letter):
    col = f"price_{letter}"
    return row.get(col, np.nan)

overpayments = []
underpayments = []
tax_rows = []

for idx, row in bl_nonopt.iterrows():
    chosen_letter = row["choice"]
    optimal_letter = row["optimal_product"]
    if pd.isna(chosen_letter) or pd.isna(optimal_letter):
        continue
    chosen_price = get_product_price(row, chosen_letter)
    optimal_price = get_product_price(row, optimal_letter)
    if np.isnan(chosen_price) or np.isnan(optimal_price) or optimal_price == 0:
        continue
    diff = chosen_price - optimal_price
    pct = diff / optimal_price * 100
    tax_rows.append({
        "category": row["category"],
        "diff_abs": diff,
        "diff_pct": pct,
        "chosen_price": chosen_price,
        "optimal_price": optimal_price,
        "steered_expensive": diff > 0,
    })
    if diff > 0:
        overpayments.append(pct)
    elif diff < 0:
        underpayments.append(pct)

n_tax = len(tax_rows)
n_expensive = sum(1 for t in tax_rows if t["steered_expensive"])
pct_expensive = n_expensive / n_tax * 100 if n_tax > 0 else 0

print(f"Non-optimal baseline trials with valid prices: {n_tax:,}")
print(f"Steered to MORE expensive: {n_expensive:,} ({pct_expensive:.1f}%)")
print(f"Steered to LESS expensive: {n_tax - n_expensive:,} ({100 - pct_expensive:.1f}%)")

if overpayments:
    print(f"\nOverpayment (when steered expensive):")
    print(f"  Mean: {np.mean(overpayments):.1f}%")
    print(f"  Median: {np.median(overpayments):.1f}%")
    print(f"  Min: {np.min(overpayments):.1f}%")
    print(f"  Max: {np.max(overpayments):.1f}%")

all_diffs_pct = [t["diff_pct"] for t in tax_rows]
print(f"\nAll price differentials (chosen - optimal, % of optimal):")
print(f"  Mean: {np.mean(all_diffs_pct):.1f}%")
print(f"  Median: {np.median(all_diffs_pct):.1f}%")

# Per-category
hdr("Brand tax by category", 2)
cat_tax = defaultdict(list)
for t in tax_rows:
    cat_tax[t["category"]].append(t)

cat_tax_results = {}
print(f"{'Category':<25} {'N':>6} {'%Expens':>9} {'Mean%':>8} {'Median%':>9}")
for cat in sorted(cat_tax.keys()):
    items = cat_tax[cat]
    n = len(items)
    n_exp = sum(1 for i in items if i["steered_expensive"])
    pcts = [i["diff_pct"] for i in items]
    cat_tax_results[cat] = {
        "n": n,
        "pct_expensive": round(n_exp / n * 100, 1) if n > 0 else None,
        "mean_diff_pct": round(float(np.mean(pcts)), 1),
        "median_diff_pct": round(float(np.median(pcts)), 1),
    }
    print(f"{cat:<25} {n:>6,} {n_exp/n*100:>8.1f}% {np.mean(pcts):>+7.1f}% {np.median(pcts):>+8.1f}%")

brand_tax = {
    "n_trials": n_tax,
    "n_steered_expensive": n_expensive,
    "pct_steered_expensive": round(pct_expensive, 2),
    "overpayment_mean_pct": round(float(np.mean(overpayments)), 2) if overpayments else None,
    "overpayment_median_pct": round(float(np.median(overpayments)), 2) if overpayments else None,
    "all_diff_mean_pct": round(float(np.mean(all_diffs_pct)), 2),
    "all_diff_median_pct": round(float(np.median(all_diffs_pct)), 2),
    "by_category": cat_tax_results,
}
with open(os.path.join(OUT, "brand_tax.json"), "w") as f:
    json.dump(brand_tax, f, indent=2)
summary["brand_tax"] = brand_tax


# ══════════════════════════════════════════════════════════════════════════
# 6. CROSS-MODEL CONVERGENCE
# ══════════════════════════════════════════════════════════════════════════
hdr("6. CROSS-MODEL CONVERGENCE")

# For each assortment at baseline: among non-optimal choices, what fraction choose the SAME wrong brand?
convergence_data = []
for aid in sorted(bl["assortment_id"].unique()):
    sub = bl[(bl["assortment_id"] == aid) & (~bl["chose_optimal"])]
    n = len(sub)
    if n < 2:
        continue
    # Count most-chosen wrong brand
    brand_counts = sub["choice"].value_counts()
    most_common_brand = brand_counts.iloc[0]
    convergence_rate = most_common_brand / n
    n_models_err = sub["model_key"].nunique()
    convergence_data.append({
        "assortment_id": aid,
        "n_nonopt": n,
        "n_models_erring": n_models_err,
        "top_wrong_brand": brand_counts.index[0],
        "top_wrong_count": int(most_common_brand),
        "convergence_rate": round(convergence_rate, 4),
    })

if convergence_data:
    conv_rates = [c["convergence_rate"] for c in convergence_data]
    print(f"Assortments with >= 2 non-optimal choices: {len(convergence_data)}")
    print(f"Mean convergence rate: {np.mean(conv_rates):.4f}")
    print(f"Median convergence rate: {np.median(conv_rates):.4f}")
    print(f"Min: {np.min(conv_rates):.4f}, Max: {np.max(conv_rates):.4f}")

    # Top 10 highest convergence
    top_conv = sorted(convergence_data, key=lambda x: -x["convergence_rate"])[:10]
    print(f"\nTop 10 convergence assortments:")
    for c in top_conv:
        print(f"  {c['assortment_id']:<30s} N={c['n_nonopt']:>4d} conv={c['convergence_rate']:.3f} top={c['top_wrong_brand']} ({c['top_wrong_count']})")

convergence_json = {
    "n_assortments": len(convergence_data),
    "mean_convergence": round(float(np.mean(conv_rates)), 4) if conv_rates else None,
    "median_convergence": round(float(np.median(conv_rates)), 4) if conv_rates else None,
    "per_assortment": convergence_data,
}
with open(os.path.join(OUT, "convergence.json"), "w") as f:
    json.dump(convergence_json, f, indent=2)
summary["convergence"] = {
    "n_assortments": len(convergence_data),
    "mean": round(float(np.mean(conv_rates)), 4) if conv_rates else None,
    "median": round(float(np.median(conv_rates)), 4) if conv_rates else None,
}


# ══════════════════════════════════════════════════════════════════════════
# 7. SEMANTIC CONTAMINATION
# ══════════════════════════════════════════════════════════════════════════
hdr("7. SEMANTIC CONTAMINATION")

# Brand-associated vocab vs spec-associated vocab in reasoning
BRAND_WORDS = {
    "brand", "brands", "reputation", "trusted", "reputable", "reliable",
    "well-known", "popular", "recognized", "established", "premium", "flagship",
    "renowned", "leading", "top-tier", "proven", "heritage", "legacy",
    "industry", "market", "leader", "name", "famous", "quality brand",
    "track record", "customer service", "support", "warranty",
}
SPEC_WORDS = {
    "specification", "specifications", "spec", "specs", "battery", "display",
    "processor", "RAM", "storage", "screen", "resolution", "camera", "weight",
    "performance", "speed", "capacity", "watt", "lumen", "decibel", "dB",
    "suction", "waterproof", "range", "connectivity", "bluetooth", "wifi",
    "feature", "features", "value", "price", "cost", "budget", "affordable",
    "utility", "score", "rating", "efficiency", "durability", "noise",
    "megapixel", "refresh rate", "latency", "bass",
}


def count_vocab(text, vocab_set):
    if pd.isna(text) or not isinstance(text, str):
        return 0
    text_lower = text.lower()
    count = 0
    for word in vocab_set:
        count += text_lower.count(word.lower())
    return count


# Compare non-optimal vs optimal reasoning at baseline
bl_with_reasoning = bl[bl["reasoning"].notna() & (bl["reasoning"] != "")].copy()
bl_with_reasoning["brand_vocab_count"] = bl_with_reasoning["reasoning"].apply(lambda x: count_vocab(x, BRAND_WORDS))
bl_with_reasoning["spec_vocab_count"] = bl_with_reasoning["reasoning"].apply(lambda x: count_vocab(x, SPEC_WORDS))
bl_with_reasoning["brand_spec_ratio"] = bl_with_reasoning.apply(
    lambda r: r["brand_vocab_count"] / max(r["spec_vocab_count"], 1), axis=1
)

opt = bl_with_reasoning[bl_with_reasoning["chose_optimal"]]
nonopt = bl_with_reasoning[~bl_with_reasoning["chose_optimal"]]

print(f"Baseline with reasoning: {len(bl_with_reasoning):,}")
print(f"  Optimal: {len(opt):,}")
print(f"  Non-optimal: {len(nonopt):,}")

print(f"\nBrand vocab count (mean):")
print(f"  Optimal: {opt['brand_vocab_count'].mean():.2f}")
print(f"  Non-optimal: {nonopt['brand_vocab_count'].mean():.2f}")
u_brand, p_brand = stats.mannwhitneyu(nonopt["brand_vocab_count"], opt["brand_vocab_count"], alternative="greater")
print(f"  Mann-Whitney (non-opt > opt): U={u_brand:.0f}, p={p_brand:.4e}")

print(f"\nSpec vocab count (mean):")
print(f"  Optimal: {opt['spec_vocab_count'].mean():.2f}")
print(f"  Non-optimal: {nonopt['spec_vocab_count'].mean():.2f}")
u_spec, p_spec = stats.mannwhitneyu(opt["spec_vocab_count"], nonopt["spec_vocab_count"], alternative="greater")
print(f"  Mann-Whitney (opt > non-opt): U={u_spec:.0f}, p={p_spec:.4e}")

print(f"\nBrand/Spec ratio (mean):")
print(f"  Optimal: {opt['brand_spec_ratio'].mean():.4f}")
print(f"  Non-optimal: {nonopt['brand_spec_ratio'].mean():.4f}")
u_ratio, p_ratio = stats.mannwhitneyu(nonopt["brand_spec_ratio"], opt["brand_spec_ratio"], alternative="greater")
print(f"  Mann-Whitney (non-opt ratio > opt ratio): U={u_ratio:.0f}, p={p_ratio:.4e}")

summary["semantic_contamination"] = {
    "n_optimal": len(opt),
    "n_nonoptimal": len(nonopt),
    "brand_vocab_mean_optimal": round(float(opt["brand_vocab_count"].mean()), 3),
    "brand_vocab_mean_nonoptimal": round(float(nonopt["brand_vocab_count"].mean()), 3),
    "brand_vocab_mw_p": float(p_brand),
    "spec_vocab_mean_optimal": round(float(opt["spec_vocab_count"].mean()), 3),
    "spec_vocab_mean_nonoptimal": round(float(nonopt["spec_vocab_count"].mean()), 3),
    "spec_vocab_mw_p": float(p_spec),
    "ratio_mean_optimal": round(float(opt["brand_spec_ratio"].mean()), 4),
    "ratio_mean_nonoptimal": round(float(nonopt["brand_spec_ratio"].mean()), 4),
    "ratio_mw_p": float(p_ratio),
}


# ══════════════════════════════════════════════════════════════════════════
# 8. CONTROL CONDITIONS (for completeness)
# ══════════════════════════════════════════════════════════════════════════
hdr("8. CONTROL CONDITIONS")
ctrls = ["control_all_familiar", "control_brand_reversal", "control_comprehension", "control_fictional_brands"]
ctrl_results = {}
for cond in ctrls:
    sub = df[df["condition"] == cond]
    n = len(sub)
    ko = int(sub["chose_optimal"].sum())
    kn = n - ko
    ci = wilson_ci(kn, n)
    odr, cior, pv = fisher_or(kn, n, k_nb, n_bl)
    ctrl_results[cond] = {
        "n": n, "optimal_k": ko, "non_optimal_k": kn,
        "optimal_rate": round(ko / n, 6) if n > 0 else None,
        "non_optimal_rate": round(kn / n, 6) if n > 0 else None,
        "ci_lo": round(ci[0], 6), "ci_hi": round(ci[1], 6),
        "or_vs_baseline": round(float(odr), 4),
        "p": float(pv),
    }
    print(f"{cond:<30s} N={n:>7,} opt={fp(ko/n if n > 0 else np.nan)} non-opt={fp(kn/n if n > 0 else np.nan)} OR={odr:.4f} p={pv:.2e}")

summary["controls"] = ctrl_results


# ══════════════════════════════════════════════════════════════════════════
# 9. MECHANISM CONDITIONS
# ══════════════════════════════════════════════════════════════════════════
hdr("9. MECHANISM CONDITIONS")
mech_conds = [c for c in sorted(df["condition"].unique()) if c.startswith("mechanism_") or c.startswith("baseline_")]
mech_results = {}
print(f"{'Condition':<38} {'N':>7} {'Rate':>10} {'OR':>10} {'p':>14}")
for cond in mech_conds:
    sub = df[df["condition"] == cond]
    n = len(sub)
    k = int((~sub["chose_optimal"]).sum())
    r = k / n if n > 0 else np.nan
    ci = wilson_ci(k, n)
    odr, cior, pv = fisher_or(k, n, k_nb, n_bl)
    mech_results[cond] = {
        "n": n, "k": k, "rate": round(r, 6) if not np.isnan(r) else None,
        "or": round(float(odr), 3), "p": float(pv),
    }
    print(f"{cond:<38} {n:>7,} {fp(r):>10} {odr:>10.3f} {pv:>14.2e}")

summary["mechanisms"] = mech_results


# ══════════════════════════════════════════════════════════════════════════
# 10. COMPARISON TABLE: 148K vs 382K
# ══════════════════════════════════════════════════════════════════════════
hdr("10. COMPARISON TABLE: 148K vs 382K")

# Previous 148K numbers (extracted from SUMMARY_REPORT.txt and CLAUDE.md)
old = {
    "total_rows": 148_000,  # approximate
    "n_models": 17,
    "baseline_n": 4_759,
    "baseline_non_opt_rate": 0.2152,
    "within_provider_corr": 0.5048,
    "between_provider_corr": 0.2253,
    "overall_corr": 0.2972,
    "mann_whitney_p": 0.0000,
    "chi2_category": 412.7,
    "confab_rate": 0.792,  # from CLAUDE.md "79.2% confabulation"
    "baseline_non_opt_k_approx": 1024,
    "spec_gap_L0": 0.2152,
    "spec_gap_L1": 0.1741,
    "spec_gap_L2": 0.1521,
    "spec_gap_L3": 0.0010,
    "spec_gap_L4": 0.0003,
    "spec_gap_L5": 0.0000,
}

new = {
    "total_rows": n_total,
    "n_models": len(models),
    "baseline_n": n_bl,
    "baseline_non_opt_rate": r_nb,
    "within_provider_corr": float(np.mean(within_corrs)) if within_corrs else np.nan,
    "between_provider_corr": float(np.mean(between_corrs)) if between_corrs else np.nan,
    "overall_corr": float(np.mean(all_corrs)) if all_corrs else np.nan,
    "mann_whitney_p": float(mw_p) if within_corrs and between_corrs else np.nan,
    "chi2_category": float(chi2_stat),
    "confab_rate": confab_rate if not np.isnan(confab_rate) else np.nan,
    "baseline_non_opt_k_approx": k_nb,
    "spec_gap_L0": spec_gap_results[0]["rate"],
    "spec_gap_L1": spec_gap_results[1]["rate"],
    "spec_gap_L2": spec_gap_results[2]["rate"],
    "spec_gap_L3": spec_gap_results[3]["rate"],
    "spec_gap_L4": spec_gap_results[4]["rate"],
    "spec_gap_L5": spec_gap_results[5]["rate"],
}

print(f"\n{'Statistic':<35} {'148K':>14} {'382K':>14} {'Delta':>12} {'FLAG':>6}")
print("-" * 85)
comparisons = [
    ("Total rows", "total_rows", False),
    ("N models", "n_models", False),
    ("Baseline N", "baseline_n", False),
    ("Baseline non-opt rate", "baseline_non_opt_rate", True),
    ("Within-provider corr", "within_provider_corr", True),
    ("Between-provider corr", "between_provider_corr", True),
    ("Overall corr", "overall_corr", True),
    ("Mann-Whitney p", "mann_whitney_p", False),
    ("Chi2 (category)", "chi2_category", False),
    ("Confabulation rate", "confab_rate", True),
    ("Baseline non-opt k", "baseline_non_opt_k_approx", False),
    ("Spec gap L0 (baseline)", "spec_gap_L0", True),
    ("Spec gap L1 (vague)", "spec_gap_L1", True),
    ("Spec gap L2 (weighted)", "spec_gap_L2", True),
    ("Spec gap L3 (explicit)", "spec_gap_L3", True),
    ("Spec gap L4 (override)", "spec_gap_L4", True),
    ("Spec gap L5 (constrained)", "spec_gap_L5", True),
]

flags = []
for label, key, is_rate in comparisons:
    o = old.get(key)
    n_ = new.get(key)
    if o is None or n_ is None or (isinstance(o, float) and np.isnan(o)) or (isinstance(n_, float) and np.isnan(n_)):
        delta_str = "N/A"
        flag = ""
    elif is_rate:
        delta = (n_ - o) * 100  # in percentage points
        delta_str = f"{delta:+.2f}pp"
        flag = "***" if abs(delta) > 1.0 else ""
        o_str = f"{o*100:.2f}%"
        n_str = f"{n_*100:.2f}%"
    else:
        delta = n_ - o
        delta_str = f"{delta:+,.0f}" if isinstance(delta, (int, float)) and abs(delta) > 1 else f"{delta:+.4f}"
        flag = "***" if isinstance(o, int) and abs(delta) > max(o * 0.1, 100) else ""
        o_str = f"{o:,.4f}" if isinstance(o, float) else f"{o:,}"
        n_str = f"{n_:,.4f}" if isinstance(n_, float) else f"{n_:,}"

    if is_rate:
        o_str = f"{o*100:.2f}%"
        n_str = f"{n_*100:.2f}%"
    elif isinstance(o, float):
        o_str = f"{o:.4f}"
        n_str = f"{n_:.4f}"
    else:
        o_str = f"{o:,}"
        n_str = f"{n_:,}"

    print(f"{label:<35} {o_str:>14} {n_str:>14} {delta_str:>12} {flag:>6}")
    if flag:
        flags.append(label)

if flags:
    print(f"\nFLAGGED (>1pp or materially different): {', '.join(flags)}")
else:
    print(f"\nNo statistics flagged as materially different.")


# ══════════════════════════════════════════════════════════════════════════
# SAVE MASTER SUMMARY
# ══════════════════════════════════════════════════════════════════════════
hdr("SAVING ALL RESULTS")

summary["total_trials"] = n_total
summary["n_models"] = len(models)
summary["models"] = models
summary["n_conditions"] = int(df["condition"].nunique())
summary["n_categories"] = int(df["category"].nunique())
summary["n_assortments"] = int(df["assortment_id"].nunique())

# Make summary JSON-serializable
def make_serializable(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_serializable(i) for i in obj]
    return obj

summary_clean = make_serializable(summary)

with open(os.path.join(OUT, "summary.json"), "w") as f:
    json.dump(summary_clean, f, indent=2)

print(f"\nAll results saved to: {OUT}")
print(f"  summary.json")
print(f"  per_model_rates.csv")
print(f"  category_rates.csv")
print(f"  spec_gap_meta.json")
print(f"  confabulation.json")
print(f"  convergence.json")
print(f"  brand_tax.json")

print("\n" + "=" * 90)
print("  382K REANALYSIS COMPLETE")
print("=" * 90)
