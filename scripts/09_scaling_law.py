#!/usr/bin/env python3
"""
Analysis 9: Memorization Scaling Law
=====================================
Tests whether brand preference follows Carlini's memorization scaling law:
    log(non_optimal_rate) = alpha + beta * log(model_params)

Hypothesis: beta > 0 implies inverse capability scaling (larger models
show MORE brand preference, i.e., more non-optimal choices).

Uses the full experiment dataset (148K trials, 18 models).
"""

import csv
import os
import sys
import json
import numpy as np
from collections import defaultdict

# Output directory
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.dirname(BASE)
OUT = os.path.join(BASE, "results", "09-scaling-law")
DATA_CSV = os.path.join(PROJ, "data", "processed", "spec_resistance_FULL.csv")

os.makedirs(OUT, exist_ok=True)

# ===================================================================
# MODEL PARAMETER ESTIMATES (billions)
# ===================================================================
MODEL_PARAMS = {
    "gpt-4.1-nano":         2,
    "gpt-4o-mini":          8,
    "gpt-4.1-mini":         8,
    "gpt-5-mini":           8,
    "claude-haiku-4.5":     20,
    "gemma-3-27b":          27,
    "gemini-2.0-flash":     30,
    "gemini-2.5-flash-lite": 20,
    "gemini-2.5-flash":     40,
    "gemini-3-flash":       40,
    "llama-3.3-70b":        70,
    "qwen-2.5-72b":        72,
    "gpt-4o":              200,
    "claude-sonnet-4.6":   200,
    "gemini-2.5-pro":      200,
    "deepseek-v3":         671,
    "deepseek-r1":         671,
    "kimi-k2":             200,
}

# Provider families for within-family analysis
PROVIDER_FAMILIES = {
    "OpenAI": ["gpt-4.1-nano", "gpt-4o-mini", "gpt-4.1-mini", "gpt-5-mini", "gpt-4o"],
    "Anthropic": ["claude-haiku-4.5", "claude-sonnet-4.6"],
    "Google": ["gemini-2.0-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash",
               "gemini-2.5-pro", "gemini-3-flash", "gemma-3-27b"],
    "OpenRouter": ["llama-3.3-70b", "qwen-2.5-72b", "deepseek-v3", "deepseek-r1", "kimi-k2"],
}

# ===================================================================
# LOAD DATA
# ===================================================================
print("Loading experiment data...")
model_stats = defaultdict(lambda: {"total": 0, "non_optimal": 0})
baseline_stats = defaultdict(lambda: {"total": 0, "non_optimal": 0})

