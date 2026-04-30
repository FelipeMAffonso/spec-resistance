"""
Generate Nature-quality figures for Specification Resistance paper.

6 main figures + 10 Extended Data figures, all 18 models.
Reads from: OSF/data/spec_resistance_EXTENDED.csv
Outputs to: results/figures/

Usage:
    python analysis/generate_figures_nature.py
    python analysis/generate_figures_nature.py --only fig1 fig3 ed2
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
import matplotlib.gridspec as gridspec
import numpy as np
from scipy import stats

# ══════════════════════════════════════════════════════════════════
# NATURE STYLE CONFIGURATION
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

# Nature column widths in inches
NATURE_SINGLE_COL = 3.5     # 89 mm
NATURE_1_5_COL    = 5.0     # ~127 mm
NATURE_DOUBLE_COL = 7.2     # 183 mm

# ── Provider colours (muted, print-safe) ─────────────────────────
C_ANTHROPIC = "#2166AC"   # blue
C_OPENAI    = "#4DAC26"   # green
C_GOOGLE    = "#D6604D"   # orange-red
C_OPEN_SRC  = "#7B3294"   # purple

GREY       = "#878787"
LIGHT_GREY = "#E0E0E0"
RED        = "#CC0000"
TEAL       = "#2166AC"    # for "improvement" direction

# ── 18 models: colour, label, marker ─────────────────────────────

MODEL_META = {
    "claude-haiku-4.5":             {"colour": C_ANTHROPIC, "label": "Claude Haiku 4.5",            "marker": "o", "provider": "Anthropic",   "proprietary": True},
    "claude-haiku-4.5-thinking":    {"colour": C_ANTHROPIC, "label": "Claude Haiku 4.5 (think)",    "marker": "o", "provider": "Anthropic",   "proprietary": True},
    "claude-sonnet-4.6":            {"colour": C_ANTHROPIC, "label": "Claude Sonnet 4.6",           "marker": "s", "provider": "Anthropic",   "proprietary": True},
    "claude-sonnet-4.6-thinking":   {"colour": C_ANTHROPIC, "label": "Claude Sonnet 4.6 (think)",   "marker": "s", "provider": "Anthropic",   "proprietary": True},
    "claude-opus-4.6":              {"colour": C_ANTHROPIC, "label": "Claude Opus 4.6",             "marker": "D", "provider": "Anthropic",   "proprietary": True},
    "claude-opus-4.7":              {"colour": C_ANTHROPIC, "label": "Claude Opus 4.7",             "marker": "X", "provider": "Anthropic",   "proprietary": True},
    "gpt-4o":                       {"colour": C_OPENAI,    "label": "GPT-4o",                      "marker": "s", "provider": "OpenAI",      "proprietary": True},
    "gpt-4o-mini":                  {"colour": C_OPENAI,    "label": "GPT-4o Mini",                 "marker": "D", "provider": "OpenAI",      "proprietary": True},
    "gpt-4.1-mini":                 {"colour": C_OPENAI,    "label": "GPT-4.1 Mini",                "marker": "^", "provider": "OpenAI",      "proprietary": True},
    "gpt-4.1-nano":                 {"colour": C_OPENAI,    "label": "GPT-4.1 Nano",                "marker": "v", "provider": "OpenAI",      "proprietary": True},
    "gpt-5-mini":                   {"colour": C_OPENAI,    "label": "GPT-5 Mini",                  "marker": "P", "provider": "OpenAI",      "proprietary": True},
    "gpt-5.4":                      {"colour": C_OPENAI,    "label": "GPT-5.4",                     "marker": "*", "provider": "OpenAI",      "proprietary": True},
    "gpt-5.4-mini":                 {"colour": C_OPENAI,    "label": "GPT-5.4 Mini",                "marker": "h", "provider": "OpenAI",      "proprietary": True},
    "gpt-5.4-mini-thinking":        {"colour": C_OPENAI,    "label": "GPT-5.4 Mini (think)",        "marker": "h", "provider": "OpenAI",      "proprietary": True},
    "gpt-5.4-nano":                 {"colour": C_OPENAI,    "label": "GPT-5.4 Nano",                "marker": "p", "provider": "OpenAI",      "proprietary": True},
    "gemini-2.0-flash":             {"colour": C_GOOGLE,    "label": "Gemini 2.0 Flash",            "marker": "o", "provider": "Google",      "proprietary": True},
    "gemini-2.5-flash":             {"colour": C_GOOGLE,    "label": "Gemini 2.5 Flash",            "marker": "s", "provider": "Google",      "proprietary": True},
    "gemini-2.5-flash-lite":        {"colour": C_GOOGLE,    "label": "Gemini 2.5 Flash Lite",       "marker": "D", "provider": "Google",      "proprietary": True},
    "gemini-2.5-pro":               {"colour": C_GOOGLE,    "label": "Gemini 2.5 Pro",              "marker": "^", "provider": "Google",      "proprietary": True},
    "gemini-3-flash":               {"colour": C_GOOGLE,    "label": "Gemini 3 Flash",              "marker": "v", "provider": "Google",      "proprietary": True},
    "gemini-3-flash-thinking":      {"colour": C_GOOGLE,    "label": "Gemini 3 Flash (think)",      "marker": "v", "provider": "Google",      "proprietary": True},
    "gemini-3.1-pro":               {"colour": C_GOOGLE,    "label": "Gemini 3.1 Pro",              "marker": "*", "provider": "Google",      "proprietary": True},
    "gemini-3.1-flash-lite":        {"colour": C_GOOGLE,    "label": "Gemini 3.1 Flash Lite",       "marker": "X", "provider": "Google",      "proprietary": True},
    "gemma-3-27b":                  {"colour": C_GOOGLE,    "label": "Gemma 3 27B",                 "marker": "P", "provider": "Google",      "proprietary": False},
    "gemma-4-31b-it":               {"colour": C_GOOGLE,    "label": "Gemma 4 31B IT",              "marker": "h", "provider": "Google",      "proprietary": False},
    "llama-3.3-70b":                {"colour": C_OPEN_SRC,  "label": "LLaMA 3.3 70B",               "marker": "o", "provider": "Open-weight", "proprietary": False},
    "deepseek-v3":                  {"colour": C_OPEN_SRC,  "label": "DeepSeek V3",                 "marker": "s", "provider": "Open-weight", "proprietary": False},
    "deepseek-r1":                  {"colour": C_OPEN_SRC,  "label": "DeepSeek R1",                 "marker": "D", "provider": "Open-weight", "proprietary": False},
    "qwen-2.5-72b":                 {"colour": C_OPEN_SRC,  "label": "Qwen 2.5 72B",                "marker": "^", "provider": "Open-weight", "proprietary": False},
    "kimi-k2":                      {"colour": C_OPEN_SRC,  "label": "Kimi K2",                     "marker": "v", "provider": "Open-weight", "proprietary": False},
}

MODEL_ORDER = [
    "claude-haiku-4.5", "claude-haiku-4.5-thinking",
    "claude-sonnet-4.6", "claude-sonnet-4.6-thinking",
    "claude-opus-4.6", "claude-opus-4.7",
    "gpt-4o", "gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1-nano",
    "gpt-5-mini", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-mini-thinking", "gpt-5.4-nano",
    "gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro",
    "gemini-3-flash", "gemini-3-flash-thinking", "gemini-3.1-pro", "gemini-3.1-flash-lite",
    "gemma-3-27b", "gemma-4-31b-it",
    "llama-3.3-70b", "deepseek-v3", "deepseek-r1", "qwen-2.5-72b", "kimi-k2",
]

PROVIDER_ORDER = ["Anthropic", "OpenAI", "Google", "Open-weight"]
PROVIDER_COLOURS = {
    "Anthropic": C_ANTHROPIC, "OpenAI": C_OPENAI,
    "Google": C_GOOGLE, "Open-weight": C_OPEN_SRC,
}

PRECISION_LABELS = ["Baseline", "Vague", "Weighted", "Explicit", "Override", "Constrained"]

ALL_32_CONDITIONS_GROUPED = [
    ("Specification Gradient (U)", [
        "baseline", "utility_vague", "utility_weighted",
        "utility_explicit", "utility_override", "utility_constrained"]),
    ("Specification Gradient (P)", [
        "preference_vague", "preference_weighted",
        "preference_explicit", "preference_override", "preference_constrained"]),
    ("Controls", [
        "control_brand_reversal", "control_all_familiar",
        "control_comprehension", "control_fictional_brands"]),
    ("Anti-Brand", [
        "anti_brand_rejection", "anti_brand_prefer_unknown",
        "anti_brand_negative_experience"]),
    ("Mechanism (explicit)", [
        "mechanism_brand_blind", "mechanism_review_equalized",
        "mechanism_price_premium", "mechanism_description_minimal",
        "mechanism_attribute_swap"]),
    ("Mechanism (baseline)", [
        "baseline_brand_blind", "baseline_review_equalized",
        "baseline_price_premium", "baseline_description_minimal",
        "baseline_badges_removed", "baseline_review_inverted",
        "baseline_price_equalized", "baseline_optimal_first",
        "baseline_expert_persona"]),
]


# ══════════════════════════════════════════════════════════════════
# DATA LOADING & STATISTICS
# ══════════════════════════════════════════════════════════════════

def load_data(csv_path: str) -> list[dict]:
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    known = set(MODEL_META.keys())
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


def bootstrap_ci(values, n_boot=10000, ci=0.95):
    if len(values) < 2:
        m = np.mean(values) if len(values) else 0.0
        return m, m
    rng = np.random.RandomState(42)
    boot = np.array([np.mean(rng.choice(values, size=len(values), replace=True))
                     for _ in range(n_boot)])
    alpha = (1 - ci) / 2
    return float(np.percentile(boot, 100 * alpha)), float(np.percentile(boot, 100 * (1 - alpha)))


def safe_err(rate, lo, hi):
    return max(0, rate - lo), max(0, hi - rate)


def models_in_data(data):
    present = set(r["model_key"] for r in data)
    return [m for m in MODEL_ORDER if m in present]


def _filter(data, **kwargs):
    out = data
    for k, v in kwargs.items():
        if isinstance(v, (list, tuple, set)):
            out = [r for r in out if r.get(k) in v]
        else:
            out = [r for r in out if r.get(k) == v]
    return out


def _save(fig, out_dir, name):
    fig.savefig(out_dir / f"{name}.png")
    fig.savefig(out_dir / f"{name}.pdf")
    plt.close(fig)


def _panel_label(ax, label, x=-0.08, y=1.06):
    ax.text(x, y, label, transform=ax.transAxes, fontsize=11,
            fontweight="bold", va="top", ha="left")


def _provider_legend(ax, loc="upper right"):
    handles = [mpatches.Patch(color=PROVIDER_COLOURS[p], label=p, alpha=0.85)
               for p in PROVIDER_ORDER]
    ax.legend(handles=handles, loc=loc, frameon=True, framealpha=0.9,
              edgecolor="#CCCCCC", fancybox=False, fontsize=5.5)


def _provider_separators(ax, models, direction="vertical"):
    """Add subtle separator lines between provider groups."""
    prev_prov = None
    for i, m in enumerate(models):
        prov = MODEL_META[m]["provider"]
        if prev_prov is not None and prov != prev_prov:
            if direction == "vertical":
                ax.axvline(i - 0.5, color=LIGHT_GREY, linewidth=0.3, zorder=0)
            else:
                ax.axhline(i - 0.5, color=LIGHT_GREY, linewidth=0.3, zorder=0)
        prev_prov = prov


# ══════════════════════════════════════════════════════════════════
# FIGURE 2 | Baseline misalignment across 18 models
# Saves as: fig2_phenomenon.png
# ══════════════════════════════════════════════════════════════════

def fig1_phenomenon(data, out):
    """4-panel horizontal forest plot of baseline non-optimal rates, split by provider.

    Layout: 2x2 grid. Each panel lists that provider's models sorted within-panel
    by non-optimal rate (descending). Shared x-axis (0% to 65%) with a dashed
    vertical reference at the 25.0% overall baseline.
    """
    # Compute baseline rates for every model
    baseline_rates = {}
    all_rates = []
    for m in MODEL_META.keys():
        rows = _filter(data, model_key=m, condition="baseline")
        r, lo, hi, n = rate_ci(rows, "non_optimal")
        baseline_rates[m] = (r, lo, hi, n)
        all_rates.append(r)
    overall_mean = float(np.mean(all_rates))

    # Group models by provider
    by_provider = {p: [] for p in PROVIDER_ORDER}
    for m, meta in MODEL_META.items():
        by_provider[meta["provider"]].append(m)
    # Sort each panel's models by rate descending
    for p in by_provider:
        by_provider[p].sort(key=lambda m: -baseline_rates[m][0])

    # Work out a shared x-max with a little head-room
    x_max = max(hi for (_, _, hi, _) in baseline_rates.values()) * 1.10
    x_max = max(x_max, 0.65)

    fig, axes = plt.subplots(2, 2, figsize=(NATURE_DOUBLE_COL, 6.4), sharex=True)
    panel_letters = ["a", "b", "c", "d"]

    for ax, provider, letter in zip(axes.flat, PROVIDER_ORDER, panel_letters):
        models = by_provider[provider]
        y_pos = np.arange(len(models))

        for i, m in enumerate(models):
            r, lo, hi, n = baseline_rates[m]
            meta = MODEL_META[m]
            # CI whisker (darker than in the 30-model plot because each panel has fewer rows)
            ax.plot([lo, hi], [i, i], color=meta["colour"],
                    linewidth=1.6, alpha=0.55, solid_capstyle="round", zorder=2)
            # Dot
            ax.scatter(r, i, s=55, color=meta["colour"], marker=meta["marker"],
                       edgecolors="white", linewidths=0.6, zorder=3)

        # Overall-corpus reference line at 25.0%
        ax.axvline(overall_mean, linestyle="--", color=GREY, linewidth=0.7, zorder=0)

        ax.set_yticks(y_pos)
        ax.set_yticklabels([MODEL_META[m]["label"] for m in models], fontsize=9)
        ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
        ax.set_xlim(-0.02, x_max)
        ax.invert_yaxis()
        ax.set_title(provider, fontsize=11, fontweight="bold",
                     color=PROVIDER_COLOURS[provider], loc="left", pad=6)
        # Panel letter in upper-left corner
        ax.text(-0.18, 1.02, letter, transform=ax.transAxes,
                fontsize=12, fontweight="bold", va="bottom", ha="left")

    # Shared x-label only on the bottom row
    for ax in axes[1, :]:
        ax.set_xlabel("Non-optimal choice rate (baseline)")

    plt.tight_layout()
    _save(fig, out, "fig2_phenomenon")
    print("  [OK] Fig 2: 4-panel baseline by provider")


# ══════════════════════════════════════════════════════════════════
# FIGURE 2 | Control conditions confirm brand-specific origin
# Saves as: fig3_controls.png
# ══════════════════════════════════════════════════════════════════

def fig2_controls(data, out):
    """Bar chart: baseline vs 4 control conditions showing near-perfect performance."""
    models = models_in_data(data)

    conditions = [
        ("baseline", "Baseline"),
        ("control_fictional_brands", "Fictional\nbrands"),
        ("control_brand_reversal", "Brand\nreversal"),
        ("control_comprehension", "Compreh-\nension"),
        ("control_all_familiar", "All\nfamiliar"),
    ]

    fig, ax = plt.subplots(figsize=(NATURE_DOUBLE_COL, 2.5))

    x = np.arange(len(conditions))
    bar_colours = [GREY, C_ANTHROPIC, C_OPENAI, C_GOOGLE, C_OPEN_SRC]

    for ci, (cond, label) in enumerate(conditions):
        # Compute optimal rate for each model, then plot mean + individual dots
        model_rates = []
        for m in models:
            rows = _filter(data, model_key=m, condition=cond)
            r, _, _, n = rate_ci(rows, "optimal")
            if n > 0:
                model_rates.append(r)

        mean_r = np.mean(model_rates) if model_rates else 0
        lo_b, hi_b = bootstrap_ci(np.array(model_rates)) if len(model_rates) > 1 else (mean_r, mean_r)

        # Bar
        ax.bar(ci, mean_r, width=0.6, color=bar_colours[ci], alpha=0.75,
               edgecolor="white", linewidth=0.3)
        # CI whisker
        ax.errorbar(ci, mean_r, yerr=[[mean_r - lo_b], [hi_b - mean_r]],
                    fmt="none", ecolor="#333333", elinewidth=0.5, capsize=2.5, capthick=0.4)
        # Individual model dots
        jitter = np.linspace(-0.15, 0.15, len(model_rates))
        ax.scatter([ci + j for j in jitter], model_rates, s=6, color="#333333",
                   alpha=0.25, zorder=4, edgecolors="none")

    ax.set_xticks(x)
    ax.set_xticklabels([c[1] for c in conditions], fontsize=6)
    ax.set_ylabel("Optimal choice rate")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax.set_ylim(0, 1.05)
    ax.axhline(1.0, linestyle=":", color=LIGHT_GREY, linewidth=0.4, zorder=0)
    ax.axhline(0.2, linestyle=":", color=LIGHT_GREY, linewidth=0.4, zorder=0)

    plt.tight_layout()
    _save(fig, out, "fig3_controls")
    print("  [OK] Fig 2: Control conditions")


# ══════════════════════════════════════════════════════════════════
# FIGURE 3 | Specification gap: phase transition
# Saves as: fig4_specification_gap.png
# ══════════════════════════════════════════════════════════════════

def fig3_specification_gap(data, out):
    """Two-panel line plot with CI bands: preference and utility pathways.
    Panels clearly distinguished with descriptive subtitles."""
    models = models_in_data(data)
    fig, axes = plt.subplots(1, 2, figsize=(NATURE_DOUBLE_COL, 3.2), sharey=True)

    panel_configs = [
        (axes[0], "preference", "a",
         "Preference pathway",
         '"Performance matters most" → utility table → "select highest"'),
        (axes[1], "utility", "b",
         "Utility pathway",
         '"60% performance, 40% price" → pre-computed scores → "maximise U"'),
    ]

    for ax, spec_type, panel_label, subtitle, description in panel_configs:
        conditions_map = {
            0: "baseline",
            1: f"{spec_type}_vague",
            2: f"{spec_type}_weighted",
            3: f"{spec_type}_explicit",
            4: f"{spec_type}_override",
            5: f"{spec_type}_constrained",
        }

        # Phase transition zone with label
        ax.axvspan(2.0, 3.0, alpha=0.08, color=C_OPEN_SRC, zorder=0)
        ax.text(2.5, 0.52, "Gap", ha="center", fontsize=6, color=C_OPEN_SRC,
                fontweight="bold", alpha=0.6)

        for m in models:
            meta = MODEL_META[m]
            ordinals, rates, ci_lo_arr, ci_hi_arr = [], [], [], []

            for ordinal in range(6):
                cond = conditions_map[ordinal]
                subset = _filter(data, model_key=m, condition=cond)
                if not subset:
                    continue
                r, lo, hi, n = rate_ci(subset, "non_optimal")
                ordinals.append(ordinal)
                rates.append(r)
                ci_lo_arr.append(lo)
                ci_hi_arr.append(hi)

            if not ordinals:
                continue

            ax.fill_between(ordinals, ci_lo_arr, ci_hi_arr,
                            alpha=0.05, color=meta["colour"], zorder=2, linewidth=0)
            ax.plot(ordinals, rates, marker=meta["marker"], color=meta["colour"],
                    linewidth=0.8, markersize=3, zorder=3,
                    markeredgecolor="white", markeredgewidth=0.3, alpha=0.8)

        ax.set_xticks(range(6))
        ax.set_xticklabels(PRECISION_LABELS, rotation=35, ha="right")
        ax.set_xlabel("Specification precision")
        ax.set_ylim(-0.03, max(0.58, ax.get_ylim()[1]))
        ax.set_xlim(-0.3, 5.5)
        _panel_label(ax, panel_label)

        # Panel subtitle: what this pathway means
        ax.set_title(subtitle, fontsize=7.5, fontweight="bold",
                     color=C_OPEN_SRC if spec_type == "preference" else C_ANTHROPIC,
                     pad=12)
        # Description below title
        ax.text(0.5, 1.02, description, transform=ax.transAxes, fontsize=4.8,
                ha="center", va="bottom", color=GREY, fontstyle="italic")

        if ax == axes[0]:
            ax.set_ylabel("Non-optimal choice rate")
            ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))

    # Compact legend
    handles = [mpatches.Patch(color=PROVIDER_COLOURS[p], label=p, alpha=0.8)
               for p in PROVIDER_ORDER]
    axes[1].legend(handles=handles, loc="upper right", frameon=True, framealpha=0.9,
                   edgecolor="#CCCCCC", fancybox=False, fontsize=5)

    plt.tight_layout(w_pad=1.0)
    fig.subplots_adjust(top=0.88)
    _save(fig, out, "fig4_specification_gap")
    print("  [OK] Fig 3: Specification gap (line + CI bands)")


# ══════════════════════════════════════════════════════════════════
# FIGURE 4 | Conjoint: brand names drive misalignment
# Saves as: fig5_conjoint.png
# ══════════════════════════════════════════════════════════════════

def fig4_conjoint(data, out):
    """a: Baseline vs attribute-swap. b: Brand familiarity. c: Confabulation."""
    models = models_in_data(data)
    fig = plt.figure(figsize=(NATURE_DOUBLE_COL, 3.0))
    gs = gridspec.GridSpec(1, 3, width_ratios=[1.0, 0.7, 0.6], wspace=0.45)
    ax_a = fig.add_subplot(gs[0])
    ax_b = fig.add_subplot(gs[1])
    ax_c = fig.add_subplot(gs[2])

    # ── Panel a: baseline vs attribute-swap dot plot ──
    for mi, m in enumerate(models):
        meta = MODEL_META[m]
        bl_rows = _filter(data, model_key=m, condition="baseline")
        sw_rows = _filter(data, model_key=m, condition="mechanism_attribute_swap")
        bl_r, bl_lo, bl_hi, _ = rate_ci(bl_rows, "non_optimal")
        sw_r, sw_lo, sw_hi, _ = rate_ci(sw_rows, "non_optimal")

        # Connect baseline to swap
        ax_a.plot([bl_r, sw_r], [mi, mi], color=LIGHT_GREY, linewidth=0.6, zorder=1)
        # Baseline dot (open)
        ax_a.scatter(bl_r, mi, s=18, facecolors="none", edgecolors=meta["colour"],
                     linewidths=0.8, zorder=3, marker="o")
        # Swap dot (filled)
        ax_a.scatter(sw_r, mi, s=18, color=meta["colour"],
                     edgecolors="white", linewidths=0.3, zorder=3, marker="o")

    ax_a.set_yticks(range(len(models)))
    ax_a.set_yticklabels([MODEL_META[m]["label"] for m in models], fontsize=5)
    ax_a.set_xlabel("Non-optimal rate")
    ax_a.xaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax_a.invert_yaxis()

    # Legend for open vs filled
    h_bl = mlines.Line2D([], [], color=GREY, marker="o", markersize=4,
                          markerfacecolor="none", markeredgecolor=GREY, linestyle="none",
                          label="Baseline")
    h_sw = mlines.Line2D([], [], color=GREY, marker="o", markersize=4,
                          markerfacecolor=GREY, markeredgecolor="white", linestyle="none",
                          label="Attr. swap")
    ax_a.legend(handles=[h_bl, h_sw], fontsize=5, loc="lower right", frameon=True)
    # Inner panel labels suppressed: this figure now feeds into the combined
    # Figure 3 (mechanism evidence) where the outer "a"/"b" overlay is the
    # canonical Nature panel labelling. Inner letters would clash visually.
    # _panel_label(ax_a, "a", x=-0.22)

    # ── Panel b: brand familiarity of non-optimal swap choices ──
    swap_nonopt = [r for r in _filter(data, condition="mechanism_attribute_swap")
                   if r.get("chose_optimal") == "False"]
    fam_levels = ["high", "medium", "low"]
    fam_colours = {"high": RED, "medium": "#B8860B", "low": C_OPENAI}
    fam_labels = {"high": "High", "medium": "Medium", "low": "Low"}
    fam_counts = {f: sum(1 for r in swap_nonopt
                         if r.get("chosen_brand_familiarity", "") == f) for f in fam_levels}
    total = sum(fam_counts.values())
    fracs = [fam_counts[f] / total if total > 0 else 0 for f in fam_levels]

    ax_b.bar(range(3), fracs, width=0.6,
             color=[fam_colours[f] for f in fam_levels],
             alpha=0.8, edgecolor="white", linewidth=0.3)
    ax_b.set_xticks(range(3))
    ax_b.set_xticklabels([fam_labels[f] for f in fam_levels], fontsize=6)
    ax_b.set_ylabel("Fraction of non-optimal")
    ax_b.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax_b.set_xlabel("Brand familiarity")
    # _panel_label(ax_b, "b", x=-0.20)  # see fig4_conjoint:515 comment

    # ── Panel c: confabulation rate ──
    swap_nonopt_judged = [r for r in swap_nonopt if r.get("judge_brand_reasoning", "") != ""]
    n_judged = len(swap_nonopt_judged)
    n_brand_yes = sum(1 for r in swap_nonopt_judged
                      if r.get("judge_brand_reasoning", "").upper() in ("YES", "TRUE", "1"))
    n_brand_no = n_judged - n_brand_yes
    frac_yes = n_brand_yes / n_judged if n_judged > 0 else 0
    frac_no = n_brand_no / n_judged if n_judged > 0 else 0

    ax_c.bar(["Cites\nbrand", "Confab-\nulates"],
             [frac_yes, frac_no], width=0.55,
             color=[RED, GREY], alpha=0.75, edgecolor="white", linewidth=0.3)
    ax_c.set_ylabel("Fraction")
    ax_c.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    # _panel_label(ax_c, "c", x=-0.22)  # see fig4_conjoint:515 comment

    plt.tight_layout()
    _save(fig, out, "fig5_conjoint")
    print("  [OK] Fig 4: Conjoint decomposition")


# ══════════════════════════════════════════════════════════════════
# FIGURE 5 | Anti-brand correction asymmetry
# Saves as: fig6_anti_brand.png
# ══════════════════════════════════════════════════════════════════

def fig5_anti_brand(data, out):
    """Forest plot: mean effect per condition with individual model dots."""
    models = models_in_data(data)

    anti_conds = [
        ("anti_brand_negative_experience", "Negative experience"),
        ("anti_brand_rejection", "Brand rejection"),
        ("anti_brand_prefer_unknown", "Prefer unknown"),
    ]

    fig, ax = plt.subplots(figsize=(NATURE_DOUBLE_COL, 2.5))

    for ci, (cond, label) in enumerate(anti_conds):
        model_deltas = []
        for m in models:
            bl_rows = _filter(data, model_key=m, condition="baseline")
            cd_rows = _filter(data, model_key=m, condition=cond)
            bl_r, _, _, _ = rate_ci(bl_rows, "non_optimal")
            cd_r, _, _, _ = rate_ci(cd_rows, "non_optimal")
            model_deltas.append(cd_r - bl_r)

        mean_delta = np.mean(model_deltas)
        lo_b, hi_b = bootstrap_ci(np.array(model_deltas))
        bar_colour = RED if mean_delta > 0 else TEAL

        # Individual model dots (scattered)
        jitter = np.random.RandomState(ci).uniform(-0.12, 0.12, len(model_deltas))
        for di, delta in enumerate(model_deltas):
            dot_c = RED if delta > 0 else TEAL
            ax.scatter(delta, ci + jitter[di], s=8, color=dot_c,
                       alpha=0.3, edgecolors="none", zorder=2)

        # Mean CI whisker
        ax.plot([lo_b, hi_b], [ci, ci], color=bar_colour,
                linewidth=2.0, alpha=0.5, solid_capstyle="round", zorder=3)
        # Mean dot
        ax.scatter(mean_delta, ci, s=50, color=bar_colour, marker="D",
                   edgecolors="white", linewidths=0.5, zorder=4)

    ax.axvline(0, color="#333333", linewidth=0.5, zorder=1)
    ax.set_yticks(range(len(anti_conds)))
    ax.set_yticklabels([c[1] for c in anti_conds], fontsize=7)
    ax.set_xlabel("Change in non-optimal rate vs. baseline")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax.invert_yaxis()

    plt.tight_layout()
    _save(fig, out, "fig6_anti_brand")
    print("  [OK] Fig 5: Anti-brand correction (forest plot)")


# ══════════════════════════════════════════════════════════════════
# FIGURE 6 | Misalignment across model families
# Saves as: fig7_model_families.png
# ══════════════════════════════════════════════════════════════════

def fig6_model_families(data, out):
    """a: Provider dot plot at baseline. b: Open-source vs proprietary convergence."""
    models = models_in_data(data)
    fig, axes = plt.subplots(1, 2, figsize=(NATURE_DOUBLE_COL, 3.5),
                              gridspec_kw={"width_ratios": [1.2, 1]})

    # ── Panel a: per-model dot plot at 3 specification levels ──
    ax = axes[0]
    conds = [
        ("baseline", GREY, "o", "Baseline"),
        ("preference_weighted", C_OPENAI, "s", "Pref. weighted"),
        ("preference_explicit", C_ANTHROPIC, "D", "Pref. explicit"),
    ]

    for ci, (cond, colour, marker, label) in enumerate(conds):
        for mi, m in enumerate(models):
            rows = _filter(data, model_key=m, condition=cond)
            r, lo, hi, n = rate_ci(rows, "non_optimal")
            x_offset = (ci - 1) * 0.25
            ax.scatter(mi + x_offset, r, s=12, color=colour, marker=marker,
                       edgecolors="white", linewidths=0.2, zorder=3, alpha=0.8)

    # Add legend
    handles = [mlines.Line2D([], [], color=c[1], marker=c[2], markersize=4,
                              markeredgecolor="white", linestyle="none", label=c[3])
               for c in conds]
    ax.legend(handles=handles, fontsize=5, loc="upper right", frameon=True)

    ax.set_xticks(range(len(models)))
    ax.set_xticklabels([MODEL_META[m]["label"] for m in models],
                        fontsize=4.5, rotation=50, ha="right")
    ax.set_ylabel("Non-optimal choice rate")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    _provider_separators(ax, models, "vertical")
    _panel_label(ax, "a", x=-0.10)

    # ── Panel b: open-source vs proprietary convergence ──
    ax = axes[1]
    ordinal_conds = {
        0: "baseline", 1: "preference_vague", 2: "preference_weighted",
        3: "preference_explicit", 4: "preference_override", 5: "preference_constrained",
    }

    prop_models = [m for m in models if MODEL_META[m]["proprietary"]]
    open_models = [m for m in models if not MODEL_META[m]["proprietary"]]

    for model_set, label, colour, lstyle in [
        (prop_models, "Proprietary", C_OPENAI, "-"),
        (open_models, "Open-weight", C_OPEN_SRC, "--"),
    ]:
        ordinals, means, ci_los, ci_his = [], [], [], []
        for ord_val in range(6):
            cond = ordinal_conds[ord_val]
            model_rates = []
            for m in model_set:
                rows = _filter(data, model_key=m, condition=cond)
                r, _, _, n = rate_ci(rows, "non_optimal")
                if n > 0:
                    model_rates.append(r)
            if model_rates:
                ordinals.append(ord_val)
                means.append(np.mean(model_rates))
                lo_b, hi_b = bootstrap_ci(np.array(model_rates))
                ci_los.append(lo_b)
                ci_his.append(hi_b)

        if ordinals:
            ax.fill_between(ordinals, ci_los, ci_his, alpha=0.10, color=colour)
            ax.plot(ordinals, means, color=colour, linewidth=1.5, linestyle=lstyle,
                    label=label, marker="o", markersize=4,
                    markeredgecolor="white", markeredgewidth=0.3)

    ax.set_xticks(range(6))
    ax.set_xticklabels(PRECISION_LABELS, rotation=35, ha="right", fontsize=5.5)
    ax.set_xlabel("Specification precision")
    ax.set_ylabel("Non-optimal rate")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax.legend(fontsize=6, loc="upper right", frameon=True)
    _panel_label(ax, "b", x=-0.15)

    plt.tight_layout()
    _save(fig, out, "fig7_model_families")
    print("  [OK] Fig 6: Model families (dot plot + convergence)")


# ══════════════════════════════════════════════════════════════════
# EXTENDED DATA FIGURE 1 | Position and letter bias
# ══════════════════════════════════════════════════════════════════

def ed1_position_bias(data, out):
    models = models_in_data(data)
    baseline = _filter(data, condition="baseline")
    fig, axes = plt.subplots(1, 3, figsize=(NATURE_DOUBLE_COL, 3.0))

    # Panel a: choice by display position
    ax = axes[0]
    positions = []
    for r in baseline:
        try:
            positions.append(int(r.get("chosen_position", -1)))
        except (ValueError, TypeError):
            pass
    if positions:
        pos_counts = np.array([positions.count(i) for i in range(5)])
        total = sum(pos_counts)
        ax.bar(range(5), pos_counts / total, width=0.6, color=C_ANTHROPIC, alpha=0.7,
               edgecolor="white", linewidth=0.3)
        ax.axhline(0.2, linestyle="--", color=GREY, linewidth=0.5)
    ax.set_xlabel("Display position")
    ax.set_xticks(range(5))
    ax.set_xticklabels([f"{i+1}" for i in range(5)])
    ax.set_ylabel("Choice frequency")
    _panel_label(ax, "a", x=-0.15)

    # Panel b: optimal rate by optimal display position
    ax = axes[1]
    for pos_val in range(5):
        subset = [r for r in baseline
                  if r.get("optimal_display_position", "") == str(pos_val)]
        r_opt, lo, hi, n = rate_ci(subset, "optimal")
        err_lo, err_hi = safe_err(r_opt, lo, hi)
        ax.bar(pos_val, r_opt, width=0.6, color=C_GOOGLE, alpha=0.7,
               edgecolor="white", linewidth=0.3)
        ax.errorbar(pos_val, r_opt, yerr=[[err_lo], [err_hi]], fmt="none",
                    ecolor="#333333", elinewidth=0.5, capsize=2, capthick=0.4)
    ax.axhline(0.2, linestyle=":", color=GREY, linewidth=0.5)
    ax.set_xlabel("Optimal product position")
    ax.set_xticks(range(5))
    ax.set_xticklabels([f"{i+1}" for i in range(5)])
    ax.set_ylabel("Optimal choice rate")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    _panel_label(ax, "b", x=-0.15)

    # Panel c: letter choice distribution
    ax = axes[2]
    letters = ["A", "B", "C", "D", "E"]
    letter_counts = {ltr: 0 for ltr in letters}
    for r in baseline:
        ch = r.get("choice", "").strip().upper()
        if ch in letter_counts:
            letter_counts[ch] += 1
    total_letters = sum(letter_counts.values())
    fracs = [letter_counts[l] / total_letters if total_letters > 0 else 0 for l in letters]

    ax.bar(range(5), fracs, width=0.6, color=C_OPEN_SRC, alpha=0.7,
           edgecolor="white", linewidth=0.3)
    ax.axhline(0.2, linestyle="--", color=GREY, linewidth=0.5)
    ax.set_xlabel("Choice letter")
    ax.set_xticks(range(5))
    ax.set_xticklabels(letters)
    ax.set_ylabel("Choice frequency")
    _panel_label(ax, "c", x=-0.15)

    plt.tight_layout()
    _save(fig, out, "ed1_position_bias")
    print("  [OK] ED Fig 1: Position and letter bias")


# ══════════════════════════════════════════════════════════════════
# EXTENDED DATA FIGURE 2 | 32-condition heatmap
# ══════════════════════════════════════════════════════════════════

def ed2_condition_heatmap(data, out):
    """All conditions x models heatmap with vertical bracket group labels."""
    models = models_in_data(data)

    # Human-readable condition labels
    COND_DISPLAY = {
        "baseline": "Baseline",
        "utility_vague": "Util. vague", "utility_weighted": "Util. weighted",
        "utility_explicit": "Util. explicit", "utility_override": "Util. override",
        "utility_constrained": "Util. constrained",
        "preference_vague": "Pref. vague", "preference_weighted": "Pref. weighted",
        "preference_explicit": "Pref. explicit", "preference_override": "Pref. override",
        "preference_constrained": "Pref. constrained",
        "control_brand_reversal": "Brand reversal",
        "control_all_familiar": "All familiar",
        "control_comprehension": "Comprehension",
        "control_fictional_brands": "Fictional brands",
        "anti_brand_rejection": "Rejection",
        "anti_brand_prefer_unknown": "Prefer unknown",
        "anti_brand_negative_experience": "Neg. experience",
        "mechanism_brand_blind": "Brand blind (E)",
        "mechanism_review_equalized": "Reviews eq. (E)",
        "mechanism_price_premium": "Price prem. (E)",
        "mechanism_description_minimal": "Desc. min. (E)",
        "mechanism_attribute_swap": "Attr. swap (E)",
        "baseline_brand_blind": "Brand blind",
        "baseline_review_equalized": "Reviews eq.",
        "baseline_review_inverted": "Reviews inv.",
        "baseline_price_premium": "Price prem. (+10%)",
        "baseline_price_equalized": "Price eq.",
        "baseline_description_minimal": "Desc. minimal",
        "baseline_badges_removed": "Badges removed",
        "baseline_optimal_first": "Optimal first",
        "baseline_expert_persona": "Expert persona",
    }

    GROUP_COLOURS = {
        "Specification Gradient (U)": C_ANTHROPIC,
        "Specification Gradient (P)": C_OPEN_SRC,
        "Controls": C_OPENAI,
        "Anti-Brand": RED,
        "Mechanism (explicit)": "#B8860B",
        "Mechanism (baseline)": C_GOOGLE,
    }
    GROUP_SHORT = {
        "Specification Gradient (U)": "Spec. (U)",
        "Specification Gradient (P)": "Spec. (P)",
        "Controls": "Controls",
        "Anti-Brand": "Anti-brand",
        "Mechanism (explicit)": "Mech. (E)",
        "Mechanism (baseline)": "Mech. (B)",
    }

    all_conds = []
    group_starts = []
    group_labels = []
    for grp_label, conds in ALL_32_CONDITIONS_GROUPED:
        group_starts.append(len(all_conds))
        group_labels.append(grp_label)
        all_conds.extend(conds)
    group_starts.append(len(all_conds))

    n_conds = len(all_conds)
    n_models = len(models)
    rate_matrix = np.full((n_conds, n_models), np.nan)

    for ci, cond in enumerate(all_conds):
        for mi, m in enumerate(models):
            subset = _filter(data, model_key=m, condition=cond)
            if subset:
                r, _, _, _ = rate_ci(subset, "non_optimal")
                rate_matrix[ci, mi] = r

    # Larger figure with auto aspect so cells become readable rectangles
    fig, ax = plt.subplots(figsize=(NATURE_DOUBLE_COL, 8.6))

    im = ax.imshow(rate_matrix, cmap="YlOrRd", aspect="auto", vmin=0.0, vmax=0.45,
                   interpolation="nearest")

    # Group separators (heavy white lines between condition groups)
    for gs_idx in group_starts[1:-1]:
        ax.axhline(y=gs_idx - 0.5, color="white", linewidth=2.4)

    # Provider separators on x-axis
    _provider_separators(ax, models, "vertical")

    ax.set_xticks(range(n_models))
    xlabels = [MODEL_META[m]["label"] for m in models]
    ax.set_xticklabels(xlabels, fontsize=8, rotation=55, ha="right",
                       rotation_mode="anchor")
    for ti, m in enumerate(models):
        ax.get_xticklabels()[ti].set_color(MODEL_META[m]["colour"])

    cond_labels_display = [COND_DISPLAY.get(c, c.replace("_", " ")) for c in all_conds]
    ax.set_yticks(range(n_conds))
    ax.set_yticklabels(cond_labels_display, fontsize=8)

    # Vertical bracket group labels on right side
    x_bracket = n_models + 0.4
    for gi in range(len(group_labels)):
        y_top = group_starts[gi]
        y_bot = group_starts[gi + 1] - 1
        mid_y = (y_top + y_bot) / 2
        grp_col = GROUP_COLOURS.get(group_labels[gi], GREY)
        short_lbl = GROUP_SHORT.get(group_labels[gi], group_labels[gi])

        # Vertical line bracket (thicker, more visible)
        ax.plot([x_bracket, x_bracket], [y_top - 0.4, y_bot + 0.4],
                color=grp_col, linewidth=1.6, clip_on=False)
        ax.plot([x_bracket - 0.2, x_bracket], [y_top - 0.4, y_top - 0.4],
                color=grp_col, linewidth=1.6, clip_on=False)
        ax.plot([x_bracket - 0.2, x_bracket], [y_bot + 0.4, y_bot + 0.4],
                color=grp_col, linewidth=1.6, clip_on=False)
        ax.text(x_bracket + 0.35, mid_y, short_lbl, fontsize=8.5, fontweight="bold",
                color=grp_col, va="center", ha="left", rotation=0, clip_on=False)

    # Colorbar (bigger labels)
    cbar = plt.colorbar(im, ax=ax, fraction=0.025, pad=0.14, shrink=0.6)
    cbar.ax.tick_params(labelsize=8)
    cbar.set_label("Non-optimal choice rate", fontsize=9)
    cbar.ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))

    plt.tight_layout()
    _save(fig, out, "ed2_condition_heatmap")
    print("  [OK] ED Fig 2: 32-condition heatmap")


# ══════════════════════════════════════════════════════════════════
# EXTENDED DATA FIGURE 3 | Dose-response for all 18 models
# ══════════════════════════════════════════════════════════════════

def ed3_dose_response(data, out):
    models = models_in_data(data)
    n = len(models)
    ncols = 6
    nrows = int(np.ceil(n / ncols))

    fig, axes_flat = plt.subplots(nrows, ncols, figsize=(NATURE_DOUBLE_COL, nrows * 2.0),
                                   sharex=True, sharey=True)
    axes = axes_flat.flatten() if hasattr(axes_flat, 'flatten') else [axes_flat]

    spec_labels_short = ["B", "V", "W", "E", "O", "C"]

    for mi, m in enumerate(models):
        ax = axes[mi]
        meta = MODEL_META[m]

        # Light grey shading for specification gap zone (weighted → explicit)
        ax.axvspan(2.0, 3.0, alpha=0.06, color=C_OPEN_SRC, zorder=0)

        for spec_type, colour, lstyle, lw in [
            ("utility", C_ANTHROPIC, "-", 1.4),
            ("preference", C_OPEN_SRC, "--", 1.4),
        ]:
            conds_map = {
                0: "baseline",
                1: f"{spec_type}_vague",
                2: f"{spec_type}_weighted",
                3: f"{spec_type}_explicit",
                4: f"{spec_type}_override",
                5: f"{spec_type}_constrained",
            }
            ordinals, rates, ci_lo_arr, ci_hi_arr = [], [], [], []
            for ordinal in range(6):
                subset = _filter(data, model_key=m, condition=conds_map[ordinal])
                if not subset:
                    continue
                r, lo, hi, n_obs = rate_ci(subset, "non_optimal")
                ordinals.append(ordinal)
                rates.append(r)
                ci_lo_arr.append(lo)
                ci_hi_arr.append(hi)

            if ordinals:
                ax.fill_between(ordinals, ci_lo_arr, ci_hi_arr,
                                alpha=0.12, color=colour, linewidth=0)
                ax.plot(ordinals, rates, color=colour, linewidth=lw,
                        linestyle=lstyle, marker="o", markersize=3.5,
                        markeredgecolor="white", markeredgewidth=0.3)

        ax.set_title(meta["label"], fontsize=6.5, color=meta["colour"], fontweight="bold",
                     pad=3)
        ax.set_xticks(range(6))
        # Show x labels on bottom row
        if mi >= (nrows - 1) * ncols:
            ax.set_xticklabels(spec_labels_short, fontsize=5.5)
        else:
            ax.set_xticklabels([])
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
        ax.set_ylim(-0.03, 0.60)
        ax.tick_params(axis="both", labelsize=5.5)

    for i in range(n, len(axes)):
        axes[i].set_visible(False)

    u_line = mlines.Line2D([], [], color=C_ANTHROPIC, linewidth=1.5, label="Utility pathway")
    p_line = mlines.Line2D([], [], color=C_OPEN_SRC, linewidth=1.5, linestyle="--",
                            label="Preference pathway")
    # Legend sits ABOVE the supxlabel to avoid horizontal overlap with the
    # specification-precision tick-letter glossary. bbox_to_anchor y=0.05 puts
    # the legend in the bottom margin reserved by subplots_adjust(bottom=0.12).
    fig.legend(handles=[u_line, p_line], loc="lower center", ncol=2, fontsize=7.5,
               frameon=True, framealpha=0.95, edgecolor="#CCCCCC",
               bbox_to_anchor=(0.5, 0.05))

    fig.supxlabel("Specification precision  (B = Baseline, V = Vague, W = Weighted, "
                  "E = Explicit, O = Override, C = Constrained)",
                  fontsize=7, y=0.01)
    fig.supylabel("Non-optimal choice rate", fontsize=8, x=0.01)

    plt.tight_layout(h_pad=1.0, w_pad=0.8)
    fig.subplots_adjust(bottom=0.12)
    _save(fig, out, "ed3_dose_response")
    print("  [OK] ED Fig 3: Dose-response curves")


# ══════════════════════════════════════════════════════════════════
# EXTENDED DATA FIGURE 4 | Baseline mechanism forest plot
# ══════════════════════════════════════════════════════════════════

def ed4_baseline_mechanisms(data, out):
    baseline_mechs = [
        ("baseline_brand_blind", "Brand names removed"),
        ("baseline_review_equalized", "Reviews equalized"),
        ("baseline_review_inverted", "Reviews inverted"),
        ("baseline_price_premium", "Price premium (+10%)"),
        ("baseline_price_equalized", "Price equalized"),
        ("baseline_description_minimal", "Minimal descriptions"),
        ("baseline_badges_removed", "Badges removed"),
        ("baseline_optimal_first", "Optimal listed first"),
        ("baseline_expert_persona", "Expert persona"),
    ]

    mech_effects = []
    for cond, label in baseline_mechs:
        bl_all = _filter(data, condition="baseline")
        mech_all = _filter(data, condition=cond)
        bl_r, _, _, _ = rate_ci(bl_all, "non_optimal")
        mech_r, mech_lo, mech_hi, n_mech = rate_ci(mech_all, "non_optimal")
        delta = mech_r - bl_r
        delta_lo = mech_lo - bl_r
        delta_hi = mech_hi - bl_r
        mech_effects.append((label, delta, delta_lo, delta_hi))

    mech_effects.sort(key=lambda x: x[1])

    fig, ax = plt.subplots(figsize=(NATURE_DOUBLE_COL, 3.5))
    y_pos = np.arange(len(mech_effects))

    for yi, (label, delta, delta_lo, delta_hi) in enumerate(mech_effects):
        colour = TEAL if delta < 0 else RED
        ax.plot([delta_lo, delta_hi], [yi, yi], color=colour,
                linewidth=1.5, alpha=0.35, solid_capstyle="round")
        ax.scatter(delta, yi, s=35, color=colour, edgecolors="white",
                   linewidths=0.5, zorder=3)

    ax.axvline(0, color="#333333", linewidth=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([m[0] for m in mech_effects], fontsize=6.5)
    ax.set_xlabel("Change in non-optimal rate vs. baseline")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax.invert_yaxis()

    plt.tight_layout()
    _save(fig, out, "ed4_baseline_mechanisms")
    print("  [OK] ED Fig 4: Baseline mechanism forest plot")


# ══════════════════════════════════════════════════════════════════
# EXTENDED DATA FIGURE 5 | Paraphrase robustness
# ══════════════════════════════════════════════════════════════════

def ed5_paraphrase(data, out):
    models = models_in_data(data)
    key_conds = [
        ("baseline", "Baseline"),
        ("preference_weighted", "Pref. weighted"),
        ("utility_explicit", "Util. explicit"),
        ("anti_brand_rejection", "Anti-brand rejection"),
        ("mechanism_brand_blind", "Brand blind (explicit)"),
    ]
    panel_labels = ["a", "b", "c", "d", "e"]

    # 3 rows x 2 cols grid, last cell empty
    fig, axes_flat = plt.subplots(3, 2, figsize=(NATURE_DOUBLE_COL, 6.0), sharey=True)
    axes = axes_flat.flatten()

    for ci, (cond, title) in enumerate(key_conds):
        ax = axes[ci]
        paraphrase_indices = sorted(set(
            r.get("paraphrase_index", "0") for r in _filter(data, condition=cond)))

        for mi, m in enumerate(models):
            meta = MODEL_META[m]
            para_rates = []
            for pi in paraphrase_indices:
                subset = _filter(data, model_key=m, condition=cond, paraphrase_index=pi)
                if subset:
                    r, _, _, _ = rate_ci(subset, "non_optimal")
                    para_rates.append(r)

            if para_rates:
                mean_r = np.mean(para_rates)
                ax.plot([min(para_rates), max(para_rates)], [mi, mi],
                        color=meta["colour"], linewidth=1.2, alpha=0.4)
                ax.scatter(para_rates, [mi] * len(para_rates),
                           s=12, color=meta["colour"], alpha=0.6,
                           edgecolors="white", linewidths=0.2, zorder=3)
                ax.scatter(mean_r, mi, s=22, marker="D", color=meta["colour"],
                           edgecolors="white", linewidths=0.4, zorder=4)

        ax.set_title(title, fontsize=7, fontweight="bold", color="#333333")
        ax.set_yticks(range(len(models)))
        if ci % 2 == 0:  # left column gets y labels
            ax.set_yticklabels([MODEL_META[m]["label"] for m in models], fontsize=5.5)
        else:
            ax.set_yticklabels([])
        ax.set_xlabel("Non-optimal rate", fontsize=6.5)
        ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
        ax.invert_yaxis()
        _panel_label(ax, panel_labels[ci], x=-0.12 if ci % 2 == 0 else -0.06)

    # Hide the 6th (empty) panel
    axes[5].set_visible(False)

    plt.tight_layout(h_pad=1.5, w_pad=1.0)
    _save(fig, out, "ed5_paraphrase")
    print("  [OK] ED Fig 5: Paraphrase robustness")


# ══════════════════════════════════════════════════════════════════
# EXTENDED DATA FIGURE 6 | Provider and cost effects
# ══════════════════════════════════════════════════════════════════

def ed6_provider_effects(data, out):
    models = models_in_data(data)
    fig, axes = plt.subplots(1, 2, figsize=(NATURE_DOUBLE_COL, 3.5))

    # Panel a: provider comparison at 3 levels (dot plot)
    ax = axes[0]
    conds = [("baseline", "Baseline"), ("preference_weighted", "Pref. weighted"),
             ("preference_explicit", "Pref. explicit")]
    markers = ["o", "s", "D"]

    for ci, (cond, clabel) in enumerate(conds):
        for pi, prov in enumerate(PROVIDER_ORDER):
            prov_models = [m for m in models if MODEL_META[m]["provider"] == prov]
            prov_rates = []
            for m in prov_models:
                rows = _filter(data, model_key=m, condition=cond)
                r, _, _, n = rate_ci(rows, "non_optimal")
                if n > 0:
                    prov_rates.append(r)
            mean_r = np.mean(prov_rates) if prov_rates else 0
            x_offset = (ci - 1) * 0.22
            ax.scatter(pi + x_offset, mean_r, s=30, color=PROVIDER_COLOURS[prov],
                       marker=markers[ci], edgecolors="white", linewidths=0.3, zorder=3)

    # Legend
    handles = [mlines.Line2D([], [], color=GREY, marker=markers[ci], markersize=4,
                              markeredgecolor="white", linestyle="none", label=conds[ci][1])
               for ci in range(len(conds))]
    ax.legend(handles=handles, fontsize=5.5, loc="upper right", frameon=True)

    ax.set_xticks(range(len(PROVIDER_ORDER)))
    ax.set_xticklabels(PROVIDER_ORDER, fontsize=6.5)
    ax.set_ylabel("Non-optimal choice rate")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    _panel_label(ax, "a", x=-0.15)

    # Panel b: cost vs non-optimal
    ax = axes[1]
    costs, nonopt_rates, scatter_models = [], [], []

    for m in models:
        rows = _filter(data, model_key=m, condition="baseline")
        r, _, _, n = rate_ci(rows, "non_optimal")
        if n > 0:
            trial_costs = []
            for row in rows:
                try:
                    trial_costs.append(float(row.get("cost_usd", 0)))
                except (ValueError, TypeError):
                    pass
            if trial_costs:
                costs.append(np.mean(trial_costs))
                nonopt_rates.append(r)
                scatter_models.append(m)

    if costs:
        costs_arr = np.array(costs)
        rates_arr = np.array(nonopt_rates)

        for i, m in enumerate(scatter_models):
            meta = MODEL_META[m]
            ax.scatter(costs_arr[i], rates_arr[i], s=25, color=meta["colour"],
                       marker=meta["marker"], edgecolors="white", linewidths=0.3, zorder=3)

        if len(costs) > 3:
            log_costs = np.log10(costs_arr + 1e-8)
            slope, intercept, r_val, p_val, _ = stats.linregress(log_costs, rates_arr)
            x_fit = np.linspace(log_costs.min(), log_costs.max(), 100)
            ax.plot(10**x_fit, slope * x_fit + intercept, color=GREY,
                    linewidth=0.8, linestyle="--", alpha=0.5)
            ax.text(0.05, 0.95, f"r = {r_val:.2f}, p = {p_val:.3f}",
                    transform=ax.transAxes, fontsize=5.5, color=GREY, va="top")

        ax.set_xscale("log")
        ax.set_xlabel("Avg. cost per trial (USD, log scale)")
        ax.set_ylabel("Non-optimal rate (baseline)")
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    _panel_label(ax, "b", x=-0.15)

    plt.tight_layout()
    _save(fig, out, "ed6_provider_effects")
    print("  [OK] ED Fig 6: Provider and cost effects")


# ══════════════════════════════════════════════════════════════════
# EXTENDED DATA FIGURE 7 | Category heatmap
# ══════════════════════════════════════════════════════════════════

def ed7_category_heatmap(data, out):
    """Category x model heatmap. No cell annotations."""
    models = models_in_data(data)
    categories = sorted(set(r.get("category", "") for r in data if r.get("category", "")))

    n_cats = len(categories)
    n_models = len(models)
    rate_matrix = np.full((n_cats, n_models), np.nan)

    for ci, cat in enumerate(categories):
        for mi, m in enumerate(models):
            subset = _filter(data, model_key=m, category=cat, condition="baseline")
            if subset:
                r, _, _, _ = rate_ci(subset, "non_optimal")
                rate_matrix[ci, mi] = r

    mean_rates = np.nanmean(rate_matrix, axis=1)
    sort_idx = np.argsort(-mean_rates)
    rate_matrix = rate_matrix[sort_idx]
    categories_sorted = [categories[i] for i in sort_idx]

    fig, ax = plt.subplots(figsize=(7.5, max(4, n_cats * 0.32)))
    im = ax.imshow(rate_matrix, cmap="YlOrRd", aspect="auto", vmin=0.0, vmax=0.50)

    ax.set_xticks(range(n_models))
    ax.set_xticklabels([MODEL_META[m]["label"] for m in models],
                        fontsize=5, rotation=45, ha="right")
    ax.set_yticks(range(n_cats))
    ax.set_yticklabels([c.replace("_", " ").title() for c in categories_sorted], fontsize=6)

    cbar = plt.colorbar(im, ax=ax, fraction=0.025, pad=0.04, shrink=0.8)
    cbar.ax.tick_params(labelsize=5)
    cbar.set_label("Non-optimal choice rate (baseline)", fontsize=6)

    plt.tight_layout()
    _save(fig, out, "ed7_category_heatmap")
    print("  [OK] ED Fig 7: Category heatmap")


# ══════════════════════════════════════════════════════════════════
# EXTENDED DATA FIGURE 8 | LLM-as-judge evaluation
# ══════════════════════════════════════════════════════════════════

def ed8_judge(data, out):
    models = models_in_data(data)
    baseline = _filter(data, condition="baseline")
    fig, axes = plt.subplots(1, 3, figsize=(NATURE_DOUBLE_COL, 3.5))

    # Panel a: coherence optimal vs non-optimal
    ax = axes[0]
    for mi, m in enumerate(models):
        meta = MODEL_META[m]
        opt_rows = [r for r in _filter(baseline, model_key=m) if r.get("chose_optimal") == "True"]
        nonopt_rows = [r for r in _filter(baseline, model_key=m) if r.get("chose_optimal") == "False"]

        opt_coh = [float(r.get("judge_coherence", "")) for r in opt_rows
                   if r.get("judge_coherence", "") not in ("", None)]
        nonopt_coh = [float(r.get("judge_coherence", "")) for r in nonopt_rows
                      if r.get("judge_coherence", "") not in ("", None)]

        if opt_coh:
            ax.scatter(mi - 0.12, np.mean(opt_coh), s=18, color=C_OPENAI,
                       marker="o", edgecolors="white", linewidths=0.3, zorder=3)
        if nonopt_coh:
            ax.scatter(mi + 0.12, np.mean(nonopt_coh), s=18, color=RED,
                       marker="s", edgecolors="white", linewidths=0.3, zorder=3)

    ax.set_xticks(range(len(models)))
    ax.set_xticklabels([MODEL_META[m]["label"].split()[0] for m in models],
                        fontsize=4, rotation=90)
    ax.set_ylabel("Mean coherence score")
    h_opt = mlines.Line2D([], [], color=C_OPENAI, marker="o", markersize=4,
                           linestyle="none", label="Optimal")
    h_non = mlines.Line2D([], [], color=RED, marker="s", markersize=4,
                           linestyle="none", label="Non-optimal")
    ax.legend(handles=[h_opt, h_non], fontsize=5, loc="lower right", frameon=True)
    _panel_label(ax, "a", x=-0.15)

    # Panel b: brand-reasoning rates (dot plot)
    ax = axes[1]
    brand_data = []
    for m in models:
        rows = _filter(baseline, model_key=m)
        judged = [r for r in rows if r.get("judge_brand_reasoning", "") != ""]
        n_judged = len(judged)
        n_yes = sum(1 for r in judged
                    if r.get("judge_brand_reasoning", "").upper() in ("YES", "TRUE", "1"))
        br = n_yes / n_judged if n_judged > 0 else 0
        brand_data.append((m, br))

    for i, (m, br) in enumerate(brand_data):
        meta = MODEL_META[m]
        ax.scatter(br, i, s=25, color=meta["colour"], marker=meta["marker"],
                   edgecolors="white", linewidths=0.3, zorder=3)

    ax.set_yticks(range(len(models)))
    ax.set_yticklabels([MODEL_META[m]["label"] for m in models], fontsize=5)
    ax.set_xlabel("Brand-reasoning rate")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax.invert_yaxis()
    _panel_label(ax, "b", x=-0.25)

    # Panel c: spec-acknowledgment at preference_weighted (dot plot)
    ax = axes[2]
    pw = _filter(data, condition="preference_weighted")

    for mi, m in enumerate(models):
        meta = MODEL_META[m]
        rows = _filter(pw, model_key=m)
        scores = []
        for r in rows:
            try:
                scores.append(float(r.get("judge_spec_acknowledgment", "")))
            except (ValueError, TypeError):
                pass

        if scores:
            mean_s = np.mean(scores)
            ax.scatter(mean_s, mi, s=25, color=meta["colour"], marker=meta["marker"],
                       edgecolors="white", linewidths=0.3, zorder=3)

    ax.set_yticks(range(len(models)))
    ax.set_yticklabels([MODEL_META[m]["label"] for m in models], fontsize=5)
    ax.set_xlabel("Spec. acknowledgment score")
    ax.invert_yaxis()
    _panel_label(ax, "c", x=-0.25)

    plt.tight_layout()
    _save(fig, out, "ed8_judge")
    print("  [OK] ED Fig 8: LLM-as-judge evaluation")


# ══════════════════════════════════════════════════════════════════
# EXTENDED DATA FIGURE 9 | Assortment difficulty ranking
# ══════════════════════════════════════════════════════════════════

def ed9_assortment_difficulty(data, out):
    """Category-level non-optimal rates with individual assortment dots."""
    models = models_in_data(data)
    baseline = _filter(data, condition="baseline")

    # Group by category
    cat_data = defaultdict(list)
    assortments = sorted(set(r.get("assortment_id", "") for r in baseline
                             if r.get("assortment_id", "")))
    for a in assortments:
        rows = _filter(baseline, assortment_id=a)
        if not rows:
            continue
        r, lo, hi, n = rate_ci(rows, "non_optimal")
        cat = rows[0].get("category", "unknown")
        cat_data[cat].append((a, r, lo, hi, n))

    # Sort categories by mean rate
    cat_means = []
    for cat, assorts in cat_data.items():
        mean_r = np.mean([a[1] for a in assorts])
        cat_means.append((cat, mean_r, assorts))
    cat_means.sort(key=lambda x: -x[1])

    fig, ax = plt.subplots(figsize=(NATURE_DOUBLE_COL, max(3, len(cat_means) * 0.25)))
    y_pos = np.arange(len(cat_means))
    overall = np.mean([a[1] for cm in cat_means for a in cm[2]])

    for i, (cat, mean_r, assorts) in enumerate(cat_means):
        # Individual assortment dots (jittered)
        for j, (a_id, r, lo, hi, n) in enumerate(assorts):
            jitter = (j - len(assorts)/2) * 0.08
            ax.scatter(r, i + jitter, s=12, color=C_GOOGLE, alpha=0.35,
                       edgecolors="none", zorder=2)

        # Category mean with CI
        rates = [a[1] for a in assorts]
        lo_b, hi_b = bootstrap_ci(np.array(rates)) if len(rates) > 1 else (mean_r, mean_r)
        ax.plot([lo_b, hi_b], [i, i], color=C_GOOGLE,
                linewidth=2.0, alpha=0.5, solid_capstyle="round", zorder=3)
        ax.scatter(mean_r, i, s=40, color=C_GOOGLE, marker="D",
                   edgecolors="white", linewidths=0.5, zorder=4)

    ax.axvline(overall, linestyle="--", color=GREY, linewidth=0.5, zorder=0)

    ax.set_yticks(y_pos)
    ax.set_yticklabels([cm[0].replace("_", " ").title() for cm in cat_means], fontsize=6)
    ax.set_xlabel("Non-optimal choice rate (baseline)")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax.invert_yaxis()

    plt.tight_layout()
    _save(fig, out, "ed9_assortment_difficulty")
    print("  [OK] ED Fig 9: Assortment difficulty (by category)")


# ══════════════════════════════════════════════════════════════════
# EXTENDED DATA FIGURE 10 | Vague paradox
# ══════════════════════════════════════════════════════════════════

def ed10_vague_paradox(data, out):
    models = models_in_data(data)

    model_deltas = []
    for m in models:
        bl_rows = _filter(data, model_key=m, condition="baseline")
        vg_rows = _filter(data, model_key=m, condition="preference_vague")
        bl_r, _, _, _ = rate_ci(bl_rows, "non_optimal")
        vg_r, vg_lo, vg_hi, _ = rate_ci(vg_rows, "non_optimal")
        delta = vg_r - bl_r
        delta_lo = vg_lo - bl_r
        delta_hi = vg_hi - bl_r
        model_deltas.append((m, delta, delta_lo, delta_hi))

    model_deltas.sort(key=lambda x: -x[1])

    fig, ax = plt.subplots(figsize=(NATURE_DOUBLE_COL, 3.5))
    y_pos = np.arange(len(model_deltas))

    for i, (m, delta, delta_lo, delta_hi) in enumerate(model_deltas):
        meta = MODEL_META[m]
        colour = RED if delta > 0 else TEAL

        # CI whisker
        ax.plot([delta_lo, delta_hi], [i, i], color=colour,
                linewidth=1.2, alpha=0.35, solid_capstyle="round", zorder=2)
        # Dot
        ax.scatter(delta, i, s=30, color=colour, marker=meta["marker"],
                   edgecolors="white", linewidths=0.4, zorder=3)

    ax.axvline(0, color="#333333", linewidth=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([MODEL_META[m[0]]["label"] for m in model_deltas], fontsize=6)
    ax.set_xlabel("Change in non-optimal rate\n(preference-vague minus baseline)")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    ax.invert_yaxis()

    plt.tight_layout()
    _save(fig, out, "ed10_vague_paradox")
    print("  [OK] ED Fig 10: Vague paradox")


# ══════════════════════════════════════════════════════════════════
# EXTENDED DATA FIGURE 11 | Confabulation gradient
# ══════════════════════════════════════════════════════════════════

def ed11_confabulation(data, out):
    """
    Two-panel dot plot with CI whiskers:
    a) Confabulation rate across specification conditions (stays high or increases)
    b) Confabulation rate across anti-brand conditions (drops sharply)
    """
    spec_conditions = [
        ("baseline", "Baseline"),
        ("utility_vague", "Utility vague"),
        ("preference_vague", "Pref. vague"),
        ("utility_weighted", "Utility weighted"),
        ("preference_weighted", "Pref. weighted"),
    ]

    anti_conditions = [
        ("baseline", "Baseline"),
        ("anti_brand_rejection", "Rejection"),
        ("anti_brand_negative_experience", "Neg. experience"),
        ("anti_brand_prefer_unknown", "Prefer unknown"),
    ]

    def confab_rate(rows_subset):
        # Confabulation rate is computed over non-optimal trials WITH judge data
        # only. Trials missing judge data (empty judge_brand_reasoning) are
        # excluded from both numerator and denominator. The original definition
        # included empty-judge trials in the numerator, which inflated the rate
        # for conditions with small non-optimal N (e.g., prefer-unknown: 344
        # non-optimal, 42 missing judge => 21 per cent vs the correct 10 per cent).
        non_opt = [r for r in rows_subset if r.get("chose_optimal") == "False"]
        with_judge = [r for r in non_opt
                      if r.get("judge_brand_reasoning", "").strip() != ""]
        if len(with_judge) == 0:
            return 0.0, 0.0, 0.0, 0
        n_confab = sum(1 for r in with_judge
                       if r.get("judge_brand_reasoning", "").strip() in ("False", "0", "0.0"))
        n = len(with_judge)
        rate = n_confab / n
        lo, hi = wilson_ci(n_confab, n)
        return rate, lo, hi, n

    by_cond = defaultdict(list)
    for r in data:
        by_cond[r["condition"]].append(r)

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(NATURE_DOUBLE_COL, 2.5))

    # Panel a: Specification gradient
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
    ax_a.scatter(rates_a, y_a, c=colours_a, s=30, zorder=5,
                 edgecolors="white", linewidths=0.4)
    ax_a.set_yticks(y_a)
    ax_a.set_yticklabels(labels_a)
    ax_a.set_xlabel("Confabulation rate (%)")
    ax_a.set_xlim(60, 100)
    ax_a.invert_yaxis()
    _panel_label(ax_a, "a")
    ax_a.axvline(x=rates_a[0], color=GREY, linestyle="--", linewidth=0.4, alpha=0.5)

    # Panel b: Anti-brand gradient
    labels_b, rates_b, los_b, his_b = [], [], [], []
    for cond, label in anti_conditions:
        rate, lo, hi, n = confab_rate(by_cond.get(cond, []))
        labels_b.append(label)
        rates_b.append(rate * 100)
        los_b.append(rate * 100 - lo * 100)
        his_b.append(hi * 100 - rate * 100)

    y_b = np.arange(len(labels_b))
    colours_b = [GREY, RED, "#B8860B", TEAL]
    ax_b.errorbar(rates_b, y_b, xerr=[los_b, his_b], fmt="none",
                  ecolor=GREY, elinewidth=0.6, capsize=2, capthick=0.4)
    ax_b.scatter(rates_b, y_b, c=colours_b, s=30, zorder=5,
                 edgecolors="white", linewidths=0.4)
    ax_b.set_yticks(y_b)
    ax_b.set_yticklabels(labels_b)
    ax_b.set_xlabel("Confabulation rate (%)")
    ax_b.set_xlim(0, 100)
    ax_b.invert_yaxis()
    _panel_label(ax_b, "b")
    ax_b.axvline(x=rates_b[0], color=GREY, linestyle="--", linewidth=0.4, alpha=0.5)

    fig.tight_layout(w_pad=3)
    _save(fig, out, "ed11_confabulation")
    print("  [OK] ED Fig 11: Confabulation gradient")


# ══════════════════════════════════════════════════════════════════
# SUMMARY STATISTICS
# ══════════════════════════════════════════════════════════════════

def print_summary(data):
    models = models_in_data(data)
    print(f"\n{'='*70}")
    print(f"SPECIFICATION RESISTANCE - {len(data)} trials across {len(models)} models")
    print(f"{'='*70}")

    for m in models:
        model_data = _filter(data, model_key=m)
        bl = _filter(model_data, condition="baseline")
        r, lo, hi, n = rate_ci(bl, "non_optimal")
        conditions = sorted(set(r_row["condition"] for r_row in model_data))
        print(f"  {MODEL_META[m]['label']:25s}  "
              f"Non-opt: {r:.1%} (CI {lo:.1%}-{hi:.1%}, n={n})  "
              f"Total: {len(model_data):6d}  Conditions: {len(conditions)}")

    all_bl = _filter(data, condition="baseline")
    overall_r, overall_lo, overall_hi, overall_n = rate_ci(all_bl, "non_optimal")
    print(f"\n  {'OVERALL':25s}  "
          f"Non-opt: {overall_r:.1%} (CI {overall_lo:.1%}-{overall_hi:.1%}, n={overall_n})")
    print(f"{'='*70}")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

FIGURE_REGISTRY = {
    "fig2": ("Fig 2: Baseline misalignment", fig1_phenomenon),
    "fig3": ("Fig 3: Control conditions", fig2_controls),
    "fig4": ("Fig 4: Specification gap", fig3_specification_gap),
    "fig5": ("Fig 5: Conjoint mechanism", fig4_conjoint),
    "fig6": ("Fig 6: Anti-brand correction", fig5_anti_brand),
    "fig7": ("Fig 7: Model families", fig6_model_families),
    "ed1":  ("ED Fig 1: Position/letter bias", ed1_position_bias),
    "ed2":  ("ED Fig 2: 32-condition heatmap", ed2_condition_heatmap),
    "ed3":  ("ED Fig 3: Dose-response all models", ed3_dose_response),
    "ed4":  ("ED Fig 4: Baseline mechanisms", ed4_baseline_mechanisms),
    "ed5":  ("ED Fig 5: Paraphrase robustness", ed5_paraphrase),
    "ed6":  ("ED Fig 6: Provider effects", ed6_provider_effects),
    "ed7":  ("ED Fig 7: Category heatmap", ed7_category_heatmap),
    "ed8":  ("ED Fig 8: LLM-as-judge", ed8_judge),
    "ed9":  ("ED Fig 9: Assortment difficulty", ed9_assortment_difficulty),
    "ed10": ("ED Fig 10: Vague paradox", ed10_vague_paradox),
    "ed11": ("ED Fig 11: Confabulation gradient", ed11_confabulation),
}


def main():
    parser = argparse.ArgumentParser(description="Generate Nature-quality figures")
    parser.add_argument("--only", nargs="*", default=None,
                        help="Generate only specific figures (e.g., fig1 fig3 ed2)")
    parser.add_argument("--csv", default=None, help="Path to CSV file")
    args = parser.parse_args()

    # Resolve bundle root from this file's location (one level up: analysis/ -> OSF/)
    base = Path(__file__).resolve().parent.parent
    csv_path = args.csv or str(base / "data" / "spec_resistance_EXTENDED.csv")
    out_dir = base / "results" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from {csv_path}...")
    data = load_data(csv_path)
    if not data:
        print("ERROR: No data loaded. Check CSV path and model keys.")
        sys.exit(1)

    print_summary(data)

    if args.only:
        to_generate = [k for k in args.only if k in FIGURE_REGISTRY]
        unknown = [k for k in args.only if k not in FIGURE_REGISTRY]
        if unknown:
            print(f"WARNING: Unknown figure keys: {unknown}")
            print(f"Available: {', '.join(FIGURE_REGISTRY.keys())}")
    else:
        to_generate = list(FIGURE_REGISTRY.keys())

    print(f"\nGenerating {len(to_generate)} Nature-quality figures in {out_dir}...")

    for key in to_generate:
        label, func = FIGURE_REGISTRY[key]
        try:
            func(data, out_dir)
        except Exception as e:
            print(f"  [FAIL] {label}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nAll figures saved to {out_dir}")


if __name__ == "__main__":
    main()
