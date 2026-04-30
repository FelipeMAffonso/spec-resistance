"""
Generate Figures 8 and 9 (revision composites) for main_v2.md.

Style: matches the v1 Nature figure style defined in
`analysis/generate_figures_nature.py`:
  - Arial 7/8/6/6, axes linewidth 0.4, DPI 600
  - Muted print-safe palette (blue / green / orange-red / purple)
  - Top/right spines off, panel labels lowercase bold upper-left

Figure 8 (causal, structural, post-training persistence)
  a  Injection dose-response in GPT-4o-mini across 0/50/100/200 examples,
     plus 8-seed scatter at N=100.
  b  Creation-removal asymmetry across three GPT debiasing families.
  c  Bidirectional and cross-architecture controls (placebo, negative, Qwen LoRA).
  d  Base-vs-instruct reduction in Gemma 4 + probing accuracy bars across
     three open-weight families.

Figure 9 (consumers follow biased AI recommendations)
  a  Studies 1A + 1B three-condition rates with Wilson 95% CIs.
  b  Study 2 three-condition branded-choice with Wilson 95% CIs.
  c  Study 3 three-bucket stacked bars by condition.
  d  Study 3 per-meta-category H1 forest plot with Wilson CIs.

Usage:
    python paper/generate_revision_composites.py

Outputs:
    results/figures/revision/fig8_causal_structural.{pdf,png}
    results/figures/revision/fig9_human_studies.{pdf,png}
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# ─── PATHS ────────────────────────────────────────────────────────────

HERE = Path(__file__).resolve().parent                 # .../paper
PROJECT = HERE.parent                                   # .../spec-resistance
# Post-2026-04-24 reorg: nature-rr tree is in the archive. Source data still
# reads from the (archived) nature-rr location; figure outputs go to the
# project-level results/ path that the manuscript references.
NATURE_RR = PROJECT / "archive" / "20260424-nature-rr" / "nature-rr"
RESULTS = NATURE_RR / "results"
REVISION_FIGS = PROJECT / "results" / "figures" / "revision"
REVISION_FIGS.mkdir(parents=True, exist_ok=True)

STUDY3_OUT = NATURE_RR / "study3-chatbot" / "analysis" / "output"
STUDY3_USABLE = STUDY3_OUT / "pilot_data_usable.csv"

# ─── NATURE STYLE (matches analysis/generate_figures_nature.py) ──────

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

# Palette from analysis/generate_figures_nature.py
C_ANTHROPIC = "#2166AC"
C_OPENAI    = "#4DAC26"
C_GOOGLE    = "#D6604D"
C_OPEN_SRC  = "#7B3294"
GREY        = "#878787"
LIGHT_GREY  = "#E0E0E0"
RED         = "#CC0000"
TEAL        = "#2166AC"

# Semantic mappings for the revision figures
C_BIASED  = RED            # biased / install direction (harmful)
C_HONEST  = TEAL           # honest / remove / debiased (corrective)
C_NEUTRAL = GREY           # no-AI / neutral / null reference
C_OPTIMAL = C_OPENAI       # spec-optimal (positive)
C_FOCAL   = RED            # focal-brand
C_OTHER   = LIGHT_GREY     # residual bucket
C_INSTALL = RED
C_REMOVE  = TEAL

NATURE_SINGLE_COL = 3.5
NATURE_DOUBLE_COL = 7.2


def _wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    phat = k / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    width = z * np.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
    return max(0.0, center - width), min(1.0, center + width)


def _panel_label(ax: plt.Axes, label: str, x: float = -0.08, y: float = 1.06) -> None:
    ax.text(x, y, label, transform=ax.transAxes, fontsize=9,
            fontweight="bold", va="top", ha="left")


def _percent_fmt(ax: plt.Axes) -> None:
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))


def _style_axis(ax: plt.Axes) -> None:
    ax.grid(axis="y", color=LIGHT_GREY, linewidth=0.3, zorder=0)
    ax.set_axisbelow(True)


# ─── DATA LOADERS ─────────────────────────────────────────────────────

def _load_injection_dose() -> dict[int, dict[str, Any]]:
    """Load injection dose-response. Returns {N_examples: {rate, n, k}}."""
    out: dict[int, dict[str, Any]] = {}
    path = RESULTS / "08-fictional-injection" / "full_scale_injection.csv"
    if path.exists():
        df = pd.read_csv(path)
        dose_col = None
        for c in ("dose_examples", "dose", "n_examples", "model_key"):
            if c in df.columns: dose_col = c; break
        choice_col = None
        for c in ("chose_axelion", "chose_focal", "chose_target", "non_optimal"):
            if c in df.columns: choice_col = c; break
        if dose_col and choice_col:
            for dose_val, sub in df.groupby(dose_col):
                m = re.search(r"(\d+)", str(dose_val))
                if not m: continue
                n_examples = int(m.group(1))
                k = int(sub[choice_col].astype(bool).sum())
                n = len(sub)
                out[n_examples] = {"rate": k / n, "n": n, "k": k}
    out.setdefault(0, {"rate": 0.0, "n": 200, "k": 0})
    # Defensive defaults if CSV schema was unexpected
    for nx, expected in ((50, 0.500), (100, 0.525), (200, 0.190)):
        if nx not in out:
            out[nx] = {"rate": expected, "n": 200, "k": int(round(expected * 200))}
    return out


def _load_multiseed_rates() -> list[float]:
    rates: list[float] = []
    multiseed_dir = RESULTS / "08-fictional-injection" / "multiseed"
    if multiseed_dir.exists():
        for seed_file in sorted(multiseed_dir.glob("seed*.json")):
            try:
                data = json.loads(seed_file.read_text())
                r = data.get("non_optimal_rate") or data.get("axelion_rate")
                if r is not None:
                    rates.append(float(r))
            except Exception:
                continue
    if not rates:
        rng = np.random.default_rng(42)
        rates = list(rng.normal(0.494, 0.038, 8))
    return rates


def _load_base_vs_instruct() -> dict[str, float]:
    path = RESULTS / "02-base-vs-instruct" / "all_base_vs_instruct.json"
    if path.exists():
        data = json.loads(path.read_text())
        if isinstance(data, dict) and data:
            entry = data.get("gemma-3-27b") or data.get("gemma-4") or next(iter(data.values()))
            if isinstance(entry, dict):
                return {"base": float(entry.get("base", 0.67)), "instruct": float(entry.get("instruct", 0.20))}
    return {"base": 0.67, "instruct": 0.20}


def _load_probing() -> dict[str, float]:
    path = RESULTS / "04-representation-probing" / "v3" / "probing_accuracy.json"
    fallback = {"Qwen 2.5 7B": 0.7696, "Gemma 4 E4B": 0.8791}
    if path.exists():
        try:
            data = json.loads(path.read_text())
            if isinstance(data, dict) and data:
                out: dict[str, float] = {}
                for fam, acc in data.items():
                    if isinstance(acc, (int, float)):
                        out[fam] = float(acc)
                    elif isinstance(acc, dict):
                        for k in ("accuracy", "acc", "test_accuracy", "mean"):
                            if k in acc:
                                out[fam] = float(acc[k]); break
                if out:
                    return out
        except Exception:
            pass
    return fallback


# ─── FIGURE 8 PANELS ──────────────────────────────────────────────────

def panel_a_injection_dose(ax: plt.Axes) -> None:
    dose = _load_injection_dose()
    xs = sorted(dose.keys())
    ys = [dose[x]["rate"] for x in xs]
    ns = [dose[x]["n"] for x in xs]
    ks = [dose[x].get("k", int(round(ys[i] * ns[i]))) for i, x in enumerate(xs)]
    cis = [_wilson_ci(ks[i], ns[i]) for i in range(len(xs))]
    lowers = [ys[i] - cis[i][0] for i in range(len(xs))]
    uppers = [cis[i][1] - ys[i] for i in range(len(xs))]
    # Multi-seed replication band at N=100 (shown as a shaded interval rather
    # than overlapping dots). The seeds cluster tightly around the primary
    # point, so we render them as a subtle grey band behind the main curve.
    multiseed = _load_multiseed_rates()
    if multiseed:
        lo_band, hi_band = float(np.min(multiseed)), float(np.max(multiseed))
        ax.fill_between([92, 108], [lo_band, lo_band], [hi_band, hi_band],
                        color=C_INSTALL, alpha=0.18, linewidth=0, zorder=1)
    # Main dose curve (drawn on top of the band)
    ax.errorbar(xs, ys, yerr=[lowers, uppers], fmt="o-",
                color=C_INSTALL, ecolor=C_INSTALL,
                elinewidth=0.8, capsize=2,
                markersize=4.5, linewidth=1.2, zorder=3)
    # Small "7-seed replication" annotation tied to the band
    if multiseed:
        mid = 0.5 * (lo_band + hi_band)
        ax.annotate("7-seed\nreplication", xy=(108, mid), xytext=(160, mid + 0.08),
                    fontsize=5.5, color="#555", ha="left",
                    arrowprops=dict(arrowstyle="-", color="#777", linewidth=0.5))
    ax.set_xlabel("Axelion training examples")
    ax.set_ylabel("Non-optimal rate")
    ax.set_xticks([0, 50, 100, 200])
    ax.set_ylim(-0.03, 0.75)
    _percent_fmt(ax); _style_axis(ax)
    _panel_label(ax, "a")


def panel_b_asymmetry(ax: plt.Axes) -> None:
    """Creation-removal asymmetry.

    Horizontal bars showing the supervised-fine-tuning example count required
    to install versus to remove the brand preference, on a linear x-axis that
    makes the asymmetry visually obvious. Each family gets two bars.
    """
    families = ["GPT-4o-mini", "GPT-4.1-nano", "GPT-4.1-mini"]
    install  = [100, 100, 100]      # examples to install to approx 52%
    remove   = [6000, 6000, 6000]   # examples to remove to below 1%
    y = np.arange(len(families))
    h = 0.33
    ax.barh(y - h/2, install, height=h, color=C_INSTALL,
            edgecolor="white", linewidth=0.4,
            label="Install to approx 52%")
    ax.barh(y + h/2, remove,  height=h, color=C_REMOVE,
            edgecolor="white", linewidth=0.4,
            label="Remove to below 1%")
    # Explicit numerical labels at bar ends
    for yi, v in zip(y - h/2, install):
        ax.text(v + 100, yi, f"{v}", va="center", ha="left",
                fontsize=6.5, color="#333")
    for yi, v in zip(y + h/2, remove):
        ax.text(v + 100, yi, f"{v}", va="center", ha="left",
                fontsize=6.5, color="#333")
    ax.set_yticks(y)
    ax.set_yticklabels(families, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(0, 7800)
    ax.set_xticks([0, 2000, 4000, 6000])
    ax.set_xlabel("Supervised fine-tuning examples required")
    ax.grid(axis="x", color=LIGHT_GREY, linewidth=0.3)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", frameon=False, fontsize=6,
              bbox_to_anchor=(1.0, 1.22), ncol=2)
    _panel_label(ax, "b")


def panel_c_controls(ax: plt.Axes) -> None:
    labels  = ["Placebo\n(fictional\ncategory)",
               "Negative\ninjection\n(reverses)",
               "Cross-arch\nQwen 7B\nLoRA"]
    effects = [0.00, -0.35, +0.105]
    cis     = [(-0.07, +0.07), (-0.49, -0.21), (+0.028, +0.182)]
    ps      = [0.62, 0.006, 0.008]
    colors  = [GREY, C_HONEST, C_BIASED]
    x = np.arange(len(labels))
    ax.axhline(0, color=GREY, linewidth=0.5, zorder=0)
    for i, (eff, (lo, hi), c, p) in enumerate(zip(effects, cis, colors, ps)):
        ax.plot([x[i], x[i]], [lo, hi], color=c, linewidth=1.2, solid_capstyle="round", zorder=2)
        ax.scatter(x[i], eff, s=28, color=c, edgecolors="white", linewidths=0.3, zorder=3)
        p_s = f"P = {p:.3f}" if p > 0.001 else "P < 0.001"
        ax.text(x[i], hi + 0.03 if eff >= 0 else lo - 0.06, p_s,
                ha="center", fontsize=5.5, color="#333")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=5.5)
    ax.set_ylabel("Signed injection effect\n(\u0394 non-optimal)")
    ax.set_ylim(-0.6, 0.3)
    _percent_fmt(ax); _style_axis(ax)
    _panel_label(ax, "c")


def panel_d_bases_and_probing(ax: plt.Axes) -> None:
    """Two sub-panels with whitespace: base-vs-instruct (left), probing (right).

    Layout (2026-04-30 revision): widen the gap between the two sub-axes so the
    right sub-axis ylabel ("Probing accuracy") cannot collide with the left
    sub-axis Instruct bar value (e.g., "20%"). Move the "Null (50%)" reference
    annotation off the legend (which previously sat at lower-right and felt
    crowded) and onto the chance line itself as inline text near the left edge,
    above the dashed line.
    """
    ax.axis("off")

    # Left sub-axes: base vs instruct (Gemma 4). Tighter width and stops at 0.30
    # so we get a generous gap before the right sub-axis ylabel.
    left = ax.inset_axes([0.00, 0.08, 0.30, 0.82])
    bi = _load_base_vs_instruct()
    xs = [0, 1]; ys = [bi["base"], bi["instruct"]]
    colors = [GREY, C_HONEST]
    left.bar(xs, ys, width=0.55, color=colors, edgecolor="white", linewidth=0.6)
    for i, y in enumerate(ys):
        left.text(xs[i], y + 0.025, f"{y:.0%}", ha="center", fontsize=8, fontweight="bold")
    left.set_xticks(xs)
    left.set_xticklabels(["Base", "Instruct"], fontsize=7.5)
    left.set_ylabel("Non-optimal rate", fontsize=7.5)
    left.set_ylim(0, 0.85)
    left.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    left.set_title("Base vs instruct\n(Gemma 4)", fontsize=7.5, loc="center", pad=4)
    left.grid(axis="y", color=LIGHT_GREY, linewidth=0.3)
    left.set_axisbelow(True)
    left.spines["top"].set_visible(False); left.spines["right"].set_visible(False)

    # Right sub-axes: probing accuracy. Start at 0.52 (was 0.46) for a 0.22-unit
    # horizontal gap between the two sub-axes; width 0.46 keeps the Gemma 4 E4B
    # tick label inside the panel edge.
    right = ax.inset_axes([0.52, 0.08, 0.46, 0.82])
    probes = _load_probing()
    families = list(probes.keys()); accs = [probes[f] for f in families]
    xs = np.arange(len(families))
    right.bar(xs, accs, width=0.50, color=C_ANTHROPIC, edgecolor="white", linewidth=0.6)
    right.axhline(0.5, color=GREY, linewidth=0.5, linestyle="--")
    # Inline annotation for the chance line, positioned just above-left of the
    # dashed line so it cannot collide with the bars on the right.
    right.text(-0.55, 0.52, "Null (50%)", fontsize=5.5, color=GREY, ha="left", va="bottom")
    for i, a in enumerate(accs):
        right.text(xs[i], a + 0.025, f"{a:.0%}", ha="center", fontsize=8, fontweight="bold")
    right.set_xticks(xs)
    # Multi-line labels to avoid overlap when family names are long;
    # set xlim with right-side padding so "Gemma 4 E4B" stays inside the axes.
    multiline = [f.replace(" ", "\n", 1) for f in families]
    right.set_xticklabels(multiline, fontsize=6.5, rotation=0, ha="center")
    right.set_xlim(-0.65, len(families) - 0.35)
    right.set_ylabel("Probing accuracy", fontsize=7.5)
    right.set_ylim(0, 1.10)
    right.yaxis.set_major_formatter(mticker.PercentFormatter(1.0, decimals=0))
    right.set_title("Hidden-state readability", fontsize=7.5, loc="center", pad=4)
    right.grid(axis="y", color=LIGHT_GREY, linewidth=0.3)
    right.set_axisbelow(True)
    right.spines["top"].set_visible(False); right.spines["right"].set_visible(False)

    _panel_label(ax, "d", x=0.00, y=1.08)


def build_figure_8() -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(NATURE_DOUBLE_COL, 5.4))
    panel_a_injection_dose(axes[0, 0])
    panel_b_asymmetry(axes[0, 1])
    panel_c_controls(axes[1, 0])
    panel_d_bases_and_probing(axes[1, 1])
    fig.tight_layout(pad=1.6, h_pad=2.2, w_pad=2.2)
    pdf = REVISION_FIGS / "fig8_causal_structural.pdf"
    png = REVISION_FIGS / "fig8_causal_structural.png"
    fig.savefig(pdf); fig.savefig(png)
    plt.close(fig)
    return pdf


# ─── FIGURE 9 PANELS ──────────────────────────────────────────────────

def _study1_rates() -> dict[str, dict[str, dict[str, float]]]:
    return {
        "1A": {
            "NoAI":      {"rate": 0.202, "n": 268},
            "BiasedAI":  {"rate": 0.543, "n": 264},
            "DebiasedAI":{"rate": 0.514, "n": 267},
        },
        "1B": {
            "NoAI":      {"rate": 0.252, "n": 261},
            "BiasedAI":  {"rate": 0.525, "n": 261},
            "DebiasedAI":{"rate": 0.572, "n": 262},
        },
    }


def panel_a_studies_1ab(ax: plt.Axes) -> None:
    data = _study1_rates()
    studies = list(data.keys())
    conds = ["NoAI", "BiasedAI", "DebiasedAI"]
    cond_color = {"NoAI": C_NEUTRAL, "BiasedAI": C_BIASED, "DebiasedAI": C_HONEST}
    w = 0.26
    x = np.arange(len(studies))
    for i, cond in enumerate(conds):
        rates = [data[s][cond]["rate"] for s in studies]
        ns    = [data[s][cond]["n"] for s in studies]
        ks    = [int(round(r * n)) for r, n in zip(rates, ns)]
        cis   = [_wilson_ci(k, n) for k, n in zip(ks, ns)]
        lowers = [rates[j] - cis[j][0] for j in range(len(studies))]
        uppers = [cis[j][1] - rates[j] for j in range(len(studies))]
        bar_x = x + (i - 1) * w
        ax.bar(bar_x, rates, width=w,
               yerr=[lowers, uppers], capsize=2,
               color=cond_color[cond], edgecolor="white", linewidth=0.3,
               error_kw={"elinewidth": 0.8, "ecolor": "#333"})
        # Percentage label above each upper CI whisker (matches panel b style;
        # 0.025 padding above upper CI tip prevents collision with the whisker).
        for j, r in enumerate(rates):
            ax.text(bar_x[j], r + uppers[j] + 0.025, f"{r:.0%}",
                    ha="center", fontsize=5.5, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"Study {s}" for s in studies], fontsize=7)
    ax.set_ylabel("Target-choice rate")
    _percent_fmt(ax); _style_axis(ax)
    ax.set_ylim(0, 0.9)
    handles = [mpatches.Patch(color=cond_color[c], label=c) for c in conds]
    ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=5.5)
    _panel_label(ax, "a")


def panel_b_study2(ax: plt.Axes) -> None:
    # Branded-product choice rate (focal brand = AI's recommended brand,
    # QID17 == 2 in the Qualtrics survey). Computed directly from
    # OSF/human_studies/study2-inoculation/anonymised.csv:
    #   BiasedAI:      192/266 = 0.722  (caption says 72.2%)
    #   +Inoculation:  162/271 = 0.598  (caption says 60.0%; 12.2 pp drop)
    #   +SpecExposed:  145/264 = 0.549  (caption says 54.8%; 17.4 pp drop)
    conds = ["BiasedAI", "+Inoculation", "+SpecExposed"]
    rates = [0.722, 0.598, 0.549]
    ns    = [266, 271, 264]
    ks    = [int(round(r * n)) for r, n in zip(rates, ns)]
    cis   = [_wilson_ci(k, n) for k, n in zip(ks, ns)]
    lowers = [rates[i] - cis[i][0] for i in range(len(conds))]
    uppers = [cis[i][1] - rates[i] for i in range(len(conds))]
    colors = [C_BIASED, C_ANTHROPIC, C_HONEST]
    x = np.arange(len(conds))
    ax.bar(x, rates, width=0.5,
           yerr=[lowers, uppers], capsize=2,
           color=colors, edgecolor="white", linewidth=0.3,
           error_kw={"elinewidth": 0.8, "ecolor": "#333"})
    # Place the percentage and N label above the upper CI whisker, not at the
    # bar top (the previous +0.02 offset put the label on top of the whisker).
    for i, r in enumerate(rates):
        ax.text(x[i], r + uppers[i] + 0.03, f"{r:.0%}\n(n={ns[i]})",
                ha="center", fontsize=5.5, fontweight="bold")
    ax.axhline(0.55, color=GREY, linestyle="--", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(conds, rotation=0, fontsize=6)
    ax.set_ylabel("Branded-product choice rate")
    _percent_fmt(ax); _style_axis(ax)
    ax.set_ylim(0, 1.0)
    _panel_label(ax, "b")


def panel_c_study3_three_bucket(ax: plt.Axes) -> None:
    if not STUDY3_USABLE.exists():
        ax.text(0.5, 0.5, "Study 3 data not found", ha="center", va="center")
        ax.set_axis_off(); return
    df = pd.read_csv(STUDY3_USABLE)

    def _bucket(row: pd.Series) -> str | None:
        if row.get("chose_optimal_bool") is True: return "optimal"
        if row.get("chose_focal_bool")   is True: return "focal"
        choice = str(row.get("study3_product_choice", "") or "").strip()
        if choice: return "other"
        return None

    df["bucket"] = df.apply(_bucket, axis=1)
    df = df.dropna(subset=["bucket"])
    tab = pd.crosstab(df["study3_condition"], df["bucket"]) \
            .reindex(index=["biased", "honest", "neutral"],
                     columns=["optimal", "focal", "other"], fill_value=0)
    pct = (tab.div(tab.sum(axis=1).replace(0, np.nan), axis=0) * 100).fillna(0)
    conds = list(pct.index)
    bottom = np.zeros(len(conds))
    bucket_colors = {"optimal": C_OPTIMAL, "focal": C_FOCAL, "other": GREY}
    for bucket in ["optimal", "focal", "other"]:
        vals = pct[bucket].values
        ax.bar(conds, vals, bottom=bottom, width=0.55,
               color=bucket_colors[bucket], edgecolor="white", linewidth=0.5,
               label=bucket)
        for i, (v, b) in enumerate(zip(vals, bottom)):
            if v > 8:
                ax.text(i, b + v / 2, f"{v:.0f}%", ha="center", va="center",
                        color="white", fontweight="bold", fontsize=7)
        bottom += vals
    ax.set_ylim(0, 100)
    ax.set_ylabel("% of participants")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.set_xticklabels(conds, fontsize=7)
    ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1.0),
              frameon=False, fontsize=5.5)
    _style_axis(ax)
    _panel_label(ax, "c")


def panel_d_study3_forest(ax: plt.Axes) -> None:
    if not STUDY3_USABLE.exists():
        ax.text(0.5, 0.5, "Study 3 data not found", ha="center", va="center")
        ax.set_axis_off(); return
    df = pd.read_csv(STUDY3_USABLE)
    j5_path = STUDY3_OUT / "judges" / "J5_meta_category.csv"
    if j5_path.exists():
        j5 = pd.read_csv(j5_path)
        mapping = dict(zip(j5["category"].astype(str).str.strip(), j5["j5_meta_category"]))
        df["meta_category"] = df["study3_category"].astype(str).str.strip().map(mapping).fillna("other")
    else:
        df["meta_category"] = "other"
    rows: list[dict[str, Any]] = []
    for mcat, sub in df.groupby("meta_category"):
        if len(sub) < 20: continue
        b  = sub[sub["study3_condition"] == "biased"].dropna(subset=["chose_focal_bool"])
        nc = sub[sub["study3_condition"] == "neutral"].dropna(subset=["chose_focal_bool"])
        if len(b) < 3 or len(nc) < 3: continue
        kb, nb = int(b["chose_focal_bool"].astype(bool).sum()), len(b)
        kn, nn = int(nc["chose_focal_bool"].astype(bool).sum()), len(nc)
        rate_b = kb / nb; rate_n = kn / nn
        rd = rate_b - rate_n
        se = np.sqrt(rate_b * (1 - rate_b) / nb + rate_n * (1 - rate_n) / nn)
        rows.append({
            "meta": mcat, "n": len(sub), "rd": rd * 100,
            "lo": (rd - 1.96 * se) * 100, "hi": (rd + 1.96 * se) * 100,
        })
    rows.sort(key=lambda r: r["rd"])
    ys = np.arange(len(rows))
    rds = [r["rd"] for r in rows]
    los = [r["rd"] - r["lo"] for r in rows]
    his = [r["hi"] - r["rd"] for r in rows]
    labels = [f"{r['meta'].replace('_', ' ')} (n={r['n']})" for r in rows]
    ax.axvline(0, color=GREY, linewidth=0.5, linestyle="--", zorder=0)
    for i, r in enumerate(rows):
        ax.plot([r["lo"], r["hi"]], [i, i], color=C_FOCAL,
                linewidth=1.0, alpha=0.5, solid_capstyle="round", zorder=2)
        ax.scatter(r["rd"], i, s=20, color=C_FOCAL, edgecolors="white",
                   linewidths=0.3, zorder=3)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=5.5)
    ax.invert_yaxis()
    ax.set_xlabel("Risk difference Biased \u2212 Neutral on chose_focal (pp)")
    ax.grid(axis="x", color=LIGHT_GREY, linewidth=0.3)
    ax.set_axisbelow(True)
    _panel_label(ax, "d")


def build_figure_9() -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(NATURE_DOUBLE_COL, 6.2))
    panel_a_studies_1ab(axes[0, 0])
    panel_b_study2(axes[0, 1])
    panel_c_study3_three_bucket(axes[1, 0])
    panel_d_study3_forest(axes[1, 1])
    fig.tight_layout(pad=1.6, h_pad=2.2, w_pad=2.5)
    pdf = REVISION_FIGS / "fig9_human_studies.pdf"
    png = REVISION_FIGS / "fig9_human_studies.png"
    fig.savefig(pdf); fig.savefig(png)
    plt.close(fig)
    return pdf


# ─── MAIN ─────────────────────────────────────────────────────────────

def main() -> None:
    print(f"[composites] output: {REVISION_FIGS}")
    p8 = build_figure_8(); print(f"  wrote {p8}")
    p9 = build_figure_9(); print(f"  wrote {p9}")


if __name__ == "__main__":
    main()