with open(DATA_CSV, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        mk = row["model_key"]
        opt = row["chose_optimal"] == "True"
        model_stats[mk]["total"] += 1
        if not opt:
            model_stats[mk]["non_optimal"] += 1
        # Baseline condition only
        if row["condition"] == "baseline":
            baseline_stats[mk]["total"] += 1
            if not opt:
                baseline_stats[mk]["non_optimal"] += 1

print(f"  Loaded {sum(s['total'] for s in model_stats.values())} trials across {len(model_stats)} models")

# ===================================================================
# COMPUTE NON-OPTIMAL RATES
# ===================================================================
results = []
for mk in sorted(model_stats.keys()):
    if mk not in MODEL_PARAMS:
        print(f"  WARNING: No param count for {mk}, skipping")
        continue
    s = model_stats[mk]
    rate = s["non_optimal"] / s["total"]
    bs = baseline_stats[mk]
    baseline_rate = bs["non_optimal"] / bs["total"] if bs["total"] > 0 else None
    results.append({
        "model": mk,
        "params_B": MODEL_PARAMS[mk],
        "total_trials": s["total"],
        "non_optimal": s["non_optimal"],
        "non_optimal_rate": rate,
        "baseline_trials": bs["total"],
        "baseline_non_optimal": bs["non_optimal"],
        "baseline_rate": baseline_rate,
    })

print("\nModel statistics:")
print(f"{'Model':30s} {'Params(B)':>10s} {'Trials':>8s} {'Non-Opt':>8s} {'Rate':>8s} {'BL Rate':>8s}")
print("-" * 85)
for r in sorted(results, key=lambda x: x["params_B"]):
    bl = f"{r['baseline_rate']:.3f}" if r['baseline_rate'] is not None else "N/A"
    print(f"{r['model']:30s} {r['params_B']:>10d} {r['total_trials']:>8d} {r['non_optimal']:>8d} {r['non_optimal_rate']:>8.4f} {bl:>8s}")

# ===================================================================
# SCALING LAW REGRESSION (ALL MODELS)
# ===================================================================
from scipy import stats as sp_stats

# Filter to models with enough data (at least 1000 trials)
valid = [r for r in results if r["total_trials"] >= 1000]
print(f"\nModels with >= 1000 trials: {len(valid)}")

# Overall non-optimal rate
log_params = np.array([np.log(r["params_B"]) for r in valid])
log_rates = np.array([np.log(r["non_optimal_rate"]) for r in valid])
rates = np.array([r["non_optimal_rate"] for r in valid])
params = np.array([r["params_B"] for r in valid])

# OLS: log(non_optimal_rate) = alpha + beta * log(params)
slope, intercept, r_value, p_value, std_err = sp_stats.linregress(log_params, log_rates)

print("\n" + "=" * 70)
print("SCALING LAW REGRESSION: log(non_opt_rate) = alpha + beta * log(params)")
print("=" * 70)
print(f"  alpha (intercept) = {intercept:.4f}")
print(f"  beta (slope)      = {slope:.4f} (SE = {std_err:.4f})")
print(f"  R-squared         = {r_value**2:.4f}")
print(f"  p-value (beta)    = {p_value:.6f}")
print(f"  95% CI for beta   = [{slope - 1.96*std_err:.4f}, {slope + 1.96*std_err:.4f}]")
print(f"  N models          = {len(valid)}")
print()
if slope > 0 and p_value < 0.05:
    print("  ==> INVERSE CAPABILITY SCALING: larger models have HIGHER non-optimal rates")
elif slope < 0 and p_value < 0.05:
    print("  ==> CAPABILITY SCALING: larger models have LOWER non-optimal rates")
else:
    print("  ==> NO SIGNIFICANT SCALING RELATIONSHIP")

# Baseline-only regression
valid_bl = [r for r in valid if r["baseline_rate"] is not None and r["baseline_rate"] > 0]
if len(valid_bl) >= 3:
    log_params_bl = np.array([np.log(r["params_B"]) for r in valid_bl])
    log_rates_bl = np.array([np.log(r["baseline_rate"]) for r in valid_bl])

    slope_bl, intercept_bl, r_bl, p_bl, se_bl = sp_stats.linregress(log_params_bl, log_rates_bl)
    print("\n" + "-" * 70)
    print("BASELINE-ONLY: log(baseline_non_opt_rate) = alpha + beta * log(params)")
    print("-" * 70)
    print(f"  alpha (intercept) = {intercept_bl:.4f}")
    print(f"  beta (slope)      = {slope_bl:.4f} (SE = {se_bl:.4f})")
    print(f"  R-squared         = {r_bl**2:.4f}")
    print(f"  p-value (beta)    = {p_bl:.6f}")
    print(f"  95% CI for beta   = [{slope_bl - 1.96*se_bl:.4f}, {slope_bl + 1.96*se_bl:.4f}]")
    print(f"  N models          = {len(valid_bl)}")

# ===================================================================
# WITHIN-FAMILY REGRESSIONS
# ===================================================================
print("\n" + "=" * 70)
print("WITHIN-PROVIDER FAMILY REGRESSIONS")
print("=" * 70)

family_results = {}
for family, models in PROVIDER_FAMILIES.items():
    fam_data = [r for r in results if r["model"] in models and r["total_trials"] >= 500]
    if len(fam_data) < 2:
        print(f"\n{family}: Insufficient models (need >= 2, have {len(fam_data)})")
        continue

    lp = np.array([np.log(r["params_B"]) for r in fam_data])
    lr = np.array([np.log(r["non_optimal_rate"]) for r in fam_data])

    if len(fam_data) >= 3:
        s, i, rv, pv, se = sp_stats.linregress(lp, lr)
    else:
        # With 2 points, perfect fit (no p-value)
        s = (lr[1] - lr[0]) / (lp[1] - lp[0]) if lp[1] != lp[0] else 0
        i = lr[0] - s * lp[0]
        rv = 1.0
        pv = float("nan")
        se = float("nan")

    family_results[family] = {
        "slope": s, "intercept": i, "r_squared": rv**2,
        "p_value": pv, "se": se, "n": len(fam_data),
        "models": [(r["model"], r["params_B"], r["non_optimal_rate"]) for r in fam_data]
    }

    print(f"\n{family} ({len(fam_data)} models):")
    for r in fam_data:
        print(f"  {r['model']:25s} {r['params_B']:>6d}B  rate={r['non_optimal_rate']:.4f}")
    print(f"  beta = {s:.4f}", end="")
    if not np.isnan(pv):
        print(f"  (p = {pv:.4f}, R2 = {rv**2:.4f})")
    else:
        print(f"  (2 points, R2 = {rv**2:.4f})")

# ===================================================================
# SPEARMAN RANK CORRELATION (robust, non-parametric)
# ===================================================================
rho, p_rho = sp_stats.spearmanr(params, rates)
print("\n" + "-" * 70)
print("SPEARMAN RANK CORRELATION (non-parametric)")
print("-" * 70)
print(f"  rho      = {rho:.4f}")
print(f"  p-value  = {p_rho:.6f}")
print(f"  N models = {len(valid)}")

# ===================================================================
# GENERATE FIGURES
# ===================================================================
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# Style
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.linewidth": 0.8,
    "figure.dpi": 300,
})

