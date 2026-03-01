"""
Generate Supplementary Figures for the spec-resistance paper.

5 supplementary figures complementing Supplementary Notes:
  S1: Confabulation gradient across conditions (Note 11)
  S2: Utility loss distributions by condition type (Note 16)
  S3: Brand familiarity composition of non-optimal choices (Notes 6, 7)
  S4: Cross-model correlation structure (Note 8)
  S5: Specification gap x price premium interaction (Notes 2, 12)

Usage:
    python analysis/generate_supplementary_figures.py
    python analysis/generate_supplementary_figures.py --only s1 s3
"""

import csv
import sys
import argparse
from collections import defaultdict
from pathlib import Path
from itertools import combinations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import numpy as np
from scipy import stats

# ══════════════════════════════════════════════════════════════════
# NATURE STYLE CONFIGURATION (matches main figures)
# ══════════════════════════════════════════════════════════════════

plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 7,
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "legend.fontsize": 6,
    "figure.dpi": 600,
    "savefig.dpi": 600,
    "savefig.bbox": "tight",
    "axes.linewidth": 0.4,
    "xtick.major.width": 0.4,
    "ytick.major.width": 0.4,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "lines.linewidth": 1.2,
    "patch.linewidth": 0.3,
})

NATURE_SINGLE_COL = 3.5
NATURE_1_5_COL    = 5.0
NATURE_DOUBLE_COL = 7.2

# Colours (match main figures exactly)
C_ANTHROPIC = "#2166AC"
C_OPENAI    = "#4DAC26"
C_GOOGLE    = "#D6604D"
C_OPEN_SRC  = "#7B3294"
GREY        = "#878787"
LIGHT_GREY  = "#E0E0E0"
RED         = "#CC0000"
GOLD        = "#B8860B"
TEAL        = "#1B9E77"

MODEL_META = {
    "claude-haiku-4.5":      {"colour": C_ANTHROPIC, "label": "Claude Haiku 4.5",      "provider": "Anthropic",  "proprietary": True},
    "claude-sonnet-4.6":     {"colour": C_ANTHROPIC, "label": "Claude Sonnet 4.6",     "provider": "Anthropic",  "proprietary": True},
    "gpt-4o":                {"colour": C_OPENAI,    "label": "GPT-4o",                "provider": "OpenAI",     "proprietary": True},
    "gpt-4o-mini":           {"colour": C_OPENAI,    "label": "GPT-4o Mini",           "provider": "OpenAI",     "proprietary": True},
    "gpt-4.1-mini":          {"colour": C_OPENAI,    "label": "GPT-4.1 Mini",          "provider": "OpenAI",     "proprietary": True},
    "gpt-4.1-nano":          {"colour": C_OPENAI,    "label": "GPT-4.1 Nano",          "provider": "OpenAI",     "proprietary": True},
    "gpt-5-mini":            {"colour": C_OPENAI,    "label": "GPT-5 Mini",            "provider": "OpenAI",     "proprietary": True},
    "gemini-2.0-flash":      {"colour": C_GOOGLE,    "label": "Gemini 2.0 Flash",      "provider": "Google",     "proprietary": True},
    "gemini-2.5-flash":      {"colour": C_GOOGLE,    "label": "Gemini 2.5 Flash",      "provider": "Google",     "proprietary": True},
    "gemini-2.5-flash-lite": {"colour": C_GOOGLE,    "label": "Gemini 2.5 Flash Lite", "provider": "Google",     "proprietary": True},
    "gemini-2.5-pro":        {"colour": C_GOOGLE,    "label": "Gemini 2.5 Pro",        "provider": "Google",     "proprietary": True},
    "gemini-3-flash":        {"colour": C_GOOGLE,    "label": "Gemini 3 Flash",        "provider": "Google",     "proprietary": True},
    "gemma-3-27b":           {"colour": C_GOOGLE,    "label": "Gemma 3 27B",           "provider": "Google",     "proprietary": False},
    "llama-3.3-70b":         {"colour": C_OPEN_SRC,  "label": "LLaMA 3.3 70B",        "provider": "Open-weight", "proprietary": False},
    "deepseek-v3":           {"colour": C_OPEN_SRC,  "label": "DeepSeek V3",           "provider": "Open-weight", "proprietary": False},
    "deepseek-r1":           {"colour": C_OPEN_SRC,  "label": "DeepSeek R1",           "provider": "Open-weight", "proprietary": False},
    "qwen-2.5-72b":          {"colour": C_OPEN_SRC,  "label": "Qwen 2.5 72B",         "provider": "Open-weight", "proprietary": False},
    "kimi-k2":               {"colour": C_OPEN_SRC,  "label": "Kimi K2",              "provider": "Open-weight", "proprietary": False},
}

