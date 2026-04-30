#!/usr/bin/env python3
"""
STATISTICAL AUDIT (Cycle 7): Independent verification of central claims.
1) Meta-analytic OR = 231.8 [132.8, 404.5]
2) Phase transition breakpoint delta AIC = 1,772
3) Per-model ORs (range 46.5 to 1,921.7), all 17 significant
4) Bonferroni-corrected significance
"""
import csv
import math
import json
import sys
import numpy as np
from collections import defaultdict, Counter
from scipy import stats as sp_stats
import statsmodels.formula.api as smf
import pandas as pd

# ------------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------------
print("=" * 70)
print("INDEPENDENT STATISTICAL AUDIT")
print("=" * 70)

data = []
with open("data/processed/spec_resistance_FULL.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        data.append(r)
print(f"Loaded {len(data):,} rows")

# Specification gradient conditions
spec_conditions = {
    "baseline",
    "utility_vague", "preference_vague",
    "utility_weighted", "preference_weighted",
    "utility_explicit", "preference_explicit",
    "utility_override", "preference_override",
    "utility_constrained", "preference_constrained",
}

# Filter to spec gradient
spec_data = [r for r in data if r["condition"] in spec_conditions]
print(f"Spec gradient subset: {len(spec_data):,} trials")

# Get models
models = sorted(set(r["model_key"] for r in spec_data))
print(f"Models: {len(models)}")
for m in models:
    n = sum(1 for r in spec_data if r["model_key"] == m)
    print(f"  {m}: {n}")

# ------------------------------------------------------------------
# CHECK 1: META-ANALYTIC OR
# ------------------------------------------------------------------
print("\n" + "=" * 70)
print("CHECK 1: META-ANALYTIC OR (claimed: 231.8 [132.8, 404.5])")
print("=" * 70)

model_results = []
log_ors = []
se_log_ors = []
weights_fe = []

for mk in models:
    mk_data = [r for r in spec_data if r["model_key"] == mk]

    # Low spec: ordinal 0, 1, 2
    low = [r for r in mk_data if int(r["condition_ordinal"]) <= 2]
    # High spec: ordinal 3, 4, 5
    high = [r for r in mk_data if int(r["condition_ordinal"]) >= 3]

    a = sum(1 for r in low if r["chose_optimal"] in ("False", False))
    b = sum(1 for r in low if r["chose_optimal"] in ("True", True))
    c = sum(1 for r in high if r["chose_optimal"] in ("False", False))
    d = sum(1 for r in high if r["chose_optimal"] in ("True", True))

    n_low = len(low)
    n_high = len(high)

    assert a + b == n_low, f"{mk}: a+b={a+b} != n_low={n_low}"
    assert c + d == n_high, f"{mk}: c+d={c+d} != n_high={n_high}"

    nonopt_rate_low = a / n_low if n_low > 0 else 0
    nonopt_rate_high = c / n_high if n_high > 0 else 0

    # Haldane correction for zero cells
    if a == 0 or b == 0 or c == 0 or d == 0:
        ac, bc, cc, dc = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    else:
        ac, bc, cc, dc = a, b, c, d

    OR = (ac * dc) / (bc * cc)
    logOR = math.log(OR)
    SE = math.sqrt(1 / ac + 1 / bc + 1 / cc + 1 / dc)
    CI_lo = math.exp(logOR - 1.96 * SE)
    CI_hi = math.exp(logOR + 1.96 * SE)
    z = logOR / SE
    p = 2 * sp_stats.norm.sf(abs(z))

    w_fe = 1 / SE**2

    model_results.append({
        "model": mk, "a": a, "b": b, "c": c, "d": d,
        "n_low": n_low, "n_high": n_high,
        "nonopt_low": nonopt_rate_low, "nonopt_high": nonopt_rate_high,
        "OR": OR, "logOR": logOR, "SE": SE,
        "CI_lo": CI_lo, "CI_hi": CI_hi,
        "z": z, "p": p,
    })
    log_ors.append(logOR)
    se_log_ors.append(SE)
    weights_fe.append(w_fe)

    sig = "*" if p < 0.05 else " "
    print(f"  {mk:28s}: a={a:4d} b={b:4d} c={c:4d} d={d:4d} | "
          f"low={nonopt_rate_low:.4f} high={nonopt_rate_high:.4f} | "
          f"OR={OR:9.2f} [{CI_lo:8.2f}, {CI_hi:10.2f}] p={p:.2e} {sig}")

log_ors = np.array(log_ors)
se_log_ors = np.array(se_log_ors)
w = np.array(weights_fe)

# ----- Fixed-effect pooled estimate -----
fe_logOR = np.sum(w * log_ors) / np.sum(w)
fe_SE = math.sqrt(1 / np.sum(w))
fe_OR = math.exp(fe_logOR)
fe_CI_lo = math.exp(fe_logOR - 1.96 * fe_SE)
fe_CI_hi = math.exp(fe_logOR + 1.96 * fe_SE)
fe_z = fe_logOR / fe_SE
fe_p = 2 * sp_stats.norm.sf(abs(fe_z))

print(f"\n  FIXED-EFFECT: OR = {fe_OR:.2f} [{fe_CI_lo:.2f}, {fe_CI_hi:.2f}], p = {fe_p:.2e}")

# ----- Random-effects (DerSimonian-Laird) -----
Q = np.sum(w * (log_ors - fe_logOR) ** 2)
df_Q = len(models) - 1
Q_p = sp_stats.chi2.sf(Q, df_Q)
I2 = max(0, (Q - df_Q) / Q) * 100

# DL tau-squared
c_dl = np.sum(w) - np.sum(w**2) / np.sum(w)
tau2 = max(0, (Q - df_Q) / c_dl)

# Random-effects weights
w_re = 1 / (se_log_ors**2 + tau2)
re_logOR = np.sum(w_re * log_ors) / np.sum(w_re)
re_SE = math.sqrt(1 / np.sum(w_re))
re_OR = math.exp(re_logOR)
re_CI_lo = math.exp(re_logOR - 1.96 * re_SE)
re_CI_hi = math.exp(re_logOR + 1.96 * re_SE)
re_z = re_logOR / re_SE
re_p = 2 * sp_stats.norm.sf(abs(re_z))

print(f"  RANDOM-EFFECTS (DL): OR = {re_OR:.2f} [{re_CI_lo:.2f}, {re_CI_hi:.2f}], p = {re_p:.2e}")
print(f"  Heterogeneity: Q = {Q:.2f} (df={df_Q}), Q_p = {Q_p:.4f}, I2 = {I2:.1f}%, tau2 = {tau2:.4f}")

# Verify against claimed values
print(f"\n  CLAIMED: OR = 231.8, CI = [132.83, 404.52]")
print(f"  COMPUTED: OR = {re_OR:.1f}, CI = [{re_CI_lo:.2f}, {re_CI_hi:.2f}]")
print(f"  MATCH OR: {'YES' if abs(re_OR - 231.8) < 0.5 else 'NO -- DISCREPANCY'}")
print(f"  MATCH CI_lo: {'YES' if abs(re_CI_lo - 132.83) < 0.5 else 'NO -- DISCREPANCY'}")
print(f"  MATCH CI_hi: {'YES' if abs(re_CI_hi - 404.52) < 0.5 else 'NO -- DISCREPANCY'}")
print(f"  MATCH I2: {'YES' if abs(I2 - 18.2) < 0.5 else 'NO -- DISCREPANCY'}")

# ------------------------------------------------------------------
# CHECK 2: PHASE TRANSITION BREAKPOINT
# ------------------------------------------------------------------
print("\n" + "=" * 70)
print("CHECK 2: PHASE TRANSITION BREAKPOINT (claimed: delta AIC = 1,772)")
print("=" * 70)

rows = []
for r in spec_data:
    ordinal = int(r["condition_ordinal"])
    nonopt = 1 if r["chose_optimal"] in ("False", False) else 0
    rows.append({"non_optimal_int": nonopt, "condition_ordinal": ordinal})

bp_df = pd.DataFrame(rows)
bp_df["is_post"] = (bp_df["condition_ordinal"] >= 3).astype(int)

print(f"  Data: {len(bp_df)} observations")
print(f"  Non-optimal rate by ordinal:")
for o in range(6):
    sub = bp_df[bp_df["condition_ordinal"] == o]
    rate = sub["non_optimal_int"].mean()
    print(f"    Ordinal {o}: {rate:.4f} (n={len(sub)})")

# Linear model
lin_model = smf.logit("non_optimal_int ~ condition_ordinal", data=bp_df).fit(disp=0)
print(f"\n  LINEAR model:")
print(f"    AIC = {lin_model.aic:.1f}")
print(f"    LL  = {lin_model.llf:.2f}")

# Piecewise model (linear + breakpoint indicator at ordinal >= 3)
bp_model = smf.logit("non_optimal_int ~ condition_ordinal + is_post", data=bp_df).fit(disp=0)
print(f"\n  PIECEWISE model (breakpoint at ordinal=3):")
print(f"    AIC = {bp_model.aic:.1f}")
print(f"    LL  = {bp_model.llf:.2f}")
print(f"    is_post coef = {bp_model.params['is_post']:.4f}")
print(f"    is_post OR = {math.exp(bp_model.params['is_post']):.4f}")

delta_AIC = lin_model.aic - bp_model.aic
LRT_chi2 = 2 * (bp_model.llf - lin_model.llf)
LRT_p = sp_stats.chi2.sf(LRT_chi2, df=1)

print(f"\n  Delta AIC (linear - piecewise) = {delta_AIC:.1f}")
print(f"  LRT chi2 = {LRT_chi2:.2f}, df=1, p = {LRT_p:.2e}")

print(f"\n  CLAIMED: delta AIC = 1772.3, LRT chi2 = 1774.31")
print(f"  COMPUTED: delta AIC = {delta_AIC:.1f}, LRT chi2 = {LRT_chi2:.2f}")
print(f"  MATCH delta_AIC: {'YES' if abs(delta_AIC - 1772.3) < 1.0 else 'NO -- DISCREPANCY'}")
print(f"  MATCH LRT: {'YES' if abs(LRT_chi2 - 1774.31) < 1.0 else 'NO -- DISCREPANCY'}")

# ------ TEST ALTERNATIVE BREAKPOINTS ------
print(f"\n  Testing alternative breakpoints to confirm ordinal=3 is optimal:")
best_bp = None
best_dAIC = -float("inf")
for bp in range(1, 6):
    bp_df_alt = bp_df.copy()
    bp_df_alt["is_post_alt"] = (bp_df_alt["condition_ordinal"] >= bp).astype(int)
    try:
        alt_model = smf.logit("non_optimal_int ~ condition_ordinal + is_post_alt", data=bp_df_alt).fit(disp=0)
        dAIC = lin_model.aic - alt_model.aic
        marker = " <-- BEST" if dAIC > best_dAIC else ""
        if dAIC > best_dAIC:
            best_dAIC = dAIC
            best_bp = bp
        print(f"    Breakpoint at ordinal >= {bp}: AIC = {alt_model.aic:.1f}, delta_AIC = {dAIC:.1f}{marker}")
    except Exception as e:
        print(f"    Breakpoint at ordinal >= {bp}: FAILED ({e})")

print(f"  Best breakpoint: ordinal >= {best_bp} (delta_AIC = {best_dAIC:.1f})")
print(f"  Breakpoint at 3 is optimal: {'YES' if best_bp == 3 else 'NO -- different breakpoint fits better'}")

# ------------------------------------------------------------------
# CHECK 3: INDIVIDUAL MODEL ORs
# ------------------------------------------------------------------
print("\n" + "=" * 70)
print("CHECK 3: PER-MODEL OR RANGE AND CELL COUNTS")
print("=" * 70)

sorted_by_or = sorted(model_results, key=lambda x: x["OR"])
print(f"  MINIMUM OR: {sorted_by_or[0]['model']} = {sorted_by_or[0]['OR']:.1f}")
print(f"  MAXIMUM OR: {sorted_by_or[-1]['model']} = {sorted_by_or[-1]['OR']:.1f}")
print(f"  CLAIMED: min=46.5 (Gemini 3 Flash), max=1921.7 (Qwen 72B)")
print(f"  MATCH min: {'YES' if abs(sorted_by_or[0]['OR'] - 46.48) < 0.5 else 'NO -- DISCREPANCY'}")
print(f"  MATCH max: {'YES' if abs(sorted_by_or[-1]['OR'] - 1921.69) < 0.5 else 'NO -- DISCREPANCY'}")

# Check for zero cells
print(f"\n  Models with zero cells (Haldane 0.5 correction applied):")
n_zero = 0
for mr in model_results:
    if mr["c"] == 0 or mr["d"] == 0 or mr["a"] == 0 or mr["b"] == 0:
        zero_cells = []
        if mr["a"] == 0: zero_cells.append("a(nonopt_low)")
        if mr["b"] == 0: zero_cells.append("b(opt_low)")
        if mr["c"] == 0: zero_cells.append("c(nonopt_high)")
        if mr["d"] == 0: zero_cells.append("d(opt_high)")
        n_zero += 1
        print(f"    {mr['model']:28s}: zeros in {', '.join(zero_cells)} | "
              f"cells=[{mr['a']}, {mr['b']}, {mr['c']}, {mr['d']}]")
print(f"  Total models with zero cells: {n_zero}/{len(models)}")

# Extremely wide CIs
print(f"\n  Models with CI width ratio > 100:")
for mr in model_results:
    width = mr["CI_hi"] / mr["CI_lo"] if mr["CI_lo"] > 0 else float("inf")
    if width > 100:
        print(f"    {mr['model']:28s}: OR={mr['OR']:.1f} [{mr['CI_lo']:.1f}, {mr['CI_hi']:.1f}] ratio={width:.0f}")

# Weight contribution
print(f"\n  Meta-analytic weights (random effects):")
w_re_arr = 1 / (se_log_ors**2 + tau2)
total_w = w_re_arr.sum()
for i, mk in enumerate(models):
    pct = w_re_arr[i] / total_w * 100
    print(f"    {mk:28s}: weight={w_re_arr[i]:.4f} ({pct:.1f}%)")

# ------------------------------------------------------------------
# CHECK 4: ALL 17/17 SIGNIFICANT (Bonferroni & Holm)
# ------------------------------------------------------------------
print("\n" + "=" * 70)
print("CHECK 4: ALL 17/17 SIGNIFICANT (with multiple testing correction)")
print("=" * 70)

p_values = [(mr["model"], mr["p"]) for mr in model_results]
p_values.sort(key=lambda x: -x[1])

bonferroni_threshold = 0.05 / len(models)
print(f"  Bonferroni threshold: alpha = 0.05/{len(models)} = {bonferroni_threshold:.5f}")

n_sig_nominal = sum(1 for _, p in p_values if p < 0.05)
n_sig_bonf = sum(1 for _, p in p_values if p < bonferroni_threshold)

print(f"  Significant at p<0.05: {n_sig_nominal}/{len(models)}")
print(f"  Significant at Bonferroni p<{bonferroni_threshold:.5f}: {n_sig_bonf}/{len(models)}")

print(f"\n  All p-values (highest to lowest):")
for mk, p in p_values:
    sig_nom = "p<0.05" if p < 0.05 else "n.s."
    sig_bonf = "p<Bonf" if p < bonferroni_threshold else ""
    print(f"    {mk:28s}: p = {p:.4e}  {sig_nom}  {sig_bonf}")

weakest = p_values[0]
print(f"\n  WEAKEST p-value: {weakest[0]} at p = {weakest[1]:.4e}")
print(f"  Survives Bonferroni: {'YES' if weakest[1] < bonferroni_threshold else 'NO'}")

# Holm-Bonferroni
print(f"\n  Holm-Bonferroni sequential test:")
sorted_asc = sorted(p_values, key=lambda x: x[1])
all_pass_holm = True
for rank, (mk, p) in enumerate(sorted_asc, 1):
    threshold = 0.05 / (len(models) - rank + 1)
    passes = p < threshold
    if not passes:
        all_pass_holm = False
    print(f"    Rank {rank:2d}: {mk:28s} p={p:.4e} < {threshold:.5f}? {'YES' if passes else 'NO'}")

print(f"  All pass Holm-Bonferroni: {'YES' if all_pass_holm else 'NO'}")

# ------------------------------------------------------------------
# SENSITIVITY: Paule-Mandel estimator
# ------------------------------------------------------------------
print("\n" + "=" * 70)
print("SENSITIVITY: Alternative tau2 estimators")
print("=" * 70)

def paule_mandel_tau2(log_ors_arr, se_arr, Q_start, df_start, c_start, max_iter=200, tol=1e-8):
    k = len(log_ors_arr)
    tau2_est = max(0, (Q_start - df_start) / c_start)
    for _ in range(max_iter):
        w_pm = 1 / (se_arr**2 + tau2_est)
        mu = np.sum(w_pm * log_ors_arr) / np.sum(w_pm)
        Q_pm = np.sum(w_pm * (log_ors_arr - mu) ** 2)
        if abs(Q_pm - (k - 1)) < tol:
            break
        dQ = -np.sum(w_pm**2 * (log_ors_arr - mu) ** 2)
        dQ += (np.sum(w_pm**2 * (log_ors_arr - mu))) ** 2 / np.sum(w_pm)
        if abs(dQ) < 1e-12:
            break
        tau2_est = tau2_est - (Q_pm - (k - 1)) / dQ
        tau2_est = max(0, tau2_est)
    return tau2_est

tau2_pm = paule_mandel_tau2(log_ors, se_log_ors, Q, df_Q, c_dl)
w_pm = 1 / (se_log_ors**2 + tau2_pm)
pm_logOR = np.sum(w_pm * log_ors) / np.sum(w_pm)
pm_SE = math.sqrt(1 / np.sum(w_pm))
pm_OR = math.exp(pm_logOR)
pm_CI_lo = math.exp(pm_logOR - 1.96 * pm_SE)
pm_CI_hi = math.exp(pm_logOR + 1.96 * pm_SE)

print(f"  DerSimonian-Laird: tau2 = {tau2:.4f}, OR = {re_OR:.1f} [{re_CI_lo:.1f}, {re_CI_hi:.1f}]")
print(f"  Paule-Mandel:      tau2 = {tau2_pm:.4f}, OR = {pm_OR:.1f} [{pm_CI_lo:.1f}, {pm_CI_hi:.1f}]")
print(f"  Sensitivity: estimates {'stable' if abs(re_OR - pm_OR) / re_OR < 0.10 else 'DIVERGE'} across estimators")

# ------------------------------------------------------------------
# BONUS: Aggregate Weighted->Explicit transition OR
# ------------------------------------------------------------------
print("\n" + "=" * 70)
print("BONUS: AGGREGATE Weighted->Explicit transition OR")
print("=" * 70)

w_data = [r for r in spec_data if int(r["condition_ordinal"]) == 2]
e_data = [r for r in spec_data if int(r["condition_ordinal"]) == 3]

a_we = sum(1 for r in w_data if r["chose_optimal"] in ("False", False))
b_we = sum(1 for r in w_data if r["chose_optimal"] in ("True", True))
c_we = sum(1 for r in e_data if r["chose_optimal"] in ("False", False))
d_we = sum(1 for r in e_data if r["chose_optimal"] in ("True", True))

print(f"  Weighted: {a_we} nonopt / {b_we} opt (n={len(w_data)}, rate={a_we / len(w_data):.4f})")
print(f"  Explicit: {c_we} nonopt / {d_we} opt (n={len(e_data)}, rate={c_we / len(e_data):.4f})")

OR_we = (a_we * d_we) / (b_we * c_we) if c_we > 0 and b_we > 0 else float("inf")
print(f"  Aggregate W->E OR = {OR_we:.2f}")
print(f"  CLAIMED in transition table: 170.71")

# Raw breakdown at EXPLICIT
print(f"\n  Raw breakdown at EXPLICIT (ordinal=3) per model:")
for mk in models:
    e_mk = [r for r in spec_data if r["model_key"] == mk and int(r["condition_ordinal"]) == 3]
    nonopt_mk = sum(1 for r in e_mk if r["chose_optimal"] in ("False", False))
    print(f"    {mk:28s}: n={len(e_mk):4d}, nonopt={nonopt_mk}")

# ------------------------------------------------------------------
# SENSITIVITY: Leave-one-out meta-analysis
# ------------------------------------------------------------------
print("\n" + "=" * 70)
print("SENSITIVITY: Leave-one-out meta-analysis")
print("=" * 70)

for exclude_i, exclude_mk in enumerate(models):
    loo_logors = np.delete(log_ors, exclude_i)
    loo_ses = np.delete(se_log_ors, exclude_i)
    loo_w = 1 / loo_ses**2
    loo_fe_logOR = np.sum(loo_w * loo_logors) / np.sum(loo_w)
    loo_Q = np.sum(loo_w * (loo_logors - loo_fe_logOR) ** 2)
    loo_df = len(loo_logors) - 1
    loo_cdl = np.sum(loo_w) - np.sum(loo_w**2) / np.sum(loo_w)
    loo_tau2 = max(0, (loo_Q - loo_df) / loo_cdl)
    loo_wre = 1 / (loo_ses**2 + loo_tau2)
    loo_re_logOR = np.sum(loo_wre * loo_logors) / np.sum(loo_wre)
    loo_re_SE = math.sqrt(1 / np.sum(loo_wre))
    loo_re_OR = math.exp(loo_re_logOR)
    loo_CI_lo = math.exp(loo_re_logOR - 1.96 * loo_re_SE)
    loo_CI_hi = math.exp(loo_re_logOR + 1.96 * loo_re_SE)
    pct_change = (loo_re_OR - re_OR) / re_OR * 100
    print(f"  Exclude {exclude_mk:28s}: OR = {loo_re_OR:7.1f} [{loo_CI_lo:6.1f}, {loo_CI_hi:7.1f}] (change: {pct_change:+.1f}%)")

print("\n" + "=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
