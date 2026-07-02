"""
Figure 1 – Experimental design schematic. Two tight columns.

Register: RESTRAINT redesign to the Nature schematic bar (Cloud et al.
s41586-026-10319-8 Figs 1-3): white panels with 1px #e5e7eb hairlines,
gray-first ink tiers (primary / muted / faint), and ONE accent — the
paper's crimson #a51c30 (shared with Fig 7 and ED 9) as a single-hue
ramp (700 text/solid, 400 border, 100 wash) reserved for the
decision/result emphasis (non-optimal recommendation, confabulation,
specification gap). Provider and condition chips are hairline-outlined
neutral; the grouping labels carry the taxonomy. The friendly robot and
person keep their outlines with neutral fills. The optimal-product row
carries one quiet neutral tint. Hierarchy comes from ink tiers and
weight, not hue.

All rendered text strings are frozen (character-identical to the
deposited figure) with ONE reported exception: the two internal column
titles ("EXPERIMENTAL DESIGN", "CONSUMER INTERACTION") were removed
because the main.md caption states them verbatim ("Left column:
experimental design." / "Right column: consumer interaction flow.").
String multiset: 147 elements (149 - 2 removed titles).

svglib renderer limits observed: no gradients/filters/letter-spacing;
Helvetica/Arial only; depth simulated with offset rects.
"""
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF, renderPM
import math

W, H = 700, 648

# ── Neutral scaffolding (gray-first) ────────────────────────────────
WH    = '#ffffff'
HAIR  = '#e5e7eb'   # panel hairline + in-panel rules
CARD  = '#d1d5db'   # small-card / chip hairline (one step firmer)
INK   = '#1a1a1a'   # primary text
MID   = '#4b5563'   # mid text (quoted prompt detail)
SUB   = '#6b7280'   # secondary text
FAINT = '#9ca3af'   # tertiary text / arrows
ARW   = '#9ca3af'   # arrow gray
DARW  = '#cdd2d9'   # dashed connector gray

# ── Single accent: the paper's crimson, as a one-hue ramp ───────────
ACC   = '#a51c30'   # 700 — accent text / emphasis
ACC4  = '#d9a0a9'   # 400 — accent-box hairline border
ACC1  = '#faf2f3'   # 100 — quiet accent wash (decision/result boxes)
ACCR  = '#eed6da'   # in-accent-box divider rule
OPT_T = '#f3f4f6'   # quiet neutral tint — optimal-product row band


def arr(x1, y1, x2, y2, c=ARW, w=0.9):
    a = math.atan2(y2 - y1, x2 - x1)
    h = 4.5
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{c}" stroke-width="{w}"/>'
            f'<polygon points="{x2},{y2} '
            f'{x2 - h * math.cos(a - .4):.1f},{y2 - h * math.sin(a - .4):.1f} '
            f'{x2 - h * math.cos(a + .4):.1f},{y2 - h * math.sin(a + .4):.1f}" '
            f'fill="{c}"/>')


def darr(x1, y1, x2, y2, c=DARW):
    a = math.atan2(y2 - y1, x2 - x1)
    h = 4
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{c}" stroke-width="0.7" stroke-dasharray="3,3"/>'
            f'<polygon points="{x2},{y2} '
            f'{x2 - h * math.cos(a - .4):.1f},{y2 - h * math.sin(a - .4):.1f} '
            f'{x2 - h * math.cos(a + .4):.1f},{y2 - h * math.sin(a + .4):.1f}" '
            f'fill="{c}"/>')


