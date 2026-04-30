"""
Generate revision figures for Nature R&R response.

Figures:
  a) Injection dose-response curve (bar chart)
  b) Debiasing comparison (bar chart)
  c) Confabulation x brand frequency scatter (cleaner version)
  d) Creation vs removal asymmetry (split panel)

Usage:
    python scripts/generate_revision_figures.py
"""

import json
import csv
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ══════════════════════════════════════════════════════════════════
# NATURE STYLE CONFIGURATION
# ══════════════════════════════════════════════════════════════════

plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 7,
    "axes.labelsize": 8,
    "axes.titlesize": 9,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 6.5,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.linewidth": 0.5,
    "xtick.major.width": 0.5,
    "ytick.major.width": 0.5,
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "lines.linewidth": 1.2,
    "patch.linewidth": 0.4,
})

# Nature column widths
SINGLE_COL = 3.25   # inches (89 mm)
DOUBLE_COL = 6.5    # inches (183 mm)

# Colorblind-friendly palette (Wong, 2011 Nature Methods)
CB_BLUE    = "#0072B2"
CB_ORANGE  = "#E69F00"
CB_GREEN   = "#009E73"
CB_RED     = "#D55E00"
CB_PURPLE  = "#CC79A7"
CB_CYAN    = "#56B4E9"
CB_YELLOW  = "#F0E442"
CB_BLACK   = "#000000"

GREY       = "#888888"
LIGHT_GREY = "#CCCCCC"


BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE / "results"
OUT_DIR = RESULTS / "figures" / "revision"


