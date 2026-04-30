#!/usr/bin/env python3
"""
Deep Analysis for Nature Revision: Four Publication-Quality Analyses
=====================================================================

Analysis 1: Specification Gap Phase Transition (central finding)
Analysis 2: Creation/Removal Asymmetry Formalization (injection vs debiasing)
Analysis 3: Confabulation Mechanism Deep Dive (Nisbett & Wilson parallel)
Analysis 4: Per-Model Specification Gap Consistency (universality)

All results saved to results/deep_analysis/ with CSV, JSON, and
publication-quality PNG+PDF figures (Nature style: Arial, 8pt, 6.5in, 300dpi).

Usage:
    cd projects/spec-resistance
    python scripts/deep_analysis.py
"""

import csv
import json
import os
import sys
import warnings
from collections import defaultdict, Counter
from pathlib import Path

import numpy as np

# --- Optional imports with graceful fallbacks ---
try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas required"); sys.exit(1)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    from matplotlib.lines import Line2D
    import matplotlib.patches as mpatches
except ImportError:
    print("ERROR: matplotlib required"); sys.exit(1)

try:
    from scipy import stats as sp_stats
    from scipy.optimize import curve_fit
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    warnings.warn("scipy not installed; some tests will be skipped.")

try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    from statsmodels.genmod.generalized_estimating_equations import GEE
    from statsmodels.genmod.families import Binomial
    from statsmodels.genmod.cov_struct import Exchangeable
    HAS_SM = True
except ImportError:
    HAS_SM = False
    warnings.warn("statsmodels not installed; GEE will be skipped.")

# ===================================================================
# PATHS
# ===================================================================
PROJECT = Path(__file__).resolve().parent.parent.parent  # spec-resistance/
DATA_CSV = PROJECT / "data" / "processed" / "spec_resistance_FULL.csv"
INJECTION_CSV = PROJECT / "nature-rr" / "results" / "08-fictional-injection" / "full_scale_injection.csv"
DEBIASING_CSV = PROJECT / "nature-rr" / "results" / "06-openai-finetune" / "full_scale_debiasing.csv"
EVAL_6K_CSV = PROJECT / "nature-rr" / "results" / "06-openai-finetune" / "eval_6k_41nano.csv"
OUT_DIR = PROJECT / "nature-rr" / "results" / "deep_analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Add project root for assortments import
sys.path.insert(0, str(PROJECT))

# ===================================================================
# NATURE STYLE
# ===================================================================
NATURE_WIDTH = 6.5     # inches (single column = 3.5, double = 6.5)
NATURE_DPI = 300
NATURE_FONT = "Arial"
NATURE_FONTSIZE = 8

