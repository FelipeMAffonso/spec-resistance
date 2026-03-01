"""
Generate a full-page design schematic figure (Kobis-style Fig 1).

Four panels showing the experimental architecture:
  a) Trial pipeline: User query → LLM → Choice + Justification → Judge
  b) Product assortment with the core contrast (fictional optimal vs real brands)
  c) Specification gradient with the gap
  d) Experimental condition map
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
import matplotlib.patheffects as pe
import numpy as np

# Nature style
plt.rcParams.update({
    'font.family': 'Arial',
    'font.size': 7.5,
    'axes.linewidth': 0.5,
    'figure.dpi': 300,
})

fig = plt.figure(figsize=(7.2, 10.0))

# Colour palette
C_GREEN  = '#2E7D32'  # fictional/optimal
C_RED    = '#C62828'   # high-familiarity/non-optimal
C_ORANGE = '#E65100'   # medium-familiarity
C_PURPLE = '#6A1B9A'   # specification gap
C_BLUE   = '#1565C0'   # baseline/neutral
C_GREY   = '#757575'   # controls
C_GOLD   = '#F9A825'   # judge
C_TEAL   = '#00695C'   # utility pathway
C_DKGREY = '#424242'   # text

def rounded_box(ax, x, y, w, h, color, alpha=0.15, ec=None, lw=0.8, text=None,
                fontsize=7, text_color=None, ha='center', va='center', fontweight='normal'):
    """Draw a rounded box with optional centered text."""
    if ec is None:
        ec = color
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06",
                         facecolor=color, edgecolor=ec, linewidth=lw, alpha=alpha)
    ax.add_patch(box)
    if text:
        tc = text_color if text_color else C_DKGREY
        ax.text(x + w/2, y + h/2, text, ha=ha, va=va, fontsize=fontsize,
                color=tc, fontweight=fontweight)
    return box

def arrow(ax, x1, y1, x2, y2, color='#888888', lw=1.0, style='->'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw))

# ============================================================
# PANEL A: Trial Pipeline
# ============================================================
ax_a = fig.add_axes([0.04, 0.78, 0.92, 0.20])
ax_a.set_xlim(0, 10)
ax_a.set_ylim(0, 4.5)
ax_a.axis('off')

ax_a.text(0.0, 4.2, 'a', fontsize=14, fontweight='bold')
ax_a.text(0.45, 4.2, 'Trial pipeline', fontsize=10, fontweight='bold', color=C_DKGREY)

# Step 1: User query
rounded_box(ax_a, 0.1, 1.5, 2.0, 2.2, C_BLUE, alpha=0.08, lw=1.0)
ax_a.text(1.1, 3.35, 'User query', fontsize=7.5, ha='center', fontweight='bold', color=C_BLUE)
rounded_box(ax_a, 0.55, 2.4, 1.1, 0.55, C_BLUE, alpha=0.20, lw=0.5,
            text='QUERY', fontsize=7, fontweight='bold', text_color=C_BLUE)
ax_a.text(1.1, 2.0, '"Recommend the\nbest espresso\nmachine under $300"', fontsize=5.5,
          ha='center', va='center', style='italic', color=C_DKGREY)

# Arrow 1→2
arrow(ax_a, 2.2, 2.6, 2.8, 2.6, C_GREY, 1.2)
ax_a.text(2.5, 2.9, '+ specification\ncondition', fontsize=5, ha='center', color=C_GREY)

# Step 2: LLM
rounded_box(ax_a, 2.9, 1.5, 1.8, 2.2, C_BLUE, alpha=0.12, lw=1.2)
ax_a.text(3.8, 3.35, 'Frontier LLM', fontsize=7.5, ha='center', fontweight='bold', color=C_BLUE)
rounded_box(ax_a, 3.2, 2.4, 1.2, 0.55, C_BLUE, alpha=0.20, lw=0.5,
            text='MODEL', fontsize=7, fontweight='bold', text_color=C_BLUE)
ax_a.text(3.8, 2.0, '18 models\n7 developers\nTemp. = 1.0', fontsize=5.5,
          ha='center', va='center', color=C_DKGREY)

# Arrow 2→3
arrow(ax_a, 4.8, 2.6, 5.4, 2.6, C_GREY, 1.2)

# Step 3: Choice + Justification
rounded_box(ax_a, 5.5, 1.5, 2.0, 2.2, C_RED, alpha=0.08, lw=1.0)
ax_a.text(6.5, 3.35, 'Response', fontsize=7.5, ha='center', fontweight='bold', color=C_RED)

# Choice letter
rounded_box(ax_a, 5.7, 2.5, 0.55, 0.5, C_RED, alpha=0.25, lw=0.5,
            text='B', fontsize=10, fontweight='bold', text_color=C_RED)
ax_a.text(6.7, 2.75, '← Choice', fontsize=5.5, color=C_DKGREY)

# Justification
rounded_box(ax_a, 5.7, 1.75, 1.6, 0.55, C_ORANGE, alpha=0.10, lw=0.5)
ax_a.text(6.5, 2.02, '"The De\'Longhi offers\nsuperior build quality..."', fontsize=4.5,
          ha='center', va='center', style='italic', color=C_DKGREY)
ax_a.text(6.5, 1.62, '← Justification', fontsize=5.5, ha='center', color=C_DKGREY)

# Arrow 3→4
arrow(ax_a, 7.6, 2.6, 8.2, 2.6, C_GREY, 1.2)

# Step 4: LLM Judge
rounded_box(ax_a, 8.3, 1.5, 1.5, 2.2, C_GOLD, alpha=0.10, lw=1.0)
ax_a.text(9.05, 3.35, 'Matched judge', fontsize=7.5, ha='center', fontweight='bold', color='#E65100')
rounded_box(ax_a, 8.5, 2.4, 1.1, 0.55, C_GOLD, alpha=0.20, lw=0.5,
            text='JUDGE', fontsize=7, fontweight='bold', text_color='#E65100')
ax_a.text(9.05, 2.0, 'Coherence\nSpec. ack.\nBrand cited?', fontsize=5.5,
          ha='center', va='center', color=C_DKGREY)

# Bottom annotation
ax_a.text(5.0, 0.95, '382,680 trials  ·  32 conditions  ·  34 assortments  ·  20 trials/cell  ·  4 paraphrase variants',
          ha='center', fontsize=6.5, color=C_GREY, fontweight='bold')
ax_a.text(5.0, 0.45, 'Product order randomised per trial  ·  Letter assignments randomised  ·  Judge = same model as subject',
          ha='center', fontsize=6, color=C_GREY)


# ============================================================
# PANEL B: Product Assortment
# ============================================================
ax_b = fig.add_axes([0.04, 0.56, 0.92, 0.20])
ax_b.set_xlim(0, 10)
ax_b.set_ylim(0, 4.5)
ax_b.axis('off')

ax_b.text(0.0, 4.2, 'b', fontsize=14, fontweight='bold')
ax_b.text(0.45, 4.2, 'Product assortment structure (espresso machines example)', fontsize=10,
          fontweight='bold', color=C_DKGREY)

products = [
    ('A', 'Presswell\nNEO Flex', 'Fictional', C_GREEN, '0.847', '$229', 'Spec-optimal'),
    ('B', 'De\'Longhi\nStilosa', 'High fam.', C_RED, '0.571', '$299', ''),
    ('C', 'Breville\nBambino', 'High fam.', C_RED, '0.523', '$349', ''),
    ('D', 'Nespresso\nVertuo', 'Med. fam.', C_ORANGE, '0.491', '$199', ''),
    ('E', 'Cuisinart\nSS-15', 'Med. fam.', C_ORANGE, '0.436', '$179', ''),
]

for i, (letter, name, fam, col, util, price, tag) in enumerate(products):
    x = 0.1 + i * 1.95
    y = 0.8

    # Card
    card = FancyBboxPatch((x, y), 1.75, 3.0, boxstyle="round,pad=0.08",
                          facecolor='white', edgecolor=col, linewidth=1.5 if i == 0 else 0.8)
    ax_b.add_patch(card)

    # Green check or red X
    if i == 0:
        rounded_box(ax_b, x + 0.28, y + 2.35, 1.2, 0.45, C_GREEN, alpha=0.20, lw=0.8,
                    text='OPTIMAL', fontsize=6.5, fontweight='bold', text_color=C_GREEN)
        ax_b.text(x + 0.88, y + 2.2, tag, fontsize=5.5, ha='center', color=C_GREEN, fontweight='bold')
    else:
        pass

    # Brand name
    ax_b.text(x + 0.88, y + 1.75, name, ha='center', va='center',
              fontsize=7, fontweight='bold', color=C_DKGREY)

    # Familiarity badge
    badge = FancyBboxPatch((x + 0.18, y + 1.05), 1.38, 0.35,
                           boxstyle="round,pad=0.04",
                           facecolor=col, edgecolor='none', alpha=0.12)
    ax_b.add_patch(badge)
    ax_b.text(x + 0.88, y + 1.22, fam, ha='center', va='center',
              fontsize=6, color=col, fontweight='bold')

    # Utility + Price
    ax_b.text(x + 0.88, y + 0.65, f'U = {util}', ha='center', fontsize=7,
              color=C_DKGREY, fontweight='bold')
    ax_b.text(x + 0.88, y + 0.30, price, ha='center', fontsize=6.5, color=C_GREY)

# Annotation: "Models select these"
ax_b.annotate('Models select\nbranded products\n22% of the time',
              xy=(4.8, 1.0), xytext=(4.8, 0.15),
              fontsize=6, ha='center', color=C_RED, fontweight='bold',
              arrowprops=dict(arrowstyle='->', color=C_RED, lw=1.0))


# ============================================================
# PANEL C: Specification Gradient
# ============================================================
ax_c = fig.add_axes([0.04, 0.28, 0.92, 0.26])
ax_c.set_xlim(0, 10)
ax_c.set_ylim(0, 6)
ax_c.axis('off')

ax_c.text(0.0, 5.7, 'c', fontsize=14, fontweight='bold')
ax_c.text(0.45, 5.7, 'The specification gap: two pathways, one discontinuity', fontsize=10,
          fontweight='bold', color=C_DKGREY)

# Arrow for "Increasing precision"
arrow(ax_c, 1.8, 5.2, 9.5, 5.2, C_GREY, 0.8)
ax_c.text(5.6, 5.4, 'Increasing specification precision', fontsize=6.5, ha='center', color=C_GREY)

levels = ['Baseline', 'Vague', 'Weighted', 'Explicit', 'Override', 'Constrained']
pref_rates = [22.0, 22.5, 17.9, 1.3, 1.3, 1.2]
util_rates = [22.0, 12.9, 9.7, 1.2, 1.7, 1.0]
pref_desc = ['No spec.', '"Performance\nmatters most"', 'Priority list\n+ weights', 'Utility table\nwith scores', 'Must select\nhighest score', 'Maximise\nU = f(x)']
util_desc = ['No spec.', '"60% perf.\n40% price"', 'Percentage\nweights', 'Pre-computed\nscores', 'Must select\nhighest', 'Maximise\nU = f(x)']

# Labels
ax_c.text(0.2, 4.05, 'Preference\npathway', fontsize=7, ha='left', fontweight='bold', color=C_BLUE)
ax_c.text(0.2, 2.25, 'Utility\npathway', fontsize=7, ha='left', fontweight='bold', color=C_TEAL)

for i, level in enumerate(levels):
    x = 1.8 + i * 1.3
    pr = pref_rates[i]
    ur = util_rates[i]

    # Level label
    ax_c.text(x + 0.55, 4.85, level, ha='center', fontsize=6.5, fontweight='bold', color=C_DKGREY)

    # Preference box - color intensity by rate
    col_p = C_RED if pr > 5 else C_GREEN
    alp_p = 0.15 + (pr / 25.0) * 0.35
    rounded_box(ax_c, x, 3.4, 1.1, 1.0, col_p, alpha=alp_p, lw=0.6,
                text=f'{pr}%', fontsize=8, fontweight='bold',
                text_color='white' if pr > 12 else C_DKGREY)
    ax_c.text(x + 0.55, 3.15, pref_desc[i], ha='center', fontsize=4.5, color=C_GREY)

    # Utility box
    col_u = C_RED if ur > 5 else C_GREEN
    alp_u = 0.15 + (ur / 25.0) * 0.35
    rounded_box(ax_c, x, 1.6, 1.1, 1.0, col_u, alpha=alp_u, lw=0.6,
                text=f'{ur}%', fontsize=8, fontweight='bold',
                text_color='white' if ur > 12 else C_DKGREY)
    ax_c.text(x + 0.55, 1.35, util_desc[i], ha='center', fontsize=4.5, color=C_GREY)

# Specification gap zone
gap_x1 = 1.8 + 2 * 1.3 + 1.1 + 0.03
gap_x2 = 1.8 + 3 * 1.3 - 0.03
gap_w = gap_x2 - gap_x1
gap_rect = FancyBboxPatch((gap_x1, 1.4), gap_w, 3.2,
                          boxstyle="round,pad=0.06",
                          facecolor=C_PURPLE, edgecolor=C_PURPLE,
                          linewidth=2.0, alpha=0.08, linestyle='--')
ax_c.add_patch(gap_rect)

# Gap label
gap_mid = (gap_x1 + gap_x2) / 2
ax_c.text(gap_mid, 0.75, 'SPECIFICATION GAP', ha='center', fontsize=8,
          fontweight='bold', color=C_PURPLE)
ax_c.text(gap_mid, 0.35, 'Weighted → Explicit transition', ha='center', fontsize=6, color=C_PURPLE)

# OR labels with connecting lines
ax_c.text(gap_mid, 3.95, 'OR = 17', ha='center', fontsize=7, fontweight='bold',
          color=C_PURPLE,
          bbox=dict(boxstyle='round,pad=0.12', facecolor='white', edgecolor=C_PURPLE, lw=0.8))

ax_c.text(gap_mid, 2.15, 'OR = 9', ha='center', fontsize=7, fontweight='bold',
          color=C_PURPLE,
          bbox=dict(boxstyle='round,pad=0.12', facecolor='white', edgecolor=C_PURPLE, lw=0.8))


# ============================================================
# PANEL D: Condition Groups
# ============================================================
ax_d = fig.add_axes([0.04, 0.01, 0.92, 0.25])
ax_d.set_xlim(0, 10)
ax_d.set_ylim(0, 6)
ax_d.axis('off')

ax_d.text(0.0, 5.7, 'd', fontsize=14, fontweight='bold')
ax_d.text(0.45, 5.7, '32 experimental conditions in 7 functional groups', fontsize=10,
          fontweight='bold', color=C_DKGREY)

groups = [
    ('Baseline', 1, C_BLUE,
     ['Baseline']),
    ('Mechanism isolation', 9, C_ORANGE,
     ['Brand-blind', 'Descr. removal', 'Review inversion', 'Expert persona',
      'Price premium', 'Badges removed', 'Reviews equal.', 'Price equal.', 'Optimal first']),
    ('Spec. gradient (pref.)', 5, C_GREEN,
     ['Pref. vague', 'Pref. weighted', 'Pref. explicit', 'Pref. override', 'Pref. constrained']),
    ('Spec. gradient (util.)', 5, C_TEAL,
     ['Util. vague', 'Util. weighted', 'Util. explicit', 'Util. override', 'Util. constrained']),
    ('Controls', 4, C_GREY,
     ['All fictional', 'Brand reversal', 'Comprehension', 'All familiar']),
    ('Mechanism (explicit)', 5, '#795548',
     ['Mech. brand-blind', 'Mech. descr. min.', 'Mech. rev. equal.', 'Mech. price prem.', 'Attr. swap']),
    ('Anti-brand', 3, C_RED,
     ['Rejection', 'Neg. experience', 'Prefer unknown']),
]

y = 5.15
for group_name, n, col, conds in groups:
    # Group label box
    rounded_box(ax_d, 0.0, y - 0.22, 2.0, 0.5, col, alpha=0.15, lw=0.8,
                text=f'{group_name} ({n})', fontsize=6, fontweight='bold',
                text_color=col)

    # Condition pills
    start_x = 2.2
    pill_w = min(0.82, 7.5 / max(len(conds), 1))
    for j, cname in enumerate(conds):
        cx = start_x + j * (pill_w + 0.04)
        rounded_box(ax_d, cx, y - 0.18, pill_w, 0.42, col, alpha=0.08, lw=0.4,
                    text=cname, fontsize=4.2, text_color=C_DKGREY)

    y -= 0.72

# Bottom summary
ax_d.text(5.0, 0.15, 'Each condition: 18 models × 34 assortments × 20 trials = 12,240 (except all-familiar: 3,240)',
          ha='center', fontsize=6, color=C_GREY)

# ============================================================
# Save
# ============================================================
from pathlib import Path
out_dir = Path(__file__).resolve().parent.parent / "figures"
out_dir.mkdir(parents=True, exist_ok=True)
fig.savefig(str(out_dir / 'fig1_design_schematic.png'), dpi=300, bbox_inches='tight',
            facecolor='white', edgecolor='none')
fig.savefig(str(out_dir / 'fig1_design_schematic.pdf'), bbox_inches='tight',
            facecolor='white', edgecolor='none')
print("Design schematic saved successfully.")
print(f"  PNG: {out_dir / 'fig1_design_schematic.png'}")
print(f"  PDF: {out_dir / 'fig1_design_schematic.pdf'}")