MODEL_ORDER = [
    "claude-haiku-4.5", "claude-sonnet-4.6",
    "gpt-4o", "gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-5-mini",
    "gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro", "gemini-3-flash", "gemma-3-27b",
    "llama-3.3-70b", "deepseek-v3", "deepseek-r1", "qwen-2.5-72b", "kimi-k2",
]


# ══════════════════════════════════════════════════════════════════
# DATA LOADING & STATISTICS
# ══════════════════════════════════════════════════════════════════

def load_data(csv_path: str) -> list[dict]:
    known = set(MODEL_META.keys())
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    filtered = [r for r in rows if r.get("model_key", "") in known]
    print(f"  Loaded {len(rows)} rows, kept {len(filtered)} for {len(known)} known models")
    return filtered


def wilson_ci(n_success: int, n_total: int, z: float = 1.96):
    if n_total == 0:
        return 0.0, 0.0
    p = n_success / n_total
    denom = 1 + z**2 / n_total
    centre = (p + z**2 / (2 * n_total)) / denom
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n_total)) / n_total) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def rate_ci(rows, metric="non_optimal"):
    n = len(rows)
    if n == 0:
        return 0.0, 0.0, 0.0, 0
    n_opt = sum(1 for r in rows if r.get("chose_optimal") == "True")
    n_success = (n - n_opt) if metric == "non_optimal" else n_opt
    rate = n_success / n
    lo, hi = wilson_ci(n_success, n)
    return rate, lo, hi, n


def _save(fig, out_dir, name):
    for ext in ("png", "pdf"):
        path = out_dir / f"{name}.{ext}"
        fig.savefig(path, dpi=600 if ext == "png" else None,
                    facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"    [OK] {name}")


# ══════════════════════════════════════════════════════════════════
# SUPPLEMENTARY FIGURE S1: CONFABULATION GRADIENT
# ══════════════════════════════════════════════════════════════════