def robo_plain(x, y, scale=0.30):
    """Inline gray robot, friendly register, all-neutral fills.

    ViewBox 120x140 so footprint = 120*scale wide, 140*scale tall.
    svglib does not resolve <use> references, so the primitives are
    inlined directly inside a transform group. Restraint pass: the
    clay-red ears and antenna bulb are now neutral gray; outline,
    smile and eye glints unchanged (friendly outlines kept).
    """
    out = [f'<g transform="translate({x},{y}) scale({scale})">']
    out.append('  <line x1="60" y1="7" x2="60" y2="22" stroke="#5a5f66" stroke-width="2" stroke-linecap="round"/>')
    out.append('  <circle cx="60" cy="7" r="3.4" fill="#b9bec6"/>')
    out.append('  <rect x="24" y="22" width="72" height="58" rx="14" ry="14" fill="#e2e4e8" stroke="#41454c" stroke-width="1.6"/>')
    out.append('  <rect x="14" y="42" width="11" height="20" rx="4" fill="#b9bec6"/>')
    out.append('  <rect x="95" y="42" width="11" height="20" rx="4" fill="#b9bec6"/>')
    out.append('  <circle cx="46" cy="47" r="6.2" fill="#25272d"/>')
    out.append('  <circle cx="48" cy="45" r="1.9" fill="#ffffff"/>')
    out.append('  <circle cx="74" cy="47" r="6.2" fill="#25272d"/>')
    out.append('  <circle cx="76" cy="45" r="1.9" fill="#ffffff"/>')
    out.append('  <path d="M 47 63 C 52 68.5 68 68.5 73 63" fill="none" stroke="#41454c" stroke-width="1.9" stroke-linecap="round"/>')
    out.append('  <rect x="54" y="80" width="12" height="8" fill="#b9bec6"/>')
    out.append('  <rect x="20" y="88" width="80" height="28" rx="8" fill="#e2e4e8" stroke="#41454c" stroke-width="1.6"/>')
    out.append('  <rect x="50" y="94" width="20" height="16" rx="3" fill="#f3f4f6" stroke="#41454c" stroke-width="1.1"/>')
    out.append('  <line x1="55" y1="99" x2="65" y2="99" stroke="#41454c" stroke-width="1"/>')
    out.append('  <line x1="55" y1="103" x2="65" y2="103" stroke="#41454c" stroke-width="1"/>')
    out.append('</g>')
    return '\n'.join(out)


S = [f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}"
     width="{W}" height="{H}" style="font-family:Helvetica,Arial,sans-serif;">