# Color map by provider
PROVIDER_COLORS = {
    "OpenAI": "#10a37f",
    "Anthropic": "#d97706",
    "Google": "#4285f4",
    "OpenRouter": "#ef4444",
}

def get_provider(mk):
    for fam, models in PROVIDER_FAMILIES.items():
        if mk in models:
            return fam
    return "Other"

# ----- Figure 1: Log-log scaling plot -----
fig, ax = plt.subplots(figsize=(8, 5.5))

for r in valid:
    prov = get_provider(r["model"])
    color = PROVIDER_COLORS.get(prov, "gray")
    size = max(30, min(200, r["total_trials"] / 100))
    ax.scatter(r["params_B"], r["non_optimal_rate"],
               c=color, s=size, alpha=0.8, zorder=5, edgecolors="white", linewidth=0.5)
    # Label
    label = r["model"].replace("gpt-", "").replace("claude-", "").replace("gemini-", "gem-").replace("gemma-", "gma-")
    ax.annotate(label, (r["params_B"], r["non_optimal_rate"]),
                fontsize=6.5, ha="center", va="bottom",
                xytext=(0, 6), textcoords="offset points")

# Regression line
x_line = np.logspace(np.log10(1.5), np.log10(800), 100)
y_line = np.exp(intercept) * x_line ** slope
ax.plot(x_line, y_line, "k--", alpha=0.5, linewidth=1.5,
        label=f"$\\beta$ = {slope:.3f} (p = {p_value:.3f})")

ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Estimated Parameters (Billions)", fontsize=12)
ax.set_ylabel("Non-Optimal Choice Rate", fontsize=12)
ax.set_title("Memorization Scaling Law: Brand Preference vs. Model Size", fontsize=13, fontweight="bold")

# Format y-axis as percentages
ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.0%}" if y >= 0.01 else f"{y:.1%}"))

# Legend for providers
for prov, color in PROVIDER_COLORS.items():
    ax.scatter([], [], c=color, s=60, label=prov, edgecolors="white", linewidth=0.5)
ax.legend(fontsize=8, loc="upper left", framealpha=0.9)

# Annotation box
textstr = (f"$\\log(rate) = {intercept:.2f} + {slope:.3f} \\cdot \\log(params)$\n"
           f"$R^2 = {r_value**2:.3f}$, $p = {p_value:.4f}$\n"
           f"Spearman $\\rho = {rho:.3f}$ ($p = {p_rho:.4f}$)")
props = dict(boxstyle="round,pad=0.4", facecolor="lightyellow", alpha=0.8)
ax.text(0.97, 0.03, textstr, transform=ax.transAxes, fontsize=8,
        verticalalignment="bottom", horizontalalignment="right", bbox=props)

plt.tight_layout()
fig.savefig(os.path.join(OUT, "scaling_law_loglog.png"), dpi=300, bbox_inches="tight")
fig.savefig(os.path.join(OUT, "scaling_law_loglog.pdf"), bbox_inches="tight")
plt.close(fig)
print(f"\nSaved: scaling_law_loglog.png/pdf")

# ----- Figure 2: Within-family comparisons -----
fig, axes = plt.subplots(2, 2, figsize=(10, 8))

for idx, (family, info) in enumerate(sorted(family_results.items())):
    ax = axes[idx // 2][idx % 2]
    models_data = info["models"]
    x_vals = [m[1] for m in models_data]
    y_vals = [m[2] for m in models_data]
    names = [m[0] for m in models_data]

    color = PROVIDER_COLORS.get(family, "gray")
    ax.scatter(x_vals, y_vals, c=color, s=80, zorder=5, edgecolors="white", linewidth=0.5)

    for name, x, y in zip(names, x_vals, y_vals):
        short = name.replace("gpt-", "").replace("claude-", "").replace("gemini-", "gem-").replace("gemma-", "gma-").replace("deepseek-", "ds-").replace("qwen-", "qw-").replace("llama-", "ll-")
        ax.annotate(short, (x, y), fontsize=7, ha="center", va="bottom",
                    xytext=(0, 6), textcoords="offset points")

    # Regression line if >= 2 points
    if len(models_data) >= 2:
        x_arr = np.array(x_vals)
        y_pred = np.exp(info["intercept"]) * x_arr ** info["slope"]
        sort_idx = np.argsort(x_arr)
        ax.plot(x_arr[sort_idx], y_pred[sort_idx], "--", color=color, alpha=0.5, linewidth=1.5)

    ax.set_xscale("log")
    p_str = f"p={info['p_value']:.3f}" if not np.isnan(info["p_value"]) else "2 pts"
    ax.set_title(f"{family} (beta={info['slope']:.3f}, {p_str})", fontsize=10, fontweight="bold")
    ax.set_xlabel("Parameters (B)")
    ax.set_ylabel("Non-Optimal Rate")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.0%}"))

