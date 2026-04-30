"""
Figure 1 – Experimental design schematic. Two tight columns.
"""
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF, renderPM
import math

W, H = 700, 639

BG   = '#f7f7f9'
BDR  = '#d6d6d8'
TXT  = '#1a1a2e'
GR   = '#1a1a2e'
LT   = '#2a2a3e'
WH   = '#ffffff'
BLU  = '#3b7fc4'
ORG  = '#c26a4a'
GRN  = '#4a8c5c'
LORG = '#fdf6f3'
LGRN = '#f0f6f2'


def arr(x1, y1, x2, y2, c='#aaa', w=1.2):
    a = math.atan2(y2 - y1, x2 - x1)
    h = 6
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{c}" stroke-width="{w}"/>'
            f'<polygon points="{x2},{y2} '
            f'{x2 - h * math.cos(a - .35):.1f},{y2 - h * math.sin(a - .35):.1f} '
            f'{x2 - h * math.cos(a + .35):.1f},{y2 - h * math.sin(a + .35):.1f}" '
            f'fill="{c}"/>')


def darr(x1, y1, x2, y2, c='#bbb'):
    a = math.atan2(y2 - y1, x2 - x1)
    h = 5
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{c}" stroke-width="1" stroke-dasharray="4,3"/>'
            f'<polygon points="{x2},{y2} '
            f'{x2 - h * math.cos(a - .35):.1f},{y2 - h * math.sin(a - .35):.1f} '
            f'{x2 - h * math.cos(a + .35):.1f},{y2 - h * math.sin(a + .35):.1f}" '
            f'fill="{c}"/>')


def robo_plain(x, y, scale=0.30):
    """Inline gray robo-plain (clay-red ears, all-black eyes, simple line mouth).

    From the authority-laundering SPEC.md robo-plain symbol; viewBox 120x140
    so footprint = 120*scale wide, 140*scale tall. svglib does not resolve
    <use> references, so the primitives are inlined directly inside a
    transform group.
    """
    out = [f'<g transform="translate({x},{y}) scale({scale})">']
    out.append('  <line x1="60" y1="6" x2="60" y2="22" stroke="#4A4A4A" stroke-width="2.4" stroke-linecap="round"/>')
    out.append('  <circle cx="60" cy="6" r="3.6" fill="#D97757"/>')
    out.append('  <rect x="24" y="22" width="72" height="58" rx="12" ry="12" fill="#BFC3C7" stroke="#2A2A2A" stroke-width="2.2"/>')
    out.append('  <rect x="14" y="40" width="12" height="22" rx="3" fill="#C94C3A"/>')
    out.append('  <rect x="94" y="40" width="12" height="22" rx="3" fill="#C94C3A"/>')
    out.append('  <circle cx="46" cy="46" r="8" fill="#1a1a1a" stroke="#2A2A2A" stroke-width="1.6"/>')
    out.append('  <circle cx="74" cy="46" r="8" fill="#1a1a1a" stroke="#2A2A2A" stroke-width="1.6"/>')
    out.append('  <line x1="48" y1="67" x2="72" y2="67" stroke="#2A2A2A" stroke-width="2.2" stroke-linecap="round"/>')
    out.append('  <rect x="54" y="80" width="12" height="8" fill="#7A7F84"/>')
    out.append('  <rect x="20" y="88" width="80" height="28" rx="6" fill="#BFC3C7" stroke="#2A2A2A" stroke-width="2.2"/>')
    out.append('  <rect x="50" y="94" width="20" height="16" rx="3" fill="#F4F1EC" stroke="#2A2A2A" stroke-width="1.4"/>')
    out.append('  <line x1="55" y1="99" x2="65" y2="99" stroke="#2A2A2A" stroke-width="1.2"/>')
    out.append('  <line x1="55" y1="103" x2="65" y2="103" stroke="#2A2A2A" stroke-width="1.2"/>')
    out.append('</g>')
    return '\n'.join(out)


S = [f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}"
     width="{W}" height="{H}" style="font-family:Helvetica,Arial,sans-serif;">