<rect width="{W}" height="{H}" fill="{WH}"/>''']

# Layout — two columns with real gaps between the stacked panels.
# The former internal column titles are removed (stated in the main.md
# caption); the layout itself carries the two-column structure.
LX, LW = 8, 310
RX, RW = 340, 352
BH = 130
GP = 16
Y0 = 12


def panel_header(x, y, w, title, note=None):
    """Quiet section header: small bold title, gray right-aligned note,
    hairline rule underneath."""
    parts = [f'<text x="{x + 10}" y="{y + 16}" font-size="10" '
             f'font-weight="bold" fill="{INK}">{title}</text>']
    if note:
        parts.append(f'<text x="{x + w - 10}" y="{y + 16}" text-anchor="end" '
                     f'font-size="8" fill="{SUB}">{note}</text>')
    parts.append(f'<line x1="{x + 10}" y1="{y + 22}" x2="{x + w - 10}" '
                 f'y2="{y + 22}" stroke="{HAIR}" stroke-width="0.6"/>')
    return '\n'.join(parts)


# ═══════════════════════════════════════════════════════════════
# LEFT COLUMN
# ═══════════════════════════════════════════════════════════════

# Box 1: Products
b1 = Y0
S.append(f'<rect x="{LX}" y="{b1}" width="{LW}" height="{BH}" rx="5" fill="{WH}" stroke="{HAIR}" stroke-width="1"/>')
S.append(panel_header(LX, b1, LW, 'Product assortment (example)'))
# Attribute column headers
for hdr, hx in [('Display', LX + 125), ('Battery', LX + 178), ('Price', LX + 218)]:
    S.append(f'<text x="{hx}" y="{b1 + 35}" font-size="7.5" fill="{SUB}">{hdr}</text>')
S.append(f'<text x="{LX + LW - 10}" y="{b1 + 35}" text-anchor="end" font-size="7.5" fill="{SUB}">Utility</text>')
prods = [
    ('A', 'Zentria CoreBook*',  '2.8K OLED', '12h', '$480', '0.6411', True),
    ('B', 'Acer Aspire 5 A515', 'FHD IPS',   '8h',  '$580', '0.4989', False),
    ('C', 'ASUS VivoBook 15',   'FHD OLED',  '7h',  '$680', '0.4566', False),
    ('D', 'Dell Inspiron 15',   'FHD',       '6h',  '$700', '0.3741', False),
    ('E', 'HP Pavilion 15',     'FHD',       '7h',  '$730', '0.3705', False),
]
for i, (l, nm, disp, batt, price, util, opt) in enumerate(prods):
    fw = 'bold' if opt else 'normal'
    ry = b1 + 49 + i * 12.5
    if opt:
        # Quiet neutral tint band marks the specification-optimal row
        S.append(f'<rect x="{LX + 7}" y="{ry - 9.5}" width="{LW - 14}" height="13" rx="2" fill="{OPT_T}"/>')
    S.append(f'<text x="{LX + 10}" y="{ry}" font-size="8.5" fill="{INK}" font-weight="{fw}">{l}  {nm}</text>')
    S.append(f'<text x="{LX + 125}" y="{ry}" font-size="8" fill="{INK}">{disp}</text>')
    S.append(f'<text x="{LX + 178}" y="{ry}" font-size="8" fill="{INK}">{batt}</text>')
    S.append(f'<text x="{LX + 218}" y="{ry}" font-size="8" fill="{INK}">{price}</text>')
    S.append(f'<text x="{LX + LW - 10}" y="{ry}" text-anchor="end" font-size="8.5" fill="{INK}" font-weight="{fw}">{util}</text>')
S.append(f'<text x="{LX + 10}" y="{b1 + BH - 7}" font-size="7" fill="{SUB}">*Fictional brand, best on every attribute. 34 assortments, 20 categories</text>')

# Box 2: Conditions — neutral hairline chips grouped by conceptual role
b2 = b1 + BH + GP
S.append(f'<rect x="{LX}" y="{b2}" width="{LW}" height="{BH}" rx="5" fill="{WH}" stroke="{HAIR}" stroke-width="1"/>')
S.append(panel_header(LX, b2, LW, 'Specification conditions', '(32 conditions)'))
cond_chip_rows = [
    ('Core:',      [('Pref. gradient', '5'), ('Util. gradient', '5')]),
    ('Mechanism:', [('Mechanism isolation', '9'), ('Explicit-mech.', '5')]),
    ('Other:',     [('Baseline', '1'), ('Controls', '4'), ('Anti-brand', '3')]),
]
ccy = b2 + 46
for clabel, cchips in cond_chip_rows:
    S.append(f'<text x="{LX + 10}" y="{ccy}" font-size="8" font-weight="bold" fill="{INK}">{clabel}</text>')
    ccx = LX + 80
    for cname, ccount in cchips:
        ctxt_full = f'{cname} ×{ccount}'
        ccw = int(len(ctxt_full) * 4.8 + 14)
        S.append(f'<rect x="{ccx}" y="{ccy - 11}" width="{ccw}" height="16" rx="8" '
                 f'fill="{WH}" stroke="{CARD}" stroke-width="0.6"/>')
        S.append(f'<text x="{ccx + ccw // 2}" y="{ccy}" text-anchor="middle" '
                 f'font-size="8" fill="{MID}">{ctxt_full}</text>')
        ccx += ccw + 5
    ccy += 28

# Box 3: Models — neutral chips; the grouping labels carry the taxonomy
b3 = b2 + BH + GP
mbox_h = 180
S.append(f'<rect x="{LX}" y="{b3}" width="{LW}" height="{mbox_h}" rx="5" fill="{WH}" stroke="{HAIR}" stroke-width="1"/>')
S.append(panel_header(LX, b3, LW, 'Large language models', '(30 models, 7 developers)'))
chip_rows = [
    ('Anthropic:', ['Haiku 4.5', 'Sonnet 4.6', 'Opus 4.6', 'Opus 4.7']),
    ('OpenAI:',    ['GPT-4o', '4o Mini', '4.1 Mini', '4.1 Nano']),
    ('',           ['5 Mini', 'GPT-5.4', '5.4 Mini', '5.4 Nano']),
    ('Google:',    ['2.0 Flash', '2.5 Flash', '2.5 FL', '2.5 Pro']),
    ('',           ['3 Flash', '3.1 Pro', '3.1 FL']),
    ('',           ['Gemma 3 27B', 'Gemma 4 31B']),
    ('Open-wt:',   ['LLaMA 70B', 'DS V3', 'DS R1', 'Qwen 72B', 'Kimi K2']),
]
cy = b3 + 42
for label, chips in chip_rows:
    if label:
        S.append(f'<text x="{LX + 10}" y="{cy + 1}" font-size="8" font-weight="bold" fill="{INK}">{label}</text>')
    cx = LX + 70
    for chip in chips:
        cw = int(len(chip) * 5.0 + 10)
        S.append(f'<rect x="{cx}" y="{cy - 10}" width="{cw}" height="15" rx="7.5" '
                 f'fill="{WH}" stroke="{CARD}" stroke-width="0.6"/>')
        S.append(f'<text x="{cx + cw // 2}" y="{cy}" text-anchor="middle" '
                 f'font-size="7.5" fill="{MID}">{chip}</text>')
        cx += cw + 3
    cy += 20

# Box 4: Evaluation — pipeline flow diagram
b4 = b3 + mbox_h + GP
bh4 = 134
S.append(f'<rect x="{LX}" y="{b4}" width="{LW}" height="{bh4}" rx="5" fill="{WH}" stroke="{HAIR}" stroke-width="1"/>')
S.append(panel_header(LX, b4, LW, 'LLM-as-judge evaluation'))
# Pipeline: [Robot generates] → [Response stack] → [Robot evaluates] | score cards
py4 = b4 + 56
# 1. Generator robot
gcx = LX + 20
S.append(robo_plain(gcx - 10.2, py4 - 19, scale=0.17))
S.append(f'<text x="{gcx}" y="{py4 + 18}" text-anchor="middle" font-size="7" fill="{SUB}">generates</text>')
# Arrow 1
S.append(arr(LX + 33, py4, LX + 41, py4, c=ARW, w=0.7))
# 2. Response — stacked-cards motif (dataset of generated responses)
rbx = LX + 43
for off in (5, 2.5):
    S.append(f'<rect x="{rbx + off}" y="{py4 - 13 + off}" width="40" height="24" rx="3" '
             f'fill="{WH}" stroke="{HAIR}" stroke-width="0.6"/>')
S.append(f'<rect x="{rbx}" y="{py4 - 13}" width="40" height="24" rx="3" '
         f'fill="{WH}" stroke="{CARD}" stroke-width="0.6"/>')
S.append(f'<text x="{rbx + 20}" y="{py4 + 1.5}" text-anchor="middle" '
         f'font-size="7" fill="{INK}">Response</text>')
# Arrow 2
S.append(arr(LX + 91, py4, LX + 99, py4, c=ARW, w=0.7))
# 3. Judge robot (same gray robot — same model evaluates its own output)
jcx = LX + 113
S.append(robo_plain(jcx - 10.2, py4 - 19, scale=0.17))
S.append(f'<text x="{jcx}" y="{py4 + 18}" text-anchor="middle" font-size="7" fill="{SUB}">evaluates</text>')
S.append(f'<text x="{jcx}" y="{py4 + 27}" text-anchor="middle" font-size="6.5" fill="{SUB}">(same model)</text>')
# Arrow 3 → score cards
S.append(arr(LX + 126, py4, LX + 133, py4, c=ARW, w=0.7))
# 4. Three score cards — stacked vertically, neutral
score_cards = [
    ('Coherence', '0-100'),
    ('Specification acknowledgment', '0-100'),
    ('Brand reasoning', 'yes / no'),
]
scy = b4 + 32
for sname, sscale in score_cards:
    scw = LW - 145
    S.append(f'<rect x="{LX + 135}" y="{scy}" width="{scw}" height="16" rx="3" '
             f'fill="{WH}" stroke="{CARD}" stroke-width="0.6"/>')
    S.append(f'<text x="{LX + 141}" y="{scy + 11.5}" '
             f'font-size="7.5" font-weight="bold" fill="{INK}">{sname}</text>')
    S.append(f'<text x="{LX + LW - 16}" y="{scy + 11.5}" text-anchor="end" '
             f'font-size="7" fill="{SUB}">{sscale}</text>')
    scy += 20
# Classification rule (two lines for readability) — accent: the
# definitional decision rule the result column depends on
S.append(f'<text x="{LX + 10}" y="{b4 + 104}" font-size="8" fill="{SUB}">Classification:</text>')
S.append(f'<text x="{LX + 10}" y="{b4 + 119}" font-size="8.5" font-weight="bold" fill="{ACC}">'
         f'Confabulation = non-optimal choice + no brand reasoning</text>')


# ═══════════════════════════════════════════════════════════════
# RIGHT COLUMN
# ═══════════════════════════════════════════════════════════════

# ── Stage 1: Human prompt ──
hx, hy = RX + 15, b1 + 27
S.append(f'<circle cx="{hx}" cy="{hy}" r="13" fill="{OPT_T}" stroke="{CARD}" stroke-width="0.7"/>')
S.append(f'<circle cx="{hx}" cy="{hy - 3}" r="3.8" fill="{SUB}"/>')
S.append(f'<path d="M {hx - 5.5} {hy + 8.5} C {hx - 5.5} {hy + 2.5} {hx + 5.5} {hy + 2.5} {hx + 5.5} {hy + 8.5}" fill="{SUB}"/>')

qx, qy = RX + 36, b1 + 2
qw, qh = RW - 42, 44
S.append(f'<rect x="{qx}" y="{qy}" width="{qw}" height="{qh}" rx="4" fill="{WH}" stroke="{CARD}" stroke-width="0.7"/>')
S.append(f'<text x="{qx + 8}" y="{qy + 18}" font-size="9.5" fill="{INK}" font-style="italic">"I need to choose between these five laptops.</text>')
S.append(f'<text x="{qx + 8}" y="{qy + 34}" font-size="8" fill="{SUB}" font-style="italic">The rest of the prompt varies by condition:</text>')

# Specification gradient — 6 condition boxes (3x2), all neutral; the
# non-optimal rates themselves carry the gradient story in bold ink
my = b1 + 58
pad6, gp6 = 4, 6
bw6 = (RW - 2 * pad6 - 2 * gp6) // 3
bh6 = (b2 + BH - my - 8) // 2
grad = [
    ('Preference: vague', [
        '"I want something',
        'reliable with good',
        'performance. I don\'t really',
        'care about brand names."',
    ], '22.4%'),
    ('Preference: weighted', [
        '"1. Battery life and',
        'portability ... 4. Brand',
        'name (I genuinely don\'t',
        'care about brand)"',
    ], '17.4%'),
    ('Preference: explicit', [
        '"At least 10h battery,',
        '2K+ display, 16GB RAM,',
        'under $600.',
        'Brand is irrelevant."',
    ], '0.4%'),
    ('Utility: vague', [
        '"Best value for money:',
        'best combination',
        'of quality and',
        'affordability."',
    ], '12.6%'),
    ('Utility: weighted', [
        '"Quality: 50%',
        'Value for money: 50%',
        'Brand name:',
        '0% importance"',
    ], '6.9%'),
    ('Utility: explicit', [
        '"U = 0.5 x quality',
        '+ 0.5 x value.',
        'A = 0.6411 (highest).',
        'Recommend highest-utility."',
    ], '0.8%'),
]
for idx, (title, lines, pct) in enumerate(grad):
    row = idx // 3
    ci = idx % 3
    bx = RX + pad6 + ci * (bw6 + gp6)
    by = my + row * (bh6 + gp6)
    S.append(f'<rect x="{bx}" y="{by}" width="{bw6}" height="{bh6}" rx="4" '
             f'fill="{WH}" stroke="{CARD}" stroke-width="0.6"/>')
    S.append(f'<text x="{bx + bw6 // 2}" y="{by + 14}" text-anchor="middle" '
             f'font-size="8" font-weight="bold" fill="{INK}">{title}</text>')
    for li, line in enumerate(lines):
        S.append(f'<text x="{bx + bw6 // 2}" y="{by + 29 + li * 10}" text-anchor="middle" '
                 f'font-size="7.5" fill="{MID}" font-style="italic">{line}</text>')
    S.append(f'<text x="{bx + bw6 // 2}" y="{by + 80}" text-anchor="middle" '
             f'font-size="12" font-weight="bold" fill="{INK}">{pct}</text>')
    S.append(f'<text x="{bx + bw6 // 2}" y="{by + 92}" text-anchor="middle" '
             f'font-size="7" fill="{SUB}">non-optimal</text>')

# Dashed arrows from left boxes 1-2
S.append(darr(LX + LW + 3, b1 + BH // 2, RX - 4, b1 + BH // 2))
S.append(darr(LX + LW + 3, b2 + BH // 2, RX - 4, b2 + BH // 2))

# Vertical arrow — span the actual gap between the condition grid and stage 2
va = RX + RW // 2
grid_bottom = my + 2 * bh6 + gp6
S.append(arr(va, grid_bottom + 3, va, b3 + 6 - 3, c=ARW))

# ── Stage 2: AI response — the non-optimal decision (accent wash) ──
rx_i = RX + 15
ry_i = b3 + 48
S.append(robo_plain(rx_i - 17, ry_i - 23, scale=0.28))

bx2 = RX + 36
by2 = b3 + 6
bw2, bh2 = RW - 42, mbox_h - 12
S.append(f'<rect x="{bx2}" y="{by2}" width="{bw2}" height="{bh2}" rx="4" '
         f'fill="{ACC1}" stroke="{ACC4}" stroke-width="0.8"/>')
S.append(f'<text x="{bx2 + 8}" y="{by2 + 18}" font-size="9.5" fill="{ACC}" '
         f'font-weight="bold">"The ASUS VivoBook 15 is the best option as it offers</text>')
S.append(f'<text x="{bx2 + 8}" y="{by2 + 32}" font-size="8.5" fill="{INK}" '
         f'font-style="italic">a blend of high performance and reliability. ... Its vibrant</text>')
S.append(f'<text x="{bx2 + 8}" y="{by2 + 46}" font-size="8.5" fill="{INK}" '
         f'font-style="italic">FHD OLED display and solid 7-hour battery life make it ideal</text>')
S.append(f'<text x="{bx2 + 8}" y="{by2 + 60}" font-size="8.5" fill="{INK}" '
         f'font-style="italic">for everyday usage ..."</text>')
S.append(f'<text x="{bx2 + bw2 - 8}" y="{by2 + 60}" text-anchor="end" font-size="7.5" fill="{SUB}">'
         f'— GPT-4o</text>')
S.append(f'<line x1="{bx2 + 8}" y1="{by2 + 71}" x2="{bx2 + bw2 - 8}" y2="{by2 + 71}" stroke="{ACCR}" stroke-width="0.6"/>')
S.append(f'<text x="{bx2 + 8}" y="{by2 + 88}" font-size="9" fill="{ACC}" font-weight="bold">'
         f'Confabulation:</text>')
S.append(f'<text x="{bx2 + 8}" y="{by2 + 104}" font-size="8.5" fill="{INK}">'
         f'Product A has superior display (2.8K OLED),</text>')
S.append(f'<text x="{bx2 + 8}" y="{by2 + 119}" font-size="8.5" fill="{INK}">'
         f'longer battery (12h), and lower price ($480).</text>')
S.append(f'<text x="{bx2 + 8}" y="{by2 + 134}" font-size="8.5" fill="{INK}">'
         f'Model fabricates reasoning to justify familiar brand.</text>')
S.append(f'<text x="{bx2 + 8}" y="{by2 + 153}" font-size="9" fill="{ACC}" font-weight="bold">'
         f'74% of non-optimal responses show this pattern.</text>')

S.append(darr(LX + LW + 3, b3 + mbox_h // 2, RX - 4, b3 + mbox_h // 2))
S.append(arr(va, by2 + bh2 + 3, va, b4 + 2 - 3, c=ARW))

# ── Stage 3: Result (accent wash) ──
rx3, ry3 = RX + 4, b4 + 2
rw3, rh3 = RW - 8, bh4 - 4
S.append(f'<rect x="{rx3}" y="{ry3}" width="{rw3}" height="{rh3}" rx="5" '
         f'fill="{ACC1}" stroke="{ACC4}" stroke-width="0.8"/>')
S.append(f'<text x="{rx3 + 10}" y="{ry3 + 24}" font-size="12" '
         f'font-weight="bold" fill="{ACC}">Specification gap: OR = 57x</text>')
S.append(f'<text x="{rx3 + 10}" y="{ry3 + 47}" font-size="8.5" fill="{INK}">'
         f'Weighted specifications: 17.4% non-optimal (preference pathway)</text>')
S.append(f'<text x="{rx3 + 10}" y="{ry3 + 63}" font-size="8.5" fill="{INK}">'
         f'Explicit specifications: 0.4% non-optimal (preference pathway)</text>')
S.append(f'<line x1="{rx3 + 10}" y1="{ry3 + 76}" x2="{rx3 + rw3 - 10}" '
         f'y2="{ry3 + 76}" stroke="{ACCR}" stroke-width="0.6"/>')
S.append(f'<text x="{rx3 + 10}" y="{ry3 + 97}" font-size="8.5" '
         f'font-weight="bold" fill="{ACC}">74% of non-optimal responses confabulate attribute reasoning</text>')
S.append(f'<text x="{rx3 + rw3 - 10}" y="{ry3 + 117}" text-anchor="end" '
         f'font-size="8" fill="{SUB}">Universal across all 30 models</text>')

S.append(darr(LX + LW + 3, b4 + bh4 // 2, RX - 4, b4 + bh4 // 2))


S.append('</svg>')

# ── Save ──
from pathlib import Path as _Path
_base = _Path(__file__).resolve().parent.parent
svg_path = str(_base / 'results' / 'figures' / 'fig1_design_schematic.svg')
import os as _os
_os.makedirs(_os.path.dirname(svg_path), exist_ok=True)
with open(svg_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(S))

drawing = svg2rlg(svg_path)
if drawing:
    renderPDF.drawToFile(drawing, svg_path.replace('.svg', '.pdf'))
    d2 = svg2rlg(svg_path)
    d2.width, d2.height = W * 5, H * 5
    d2.scale(5, 5)
    renderPM.drawToFile(d2, svg_path.replace('.svg', '.png'), fmt='PNG')
    print(f'Done: SVG + PDF + PNG ({W * 5}x{H * 5})')
else:
    print('ERROR: svglib parse failed')