def s1_confabulation_gradient(data, out_dir):
    """
    Two-panel dot plot with CI whiskers:
    a) Confabulation rate across specification conditions
    b) Confabulation rate across anti-brand conditions
    """
    spec_conditions = [
        ("baseline", "Baseline"),
        ("utility_vague", "Util. vague"),
        ("preference_vague", "Pref. vague"),
        ("utility_weighted", "Util. weighted"),
        ("preference_weighted", "Pref. weighted"),
    ]

    anti_conditions = [
        ("baseline", "Baseline"),
        ("anti_brand_rejection", "Rejection"),
        ("anti_brand_negative_experience", "Neg. experience"),
        ("anti_brand_prefer_unknown", "Prefer unknown"),
    ]

    def confab_rate(rows_subset):
        non_opt = [r for r in rows_subset if r.get("chose_optimal") == "False"]
        if len(non_opt) == 0:
            return 0.0, 0.0, 0.0, 0
        n_confab = sum(1 for r in non_opt
                       if r.get("judge_brand_reasoning", "").strip() in ("False", "0", "0.0", ""))
        n = len(non_opt)
        rate = n_confab / n
        lo, hi = wilson_ci(n_confab, n)
        return rate, lo, hi, n

    by_cond = defaultdict(list)
    for r in data:
        by_cond[r["condition"]].append(r)

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(NATURE_DOUBLE_COL, 2.2))

    # Panel a: Specification gradient (horizontal dot plot)
    labels_a, rates_a, los_a, his_a = [], [], [], []
    for cond, label in spec_conditions:
        rate, lo, hi, n = confab_rate(by_cond.get(cond, []))
        labels_a.append(label)
        rates_a.append(rate * 100)
        los_a.append(rate * 100 - lo * 100)
        his_a.append(hi * 100 - rate * 100)

    y_a = np.arange(len(labels_a))
    colours_a = [GREY, C_OPENAI, C_ANTHROPIC, C_OPENAI, C_ANTHROPIC]
    ax_a.errorbar(rates_a, y_a, xerr=[los_a, his_a], fmt="none",
                  ecolor=GREY, elinewidth=0.6, capsize=2, capthick=0.4)
    ax_a.scatter(rates_a, y_a, c=colours_a, s=30, zorder=5, edgecolors="white", linewidths=0.4)
    ax_a.set_yticks(y_a)
    ax_a.set_yticklabels(labels_a)
    ax_a.set_xlabel("Confabulation rate (%)")
    ax_a.set_xlim(60, 100)
    ax_a.invert_yaxis()
    ax_a.set_title("a", fontweight="bold", loc="left", fontsize=9)
    ax_a.axvline(x=rates_a[0], color=GREY, linestyle="--", linewidth=0.4, alpha=0.5)

    # Panel b: Anti-brand gradient (horizontal dot plot)
    labels_b, rates_b, los_b, his_b = [], [], [], []
    for cond, label in anti_conditions:
        rate, lo, hi, n = confab_rate(by_cond.get(cond, []))
        labels_b.append(label)
        rates_b.append(rate * 100)
        los_b.append(rate * 100 - lo * 100)
        his_b.append(hi * 100 - rate * 100)

    y_b = np.arange(len(labels_b))
    colours_b = [GREY, RED, GOLD, TEAL]
    ax_b.errorbar(rates_b, y_b, xerr=[los_b, his_b], fmt="none",
                  ecolor=GREY, elinewidth=0.6, capsize=2, capthick=0.4)
    ax_b.scatter(rates_b, y_b, c=colours_b, s=30, zorder=5, edgecolors="white", linewidths=0.4)
    ax_b.set_yticks(y_b)
    ax_b.set_yticklabels(labels_b)
    ax_b.set_xlabel("Confabulation rate (%)")
    ax_b.set_xlim(0, 100)
    ax_b.invert_yaxis()
    ax_b.set_title("b", fontweight="bold", loc="left", fontsize=9)
    ax_b.axvline(x=rates_b[0], color=GREY, linestyle="--", linewidth=0.4, alpha=0.5)

    fig.tight_layout(w_pad=3)
    _save(fig, out_dir, "supp_fig1_confabulation_gradient")


# ══════════════════════════════════════════════════════════════════
# SUPPLEMENTARY FIGURE S2: UTILITY LOSS DISTRIBUTIONS
# ══════════════════════════════════════════════════════════════════