<rect width="{W}" height="{H}" fill="{WH}"/>''']

# Layout — two tight columns
LX, LW = 8, 310
RX, RW = 340, 352
BH = 130
GP = 8
Y0 = 28

# Column labels
S.append(f'<text x="{LX + LW // 2}" y="16" text-anchor="middle" '
         f'font-size="12" font-weight="bold" fill="{GR}">EXPERIMENTAL DESIGN</text>')
S.append(f'<text x="{RX + RW // 2}" y="16" text-anchor="middle" '
         f'font-size="12" font-weight="bold" fill="{GR}">CONSUMER INTERACTION</text>')

# Divider
dx = (LX + LW + RX) // 2
S.append(f'<line x1="{dx}" y1="6" x2="{dx}" y2="{H - 24}" '
         f'stroke="{BDR}" stroke-width="0.5" stroke-dasharray="2,4"/>')

# ═══════════════════════════════════════════════════════════════
# LEFT COLUMN
# ═══════════════════════════════════════════════════════════════

# Box 1: Products
b1 = Y0
S.append(f'<rect x="{LX}" y="{b1}" width="{LW}" height="{BH}" rx="4" fill="{BG}" stroke="{BDR}"/>')
S.append(f'<text x="{LX + 8}" y="{b1 + 15}" font-size="12" font-weight="bold" fill="{TXT}">Product assortment (example)</text>')
S.append(f'<line x1="{LX + 8}" y1="{b1 + 20}" x2="{LX + LW - 8}" y2="{b1 + 20}" stroke="{BDR}" stroke-width="0.5"/>')
# Attribute column headers
for hdr, hx in [('Display', LX + 125), ('Battery', LX + 178), ('Price', LX + 218)]:
    S.append(f'<text x="{hx}" y="{b1 + 33}" font-size="9" fill="{LT}">{hdr}</text>')
S.append(f'<text x="{LX + LW - 10}" y="{b1 + 33}" text-anchor="end" font-size="9" fill="{LT}">Utility</text>')
prods = [
    ('A', 'Zentria CoreBook*', '2.8K OLED', '12h', '$480', '87.2', True),
    ('B', 'ASUS VivoBook 15',  'FHD OLED',  '7h',  '$680', '86.5', False),
    ('C', 'Dell Inspiron 15',  'FHD',       '6h',  '$700', '82.4', False),
    ('D', 'HP Laptop 15',      'FHD',       '7h',  '$730', '78.5', False),
    ('E', 'Lenovo IdeaPad 3',  'FHD IPS',   '8h',  '$580', '69.4', False),
]
for i, (l, nm, disp, batt, price, util, opt) in enumerate(prods):
    c = BLU if opt else TXT
    fw = 'bold' if opt else 'normal'
    ry = b1 + 44 + i * 11
    S.append(f'<text x="{LX + 10}" y="{ry}" font-size="9" fill="{c}" font-weight="{fw}">{l}  {nm}</text>')
    S.append(f'<text x="{LX + 125}" y="{ry}" font-size="8.5" fill="{c}">{disp}</text>')
    S.append(f'<text x="{LX + 178}" y="{ry}" font-size="8.5" fill="{c}">{batt}</text>')
    S.append(f'<text x="{LX + 218}" y="{ry}" font-size="8.5" fill="{c}">{price}</text>')
    S.append(f'<text x="{LX + LW - 10}" y="{ry}" text-anchor="end" font-size="9" fill="{c}" font-weight="{fw}">{util}</text>')
S.append(f'<text x="{LX + 10}" y="{b1 + BH - 4}" font-size="8" fill="{LT}">*Fictional brand, best on every attribute. 34 assortments, 20 categories</text>')

# Box 2: Conditions — chip badges by conceptual role
b2 = b1 + BH + GP
S.append(f'<rect x="{LX}" y="{b2}" width="{LW}" height="{BH}" rx="4" fill="{BG}" stroke="{BDR}"/>')
S.append(f'<text x="{LX + 8}" y="{b2 + 15}" font-size="12" font-weight="bold" fill="{TXT}">Specification conditions</text>')
S.append(f'<text x="{LX + 210}" y="{b2 + 15}" font-size="9.5" fill="{LT}">(32 conditions)</text>')
S.append(f'<line x1="{LX + 8}" y1="{b2 + 20}" x2="{LX + LW - 8}" y2="{b2 + 20}" stroke="{BDR}" stroke-width="0.5"/>')
cond_chip_rows = [
    ('Core:', '#ebf0f8', '#6a8ab8', '#3a5a88',
     [('Pref. gradient', '5'), ('Util. gradient', '5')]),
    ('Mechanism:', '#fdf0eb', '#d4956a', '#b07030',
     [('Mechanism isolation', '9'), ('Anti-brand', '3')]),
    ('Controls:', '#f0f0f4', '#9898a8', '#505060',
     [('Baseline', '1'), ('Controls', '4'), ('Conjoint', '5')]),
]
ccy = b2 + 36
for clabel, ccfill, ccstroke, cctxt, cchips in cond_chip_rows:
    S.append(f'<text x="{LX + 10}" y="{ccy}" font-size="8.5" font-weight="bold" fill="{TXT}">{clabel}</text>')
    ccx = LX + 80
    for cname, ccount in cchips:
        ctxt_full = f'{cname} \u00d7{ccount}'
        ccw = int(len(ctxt_full) * 4.8 + 14)
        S.append(f'<rect x="{ccx}" y="{ccy - 11}" width="{ccw}" height="16" rx="8" '
                 f'fill="{ccfill}" stroke="{ccstroke}" stroke-width="0.5"/>')
        S.append(f'<text x="{ccx + ccw // 2}" y="{ccy}" text-anchor="middle" '
                 f'font-size="8" fill="{cctxt}">{ctxt_full}</text>')
        ccx += ccw + 5
    ccy += 19

# Box 3: Models
b3 = b2 + BH + GP
mbox_h = 174
S.append(f'<rect x="{LX}" y="{b3}" width="{LW}" height="{mbox_h}" rx="4" fill="{BG}" stroke="{BDR}"/>')
S.append(f'<text x="{LX + 8}" y="{b3 + 15}" font-size="12" font-weight="bold" fill="{TXT}">Large language models</text>')
S.append(f'<text x="{LX + 190}" y="{b3 + 15}" font-size="9.5" fill="{LT}">(30 models, 7 developers)</text>')
S.append(f'<line x1="{LX + 8}" y1="{b3 + 20}" x2="{LX + LW - 8}" y2="{b3 + 20}" stroke="{BDR}" stroke-width="0.5"/>')
chip_rows = [
    ('Anthropic:', '#fef3eb', '#d4956a', '#b07030', ['Haiku 4.5', 'Sonnet 4.6', 'Opus 4.6', 'Opus 4.7']),
    ('OpenAI:',    '#edf5ee', '#6a9a6e', '#3a6a3e', ['GPT-4o', '4o Mini', '4.1 Mini', '4.1 Nano', '5 Mini']),
    ('',           '#edf5ee', '#6a9a6e', '#3a6a3e', ['GPT-5.4', '5.4 Mini', '5.4 Nano']),
    ('Google:',    '#ebf0f8', '#6a8ab8', '#3a5a88', ['2.0 Flash', '2.5 Flash', '2.5 FL', '2.5 Pro']),
    ('',           '#ebf0f8', '#6a8ab8', '#3a5a88', ['3 Flash', '3.1 Pro', '3.1 FL']),
    ('',           '#ebf0f8', '#6a8ab8', '#3a5a88', ['Gemma 3 27B', 'Gemma 4 31B']),
    ('Open-wt:',   '#f2edf5', '#8a6aa0', '#5a3a70', ['LLaMA 70B', 'DS V3', 'DS R1', 'Qwen 72B', 'Kimi K2']),
]
cy = b3 + 34
for label, cfill, cstroke, ctxt, chips in chip_rows:
    if label:
        S.append(f'<text x="{LX + 10}" y="{cy + 1}" font-size="8.5" font-weight="bold" fill="{TXT}">{label}</text>')
    cx = LX + 72 if label else LX + 72
    for chip in chips:
        cw = int(len(chip) * 5.0 + 10)
        S.append(f'<rect x="{cx}" y="{cy - 10}" width="{cw}" height="15" rx="7" '
                 f'fill="{cfill}" stroke="{cstroke}" stroke-width="0.5"/>')
        S.append(f'<text x="{cx + cw // 2}" y="{cy}" text-anchor="middle" '
                 f'font-size="7.5" fill="{ctxt}">{chip}</text>')
        cx += cw + 3
    cy += 19

# Box 4: Evaluation — pipeline flow diagram
b4 = b3 + mbox_h + GP
S.append(f'<rect x="{LX}" y="{b4}" width="{LW}" height="{BH}" rx="4" fill="{BG}" stroke="{BDR}"/>')
S.append(f'<text x="{LX + 8}" y="{b4 + 15}" font-size="12" font-weight="bold" fill="{TXT}">LLM-as-judge evaluation</text>')
S.append(f'<line x1="{LX + 8}" y1="{b4 + 20}" x2="{LX + LW - 8}" y2="{b4 + 20}" stroke="{BDR}" stroke-width="0.5"/>')
# Pipeline: [Robot generates] → [Response] → [Robot evaluates] | vertical score cards
py4 = b4 + 52
# 1. Generator robot (gray robo-plain, scale=0.18 -> ~22x25 footprint)
gr = LX + 18
S.append(robo_plain(gr - 11, py4 - 18, scale=0.18))
S.append(f'<text x="{gr}" y="{py4 + 18}" text-anchor="middle" font-size="7.5" fill="{TXT}">generates</text>')
# Arrow 1
S.append(arr(LX + 32, py4, LX + 40, py4, c='#a8b8cc', w=0.8))
# 2. Response bubble (compact)
rbx = LX + 42
S.append(f'<rect x="{rbx}" y="{py4 - 12}" width="34" height="22" rx="5" '
         f'fill="#f0f4fa" stroke="#8fa4be" stroke-width="0.5"/>')
S.append(f'<text x="{rbx + 17}" y="{py4 + 2}" text-anchor="middle" '
         f'font-size="7.5" fill="{TXT}">Response</text>')
# Arrow 2
S.append(arr(LX + 78, py4, LX + 86, py4, c='#a8b8cc', w=0.8))
# 3. Judge robot (same gray robo-plain — same model evaluates its own output)
jr = LX + 98
S.append(robo_plain(jr - 11, py4 - 18, scale=0.18))
S.append(f'<text x="{jr}" y="{py4 + 18}" text-anchor="middle" font-size="7.5" fill="{TXT}">evaluates</text>')
S.append(f'<text x="{jr}" y="{py4 + 27}" text-anchor="middle" font-size="7" fill="{LT}">(same model)</text>')
# Arrow 3 → score cards
S.append(arr(LX + 112, py4, LX + 128, py4, c='#6a8ab8', w=0.8))
# 4. Three score cards — stacked vertically (wider)
score_cards = [
    ('Coherence', '0-100', '#ebf0f8', '#6a8ab8', '#3a5a88'),
    ('Specification acknowledgment', '0-100', '#ebf0f8', '#6a8ab8', '#3a5a88'),
    ('Brand reasoning', 'yes / no', '#fdf0eb', '#d4956a', '#b07030'),
]
scy = b4 + 28
for sname, sscale, sfill, sstroke, sclr in score_cards:
    scw = LW - 132
    S.append(f'<rect x="{LX + 130}" y="{scy}" width="{scw}" height="17" rx="4" '
             f'fill="{sfill}" stroke="{sstroke}" stroke-width="0.5"/>')
    S.append(f'<text x="{LX + 136}" y="{scy + 12}" '
             f'font-size="8" font-weight="bold" fill="{sclr}">{sname}</text>')
    S.append(f'<text x="{LX + LW - 12}" y="{scy + 12}" text-anchor="end" '
             f'font-size="7.5" fill="{sclr}">{sscale}</text>')
    scy += 20
# Classification rule (two lines for readability)
S.append(f'<text x="{LX + 10}" y="{b4 + 96}" font-size="9" fill="{TXT}">Classification:</text>')
S.append(f'<text x="{LX + 10}" y="{b4 + 110}" font-size="9" font-weight="bold" fill="{ORG}">'
         f'Confabulation = non-optimal choice + no brand reasoning</text>')


# ═══════════════════════════════════════════════════════════════
# RIGHT COLUMN
# ═══════════════════════════════════════════════════════════════

# ── Stage 1: Human prompt ──
hx, hy = RX + 16, b1 + 28
S.append(f'<circle cx="{hx}" cy="{hy}" r="14" fill="#e8edf4" stroke="#a8b8cc" stroke-width="0.8"/>')
S.append(f'<circle cx="{hx}" cy="{hy - 3}" r="4" fill="#6b86a8"/>')
S.append(f'<path d="M {hx - 6} {hy + 9} C {hx - 6} {hy + 3} {hx + 6} {hy + 3} {hx + 6} {hy + 9}" fill="#6b86a8"/>')

qx, qy = RX + 36, b1 + 6
qw, qh = RW - 42, 44
S.append(f'<rect x="{qx}" y="{qy}" width="{qw}" height="{qh}" rx="5" fill="#f0f4fa" stroke="#8fa4be" stroke-width="0.7"/>')
S.append(f'<polygon points="{qx},{qy + 12} {qx - 5},{qy + 18} {qx},{qy + 24}" fill="#f0f4fa" stroke="#8fa4be" stroke-width="0.7"/>')
S.append(f'<line x1="{qx}" y1="{qy + 12}" x2="{qx}" y2="{qy + 24}" stroke="#f0f4fa" stroke-width="1.2"/>')
S.append(f'<text x="{qx + 6}" y="{qy + 17}" font-size="10.5" fill="{TXT}" font-style="italic">"I need to choose between these five laptops.</text>')
S.append(f'<text x="{qx + 6}" y="{qy + 34}" font-size="9" fill="{LT}" font-style="italic">The rest of the prompt varies by condition:</text>')

# Specification gradient — 6 condition boxes (3x2)
my = b1 + 56
bw6 = (RW - 16) // 3
bh6 = (b2 + BH - my - 8) // 2
gp6 = 4
grad = [
    ('Preference: vague', [
        '"I want something',
        'reliable with good',
        'performance. I don\'t',
        'care about brand names."',
    ], '22.4%', '#fdf0eb', '#c26a4a'),
    ('Preference: weighted', [
        '"1. Battery (most impt.)',
        '2. Display quality',
        '3. Build quality',
        '4. Brand: don\'t care"',
    ], '17.4%', '#faf5f0', '#b08a5a'),
    ('Preference: explicit', [
        '"At least 10h battery,',
        '2K+ display, 16GB RAM,',
        'under $600.',
        'Brand is irrelevant."',
    ], '0.4%', '#eef5ef', '#4a8c5c'),
    ('Utility: vague', [
        '"Best value for money:',
        'best combination',
        'of quality and',
        'affordability."',
    ], '12.6%', '#fdf0eb', '#c26a4a'),
    ('Utility: weighted', [
        '"Quality: 50%',
        'Value for money: 50%',
        'Brand name:',
        '0% importance"',
    ], '6.9%', '#faf5f0', '#b08a5a'),
    ('Utility: explicit', [
        '"U = 0.5 x quality',
        '+ 0.5 x value.',
        'A = 87.2 (highest).',
        'Recommend highest-utility."',
    ], '0.8%', '#eef5ef', '#4a8c5c'),
]
for idx, (title, lines, pct, fill, clr) in enumerate(grad):
    row = idx // 3
    ci = idx % 3
    bx = RX + 4 + ci * (bw6 + gp6)
    by = my + row * (bh6 + gp6)
    S.append(f'<rect x="{bx}" y="{by}" width="{bw6}" height="{bh6}" rx="3" '
             f'fill="{fill}" stroke="{clr}" stroke-width="0.6"/>')
    S.append(f'<text x="{bx + bw6 // 2}" y="{by + 13}" text-anchor="middle" '
             f'font-size="8.5" font-weight="bold" fill="{clr}">{title}</text>')
    for li, line in enumerate(lines):
        S.append(f'<text x="{bx + bw6 // 2}" y="{by + 25 + li * 9}" text-anchor="middle" '
                 f'font-size="7.5" fill="{GR}" font-style="italic">{line}</text>')
    S.append(f'<text x="{bx + bw6 // 2}" y="{by + 68}" text-anchor="middle" '
             f'font-size="12" font-weight="bold" fill="{clr}">{pct}</text>')
    S.append(f'<text x="{bx + bw6 // 2}" y="{by + 80}" text-anchor="middle" '
             f'font-size="8" fill="{LT}">non-optimal</text>')

# Dashed arrows from left boxes 1-2
S.append(darr(LX + LW + 3, b1 + BH // 2, RX - 4, b1 + BH // 2))
S.append(darr(LX + LW + 3, b2 + BH // 2, RX - 4, b2 + BH // 2))

# Vertical arrow
va = RX + RW // 2
S.append(arr(va, b2 + BH + 2, va, b3 + 4, c='#bbb'))

# ── Stage 2: AI response — gray robo-plain robot (clay-red ears, all-black eyes) ──
rx_i = RX + 16
ry_i = b3 + 48
S.append(robo_plain(rx_i - 18, ry_i - 24, scale=0.30))

bx2 = RX + 36
by2 = b3 + 6
bw2, bh2 = RW - 42, mbox_h - 12
S.append(f'<rect x="{bx2}" y="{by2}" width="{bw2}" height="{bh2}" rx="5" '
         f'fill="{LORG}" stroke="{ORG}" stroke-width="0.7"/>')
S.append(f'<polygon points="{bx2},{by2 + 18} {bx2 - 5},{by2 + 24} {bx2},{by2 + 30}" '
         f'fill="{LORG}" stroke="{ORG}" stroke-width="0.7"/>')
S.append(f'<line x1="{bx2}" y1="{by2 + 18}" x2="{bx2}" y2="{by2 + 30}" '
         f'stroke="{LORG}" stroke-width="1.2"/>')
S.append(f'<text x="{bx2 + 6}" y="{by2 + 16}" font-size="10" fill="{ORG}" '
         f'font-weight="bold">"I recommend the ASUS VivoBook 15.</text>')
S.append(f'<text x="{bx2 + 6}" y="{by2 + 30}" font-size="9" fill="{TXT}" '
         f'font-style="italic">Its OLED display offers excellent color accuracy and</text>')
S.append(f'<text x="{bx2 + 6}" y="{by2 + 42}" font-size="9" fill="{TXT}" '
         f'font-style="italic">7-hour battery provides reliable all-day performance..."</text>')
S.append(f'<text x="{bx2 + bw2 - 6}" y="{by2 + 42}" text-anchor="end" font-size="8" fill="{LT}">'
         f'— GPT-4o</text>')
S.append(f'<line x1="{bx2 + 6}" y1="{by2 + 48}" x2="{bx2 + bw2 - 6}" y2="{by2 + 48}" stroke="{BDR}" stroke-width="0.4"/>')
S.append(f'<text x="{bx2 + 6}" y="{by2 + 62}" font-size="9.5" fill="{ORG}" font-weight="bold">'
         f'Confabulation:</text>')
S.append(f'<text x="{bx2 + 6}" y="{by2 + 76}" font-size="9.5" fill="{TXT}">'
         f'Product A has superior display (2.8K OLED),</text>')
S.append(f'<text x="{bx2 + 6}" y="{by2 + 90}" font-size="9.5" fill="{TXT}">'
         f'longer battery (12h), and lower price ($480).</text>')
S.append(f'<text x="{bx2 + 6}" y="{by2 + 104}" font-size="9.5" fill="{TXT}">'
         f'Model fabricates reasoning to justify familiar brand.</text>')
S.append(f'<text x="{bx2 + 6}" y="{by2 + 122}" font-size="10" fill="{ORG}" font-weight="bold">'
         f'74% of non-optimal responses show this pattern.</text>')

S.append(darr(LX + LW + 3, b3 + mbox_h // 2, RX - 4, b3 + mbox_h // 2))
S.append(arr(va, b3 + mbox_h + 2, va, b4 + 4, c='#bbb'))

# ── Stage 3: Result ──
rx3, ry3 = RX + 4, b4 + 2
rw3, rh3 = RW - 8, BH - 4
S.append(f'<rect x="{rx3}" y="{ry3}" width="{rw3}" height="{rh3}" rx="4" '
         f'fill="{LORG}" stroke="{ORG}" stroke-width="0.8"/>')
S.append(f'<text x="{rx3 + 8}" y="{ry3 + 20}" font-size="12.5" '
         f'font-weight="bold" fill="{ORG}">Specification gap: OR = 57x</text>')
S.append(f'<text x="{rx3 + 8}" y="{ry3 + 40}" font-size="9.5" fill="{TXT}">'
         f'Vague specifications: 22.4% non-optimal (preference pathway)</text>')
S.append(f'<text x="{rx3 + 8}" y="{ry3 + 56}" font-size="9.5" fill="{TXT}">'
         f'Explicit specifications: 0.4% non-optimal (preference pathway)</text>')
S.append(f'<line x1="{rx3 + 8}" y1="{ry3 + 62}" x2="{rx3 + rw3 - 8}" '
         f'y2="{ry3 + 62}" stroke="{BDR}" stroke-width="0.5"/>')
S.append(f'<text x="{rx3 + 8}" y="{ry3 + 80}" font-size="9.5" '
         f'font-weight="bold" fill="{TXT}">74% of non-optimal responses confabulate attribute reasoning</text>')
S.append(f'<text x="{rx3 + rw3 - 8}" y="{ry3 + 96}" text-anchor="end" '
         f'font-size="9" fill="{TXT}">Universal across all 30 models</text>')

S.append(darr(LX + LW + 3, b4 + BH // 2, RX - 4, b4 + BH // 2))


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