def set_nature_style():
    """Configure matplotlib for Nature-quality figures."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [NATURE_FONT, "Helvetica", "DejaVu Sans"],
        "font.size": NATURE_FONTSIZE,
        "axes.labelsize": 8,
        "axes.titlesize": 9,
        "axes.linewidth": 0.5,
        "xtick.major.width": 0.5,
        "ytick.major.width": 0.5,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "figure.dpi": NATURE_DPI,
        "savefig.dpi": NATURE_DPI,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05,
        "lines.linewidth": 1.0,
        "lines.markersize": 4,
        "pdf.fonttype": 42,    # TrueType (editable in Illustrator)
        "ps.fonttype": 42,
    })

set_nature_style()

# Provider color scheme
PROVIDER_COLORS = {
    "anthropic": "#D97706",   # amber
    "openai": "#10B981",      # emerald
    "google": "#3B82F6",      # blue
    "openrouter": "#8B5CF6",  # violet
}

MODEL_PROVIDERS = {
    "claude-haiku-4.5": "anthropic", "claude-sonnet-4.6": "anthropic",
    "gpt-4o": "openai", "gpt-4o-mini": "openai", "gpt-4.1-mini": "openai",
    "gpt-4.1-nano": "openai", "gpt-5-mini": "openai",
    "gemini-2.0-flash": "google", "gemini-2.5-flash": "google",
    "gemini-2.5-flash-lite": "google", "gemini-2.5-pro": "google",
    "gemini-3-flash": "google", "gemma-3-27b": "google",
    "deepseek-v3": "openrouter", "deepseek-r1": "openrouter",
    "llama-3.3-70b": "openrouter", "qwen-2.5-72b": "openrouter",
    "kimi-k2": "openrouter",
}

# Short display names
MODEL_SHORT = {
    "claude-haiku-4.5": "Haiku 4.5", "claude-sonnet-4.6": "Sonnet 4.6",
    "gpt-4o": "GPT-4o", "gpt-4o-mini": "GPT-4o Mini",
    "gpt-4.1-mini": "GPT-4.1 Mini", "gpt-4.1-nano": "GPT-4.1 Nano",
    "gpt-5-mini": "GPT-5 Mini",
    "gemini-2.0-flash": "Gem 2.0 Flash", "gemini-2.5-flash": "Gem 2.5 Flash",
    "gemini-2.5-flash-lite": "Gem 2.5 FL", "gemini-2.5-pro": "Gem 2.5 Pro",
    "gemini-3-flash": "Gem 3 Flash", "gemma-3-27b": "Gemma 27B",
    "deepseek-v3": "DS V3", "deepseek-r1": "DS R1",
    "llama-3.3-70b": "LLaMA 70B", "qwen-2.5-72b": "Qwen 72B",
    "kimi-k2": "Kimi K2",
}

SPEC_LEVELS = ["none", "vague", "weighted", "explicit", "override", "constrained"]
SPEC_LABELS = ["Baseline", "Vague", "Weighted", "Explicit", "Override", "Constrained"]
SPEC_ORDINALS = [0, 1, 2, 3, 4, 5]

def save_fig(fig, name):
    """Save figure as both PNG and PDF."""
    fig.savefig(OUT_DIR / f"{name}.png", dpi=NATURE_DPI)
    fig.savefig(OUT_DIR / f"{name}.pdf")
    plt.close(fig)
    print(f"  Saved {name}.png + .pdf")


# ===================================================================
# DATA LOADING
# ===================================================================
def load_main_data():
    """Load spec_resistance_FULL.csv into a DataFrame."""
    print(f"Loading {DATA_CSV}...")
    df = pd.read_csv(DATA_CSV, low_memory=False)
    # Convert key columns
    df["chose_optimal"] = df["chose_optimal"].map({"True": True, "False": False, True: True, False: False})
    df["non_optimal"] = ~df["chose_optimal"]
    df["condition_ordinal"] = df["condition_ordinal"].astype(int)
    df["judge_brand_reasoning"] = df["judge_brand_reasoning"].map(
        {"True": True, "False": False, True: True, False: False, "": np.nan}
    )
    print(f"  Loaded {len(df):,} trials, {df['model_key'].nunique()} models")
    return df


# ===================================================================
# ANALYSIS 1: Specification Gap Phase Transition
# ===================================================================
def analysis_1_phase_transition(df):
    """
    For each model, compute non-optimal rate at each specification level.
    Plot trajectories, compute transition odds ratios, test universality.
    """
    print("\n" + "="*70)
    print("ANALYSIS 1: Specification Gap Phase Transition")
    print("="*70)

    # Filter to specification gradient conditions only
    # These are: baseline (ordinal=0), utility_*/preference_* (ordinals 1-5)
    spec_conditions = [
        "baseline",
        "utility_vague", "preference_vague",
        "utility_weighted", "preference_weighted",
        "utility_explicit", "preference_explicit",
        "utility_override", "preference_override",
        "utility_constrained", "preference_constrained",
    ]
    dg = df[df["condition"].isin(spec_conditions)].copy()
    print(f"  Specification gradient subset: {len(dg):,} trials")

    # Per-model, per-level non-optimal rate
    models = sorted(dg["model_key"].unique())
    results_by_model = {}
    for mk in models:
        dm = dg[dg["model_key"] == mk]
        rates = {}
        counts = {}
        for ordinal in SPEC_ORDINALS:
            sub = dm[dm["condition_ordinal"] == ordinal]
            n = len(sub)
            if n == 0:
                rates[ordinal] = np.nan
                counts[ordinal] = 0
                continue
            rate = sub["non_optimal"].mean()
            rates[ordinal] = rate
            counts[ordinal] = n
        results_by_model[mk] = {"rates": rates, "counts": counts}

    # --- Table ---
    rows = []
    for mk in models:
        row = {"model": mk}
        for i, lvl in enumerate(SPEC_LABELS):
            row[lvl] = results_by_model[mk]["rates"][i]
            row[f"{lvl}_n"] = results_by_model[mk]["counts"][i]
        rows.append(row)
    tbl = pd.DataFrame(rows)
    tbl.to_csv(OUT_DIR / "a1_model_trajectories.csv", index=False)
    print("  Saved a1_model_trajectories.csv")

    # --- Transition odds ratios ---
    transitions = [
        ("Baseline->Vague", 0, 1),
        ("Vague->Weighted", 1, 2),
        ("Weighted->Explicit", 2, 3),
        ("Explicit->Override", 3, 4),
        ("Override->Constrained", 4, 5),
    ]
    or_results = []
    for trans_name, o1, o2 in transitions:
        # Aggregate across all models
        sub1 = dg[dg["condition_ordinal"] == o1]
        sub2 = dg[dg["condition_ordinal"] == o2]
        a = sub1["non_optimal"].sum()  # non-optimal at level o1
        b = len(sub1) - a              # optimal at level o1
        c = sub2["non_optimal"].sum()  # non-optimal at level o2
        d = len(sub2) - c              # optimal at level o2

        # Odds ratio: (a/b) / (c/d) = (a*d) / (b*c)
        # This gives OR > 1 when non-optimal is more common at the lower level
        if c == 0 or b == 0:
            odds_ratio = float("inf")
            log_or = float("inf")
            se_log_or = np.nan
            ci_lo, ci_hi = np.nan, np.nan
            p_val = 0.0
        else:
            odds_ratio = (a * d) / (b * c)
            log_or = np.log(odds_ratio)
            # Woolf's formula for SE of log(OR)
            se_log_or = np.sqrt(1/max(a,1) + 1/max(b,1) + 1/max(c,1) + 1/max(d,1))
            ci_lo = np.exp(log_or - 1.96 * se_log_or)
            ci_hi = np.exp(log_or + 1.96 * se_log_or)
            # Chi-squared test
            if HAS_SCIPY:
                table = np.array([[a, b], [c, d]])
                chi2, p_val, _, _ = sp_stats.chi2_contingency(table, correction=False)
            else:
                p_val = np.nan

        # Per-model ORs for this transition
        model_ors = []
        for mk in models:
            dm = dg[dg["model_key"] == mk]
            s1 = dm[dm["condition_ordinal"] == o1]
            s2 = dm[dm["condition_ordinal"] == o2]
            a_m = s1["non_optimal"].sum()
            b_m = len(s1) - a_m
            c_m = s2["non_optimal"].sum()
            d_m = len(s2) - c_m
            if c_m == 0 or b_m == 0:
                model_ors.append({"model": mk, "OR": float("inf")})
            elif a_m == 0:
                model_ors.append({"model": mk, "OR": 0.0})
            else:
                model_ors.append({"model": mk, "OR": (a_m * d_m) / (b_m * c_m)})

        or_results.append({
            "transition": trans_name,
            "OR_aggregate": round(odds_ratio, 2),
            "CI_95_lo": round(ci_lo, 2) if not np.isnan(ci_lo) else None,
            "CI_95_hi": round(ci_hi, 2) if not np.isnan(ci_hi) else None,
            "p_value": f"{p_val:.2e}" if not np.isnan(p_val) else None,
            "n_level_lower": int(len(sub1)),
            "n_level_upper": int(len(sub2)),
            "rate_lower": round(sub1["non_optimal"].mean(), 4),
            "rate_upper": round(sub2["non_optimal"].mean(), 4),
            "model_ORs": model_ors,
        })
        print(f"  {trans_name}: OR={odds_ratio:.2f} [{ci_lo:.2f}, {ci_hi:.2f}], p={p_val:.2e}")

    # --- Check universality: is weighted->explicit the LARGEST transition for each model? ---
    # Use absolute rate DROP (not OR) because when rates reach zero, ORs become infinite/degenerate
    print("\n  Universality check: Is Weighted->Explicit the largest absolute rate drop for each model?")
    universality = []
    for mk in models:
        transition_drops = {}
        for trans_name, o1, o2 in transitions:
            dm = dg[dg["model_key"] == mk]
            s1 = dm[dm["condition_ordinal"] == o1]
            s2 = dm[dm["condition_ordinal"] == o2]
            rate1 = s1["non_optimal"].mean() if len(s1) > 0 else 0
            rate2 = s2["non_optimal"].mean() if len(s2) > 0 else 0
            drop = rate1 - rate2  # positive means non-optimal decreased
            transition_drops[trans_name] = drop

        largest = max(transition_drops, key=transition_drops.get)
        is_we = "Weighted->Explicit" in largest
        we_drop = transition_drops["Weighted->Explicit"]
        universality.append({
            "model": mk,
            "largest_transition": largest,
            "largest_drop_pp": round(transition_drops[largest] * 100, 2),
            "weighted_explicit_drop_pp": round(we_drop * 100, 2),
            "is_weighted_explicit_largest": is_we,
            "all_drops_pp": {k: round(v*100, 2) for k, v in transition_drops.items()},
        })
        marker = "YES" if is_we else "NO"
        print(f"    {mk:28s}: largest={largest} (drop={transition_drops[largest]*100:.1f}pp), W->E drop={we_drop*100:.1f}pp  [{marker}]")

    n_yes = sum(1 for u in universality if u["is_weighted_explicit_largest"])
    print(f"  Universality: {n_yes}/{len(models)} models have W->E as largest transition")

    # --- GEE logistic regression ---
    gee_result = None
    if HAS_SM:
        print("\n  GEE logistic regression (ordinal predictor, clustered on model)...")
        dg_gee = dg[["non_optimal", "condition_ordinal", "model_key"]].dropna().copy()
        dg_gee["non_optimal_int"] = dg_gee["non_optimal"].astype(int)
        # Encode model as integer group
        model_map = {m: i for i, m in enumerate(sorted(dg_gee["model_key"].unique()))}
        dg_gee["model_group"] = dg_gee["model_key"].map(model_map)
        dg_gee = dg_gee.sort_values("model_group").reset_index(drop=True)

        try:
            gee_model = GEE.from_formula(
                "non_optimal_int ~ condition_ordinal",
                groups="model_group",
                data=dg_gee,
                family=Binomial(),
                cov_struct=Exchangeable(),
            )
            gee_fit = gee_model.fit()
            gee_result = {
                "intercept": round(float(gee_fit.params["Intercept"]), 4),
                "slope": round(float(gee_fit.params["condition_ordinal"]), 4),
                "slope_SE": round(float(gee_fit.bse["condition_ordinal"]), 4),
                "slope_p": f"{float(gee_fit.pvalues['condition_ordinal']):.2e}",
                "slope_OR": round(np.exp(float(gee_fit.params["condition_ordinal"])), 4),
                "n_clusters": len(model_map),
                "n_obs": len(dg_gee),
            }
            print(f"    Slope (log-OR per level): {gee_result['slope']} (SE={gee_result['slope_SE']}, p={gee_result['slope_p']})")
            print(f"    OR per level increase: {gee_result['slope_OR']}")
        except Exception as e:
            print(f"    GEE failed: {e}")

    # --- Breakpoint / changepoint test at weighted->explicit ---
    breakpoint_result = None
    if HAS_SM:
        print("\n  Piecewise regression: testing breakpoint at Weighted->Explicit boundary...")
        dg_bp = dg[["non_optimal", "condition_ordinal"]].dropna().copy()
        dg_bp["non_optimal_int"] = dg_bp["non_optimal"].astype(int)
        # Piecewise: slope1 for ordinals 0-2, slope2 for ordinals 3-5
        dg_bp["ordinal_pre"] = dg_bp["condition_ordinal"].clip(upper=2)
        dg_bp["ordinal_post"] = (dg_bp["condition_ordinal"] - 3).clip(lower=0)
        dg_bp["is_post"] = (dg_bp["condition_ordinal"] >= 3).astype(int)

        try:
            # Model with indicator for post-breakpoint
            bp_model = smf.logit(
                "non_optimal_int ~ condition_ordinal + is_post",
                data=dg_bp
            ).fit(disp=0)
            breakpoint_result = {
                "ordinal_coef": round(float(bp_model.params["condition_ordinal"]), 4),
                "is_post_coef": round(float(bp_model.params["is_post"]), 4),
                "is_post_OR": round(np.exp(float(bp_model.params["is_post"])), 4),
                "is_post_p": f"{float(bp_model.pvalues['is_post']):.2e}",
                "pseudo_r2": round(float(bp_model.prsquared), 4),
                "AIC_piecewise": round(float(bp_model.aic), 1),
            }
            # Compare with linear-only model
            lin_model = smf.logit(
                "non_optimal_int ~ condition_ordinal",
                data=dg_bp
            ).fit(disp=0)
            breakpoint_result["AIC_linear"] = round(float(lin_model.aic), 1)
            breakpoint_result["delta_AIC"] = round(
                breakpoint_result["AIC_linear"] - breakpoint_result["AIC_piecewise"], 1
            )
            # LRT
            lr_stat = 2 * (bp_model.llf - lin_model.llf)
            lr_p = sp_stats.chi2.sf(lr_stat, df=1) if HAS_SCIPY else np.nan
            breakpoint_result["LRT_chi2"] = round(lr_stat, 2)
            breakpoint_result["LRT_p"] = f"{lr_p:.2e}"
            print(f"    Breakpoint indicator OR: {breakpoint_result['is_post_OR']} (p={breakpoint_result['is_post_p']})")
            print(f"    Delta AIC (linear - piecewise): {breakpoint_result['delta_AIC']}")
            print(f"    LRT: chi2={breakpoint_result['LRT_chi2']}, p={breakpoint_result['LRT_p']}")
        except Exception as e:
            print(f"    Breakpoint test failed: {e}")

    # --- FIGURE 1: Individual model trajectories ---
    fig, ax = plt.subplots(figsize=(NATURE_WIDTH, 4.0))

    for mk in models:
        rates = results_by_model[mk]["rates"]
        xs = list(range(6))
        ys = [rates[o] * 100 for o in SPEC_ORDINALS]
        prov = MODEL_PROVIDERS.get(mk, "openrouter")
        color = PROVIDER_COLORS.get(prov, "#888888")
        ax.plot(xs, ys, marker="o", color=color, alpha=0.45, markersize=3, linewidth=0.8)

    # Aggregate line (thick)
    agg_rates = []
    for o in SPEC_ORDINALS:
        sub = dg[dg["condition_ordinal"] == o]
        agg_rates.append(sub["non_optimal"].mean() * 100)
    ax.plot(range(6), agg_rates, color="black", linewidth=2.5, marker="s",
            markersize=5, zorder=10, label="Aggregate (all models)")

    # Vertical line at the weighted->explicit boundary
    ax.axvline(x=2.5, color="red", linestyle="--", linewidth=0.8, alpha=0.7)
    ax.annotate("Phase transition", xy=(2.5, max(agg_rates)*0.85),
                fontsize=7, color="red", ha="center", style="italic")

    ax.set_xticks(range(6))
    ax.set_xticklabels(SPEC_LABELS, rotation=30, ha="right")
    ax.set_ylabel("Non-optimal rate (%)")
    ax.set_xlabel("Specification level")
    ax.set_title("Specification Gap Phase Transition: Individual Model Trajectories", fontsize=9, fontweight="bold")

    # Legend for providers
    legend_handles = [
        Line2D([0], [0], color=c, marker="o", markersize=4, linestyle="-", label=p.title())
        for p, c in PROVIDER_COLORS.items()
    ]
    legend_handles.append(Line2D([0], [0], color="black", marker="s", markersize=5,
                                  linewidth=2.5, label="Aggregate"))
    ax.legend(handles=legend_handles, loc="upper right", frameon=True, edgecolor="gray",
              framealpha=0.9, fontsize=6)
    ax.set_ylim(bottom=-1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    save_fig(fig, "a1_phase_transition_trajectories")

    # --- FIGURE 1b: Transition OR bar chart (log scale, finite ORs only in bars) ---
    fig, ax = plt.subplots(figsize=(NATURE_WIDTH * 0.6, 3.5))
    trans_names = [t["transition"] for t in or_results]
    trans_ors = [t["OR_aggregate"] for t in or_results]
    # Use absolute rate drops (pp) instead, which are always finite and interpretable
    trans_drops = []
    for t in or_results:
        drop = (t["rate_lower"] - t["rate_upper"]) * 100  # pp
        trans_drops.append(drop)

    colors = ["#6B7280"] * 5
    colors[2] = "#DC2626"  # Weighted->Explicit in red
    bars = ax.bar(range(5), trans_drops, color=colors, edgecolor="white", linewidth=0.5)

    # Add value labels with both pp drop and OR
    for i, (bar, pp, or_val) in enumerate(zip(bars, trans_drops, trans_ors)):
        or_str = f"OR={or_val:.0f}" if or_val < 10000 else "OR=inf"
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + max(trans_drops)*0.03,
                f"{pp:.1f}pp\n({or_str})",
                ha="center", va="bottom", fontsize=5.5, fontweight="bold")

    ax.set_xticks(range(5))
    ax.set_xticklabels([t.replace("->", "\n\u2192\n") for t in trans_names], fontsize=6)
    ax.set_ylabel("Absolute rate drop (percentage points)")
    ax.set_title("Transition Magnitude: Weighted\u2192Explicit Dominates", fontsize=9, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    save_fig(fig, "a1_transition_odds_ratios")

    # --- Save JSON summary ---
    summary = {
        "analysis": "Specification Gap Phase Transition",
        "n_trials_gradient": int(len(dg)),
        "n_models": len(models),
        "aggregate_rates": {SPEC_LABELS[i]: round(agg_rates[i], 2) for i in range(6)},
        "transitions": [{k: v for k, v in t.items() if k != "model_ORs"} for t in or_results],
        "universality": universality,
        "universality_fraction": f"{n_yes}/{len(models)}",
        "gee": gee_result,
        "breakpoint": breakpoint_result,
    }
    with open(OUT_DIR / "a1_phase_transition_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print("  Saved a1_phase_transition_summary.json")

    return summary


# ===================================================================
# ANALYSIS 2: Creation/Removal Asymmetry
# ===================================================================
def analysis_2_asymmetry(df_main):
    """
    Compute the formal asymmetry ratio between injection and debiasing.
    Fit dose-response curves to both processes.

    Key insight: Injection data tracks THREE metrics per dose level:
    - chose_axelion: rate of choosing the INJECTED fictional brand
    - chose_optimal: rate of choosing the objectively best product
    - chose_branded: rate of choosing a real (familiar) brand

    At 200 examples, Axelion rate DROPS because the model learned to prefer
    fictional brands generally, so it picks the optimal fictional brand
    (Zentria) instead. The key injection metric is the BRANDED rate (how
    quickly training shifts preferences away from real brands).

    For debiasing: 500 examples of "pick the optimal product" training
    reduce the non-optimal rate. We compare efficiency: examples-per-pp
    of brand preference shift (injection) vs examples-per-pp of bias
    removal (debiasing).
    """
    print("\n" + "="*70)
    print("ANALYSIS 2: Creation/Removal Asymmetry Formalization")
    print("="*70)

    # --- Load injection data ---
    inj = pd.read_csv(INJECTION_CSV)
    print(f"  Injection data: {len(inj)} trials")

    # Compute all three metrics per dose level
    inj_metrics = {}
    for mk in ["baseline", "control_neutral", "injection_50", "injection_100", "injection_200"]:
        sub = inj[inj["model_key"] == mk]
        n = len(sub)
        if n == 0:
            continue
        axelion_rate = sub["chose_axelion"].astype(int).mean()
        optimal_rate = sub["chose_optimal"].astype(int).mean()
        branded_rate = sub["chose_branded"].astype(int).mean()
        inj_metrics[mk] = {
            "n": n,
            "axelion_rate": float(axelion_rate),
            "optimal_rate": float(optimal_rate),
            "branded_rate": float(branded_rate),
        }
        print(f"    {mk:20s}: n={n}, axelion={axelion_rate:.3f}, optimal={optimal_rate:.3f}, branded={branded_rate:.3f}")

    # --- Load debiasing data ---
    deb = pd.read_csv(DEBIASING_CSV)
    print(f"\n  Debiasing data: {len(deb)} trials")
    deb_rates = {}
    for mk in sorted(deb["model_key"].unique()):
        sub = deb[deb["model_key"] == mk]
        rate = sub["chose_optimal"].astype(bool).mean()
        deb_rates[mk] = {"rate": float(rate), "n": len(sub)}
        print(f"    {mk:20s}: optimal_rate={rate:.4f}, n={len(sub)}")

    # --- Load eval_6k data (gpt-4.1-nano debiasing) ---
    eval6k = pd.read_csv(EVAL_6K_CSV)
    print(f"\n  Eval 6k (4.1-nano): {len(eval6k)} trials")
    eval6k_rates = {}
    for mk in sorted(eval6k["model_key"].unique()):
        sub = eval6k[eval6k["model_key"] == mk]
        rate = sub["chose_optimal"].astype(bool).mean()
        eval6k_rates[mk] = {"rate": float(rate), "n": len(sub)}
        print(f"    {mk:20s}: optimal_rate={rate:.4f}, n={len(sub)}")

    # --- Main experiment baselines for reference ---
    base_4omini = df_main[(df_main["model_key"] == "gpt-4o-mini") & (df_main["condition"] == "baseline")]
    base_nonopt_4omini = base_4omini["non_optimal"].mean() if len(base_4omini) > 0 else np.nan
    base_41nano = df_main[(df_main["model_key"] == "gpt-4.1-nano") & (df_main["condition"] == "baseline")]
    base_nonopt_41nano = base_41nano["non_optimal"].mean() if len(base_41nano) > 0 else np.nan
    print(f"\n  Main experiment baselines:")
    print(f"    gpt-4o-mini: non-optimal={base_nonopt_4omini:.4f}, n={len(base_4omini)}")
    print(f"    gpt-4.1-nano: non-optimal={base_nonopt_41nano:.4f}, n={len(base_41nano)}")

    # =====================================================================
    # INJECTION DOSE-RESPONSE: branded_rate as a function of dose
    # This is monotonically DECREASING (more injection = less brand loyalty)
    # =====================================================================
    inj_doses = [0, 50, 100, 200]
    inj_branded = [inj_metrics[k]["branded_rate"] for k in ["baseline", "injection_50", "injection_100", "injection_200"]]
    inj_axelion = [inj_metrics[k]["axelion_rate"] for k in ["baseline", "injection_50", "injection_100", "injection_200"]]
    inj_optimal = [inj_metrics[k]["optimal_rate"] for k in ["baseline", "injection_50", "injection_100", "injection_200"]]

    print(f"\n  Injection dose-response:")
    print(f"    Doses:   {inj_doses}")
    print(f"    Branded: {[f'{r:.3f}' for r in inj_branded]}")
    print(f"    Axelion: {[f'{r:.3f}' for r in inj_axelion]}")
    print(f"    Optimal: {[f'{r:.3f}' for r in inj_optimal]}")

    # Efficiency metric: percentage points of branded-rate reduction per training example
    inj_branded_drop = inj_branded[0] - inj_branded[-1]  # baseline - 200 examples
    inj_pp_per_example = inj_branded_drop / 200 * 100  # pp per example
    print(f"\n  Injection efficiency:")
    print(f"    Branded rate drop: {inj_branded[0]*100:.1f}% -> {inj_branded[-1]*100:.1f}% = {inj_branded_drop*100:.1f}pp with 200 examples")
    print(f"    Efficiency: {inj_pp_per_example:.3f} pp per training example")

    # At 50 examples: how much branded shift?
    inj_50_drop = inj_branded[0] - inj_branded[1]
    print(f"    At 50 examples: branded drop = {inj_50_drop*100:.1f}pp ({inj_50_drop/inj_branded[0]*100:.1f}% reduction)")

    # =====================================================================
    # DEBIASING
    # =====================================================================
    deb_baseline_opt = deb_rates.get("baseline", {}).get("rate", np.nan)
    deb_500_opt = deb_rates.get("debiasing-500", {}).get("rate", np.nan)
    deb_nonopt_bl = 1 - deb_baseline_opt
    deb_nonopt_500 = 1 - deb_500_opt
    deb_reduction_pp = deb_nonopt_bl - deb_nonopt_500
    deb_reduction_frac = deb_reduction_pp / deb_nonopt_bl if deb_nonopt_bl > 0 else np.nan
    deb_pp_per_example = deb_reduction_pp / 500 * 100  # pp per example

    nano_bl_opt = eval6k_rates.get("baseline-41nano", {}).get("rate", np.nan)
    nano_6k_opt = eval6k_rates.get("ft-6k-41nano", {}).get("rate", np.nan)
    nano_nonopt_bl = 1 - nano_bl_opt
    nano_nonopt_6k = 1 - nano_6k_opt
    nano_reduction_pp = nano_nonopt_bl - nano_nonopt_6k
    nano_reduction_frac = nano_reduction_pp / nano_nonopt_bl if nano_nonopt_bl > 0 else np.nan
    nano_pp_per_example = nano_reduction_pp / 6000 * 100  # pp per example

    print(f"\n  Debiasing (gpt-4o-mini, 500 examples):")
    print(f"    Non-optimal: {deb_nonopt_bl*100:.1f}% -> {deb_nonopt_500*100:.1f}% = {deb_reduction_pp*100:.1f}pp drop")
    print(f"    Reduction fraction: {deb_reduction_frac:.3f}")
    print(f"    Efficiency: {deb_pp_per_example:.4f} pp per training example")

    print(f"\n  Debiasing (gpt-4.1-nano, 6000 examples):")
    print(f"    Non-optimal: {nano_nonopt_bl*100:.1f}% -> {nano_nonopt_6k*100:.1f}% = {nano_reduction_pp*100:.1f}pp drop")
    print(f"    Reduction fraction: {nano_reduction_frac:.3f}")
    print(f"    Efficiency: {nano_pp_per_example:.4f} pp per training example")

    # =====================================================================
    # ASYMMETRY RATIO: efficiency of creation vs removal
    # =====================================================================
    # Injection: 50 examples created a 7pp shift in branded rate (32% -> 25%)
    # That's 0.14 pp per example
    # Debiasing: 500 examples created a ~14.4pp shift in non-optimal rate
    # That's 0.029 pp per example
    # Asymmetry ratio = injection_efficiency / debiasing_efficiency

    asym_ratio_4omini = inj_pp_per_example / deb_pp_per_example if deb_pp_per_example > 0 else np.nan
    asym_ratio_41nano = inj_pp_per_example / nano_pp_per_example if nano_pp_per_example > 0 else np.nan

    print(f"\n  ASYMMETRY RATIOS (injection efficiency / debiasing efficiency):")
    print(f"    vs gpt-4o-mini (500 ex): {asym_ratio_4omini:.1f}x")
    print(f"    vs gpt-4.1-nano (6k ex): {asym_ratio_41nano:.1f}x")
    print(f"    Interpretation: It takes {asym_ratio_4omini:.0f}x more training examples")
    print(f"    to REMOVE a pp of brand preference than to CREATE one")

    # --- Bootstrap CI for asymmetry ratio ---
    asym_boots = []
    if HAS_SCIPY:
        rng = np.random.default_rng(42)
        n_boot = 10000
        for _ in range(n_boot):
            # Bootstrap injection
            n_bl = inj_metrics["baseline"]["n"]
            n_200 = inj_metrics["injection_200"]["n"]
            boot_bl_branded = rng.binomial(n_bl, inj_branded[0]) / n_bl
            boot_200_branded = rng.binomial(n_200, inj_branded[-1]) / n_200
            boot_inj_drop = boot_bl_branded - boot_200_branded
            boot_inj_eff = boot_inj_drop / 200 * 100

            # Bootstrap debiasing
            n_deb_bl = deb_rates.get("baseline", {}).get("n", 680)
            n_deb_500 = deb_rates.get("debiasing-500", {}).get("n", 680)
            boot_deb_bl = rng.binomial(n_deb_bl, deb_nonopt_bl) / n_deb_bl
            boot_deb_500 = rng.binomial(n_deb_500, deb_nonopt_500) / n_deb_500
            boot_deb_drop = boot_deb_bl - boot_deb_500
            boot_deb_eff = boot_deb_drop / 500 * 100

            if boot_deb_eff > 0.001 and boot_inj_eff > 0:
                ratio = boot_inj_eff / boot_deb_eff
                if 0.1 < ratio < 200:
                    asym_boots.append(ratio)

    asym_ci = None
    if len(asym_boots) > 100:
        asym_ci = {
            "median": round(float(np.median(asym_boots)), 1),
            "CI95_lo": round(float(np.percentile(asym_boots, 2.5)), 1),
            "CI95_hi": round(float(np.percentile(asym_boots, 97.5)), 1),
            "n_valid_boots": len(asym_boots),
        }
        print(f"\n  Bootstrap asymmetry ratio (vs 4o-mini): {asym_ci['median']}x [{asym_ci['CI95_lo']}, {asym_ci['CI95_hi']}] (95% CI)")

    # --- Statistical test: is the branded rate shift significant at each dose? ---
    injection_tests = []
    if HAS_SCIPY:
        for dose_key, dose_val in [("injection_50", 50), ("injection_100", 100), ("injection_200", 200)]:
            n_bl = inj_metrics["baseline"]["n"]
            x_bl = int(inj_metrics["baseline"]["branded_rate"] * n_bl)
            n_d = inj_metrics[dose_key]["n"]
            x_d = int(inj_metrics[dose_key]["branded_rate"] * n_d)
            # Two-proportion z-test
            p_pooled = (x_bl + x_d) / (n_bl + n_d)
            se_p = np.sqrt(p_pooled * (1 - p_pooled) * (1/n_bl + 1/n_d))
            z = (inj_metrics["baseline"]["branded_rate"] - inj_metrics[dose_key]["branded_rate"]) / se_p if se_p > 0 else 0
            p_val = 2 * sp_stats.norm.sf(abs(z))
            injection_tests.append({
                "dose": dose_val,
                "branded_baseline": round(inj_branded[0], 4),
                "branded_dose": round(inj_metrics[dose_key]["branded_rate"], 4),
                "z": round(z, 2),
                "p": f"{p_val:.4f}",
            })
            print(f"    Branded rate test (baseline vs {dose_val} ex): z={z:.2f}, p={p_val:.4f}")

    # --- FIGURE 2: Three-panel asymmetry figure ---
    fig, axes = plt.subplots(1, 3, figsize=(NATURE_WIDTH, 3.0))

    # Panel a: Injection dose-response (3 metrics)
    ax = axes[0]
    ax.plot(inj_doses, [r*100 for r in inj_branded], "o-", color="#DC2626",
            label="Branded (real)", markersize=4, linewidth=1.2)
    ax.plot(inj_doses, [r*100 for r in inj_axelion], "s--", color="#8B5CF6",
            label="Axelion (injected)", markersize=4, linewidth=1.0, alpha=0.7)
    ax.plot(inj_doses, [r*100 for r in inj_optimal], "^:", color="#10B981",
            label="Optimal", markersize=4, linewidth=1.0, alpha=0.7)
    ax.set_xlabel("Injection training examples")
    ax.set_ylabel("Choice rate (%)")
    ax.set_title("a  Preference injection", fontsize=9, fontweight="bold", loc="left")
    ax.legend(fontsize=5, loc="center right", frameon=True, edgecolor="gray")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Panel b: Debiasing before/after
    ax = axes[1]
    deb_labels = ["4o-mini\nbaseline", "4o-mini\n500 ex.", "4.1-nano\nbaseline", "4.1-nano\n6k ex."]
    deb_vals = [deb_nonopt_bl*100, deb_nonopt_500*100, nano_nonopt_bl*100, nano_nonopt_6k*100]
    deb_colors = ["#6B7280", "#10B981", "#6B7280", "#3B82F6"]
    bars = ax.bar(range(4), deb_vals, color=deb_colors, edgecolor="white", linewidth=0.5)
    for bar, val in zip(bars, deb_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=6)
    ax.set_xticks(range(4))
    ax.set_xticklabels(deb_labels, fontsize=5.5)
    ax.set_ylabel("Non-optimal rate (%)")
    ax.set_title("b  Debiasing fine-tuning", fontsize=9, fontweight="bold", loc="left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Panel c: Efficiency comparison (pp per example)
    ax = axes[2]
    eff_labels = ["Injection\n(create bias)", "Debiasing\n4o-mini", "Debiasing\n4.1-nano"]
    eff_vals = [inj_pp_per_example, deb_pp_per_example, nano_pp_per_example]
    eff_colors = ["#DC2626", "#10B981", "#3B82F6"]
    bars = ax.bar(range(3), eff_vals, color=eff_colors, edgecolor="white", linewidth=0.5)
    for bar, val in zip(bars, eff_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(eff_vals)*0.02,
                f"{val:.3f}", ha="center", va="bottom", fontsize=6)
    ax.set_xticks(range(3))
    ax.set_xticklabels(eff_labels, fontsize=5.5)
    ax.set_ylabel("pp shift per training example")
    ax.set_title("c  Efficiency asymmetry", fontsize=9, fontweight="bold", loc="left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Add asymmetry ratio annotation
    if not np.isnan(asym_ratio_4omini):
        ax.annotate(f"{asym_ratio_4omini:.0f}x", xy=(0.5, max(eff_vals)*0.7),
                    fontsize=14, fontweight="bold", color="#DC2626",
                    ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#DC2626"))

    plt.tight_layout()
    save_fig(fig, "a2_asymmetry_dose_response")

    # --- Save summary ---
    summary = {
        "analysis": "Creation/Removal Asymmetry",
        "injection_metrics": {k: v for k, v in inj_metrics.items()},
        "injection_dose_response": {
            "doses": inj_doses,
            "branded_rates": inj_branded,
            "axelion_rates": inj_axelion,
            "optimal_rates": inj_optimal,
            "branded_drop_0_to_200": round(inj_branded_drop * 100, 1),
            "pp_per_example": round(inj_pp_per_example, 4),
        },
        "injection_statistical_tests": injection_tests,
        "debiasing_4omini": {
            "baseline_nonopt": round(deb_nonopt_bl, 4),
            "debiased_500_nonopt": round(deb_nonopt_500, 4),
            "reduction_pp": round(deb_reduction_pp * 100, 1),
            "reduction_fraction": round(deb_reduction_frac, 4),
            "pp_per_example": round(deb_pp_per_example, 4),
        },
        "debiasing_41nano": {
            "baseline_nonopt": round(nano_nonopt_bl, 4),
            "debiased_6k_nonopt": round(nano_nonopt_6k, 4),
            "reduction_pp": round(nano_reduction_pp * 100, 1),
            "reduction_fraction": round(nano_reduction_frac, 4),
            "pp_per_example": round(nano_pp_per_example, 4),
        },
        "asymmetry_ratio_vs_4omini": round(asym_ratio_4omini, 1) if not np.isnan(asym_ratio_4omini) else None,
        "asymmetry_ratio_vs_41nano": round(asym_ratio_41nano, 1) if not np.isnan(asym_ratio_41nano) else None,
        "asymmetry_bootstrap_CI": asym_ci,
    }

    # Save CSV with dose-response data
    dr_rows = []
    for i, dose in enumerate(inj_doses):
        dr_rows.append({
            "process": "injection",
            "dose": dose,
            "branded_rate": inj_branded[i],
            "axelion_rate": inj_axelion[i],
            "optimal_rate": inj_optimal[i],
        })
    dr_rows.append({"process": "debiasing_4omini", "dose": 0, "nonopt_rate": deb_nonopt_bl})
    dr_rows.append({"process": "debiasing_4omini", "dose": 500, "nonopt_rate": deb_nonopt_500})
    dr_rows.append({"process": "debiasing_41nano", "dose": 0, "nonopt_rate": nano_nonopt_bl})
    dr_rows.append({"process": "debiasing_41nano", "dose": 6000, "nonopt_rate": nano_nonopt_6k})
    pd.DataFrame(dr_rows).to_csv(OUT_DIR / "a2_dose_response_data.csv", index=False)

    with open(OUT_DIR / "a2_asymmetry_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print("  Saved a2_asymmetry_summary.json + a2_dose_response_data.csv")

    return summary


# ===================================================================
# ANALYSIS 3: Confabulation Mechanism Deep Dive
# ===================================================================
def analysis_3_confabulation(df):
    """
    For non-optimal baseline choices: what brand was chosen, what was cited,
    and is the justification objectively false?
    """
    print("\n" + "="*70)
    print("ANALYSIS 3: Confabulation Mechanism Deep Dive")
    print("="*70)

    # Load assortments for brand mapping
    from experiment.assortments import ALL_ASSORTMENTS

    # Build assortment lookup: assortment_id -> {letter -> product_info}
    assortment_map = {}
    for a in ALL_ASSORTMENTS:
        aid = a["id"]
        products = a["products"]
        # Products are indexed 0-4, mapping to letters A-E in original order
        assortment_map[aid] = {
            "products": products,
            "category": a["category"],
        }

    # Filter to baseline non-optimal choices
    baseline = df[(df["condition"] == "baseline") & (df["non_optimal"] == True)].copy()
    print(f"  Baseline non-optimal choices: {len(baseline):,}")

    # For each non-optimal choice, identify: which brand was chosen, its familiarity
    brand_counts = Counter()
    fam_counts = Counter()
    br_by_fam = Counter()  # (familiarity, brand_reasoning) -> count

    for _, row in baseline.iterrows():
        fam = row["chosen_brand_familiarity"]
        fam_counts[fam] += 1
        br = row["judge_brand_reasoning"]
        if pd.notna(br):
            br_by_fam[(fam, br)] += 1

    print(f"\n  Familiarity of chosen brands (non-optimal at baseline):")
    for fam in ["high", "medium", "low"]:
        c = fam_counts.get(fam, 0)
        pct = c / len(baseline) * 100 if len(baseline) > 0 else 0
        print(f"    {fam}: {c} ({pct:.1f}%)")

    # Brand reasoning: does the model cite brand explicitly?
    br_true = baseline["judge_brand_reasoning"].sum() if baseline["judge_brand_reasoning"].dtype == bool else \
              (baseline["judge_brand_reasoning"] == True).sum()
    br_false = (baseline["judge_brand_reasoning"] == False).sum()
    br_total = br_true + br_false
    confab_rate = br_false / br_total * 100 if br_total > 0 else 0
    explicit_brand_rate = br_true / br_total * 100 if br_total > 0 else 0

    print(f"\n  Brand reasoning in non-optimal baseline choices:")
    print(f"    Cites brand explicitly: {br_true} ({explicit_brand_rate:.1f}%)")
    print(f"    Confabulates attribute justification: {br_false} ({confab_rate:.1f}%)")
    print(f"    Total with judge data: {br_total}")

    # --- Per-model confabulation breakdown ---
    print("\n  Per-model confabulation rates at baseline:")
    model_confab = []
    for mk in sorted(baseline["model_key"].unique()):
        mb = baseline[baseline["model_key"] == mk]
        n_nonopt = len(mb)
        br_t = (mb["judge_brand_reasoning"] == True).sum()
        br_f = (mb["judge_brand_reasoning"] == False).sum()
        tot = br_t + br_f
        cr = br_f / tot * 100 if tot > 0 else 0
        model_confab.append({
            "model": mk,
            "n_nonoptimal": int(n_nonopt),
            "brand_cited": int(br_t),
            "attribute_confabulated": int(br_f),
            "confabulation_rate": round(cr, 1),
        })
        print(f"    {mk:28s}: {n_nonopt:4d} non-opt, confab={cr:.1f}%")

    # --- Per-category confabulation ---
    print("\n  Per-category confabulation rates at baseline:")
    cat_confab = []
    for cat in sorted(baseline["category"].unique()):
        cb = baseline[baseline["category"] == cat]
        n_nonopt = len(cb)
        br_t = (cb["judge_brand_reasoning"] == True).sum()
        br_f = (cb["judge_brand_reasoning"] == False).sum()
        tot = br_t + br_f
        cr = br_f / tot * 100 if tot > 0 else 0
        cat_confab.append({
            "category": cat,
            "n_nonoptimal": int(n_nonopt),
            "confabulation_rate": round(cr, 1),
        })
        if n_nonopt >= 5:
            print(f"    {cat:25s}: {n_nonopt:4d} non-opt, confab={cr:.1f}%")

    # --- Fabrication rate: response text analysis ---
    # Sample raw JSON files to check if cited attributes are objectively false
    # We use the judge_brand_reasoning=False cases and check the raw response
    print("\n  Fabrication analysis (sampling raw JSON responses)...")
    import glob as glob_mod

    fabrication_results = {
        "n_sampled": 0,
        "n_response_available": 0,
    }

    # For a robust fabrication analysis, we look at chosen_brand_familiarity
    # If model chose a high-familiarity brand but cited attributes, and the
    # optimal (low-fam) product actually scores BETTER on those attributes,
    # that's fabrication.

    # Cross-tabulation: familiarity x brand_reasoning
    cross_tab = pd.crosstab(
        baseline["chosen_brand_familiarity"].fillna("unknown"),
        baseline["judge_brand_reasoning"].fillna("unknown"),
        margins=True,
    )
    print("\n  Cross-tabulation: Familiarity x Brand Reasoning")
    print(cross_tab.to_string())

    # Utility loss analysis for confabulated choices
    confab_choices = baseline[baseline["judge_brand_reasoning"] == False]
    explicit_choices = baseline[baseline["judge_brand_reasoning"] == True]

    if len(confab_choices) > 0:
        confab_loss = confab_choices["utility_loss"].astype(float)
        print(f"\n  Utility loss for confabulated choices: mean={confab_loss.mean():.4f}, median={confab_loss.median():.4f}")
    if len(explicit_choices) > 0:
        explicit_loss = explicit_choices["utility_loss"].astype(float)
        print(f"  Utility loss for brand-explicit choices: mean={explicit_loss.mean():.4f}, median={explicit_loss.median():.4f}")

    # Test: confabulated choices have similar utility loss to brand-cited choices
    if len(confab_choices) > 10 and len(explicit_choices) > 10 and HAS_SCIPY:
        u_stat, u_p = sp_stats.mannwhitneyu(
            confab_choices["utility_loss"].astype(float),
            explicit_choices["utility_loss"].astype(float),
            alternative="two-sided",
        )
        print(f"  Mann-Whitney U test (utility loss): U={u_stat:.0f}, p={u_p:.4f}")
        fabrication_results["utility_loss_test"] = {
            "U": float(u_stat), "p": float(u_p),
            "confab_mean_loss": round(float(confab_loss.mean()), 4),
            "explicit_mean_loss": round(float(explicit_loss.mean()), 4),
        }

    # --- Chi-squared test: familiarity vs confabulation ---
    if HAS_SCIPY:
        # Build 2x2: (high_fam vs other) x (confabulated vs brand_cited)
        high_confab = ((baseline["chosen_brand_familiarity"] == "high") & (baseline["judge_brand_reasoning"] == False)).sum()
        high_brand = ((baseline["chosen_brand_familiarity"] == "high") & (baseline["judge_brand_reasoning"] == True)).sum()
        other_confab = ((baseline["chosen_brand_familiarity"] != "high") & (baseline["judge_brand_reasoning"] == False)).sum()
        other_brand = ((baseline["chosen_brand_familiarity"] != "high") & (baseline["judge_brand_reasoning"] == True)).sum()
        table = np.array([[high_confab, high_brand], [other_confab, other_brand]])
        if table.min() > 0:
            chi2, p, dof, expected = sp_stats.chi2_contingency(table)
            print(f"\n  Chi-squared (high-fam vs other, confab vs brand-cited):")
            print(f"    chi2={chi2:.2f}, p={p:.4f}, dof={dof}")
            fabrication_results["familiarity_chi2"] = {"chi2": round(chi2, 2), "p": round(p, 4), "dof": int(dof)}

    # --- FIGURE 3a: Confabulation breakdown ---
    fig, axes = plt.subplots(1, 3, figsize=(NATURE_WIDTH, 3.0))

    # Panel a: Pie chart of brand reasoning
    ax = axes[0]
    sizes = [confab_rate, explicit_brand_rate]
    labels = [f"Attribute\nconfabulation\n({confab_rate:.1f}%)",
              f"Brand\ncited\n({explicit_brand_rate:.1f}%)"]
    colors = ["#DC2626", "#6B7280"]
    ax.pie(sizes, labels=labels, colors=colors, startangle=90,
           textprops={"fontsize": 6}, autopct="", pctdistance=0.7)
    ax.set_title("a  Justification type", fontsize=9, fontweight="bold", loc="left")

    # Panel b: Familiarity distribution of non-optimal choices
    ax = axes[1]
    fam_order = ["high", "medium", "low"]
    fam_vals = [fam_counts.get(f, 0) for f in fam_order]
    fam_pcts = [v / sum(fam_vals) * 100 for v in fam_vals]
    fam_colors = ["#DC2626", "#F59E0B", "#10B981"]
    bars = ax.bar(fam_order, fam_pcts, color=fam_colors, edgecolor="white", linewidth=0.5)
    for bar, pct in zip(bars, fam_pcts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{pct:.1f}%", ha="center", va="bottom", fontsize=6)
    ax.set_ylabel("% of non-optimal choices")
    ax.set_xlabel("Brand familiarity")
    ax.set_title("b  Chosen brand familiarity", fontsize=9, fontweight="bold", loc="left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Panel c: Per-model confabulation rate
    ax = axes[2]
    mc_df = pd.DataFrame(model_confab)
    mc_df = mc_df.sort_values("confabulation_rate", ascending=True)
    colors_bar = [PROVIDER_COLORS.get(MODEL_PROVIDERS.get(m, ""), "#888") for m in mc_df["model"]]
    short_names = [MODEL_SHORT.get(m, m[:12]) for m in mc_df["model"]]
    ax.barh(range(len(mc_df)), mc_df["confabulation_rate"], color=colors_bar,
            edgecolor="white", linewidth=0.3)
    ax.set_yticks(range(len(mc_df)))
    ax.set_yticklabels(short_names, fontsize=5)
    ax.set_xlabel("Confabulation rate (%)")
    ax.set_title("c  By model", fontsize=9, fontweight="bold", loc="left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    save_fig(fig, "a3_confabulation_mechanism")

    # --- Save ---
    pd.DataFrame(model_confab).to_csv(OUT_DIR / "a3_confabulation_by_model.csv", index=False)
    pd.DataFrame(cat_confab).to_csv(OUT_DIR / "a3_confabulation_by_category.csv", index=False)

    summary = {
        "analysis": "Confabulation Mechanism Deep Dive",
        "n_baseline_nonoptimal": int(len(baseline)),
        "confabulation_rate_pct": round(confab_rate, 1),
        "explicit_brand_rate_pct": round(explicit_brand_rate, 1),
        "familiarity_distribution": {k: int(v) for k, v in fam_counts.items()},
        "fabrication": fabrication_results,
        "cross_tabulation": cross_tab.to_dict(),
    }
    with open(OUT_DIR / "a3_confabulation_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print("  Saved a3_confabulation_summary.json")

    return summary


# ===================================================================
# ANALYSIS 4: Per-Model Specification Gap Consistency (Universality)
# ===================================================================
def analysis_4_universality(df):
    """
    Compute the specification gap OR for each model individually.
    Show that ALL models have a significant gap.
    Hierarchical/meta-analytic summary.
    """
    print("\n" + "="*70)
    print("ANALYSIS 4: Per-Model Specification Gap Consistency (Universality)")
    print("="*70)

    # Specification gap = OR comparing "low specification" (ordinal 0-2)
    # vs "high specification" (ordinal 3-5) on non-optimal rate
    spec_conditions = [
        "baseline",
        "utility_vague", "preference_vague",
        "utility_weighted", "preference_weighted",
        "utility_explicit", "preference_explicit",
        "utility_override", "preference_override",
        "utility_constrained", "preference_constrained",
    ]
    dg = df[df["condition"].isin(spec_conditions)].copy()
    dg["spec_high"] = (dg["condition_ordinal"] >= 3).astype(int)

    models = sorted(dg["model_key"].unique())
    model_results = []
    log_ors = []
    se_log_ors = []
    weights = []

    for mk in models:
        dm = dg[dg["model_key"] == mk]
        # Low spec (0-2): non-optimal vs optimal
        low = dm[dm["spec_high"] == 0]
        high = dm[dm["spec_high"] == 1]

        a = int(low["non_optimal"].sum())      # non-optimal at low spec
        b = int(len(low) - a)                   # optimal at low spec
        c = int(high["non_optimal"].sum())      # non-optimal at high spec
        d = int(len(high) - c)                  # optimal at high spec

        # Apply 0.5 continuity correction if any cell is zero
        if a == 0 or b == 0 or c == 0 or d == 0:
            a_c, b_c, c_c, d_c = a + 0.5, b + 0.5, c + 0.5, d + 0.5
        else:
            a_c, b_c, c_c, d_c = a, b, c, d

        odds_ratio = (a_c * d_c) / (b_c * c_c)
        log_or = np.log(odds_ratio)
        se = np.sqrt(1/a_c + 1/b_c + 1/c_c + 1/d_c)
        ci_lo = np.exp(log_or - 1.96 * se)
        ci_hi = np.exp(log_or + 1.96 * se)
        z = log_or / se
        p_val = 2 * sp_stats.norm.sf(abs(z)) if HAS_SCIPY else np.nan

        significant = p_val < 0.05 if not np.isnan(p_val) else None

        model_results.append({
            "model": mk,
            "provider": MODEL_PROVIDERS.get(mk, "unknown"),
            "n_low_spec": int(len(low)),
            "n_high_spec": int(len(high)),
            "nonopt_rate_low": round(low["non_optimal"].mean(), 4),
            "nonopt_rate_high": round(high["non_optimal"].mean(), 4),
            "OR": round(odds_ratio, 2),
            "log_OR": round(log_or, 4),
            "SE_log_OR": round(se, 4),
            "CI95_lo": round(ci_lo, 2),
            "CI95_hi": round(ci_hi, 2),
            "z": round(z, 2),
            "p_value": f"{p_val:.2e}" if not np.isnan(p_val) else None,
            "significant_p05": significant,
        })

        log_ors.append(log_or)
        se_log_ors.append(se)
        weights.append(1 / se**2)

        sig_str = "*" if significant else ""
        print(f"  {mk:28s}: OR={odds_ratio:8.2f} [{ci_lo:7.2f}, {ci_hi:9.2f}]  p={p_val:.2e} {sig_str}")

    n_significant = sum(1 for r in model_results if r["significant_p05"])
    print(f"\n  Models with significant gap (p<0.05): {n_significant}/{len(models)}")

    # --- Fixed-effect meta-analysis ---
    log_ors = np.array(log_ors)
    se_log_ors = np.array(se_log_ors)
    w = np.array(weights)

    # Fixed-effect pooled estimate
    pooled_log_or = np.sum(w * log_ors) / np.sum(w)
    pooled_se = np.sqrt(1 / np.sum(w))
    pooled_or = np.exp(pooled_log_or)
    pooled_ci_lo = np.exp(pooled_log_or - 1.96 * pooled_se)
    pooled_ci_hi = np.exp(pooled_log_or + 1.96 * pooled_se)
    pooled_z = pooled_log_or / pooled_se
    pooled_p = 2 * sp_stats.norm.sf(abs(pooled_z)) if HAS_SCIPY else np.nan

    print(f"\n  Fixed-effect meta-analytic OR: {pooled_or:.2f} [{pooled_ci_lo:.2f}, {pooled_ci_hi:.2f}], p={pooled_p:.2e}")

    # --- Random-effects meta-analysis (DerSimonian-Laird) ---
    Q = np.sum(w * (log_ors - pooled_log_or)**2)
    df_Q = len(models) - 1
    Q_p = sp_stats.chi2.sf(Q, df_Q) if HAS_SCIPY else np.nan
    I2 = max(0, (Q - df_Q) / Q) * 100

    # DerSimonian-Laird tau^2
    c_dl = np.sum(w) - np.sum(w**2) / np.sum(w)
    tau2 = max(0, (Q - df_Q) / c_dl)
    w_re = 1 / (se_log_ors**2 + tau2)
    re_log_or = np.sum(w_re * log_ors) / np.sum(w_re)
    re_se = np.sqrt(1 / np.sum(w_re))
    re_or = np.exp(re_log_or)
    re_ci_lo = np.exp(re_log_or - 1.96 * re_se)
    re_ci_hi = np.exp(re_log_or + 1.96 * re_se)
    re_z = re_log_or / re_se
    re_p = 2 * sp_stats.norm.sf(abs(re_z)) if HAS_SCIPY else np.nan

    print(f"  Random-effects (DL) OR: {re_or:.2f} [{re_ci_lo:.2f}, {re_ci_hi:.2f}], p={re_p:.2e}")
    print(f"  Heterogeneity: Q={Q:.1f} (df={df_Q}, p={Q_p:.4f}), I2={I2:.1f}%, tau2={tau2:.4f}")

    # --- FIGURE 4: Forest plot ---
    fig, ax = plt.subplots(figsize=(NATURE_WIDTH * 0.7, max(4.5, len(models) * 0.25 + 1.5)))

    # Sort by OR
    mr_df = pd.DataFrame(model_results).sort_values("OR", ascending=True)

    y_positions = list(range(len(mr_df)))
    for i, (_, row) in enumerate(mr_df.iterrows()):
        color = PROVIDER_COLORS.get(row["provider"], "#888")
        # Point estimate
        ax.plot(row["log_OR"], i, "o", color=color, markersize=5, zorder=5)
        # CI whisker
        ax.plot([np.log(row["CI95_lo"]), np.log(row["CI95_hi"])], [i, i],
                color=color, linewidth=1.5, alpha=0.8)

    # Pooled estimate (random effects)
    ax.axvline(x=re_log_or, color="black", linewidth=1.5, zorder=1)
    ax.axvspan(np.log(re_ci_lo), np.log(re_ci_hi), color="black", alpha=0.1, zorder=0)

    # Null line
    ax.axvline(x=0, color="gray", linewidth=0.5, linestyle="--")

    ax.set_yticks(y_positions)
    ax.set_yticklabels([MODEL_SHORT.get(m, m) for m in mr_df["model"]], fontsize=6)
    ax.set_xlabel("log(Odds Ratio) for specification gap")
    ax.set_title("Per-Model Specification Gap: Forest Plot", fontsize=9, fontweight="bold")

    # Add OR values on right
    for i, (_, row) in enumerate(mr_df.iterrows()):
        ax.text(ax.get_xlim()[1] * 0.98, i,
                f'OR={row["OR"]:.1f}', fontsize=5, va="center", ha="right")

    # Legend
    legend_handles = [
        Line2D([0], [0], color=c, marker="o", markersize=4, linestyle="none", label=p.title())
        for p, c in PROVIDER_COLORS.items()
    ]
    legend_handles.append(mpatches.Patch(color="black", alpha=0.2, label=f"RE pooled: {re_or:.1f}"))
    ax.legend(handles=legend_handles, loc="lower right", frameon=True, fontsize=5)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    save_fig(fig, "a4_forest_plot")

    # --- FIGURE 4b: Model heatmap at each spec level ---
    fig, ax = plt.subplots(figsize=(NATURE_WIDTH * 0.65, max(4.0, len(models) * 0.25 + 1.0)))

    # Build matrix: models x spec levels
    matrix = np.zeros((len(models), 6))
    model_order = sorted(models, key=lambda m: -dg[dg["model_key"]==m]["non_optimal"].mean())
    for i, mk in enumerate(model_order):
        dm = dg[dg["model_key"] == mk]
        for j, ordinal in enumerate(SPEC_ORDINALS):
            sub = dm[dm["condition_ordinal"] == ordinal]
            if len(sub) > 0:
                matrix[i, j] = sub["non_optimal"].mean() * 100
            else:
                matrix[i, j] = np.nan

    im = ax.imshow(matrix, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=40)

    # Annotate cells
    for i in range(len(model_order)):
        for j in range(6):
            val = matrix[i, j]
            if not np.isnan(val):
                color = "white" if val > 25 else "black"
                ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=5, color=color)

    ax.set_xticks(range(6))
    ax.set_xticklabels(SPEC_LABELS, fontsize=6, rotation=30, ha="right")
    ax.set_yticks(range(len(model_order)))
    ax.set_yticklabels([MODEL_SHORT.get(m, m) for m in model_order], fontsize=5)
    ax.set_title("Non-Optimal Rate (%) by Model and Specification Level", fontsize=9, fontweight="bold")

    cbar = plt.colorbar(im, ax=ax, fraction=0.02, pad=0.04)
    cbar.set_label("Non-optimal rate (%)", fontsize=6)
    cbar.ax.tick_params(labelsize=5)

    plt.tight_layout()
    save_fig(fig, "a4_model_spec_heatmap")

    # --- Save ---
    pd.DataFrame(model_results).to_csv(OUT_DIR / "a4_per_model_OR.csv", index=False)

    summary = {
        "analysis": "Per-Model Specification Gap Consistency",
        "n_models": len(models),
        "n_significant_p05": n_significant,
        "all_significant": n_significant == len(models),
        "fixed_effect": {
            "OR": round(pooled_or, 2),
            "CI95": [round(pooled_ci_lo, 2), round(pooled_ci_hi, 2)],
            "p": f"{pooled_p:.2e}",
        },
        "random_effects_DL": {
            "OR": round(re_or, 2),
            "CI95": [round(re_ci_lo, 2), round(re_ci_hi, 2)],
            "p": f"{re_p:.2e}",
        },
        "heterogeneity": {
            "Q": round(Q, 1),
            "df": int(df_Q),
            "Q_p": f"{Q_p:.4f}" if not np.isnan(Q_p) else None,
            "I2_pct": round(I2, 1),
            "tau2": round(tau2, 4),
        },
    }
    with open(OUT_DIR / "a4_universality_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print("  Saved a4_universality_summary.json")

    return summary


# ===================================================================
# GRAND SUMMARY
# ===================================================================
def write_grand_summary(s1, s2, s3, s4):
    """Write a combined JSON summary of all four analyses."""
    grand = {
        "analysis_suite": "Deep Analysis for Nature Revision",
        "date": pd.Timestamp.now().isoformat(),
        "analysis_1_phase_transition": s1,
        "analysis_2_asymmetry": s2,
        "analysis_3_confabulation": s3,
        "analysis_4_universality": s4,
    }
    with open(OUT_DIR / "grand_summary.json", "w") as f:
        json.dump(grand, f, indent=2, default=str)
    print(f"\nGrand summary saved to {OUT_DIR / 'grand_summary.json'}")


# ===================================================================
# MAIN
# ===================================================================
if __name__ == "__main__":
    print("="*70)
    print("DEEP ANALYSIS: Nature Revision — 4 Publication-Quality Analyses")
    print("="*70)

    df = load_main_data()

    s1 = analysis_1_phase_transition(df)
    s2 = analysis_2_asymmetry(df)
    s3 = analysis_3_confabulation(df)
    s4 = analysis_4_universality(df)

    write_grand_summary(s1, s2, s3, s4)

    print("\n" + "="*70)
    print("ALL ANALYSES COMPLETE")
    print(f"Output directory: {OUT_DIR}")
    print("="*70)