def s2_utility_loss(data, out_dir):
    """
    Two-panel figure:
    a) Box plots of utility loss by condition group (clean, no strip)
    b) Scatter: non-optimal rate vs mean utility loss per model at baseline
    """
    groups = {
        "Baseline": ["baseline"],
        "Spec. gradient": ["preference_vague", "preference_weighted", "utility_vague", "utility_weighted"],
        "Anti-brand": ["anti_brand_rejection", "anti_brand_negative_experience", "anti_brand_prefer_unknown"],
        "Price premium": ["baseline_price_premium"],
        "Mechanism": ["baseline_brand_blind", "baseline_description_minimal",
                       "baseline_expert_persona", "baseline_review_inverted"],
    }

    by_cond = defaultdict(list)
    for r in data:
        by_cond[r["condition"]].append(r)

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(NATURE_DOUBLE_COL, 2.5),
                                      gridspec_kw={"width_ratios": [1.3, 1]})

    # Panel a: Box plots
    group_names = list(groups.keys())
    group_colours = [GREY, C_ANTHROPIC, RED, GOLD, C_GOOGLE]
    all_losses = []
    for gname in group_names:
        conds = groups[gname]
        losses = []
        for c in conds:
            for r in by_cond.get(c, []):
                if r.get("chose_optimal") == "False":
                    try:
                        loss = float(r.get("utility_loss", 0))
                        if loss > 0:
                            losses.append(loss)
                    except (ValueError, TypeError):
                        pass
        all_losses.append(losses)

    positions = np.arange(len(group_names))
    bp = ax_a.boxplot(all_losses, positions=positions, widths=0.5, patch_artist=True,
                      showfliers=False,
                      medianprops=dict(color="black", linewidth=0.8),
                      whiskerprops=dict(linewidth=0.4),
                      capprops=dict(linewidth=0.4),
                      boxprops=dict(linewidth=0.4))
    for patch, colour in zip(bp["boxes"], group_colours):
        patch.set_facecolor(colour)
        patch.set_alpha(0.5)

    ax_a.set_xticks(positions)
    ax_a.set_xticklabels(group_names, fontsize=5.5)
    ax_a.set_ylabel("Utility loss")
    ax_a.set_title("a", fontweight="bold", loc="left", fontsize=9)

    # Panel b: Scatter per model
    baseline = by_cond.get("baseline", [])
    by_model = defaultdict(list)
    for r in baseline:
        by_model[r["model_key"]].append(r)

    x_vals, y_vals, colours = [], [], []
    for mk in MODEL_ORDER:
        rows = by_model.get(mk, [])
        if len(rows) < 10:
            continue
        rate, _, _, _ = rate_ci(rows, "non_optimal")
        non_opt = [r for r in rows if r.get("chose_optimal") == "False"]
        if len(non_opt) < 3:
            continue
        losses = []
        for r in non_opt:
            try:
                losses.append(float(r.get("utility_loss", 0)))
            except (ValueError, TypeError):
                pass
        if not losses:
            continue
        x_vals.append(rate * 100)
        y_vals.append(np.mean(losses))
        colours.append(MODEL_META[mk]["colour"])

    ax_b.scatter(x_vals, y_vals, c=colours, s=20, edgecolors="white", linewidths=0.3, zorder=3)

    if len(x_vals) > 2:
        slope, intercept, r_val, p_val, _ = stats.linregress(x_vals, y_vals)
        x_fit = np.linspace(min(x_vals), max(x_vals), 50)
        ax_b.plot(x_fit, slope * x_fit + intercept, color=GREY, linewidth=0.8,
                  linestyle="--", alpha=0.6)
        ax_b.text(0.95, 0.05, f"r = {r_val:.2f}",
                  transform=ax_b.transAxes, fontsize=6, ha="right", va="bottom", color=GREY)

    ax_b.set_xlabel("Non-optimal rate (%)")
    ax_b.set_ylabel("Mean utility loss")
    ax_b.set_title("b", fontweight="bold", loc="left", fontsize=9)

    # Provider legend
    handles = [mlines.Line2D([], [], marker="o", color=c, linestyle="", markersize=4,
               markeredgecolor="white", markeredgewidth=0.3, label=p)
               for p, c in [("Anthropic", C_ANTHROPIC), ("OpenAI", C_OPENAI),
                             ("Google", C_GOOGLE), ("Open-weight", C_OPEN_SRC)]]
    ax_b.legend(handles=handles, loc="upper left", frameon=False, fontsize=5)

    fig.tight_layout(w_pad=3)
    _save(fig, out_dir, "supp_fig2_utility_loss")


# ══════════════════════════════════════════════════════════════════
# SUPPLEMENTARY FIGURE S3: BRAND FAMILIARITY COMPOSITION
# ══════════════════════════════════════════════════════════════════

def s3_brand_composition(data, out_dir):
    """
    Compact horizontal stacked bar chart: brand familiarity composition of
    non-optimal choices across key conditions (5 most informative).
    """
    conditions = [
        ("baseline", "Baseline"),
        ("baseline_brand_blind", "Brand blind"),
        ("mechanism_attribute_swap", "Attribute swap"),
        ("anti_brand_rejection", "Anti-brand"),
        ("baseline_price_premium", "Price premium"),
    ]

    by_cond = defaultdict(list)
    for r in data:
        by_cond[r["condition"]].append(r)

    labels = []
    high_pcts, med_pcts, low_pcts = [], [], []

    for cond, label in conditions:
        non_opt = [r for r in by_cond.get(cond, []) if r.get("chose_optimal") == "False"]
        n = len(non_opt)
        if n == 0:
            labels.append(label)
            high_pcts.append(0)
            med_pcts.append(0)
            low_pcts.append(0)
            continue

        n_high = sum(1 for r in non_opt if r.get("chosen_brand_familiarity", "").strip() == "high")
        n_med = sum(1 for r in non_opt if r.get("chosen_brand_familiarity", "").strip() == "medium")
        n_low = sum(1 for r in non_opt if r.get("chosen_brand_familiarity", "").strip() == "low")

        labels.append(label)
        high_pcts.append(n_high / n * 100)
        med_pcts.append(n_med / n * 100)
        low_pcts.append(n_low / n * 100)

    fig, ax = plt.subplots(1, 1, figsize=(NATURE_SINGLE_COL, 1.8))

    y = np.arange(len(labels))
    bar_h = 0.55

    ax.barh(y, high_pcts, bar_h, label="High", color=C_GOOGLE, alpha=0.7)
    ax.barh(y, med_pcts, bar_h, left=high_pcts, label="Medium", color=GOLD, alpha=0.7)
    lefts_low = [h + m for h, m in zip(high_pcts, med_pcts)]
    ax.barh(y, low_pcts, bar_h, left=lefts_low, label="Low", color=C_OPENAI, alpha=0.7)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=6.5)
    ax.set_xlabel("Brand familiarity composition (%)")
    ax.set_xlim(0, 102)
    ax.invert_yaxis()
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.38), ncol=3,
              frameon=True, facecolor='white', edgecolor='none',
              fontsize=5.5, title="Familiarity", title_fontsize=5.5)

    fig.tight_layout()
    _save(fig, out_dir, "supp_fig3_brand_composition")


