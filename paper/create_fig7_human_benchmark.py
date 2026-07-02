#!/usr/bin/env python3
"""create_fig7_human_benchmark.py - Figure 7 (human-advisor benchmark), CONFIRMATORY FINAL.

Values are the pre-registered confirmatory study (N = 1,182 kept of 1,200 recruited; Prolific
6a45bfc2b0e5b9f724fae913 / Qualtrics SV_3aTREYk0P17q75k), computed by
post-1st-review/reruns/confirmatory_FINAL_numbers.py from the final settled export restricted to
the 1,200 approved submissions (source of truth: reruns/confirmatory_FINAL_numbers.json):
  humans by level: baseline 257/387 (66.4%), weighted 287/400 (71.8%), explicit 261/395 (66.1%);
  matched model arm (occupancy-weighted): baseline 36.3%, weighted 42.7%, explicit 99.7%;
  NL levels by frame: advisor 75.4 vs 39.6 (+35.8); chooser 62.6 vs 39.5 (+23.1).
House style matched to fig9_human_studies (navy human, crimson model, Wilson CIs, shared legend)
and to the shared Nature style block in analysis/generate_figures_nature.py (Arial 7 pt, 0.4 pt
spines, 600 dpi, bold 10 pt panel letters).
"""
import math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUTS = [ROOT / "results" / "figures", ROOT / "OSF" / "results" / "figures"]

HUMAN = {"baseline": (257, 387), "weighted": (287, 400), "explicit\nnumeric": (261, 395)}
MODEL = {"baseline": 36.3, "weighted": 42.7, "explicit\nnumeric": 99.7}
FRAMES = {"advise other": (75.4, 39.6), "choose self": (62.6, 39.5)}

NAVY, CRIMSON = "#1f4e79", "#a51c30"


def wilson(k, n):
    if n == 0:
        return 0, 0, 0
    p = k / n
    z = 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * p, 100 * (c - h), 100 * (c + h)


# ── Nature house style (mirrors analysis/generate_figures_nature.py) ──
plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 7,
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 6,
    "figure.dpi": 600,
    "savefig.dpi": 600,
    "axes.linewidth": 0.4,
    "xtick.major.width": 0.4,
    "ytick.major.width": 0.4,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "lines.linewidth": 1.2,
})

fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6), gridspec_kw={"width_ratios": [1.35, 1]})

ax = axes[0]
levels = list(HUMAN.keys())
x = range(len(levels))
hp = [wilson(*HUMAN[r]) for r in levels]
ax.errorbar(x, [v[0] for v in hp],
            yerr=[[v[0] - v[1] for v in hp], [v[2] - v[0] for v in hp]],
            fmt="o-", color=NAVY, lw=1.2, ms=3.5, capsize=2,
            elinewidth=0.8, capthick=0.8, label="Human advisors")
ax.plot(x, [MODEL[r] for r in levels], "s--", color=CRIMSON, lw=1.2, ms=3.5,
        dashes=(4, 2.5), label="Matched model arm (30-model corpus)")
for i, r in enumerate(levels):
    ax.annotate(f"{hp[i][0]:.0f}%", (i, hp[i][0]), textcoords="offset points",
                xytext=(0, 8.5), ha="center", fontsize=6.5, color=NAVY)
    ax.annotate(f"{MODEL[r]:.0f}%", (i, MODEL[r]), textcoords="offset points",
                xytext=(0, -12), ha="center", fontsize=6.5, color=CRIMSON)
ax.set_xticks(list(x))
ax.set_xticklabels(levels)
ax.set_xlim(-0.25, len(levels) - 0.75)
ax.set_ylabel("Specification-optimal choice (%)")
ax.set_ylim(0, 105)
ax.set_yticks(range(0, 101, 20))
ax.text(-0.16, 1.04, "a", transform=ax.transAxes, fontsize=10,
        fontweight="bold", va="bottom", ha="left")
ax.text(0, 1.04, "By instruction level", transform=ax.transAxes,
        fontsize=8, va="bottom", ha="left")
# Legend ordered to match the visual stacking (human line sits on top)
_handles, _labels = ax.get_legend_handles_labels()
_order = [_labels.index("Human advisors"),
          _labels.index("Matched model arm (30-model corpus)")]
ax.legend([_handles[i] for i in _order], [_labels[i] for i in _order],
          frameon=False, loc="lower right", handlelength=1.8,
          borderaxespad=0.3, labelspacing=0.4)

ax = axes[1]
labels = list(FRAMES.keys())
xb = range(len(labels))
w = 0.32
ax.bar([i - w / 2 for i in xb], [FRAMES[k][0] for k in labels], w, color=NAVY, label="Human")
ax.bar([i + w / 2 for i in xb], [FRAMES[k][1] for k in labels], w, color=CRIMSON, label="Model")
for i, k in enumerate(labels):
    hv, mv = FRAMES[k]
    ax.annotate(f"{hv:.0f}%", (i - w / 2, hv), textcoords="offset points", xytext=(0, 2),
                ha="center", fontsize=6.5, color=NAVY)
    ax.annotate(f"{mv:.0f}%", (i + w / 2, mv), textcoords="offset points", xytext=(0, 2),
                ha="center", fontsize=6.5, color=CRIMSON)
    ax.annotate(f"+{hv - mv:.1f} pp", (i, max(hv, mv) + 10), ha="center", fontsize=7,
                fontweight="bold", color="#333333")
ax.set_xticks(list(xb))
ax.set_xticklabels(labels)
ax.set_xlim(-0.55, len(labels) - 0.45)
ax.set_ylim(0, 105)
ax.set_yticks(range(0, 101, 20))
ax.text(-0.13, 1.04, "b", transform=ax.transAxes, fontsize=10,
        fontweight="bold", va="bottom", ha="left")
ax.text(0, 1.04, "Natural-language levels, by frame", transform=ax.transAxes,
        fontsize=8, va="bottom", ha="left")

fig.text(0.995, 0.015, "Pre-registered confirmatory study (N = 1,182 kept of 1,200 recruited)",
         ha="right", fontsize=6, style="italic", color="#666666")
fig.tight_layout(rect=(0, 0.05, 1, 1), w_pad=2.2)

for out in OUTS:
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / "fig7_human_benchmark.png", dpi=600)
    fig.savefig(out / "fig7_human_benchmark.pdf")
    print("wrote", out / "fig7_human_benchmark.png")