plt.suptitle("Within-Provider Scaling Analysis", fontsize=13, fontweight="bold", y=1.01)
plt.tight_layout()
fig.savefig(os.path.join(OUT, "scaling_law_families.png"), dpi=300, bbox_inches="tight")
fig.savefig(os.path.join(OUT, "scaling_law_families.pdf"), bbox_inches="tight")
plt.close(fig)
print(f"Saved: scaling_law_families.png/pdf")

# ----- Figure 3: Residual plot -----
fig, ax = plt.subplots(figsize=(7, 4.5))

predicted = intercept + slope * log_params
residuals = log_rates - predicted

for i, r in enumerate(valid):
    prov = get_provider(r["model"])
    color = PROVIDER_COLORS.get(prov, "gray")
    ax.scatter(r["params_B"], residuals[i], c=color, s=60, alpha=0.8,
               edgecolors="white", linewidth=0.5)
    label = r["model"].replace("gpt-", "").replace("claude-", "").replace("gemini-", "gem-").replace("gemma-", "gma-")
    ax.annotate(label, (r["params_B"], residuals[i]),
                fontsize=6, ha="center", va="bottom",
                xytext=(0, 5), textcoords="offset points")

ax.axhline(0, color="black", linewidth=0.5, linestyle="--")
ax.set_xscale("log")
ax.set_xlabel("Estimated Parameters (Billions)", fontsize=11)
ax.set_ylabel("Residual (log scale)", fontsize=11)
ax.set_title("Scaling Law Residuals", fontsize=12, fontweight="bold")
plt.tight_layout()
fig.savefig(os.path.join(OUT, "scaling_law_residuals.png"), dpi=300, bbox_inches="tight")
fig.savefig(os.path.join(OUT, "scaling_law_residuals.pdf"), bbox_inches="tight")
plt.close(fig)
print(f"Saved: scaling_law_residuals.png/pdf")

# ===================================================================
# SAVE RESULTS
# ===================================================================
output = {
    "overall_regression": {
        "equation": "log(non_optimal_rate) = alpha + beta * log(params_B)",
        "alpha": float(intercept),
        "beta": float(slope),
        "beta_se": float(std_err),
        "beta_95ci": [float(slope - 1.96 * std_err), float(slope + 1.96 * std_err)],
        "r_squared": float(r_value**2),
        "p_value": float(p_value),
        "n_models": len(valid),
        "interpretation": "Inverse capability scaling" if slope > 0 and p_value < 0.05 else
                         "Capability scaling" if slope < 0 and p_value < 0.05 else
                         "No significant relationship",
    },
    "spearman": {
        "rho": float(rho),
        "p_value": float(p_rho),
        "n": len(valid),
    },
    "baseline_regression": {
        "alpha": float(intercept_bl) if len(valid_bl) >= 3 else None,
        "beta": float(slope_bl) if len(valid_bl) >= 3 else None,
        "r_squared": float(r_bl**2) if len(valid_bl) >= 3 else None,
        "p_value": float(p_bl) if len(valid_bl) >= 3 else None,
        "n_models": len(valid_bl),
    },
    "within_family": {},
    "model_data": [],
}

for family, info in family_results.items():
    output["within_family"][family] = {
        "beta": float(info["slope"]),
        "r_squared": float(info["r_squared"]),
        "p_value": float(info["p_value"]) if not np.isnan(info["p_value"]) else None,
        "n_models": info["n"],
        "models": [(m[0], m[1], round(m[2], 5)) for m in info["models"]],
    }

for r in results:
    output["model_data"].append({
        "model": r["model"],
        "params_B": r["params_B"],
        "total_trials": r["total_trials"],
        "non_optimal_rate": round(r["non_optimal_rate"], 5),
        "baseline_rate": round(r["baseline_rate"], 5) if r["baseline_rate"] is not None else None,
    })

with open(os.path.join(OUT, "scaling_law_results.json"), "w") as f:
    json.dump(output, f, indent=2)
print(f"\nSaved: scaling_law_results.json")

print("\n" + "=" * 70)
print("ANALYSIS 9 COMPLETE")
print("=" * 70)