# ══════════════════════════════════════════════════════════════════
# SUPPLEMENTARY FIGURE S4: CROSS-MODEL CORRELATION STRUCTURE
# ══════════════════════════════════════════════════════════════════

def s4_correlation_structure(data, out_dir):
    """
    Two-panel figure:
    a) Heatmap of pairwise correlations (clean, no cell text)
    b) Distribution of within-provider vs cross-provider correlations
    """
    baseline = [r for r in data if r.get("condition") == "baseline"]
    by_model_assort = defaultdict(lambda: defaultdict(list))
    for r in baseline:
        by_model_assort[r["model_key"]][r["assortment_id"]].append(r)

    models_with_data = []
    for mk in MODEL_ORDER:
        assortments = by_model_assort.get(mk, {})
        if len(assortments) >= 5:
            models_with_data.append(mk)

    if len(models_with_data) < 3:
        print("    [SKIP] s4: insufficient model data")
        return

    all_assorts = set()
    for mk in models_with_data:
        all_assorts.update(by_model_assort[mk].keys())

    model_vectors = {}
    for mk in models_with_data:
        vec = {}
        for a in all_assorts:
            rows = by_model_assort[mk].get(a, [])
            if len(rows) >= 5:
                n_non_opt = sum(1 for r in rows if r.get("chose_optimal") == "False")
                vec[a] = n_non_opt / len(rows)
        model_vectors[mk] = vec

    n_models = len(models_with_data)
    corr_matrix = np.full((n_models, n_models), np.nan)
    within_corrs, cross_corrs = [], []

    for i, m1 in enumerate(models_with_data):
        for j, m2 in enumerate(models_with_data):
            if i == j:
                corr_matrix[i, j] = 1.0
                continue
            common = set(model_vectors[m1].keys()) & set(model_vectors[m2].keys())
            if len(common) < 5:
                continue
            v1 = [model_vectors[m1][a] for a in sorted(common)]
            v2 = [model_vectors[m2][a] for a in sorted(common)]
            if np.std(v1) == 0 or np.std(v2) == 0:
                continue
            r_val, _ = stats.pearsonr(v1, v2)
            corr_matrix[i, j] = r_val

            if i < j:
                prov1 = MODEL_META[m1]["provider"]
                prov2 = MODEL_META[m2]["provider"]
                if prov1 == prov2:
                    within_corrs.append(r_val)
                else:
                    cross_corrs.append(r_val)

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(NATURE_DOUBLE_COL, 3.2),
                                      gridspec_kw={"width_ratios": [1.4, 1]})

    # Panel a: Heatmap (no cell text)
    model_labels = [MODEL_META[mk]["label"] for mk in models_with_data]
    model_colours_y = [MODEL_META[mk]["colour"] for mk in models_with_data]

    masked = np.ma.masked_invalid(corr_matrix)
    im = ax_a.imshow(masked, cmap="RdBu_r", vmin=-0.2, vmax=1, aspect="auto")

    ax_a.set_xticks(range(n_models))
    ax_a.set_xticklabels(model_labels, rotation=45, ha="right", fontsize=4.5)
    ax_a.set_yticks(range(n_models))
    ax_a.set_yticklabels(model_labels, fontsize=4.5)

    for i, colour in enumerate(model_colours_y):
        ax_a.get_yticklabels()[i].set_color(colour)
        ax_a.get_xticklabels()[i].set_color(colour)

    cbar = fig.colorbar(im, ax=ax_a, shrink=0.7, aspect=20)
    cbar.set_label("Pearson r", fontsize=6)
    cbar.ax.tick_params(labelsize=5)
    ax_a.set_title("a", fontweight="bold", loc="left", fontsize=9)

    # Panel b: Within vs cross-provider histograms
    if within_corrs and cross_corrs:
        bins = np.linspace(0, 1, 20)
        ax_b.hist(within_corrs, bins=bins, alpha=0.55, color=C_ANTHROPIC,
                  label="Within-provider", edgecolor="white", linewidth=0.3)
        ax_b.hist(cross_corrs, bins=bins, alpha=0.55, color=C_OPEN_SRC,
                  label="Cross-provider", edgecolor="white", linewidth=0.3)

        ax_b.axvline(np.mean(within_corrs), color=C_ANTHROPIC, linestyle="--", linewidth=0.8)
        ax_b.axvline(np.mean(cross_corrs), color=C_OPEN_SRC, linestyle="--", linewidth=0.8)

        ax_b.set_xlabel("Pearson r")
        ax_b.set_ylabel("Count")
        ax_b.legend(loc="upper left", frameon=False, fontsize=5.5)

    ax_b.set_title("b", fontweight="bold", loc="left", fontsize=9)

    fig.tight_layout(w_pad=2)
    _save(fig, out_dir, "supp_fig4_correlation_structure")