def save_fig(fig, name):
    """Save figure as PNG and PDF."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        path = OUT_DIR / f"{name}.{ext}"
        fig.savefig(str(path), dpi=300, bbox_inches="tight", pad_inches=0.05)
        print(f"  Saved: {path}")
    plt.close(fig)


def add_value_labels(ax, bars, fmt="{:.0f}%", offset=1.5, fontsize=6.5):
    """Add value labels above bars."""
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.,
            height + offset,
            fmt.format(height),
            ha="center", va="bottom",
            fontsize=fontsize, fontweight="bold",
        )


# ══════════════════════════════════════════════════════════════════
# FIGURE A: Injection Dose-Response Curve
# ══════════════════════════════════════════════════════════════════

def fig_injection_dose_response():
    """Bar chart: Axelion preference rate across 5 fine-tuning conditions."""
    print("\n[A] Injection dose-response curve...")

    with open(str(RESULTS / "08-fictional-injection" / "injection_results.json")) as f:
        data = json.load(f)

    # Extract in logical order
    conditions = [
        ("control (neutral only)", "Control\n(neutral)"),
        ("baseline (gpt-4o-mini)", "Baseline\n(no training)"),
        ("injection_50 (Axelion)", "Injection\n50 examples"),
        ("injection_100 (Axelion)", "Injection\n100 examples"),
        ("injection_200 (Axelion)", "Injection\n200 examples"),
    ]

    labels = []
    axelion_rates = []
    optimal_rates = []
    other_rates = []
    for key, label in conditions:
        d = data[key]
        total = d["optimal"] + d["axelion"] + d["other_branded"] + d["parse_fail"]
        axelion_rates.append(d["axelion"] / total * 100)
        optimal_rates.append(d["optimal"] / total * 100)
        other_rates.append(d["other_branded"] / total * 100)
        labels.append(label)

    x = np.arange(len(labels))
    width = 0.55

    fig, ax = plt.subplots(figsize=(DOUBLE_COL * 0.55, 2.8))

    # Stacked bars: Axelion (primary) + optimal + other
    bars_axelion = ax.bar(x, axelion_rates, width, color=CB_RED, label="Injected brand (Axelion)", zorder=3)
    bars_optimal = ax.bar(x, optimal_rates, width, bottom=axelion_rates, color=CB_BLUE, label="Optimal product", zorder=3)
    bottom2 = [a + o for a, o in zip(axelion_rates, optimal_rates)]
    bars_other = ax.bar(x, other_rates, width, bottom=bottom2, color=LIGHT_GREY, label="Other branded", zorder=3)

    # Add Axelion rate labels inside bars
    for i, bar in enumerate(bars_axelion):
        height = bar.get_height()
        if height > 5:
            ax.text(
                bar.get_x() + bar.get_width() / 2.,
                height / 2.,
                f"{height:.0f}%",
                ha="center", va="center",
                fontsize=7, fontweight="bold", color="white",
            )

    ax.set_ylabel("Proportion of recommendations (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6.5)
    ax.set_ylim(0, 108)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(20))
    ax.legend(loc="upper right", frameon=False, fontsize=6)

    # Title
    ax.set_title("Fine-tuning injection: dose-response", fontsize=9, fontweight="bold", pad=8)

    fig.tight_layout()
    save_fig(fig, "fig_injection_dose_response")


# ══════════════════════════════════════════════════════════════════
# FIGURE B: Debiasing Comparison
# ══════════════════════════════════════════════════════════════════

def fig_debiasing_comparison():
    """Bar chart: non-optimal rate for baseline vs control-neutral vs debiased-500."""
    print("\n[B] Debiasing comparison...")

    with open(str(RESULTS / "06-openai-finetune" / "preliminary_debiasing.json")) as f:
        prelim = json.load(f)

    with open(str(RESULTS / "06-openai-finetune" / "debiasing_500_results.json")) as f:
        deb500 = json.load(f)

    conditions = [
        ("Baseline\n(gpt-4o-mini)", prelim["baseline"]["nonoptimal_rate"] * 100),
        ("Control\n(neutral fine-tune)", prelim["control-neutral"]["nonoptimal_rate"] * 100),
        ("Debiasing\n(500 examples)", deb500["summary"]["nonoptimal_rate"] * 100),
    ]

    labels = [c[0] for c in conditions]
    rates = [c[1] for c in conditions]

    fig, ax = plt.subplots(figsize=(SINGLE_COL, 2.8))

    x = np.arange(len(labels))
    width = 0.5
    colors = [CB_RED, CB_ORANGE, CB_GREEN]

    bars = ax.bar(x, rates, width, color=colors, zorder=3, edgecolor="white", linewidth=0.5)
    add_value_labels(ax, bars, fmt="{:.0f}%", offset=0.8)

    ax.set_ylabel("Non-optimal rate (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6.5)
    ax.set_ylim(0, 35)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(5))

    # Add annotation arrow showing improvement
    ax.annotate(
        "",
        xy=(2, rates[2] + 2.5), xytext=(0, rates[0] - 1),
        arrowprops=dict(arrowstyle="->", color=CB_GREEN, lw=1.5, connectionstyle="arc3,rad=-0.2"),
    )
    mid_x = 1.0
    mid_y = (rates[0] + rates[2]) / 2 + 4
    reduction = ((rates[0] - rates[2]) / rates[0]) * 100
    ax.text(mid_x, mid_y, f"{reduction:.0f}% reduction",
            fontsize=7, color=CB_GREEN, fontweight="bold", ha="center")

    ax.set_title("Debiasing via fine-tuning", fontsize=9, fontweight="bold", pad=8)

    fig.tight_layout()
    save_fig(fig, "fig_debiasing_comparison")


# ══════════════════════════════════════════════════════════════════
# FIGURE C: Confabulation x Brand Frequency Scatter
# ══════════════════════════════════════════════════════════════════

def fig_confabulation_frequency():
    """Scatter: confabulation rate vs log brand frequency, sized by trial count."""
    print("\n[C] Confabulation x brand frequency scatter...")

    csv_path = RESULTS / "confabulation_by_brand.csv"
    brands = []
    with open(str(csv_path), encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            n = int(row["n_trials"])
            non_opt = float(row["non_optimal_rate"])
            confab = float(row["confab_rate"]) if row["confab_rate"] else 0.0
            log_f = float(row["log_freq"]) if row["log_freq"] else None
            tier = row["familiarity_tier"]
            name = row["chosen_brand"]
            if log_f is not None and n >= 10 and non_opt > 0:
                brands.append({
                    "name": name,
                    "n": n,
                    "non_optimal_rate": non_opt,
                    "confab_rate": confab,
                    "confab_given_nonoptimal": float(row["confab_given_nonoptimal"]) if row["confab_given_nonoptimal"] else 0,
                    "log_freq": log_f,
                    "tier": tier,
                })

    fig, ax = plt.subplots(figsize=(DOUBLE_COL * 0.55, 3.2))

    tier_colors = {"high": CB_RED, "medium": CB_ORANGE, "low": CB_CYAN}
    tier_labels = {"high": "High familiarity", "medium": "Medium familiarity", "low": "Low familiarity"}

    # Plot each tier
    for tier in ["low", "medium", "high"]:
        subset = [b for b in brands if b["tier"] == tier]
        if not subset:
            continue
        xs = [b["log_freq"] for b in subset]
        ys = [b["confab_given_nonoptimal"] * 100 for b in subset]
        sizes = [max(15, min(200, b["n"] / 8)) for b in subset]
        ax.scatter(xs, ys, s=sizes, c=tier_colors[tier], alpha=0.7,
                   edgecolors="white", linewidths=0.3, label=tier_labels[tier], zorder=3)

    # Label the most prominent brands
    label_brands = {"Samsung", "Apple", "Sony", "Dell", "JBL", "Beyerdynamic",
                    "ASUS", "OnePlus", "Google", "De'Longhi", "Nike", "Bose",
                    "Sennheiser", "HP", "LG", "Vizio", "AeroPress"}
    for b in brands:
        if b["name"] in label_brands:
            y_val = b["confab_given_nonoptimal"] * 100
            # Offset labels to avoid overlap
            x_off = 0.08
            y_off = -3 if y_val > 50 else 3
            if b["name"] == "Bose":
                y_off = 5
            elif b["name"] == "LG":
                y_off = 5
            elif b["name"] == "HP":
                x_off = -0.15
                y_off = -4
            ax.annotate(
                b["name"], (b["log_freq"], y_val),
                xytext=(b["log_freq"] + x_off, y_val + y_off),
                fontsize=5.5, color="#333333",
                arrowprops=dict(arrowstyle="-", color="#999999", lw=0.3) if abs(y_off) > 3 else None,
            )

    # Trend line (all brands with non-optimal > 0)
    all_x = [b["log_freq"] for b in brands]
    all_y = [b["confab_given_nonoptimal"] * 100 for b in brands]
    if len(all_x) > 2:
        from scipy import stats as sp_stats
        slope, intercept, r, p, se = sp_stats.linregress(all_x, all_y)
        x_line = np.linspace(min(all_x) - 0.2, max(all_x) + 0.2, 100)
        y_line = slope * x_line + intercept
        ax.plot(x_line, y_line, color=GREY, linewidth=1, linestyle="--", alpha=0.7, zorder=2)
        ax.text(
            max(all_x) - 0.3, slope * (max(all_x) - 0.3) + intercept + 4,
            f"r = {r:.2f}, p = {p:.3f}",
            fontsize=6, color=GREY, style="italic",
        )

    ax.set_xlabel("Training corpus frequency (log scale)")
    ax.set_ylabel("Confabulation rate given non-optimal (%)")
    ax.set_ylim(-5, 110)
    ax.set_xlim(0, 8.5)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(20))
    ax.legend(loc="lower right", frameon=False, fontsize=6, markerscale=0.6)

    ax.set_title("Confabulation scales with brand frequency", fontsize=9, fontweight="bold", pad=8)

    fig.tight_layout()
    save_fig(fig, "fig_confabulation_by_frequency")


# ══════════════════════════════════════════════════════════════════
# FIGURE D: Creation vs Removal Asymmetry (Split Panel)
# ══════════════════════════════════════════════════════════════════

def fig_asymmetry_panel():
    """Split panel: injection (left) vs debiasing (right) showing cost asymmetry."""
    print("\n[D] Creation vs removal asymmetry panel...")

    # --- Left panel data: injection ---
    with open(str(RESULTS / "08-fictional-injection" / "injection_results.json")) as f:
        inj = json.load(f)

    inj_conditions = [
        ("Control\n(neutral)", "control (neutral only)"),
        ("50 ex.", "injection_50 (Axelion)"),
        ("100 ex.", "injection_100 (Axelion)"),
    ]
    inj_labels = [c[0] for c in inj_conditions]
    inj_rates = []
    for _, key in inj_conditions:
        d = inj[key]
        total = d["optimal"] + d["axelion"] + d["other_branded"] + d["parse_fail"]
        inj_rates.append(d["axelion"] / total * 100)

    # --- Right panel data: debiasing ---
    with open(str(RESULTS / "06-openai-finetune" / "preliminary_debiasing.json")) as f:
        prelim = json.load(f)
    with open(str(RESULTS / "06-openai-finetune" / "debiasing_500_results.json")) as f:
        deb500 = json.load(f)

    deb_conditions = [
        ("Baseline", prelim["baseline"]["nonoptimal_rate"] * 100),
        ("Control\n(neutral)", prelim["control-neutral"]["nonoptimal_rate"] * 100),
        ("500 ex.", deb500["summary"]["nonoptimal_rate"] * 100),
    ]
    deb_labels = [c[0] for c in deb_conditions]
    deb_rates = [c[1] for c in deb_conditions]

    # Create figure with two panels
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(DOUBLE_COL, 2.8))

    # --- LEFT: Injection (creating preferences) ---
    x1 = np.arange(len(inj_labels))
    width = 0.5
    bars1 = ax1.bar(x1, inj_rates, width, color=CB_RED, zorder=3, edgecolor="white", linewidth=0.5)
    add_value_labels(ax1, bars1, offset=1.2)

    ax1.set_ylabel("Brand preference rate (%)")
    ax1.set_xticks(x1)
    ax1.set_xticklabels(inj_labels, fontsize=6.5)
    ax1.set_ylim(0, 70)
    ax1.yaxis.set_major_locator(mticker.MultipleLocator(10))
    ax1.set_title("Creating preferences\n(injection fine-tuning)", fontsize=8, fontweight="bold", pad=6)

    # Arrow: 50 examples suffice
    ax1.annotate(
        "50 examples\nsuffice",
        xy=(1, inj_rates[1] + 2), xytext=(1.8, inj_rates[1] + 15),
        fontsize=6.5, fontweight="bold", color=CB_RED, ha="center",
        arrowprops=dict(arrowstyle="->", color=CB_RED, lw=1),
    )

    # Panel label
    ax1.text(-0.15, 1.08, "a", transform=ax1.transAxes, fontsize=12,
             fontweight="bold", va="top")

    # --- RIGHT: Debiasing (removing preferences) ---
    x2 = np.arange(len(deb_labels))
    colors2 = [CB_RED, CB_ORANGE, CB_GREEN]
    bars2 = ax2.bar(x2, deb_rates, width, color=colors2, zorder=3, edgecolor="white", linewidth=0.5)
    add_value_labels(ax2, bars2, offset=0.6)

    ax2.set_ylabel("Non-optimal rate (%)")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(deb_labels, fontsize=6.5)
    ax2.set_ylim(0, 35)
    ax2.yaxis.set_major_locator(mticker.MultipleLocator(5))
    ax2.set_title("Removing preferences\n(debiasing fine-tuning)", fontsize=8, fontweight="bold", pad=6)

    # Arrow: 500 examples needed
    ax2.annotate(
        "500 examples\nrequired",
        xy=(2, deb_rates[2] + 1), xytext=(1.2, deb_rates[2] + 12),
        fontsize=6.5, fontweight="bold", color=CB_GREEN, ha="center",
        arrowprops=dict(arrowstyle="->", color=CB_GREEN, lw=1),
    )

    # Panel label
    ax2.text(-0.15, 1.08, "b", transform=ax2.transAxes, fontsize=12,
             fontweight="bold", va="top")

    # Add shared annotation at bottom
    fig.text(0.5, -0.04,
             "Creating brand preference: 50 examples.  Removing it: 500 examples (10x asymmetry).",
             ha="center", fontsize=7.5, fontweight="bold", color="#333333",
             style="italic")

    fig.tight_layout(w_pad=3)
    save_fig(fig, "fig_asymmetry_creation_vs_removal")


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("Generating Nature revision figures")
    print(f"Output: {OUT_DIR}")
    print("=" * 60)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fig_injection_dose_response()
    fig_debiasing_comparison()
    fig_confabulation_frequency()
    fig_asymmetry_panel()

    print("\n" + "=" * 60)
    print("All revision figures generated successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