# ══════════════════════════════════════════════════════════════════
# SUPPLEMENTARY FIGURE S5: SPECIFICATION GAP x PRICE PREMIUM
# ══════════════════════════════════════════════════════════════════

def s5_spec_gap_price(data, out_dir):
    """
    Two-panel figure: price premium effect decomposition.
    a) Per-model paired dot plot: baseline vs price premium, sorted by effect.
    b) 2x2 interaction: specification level x price condition with model dots.
    """
    by_cond = defaultdict(list)
    for r in data:
        by_cond[r["condition"]].append(r)

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(NATURE_DOUBLE_COL, 4.5),
                                      gridspec_kw={"width_ratios": [1.2, 1]})

    # ── Panel a: Per-model paired dot plot ──
    model_effects = []
    for mk in MODEL_ORDER:
        meta = MODEL_META.get(mk)
        if not meta:
            continue
        bl_rows = [r for r in by_cond.get("baseline", []) if r["model_key"] == mk]
        pp_rows = [r for r in by_cond.get("baseline_price_premium", []) if r["model_key"] == mk]
        if len(bl_rows) < 10 or len(pp_rows) < 10:
            continue
        bl_r, bl_lo, bl_hi, _ = rate_ci(bl_rows, "non_optimal")
        pp_r, pp_lo, pp_hi, _ = rate_ci(pp_rows, "non_optimal")
        delta = pp_r - bl_r
        model_effects.append((mk, bl_r, pp_r, delta, meta))

    model_effects.sort(key=lambda x: -x[3])  # sort by effect size (largest first)

    for i, (mk, bl_r, pp_r, delta, meta) in enumerate(model_effects):
        # Connecting line
        ax_a.plot([bl_r * 100, pp_r * 100], [i, i], color=LIGHT_GREY,
                  linewidth=0.8, zorder=1)
        # Baseline dot (open)
        ax_a.scatter(bl_r * 100, i, s=20, facecolors="none",
                     edgecolors=meta["colour"], linewidths=0.8, zorder=3, marker="o")
        # Price premium dot (filled)
        ax_a.scatter(pp_r * 100, i, s=20, color=meta["colour"],
                     edgecolors="white", linewidths=0.3, zorder=3, marker="o")

    ax_a.set_yticks(range(len(model_effects)))
    ax_a.set_yticklabels([MODEL_META[m[0]]["label"] for m in model_effects], fontsize=5.5)
    ax_a.set_xlabel("Non-optimal rate (%)")
    ax_a.invert_yaxis()
    ax_a.set_title("a", fontweight="bold", loc="left", fontsize=9)

    # Legend for open vs filled
    h_bl = mlines.Line2D([], [], color=GREY, marker="o", markersize=4,
                          markerfacecolor="none", markeredgecolor=GREY, linestyle="none",
                          label="Baseline price")
    h_pp = mlines.Line2D([], [], color=GREY, marker="o", markersize=4,
                          markerfacecolor=GREY, markeredgecolor="white", linestyle="none",
                          label="Price premium")
    ax_a.legend(handles=[h_bl, h_pp], fontsize=5.5, loc="lower right", frameon=True,
                framealpha=0.9, edgecolor="#CCCCCC", fancybox=False)

    # ── Panel b: 2x2 interaction with individual model dots ──
    interaction_conds = [
        ("baseline", "Baseline"),
        ("baseline_price_premium", "Price\npremium"),
        ("preference_explicit", "Explicit"),
        ("mechanism_price_premium", "Explicit +\npremium"),
    ]
    bar_colours = [C_ANTHROPIC, RED, C_ANTHROPIC, RED]

    for ci, (cond, label) in enumerate(interaction_conds):
        model_rates = []
        for mk in MODEL_ORDER:
            rows = [r for r in by_cond.get(cond, []) if r["model_key"] == mk]
            if len(rows) < 10:
                continue
            r, _, _, _ = rate_ci(rows, "non_optimal")
            model_rates.append((mk, r))

        if not model_rates:
            continue

        rates_only = [x[1] for x in model_rates]
        mean_r = np.mean(rates_only)
        lo_b, hi_b = (mean_r, mean_r)
        if len(rates_only) > 1:
            rng = np.random.RandomState(42)
            boot = np.array([np.mean(rng.choice(rates_only, size=len(rates_only), replace=True))
                             for _ in range(5000)])
            lo_b = float(np.percentile(boot, 2.5))
            hi_b = float(np.percentile(boot, 97.5))

        # Bar
        ax_b.bar(ci, mean_r * 100, width=0.6, color=bar_colours[ci], alpha=0.55,
                 edgecolor="white", linewidth=0.3)
        # CI whisker
        ax_b.errorbar(ci, mean_r * 100,
                      yerr=[[max(0, mean_r * 100 - lo_b * 100)], [hi_b * 100 - mean_r * 100]],
                      fmt="none", ecolor="#333333", elinewidth=0.5, capsize=2.5, capthick=0.4)
        # Individual model dots
        jitter = np.linspace(-0.15, 0.15, len(model_rates))
        for ji, (mk, r) in enumerate(model_rates):
            ax_b.scatter(ci + jitter[ji], r * 100, s=8,
                         color=MODEL_META[mk]["colour"], alpha=0.4,
                         edgecolors="none", zorder=4)

    ax_b.set_xticks(range(4))
    ax_b.set_xticklabels([c[1] for c in interaction_conds], fontsize=5.5)
    ax_b.set_ylabel("Non-optimal rate (%)")
    ax_b.set_title("b", fontweight="bold", loc="left", fontsize=9)

    fig.tight_layout(w_pad=2.5)
    _save(fig, out_dir, "supp_fig5_spec_gap_price")


# ══════════════════════════════════════════════════════════════════
# REGISTRY & MAIN
# ══════════════════════════════════════════════════════════════════

FIGURE_REGISTRY = {
    "s1": ("Supp Fig 1: Confabulation gradient", s1_confabulation_gradient),
    "s2": ("Supp Fig 2: Utility loss distributions", s2_utility_loss),
    "s3": ("Supp Fig 3: Brand familiarity composition", s3_brand_composition),
    "s4": ("Supp Fig 4: Cross-model correlations", s4_correlation_structure),
    "s5": ("Supp Fig 5: Spec gap x price premium", s5_spec_gap_price),
}


def main():
    parser = argparse.ArgumentParser(description="Generate supplementary figures")
    parser.add_argument("--only", nargs="+", help="Generate only these figures (e.g., s1 s3)")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent
    csv_path = base / "data" / "spec_resistance_CLEAN.csv"
    out_dir = base / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}")
        sys.exit(1)

    print("Loading data...")
    data = load_data(str(csv_path))

    targets = args.only if args.only else list(FIGURE_REGISTRY.keys())
    for key in targets:
        if key not in FIGURE_REGISTRY:
            print(f"  [SKIP] Unknown figure: {key}")
            continue
        label, func = FIGURE_REGISTRY[key]
        print(f"  Generating {label}...")
        try:
            func(data, out_dir)
        except Exception as e:
            print(f"    [FAIL] {label}: {e}")
            import traceback
            traceback.print_exc()

    print("Done.")


if __name__ == "__main__":
    main()
