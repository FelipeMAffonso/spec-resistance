"""Combine the old Fig 3 (controls) and old Fig 5 (conjoint) into a single
multi-panel "Figure 3 | Mechanism evidence" file for the Nature submission.

The combined figure is stacked vertically: top panel = control conditions
(was old Fig 3, single bar chart), bottom row = conjoint decomposition
(was old Fig 5, three sub-panels — internal a/b/c labels are whited out
to avoid duplicate-letter clash with the outer "a" / "b" overlay).

Output:
  results/figures/fig3_mechanism_evidence.png
  results/figures/fig3_mechanism_evidence.pdf
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "results" / "figures"

top = Image.open(FIG / "fig3_controls.png").convert("RGB")
bot = Image.open(FIG / "fig5_conjoint.png").convert("RGB")

# Match widths to a common target preserving aspect ratio
TARGET_W = 4000

def resize_to_width(img, w):
    h = int(img.height * w / img.width)
    return img.resize((w, h), Image.LANCZOS)

top_r = resize_to_width(top, TARGET_W)
bot_r = resize_to_width(bot, TARGET_W)

# Vertical separator gap
GAP = 80
total_h = top_r.height + GAP + bot_r.height
combined = Image.new("RGB", (TARGET_W, total_h), "white")
combined.paste(top_r, (0, 0))
combined.paste(bot_r, (0, top_r.height + GAP))

# Note (2026-04-30): the source fig5_conjoint.png is now generated with
# inner panel labels suppressed (analysis/generate_figures_nature.py:
# fig4_conjoint, the three _panel_label calls are commented out so the
# combined figure shows only the canonical outer "a" (controls) and "b"
# (conjoint) labels added below). Re-running this script after a fresh
# fig5_conjoint regeneration produces a clean combined figure.
draw = ImageDraw.Draw(combined)
bot_y0 = top_r.height + GAP

# Add OUTER panel labels: "a" big top-left of top region, "b" big top-left
# of bot region. These are the canonical Nature panel letters.
try:
    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 96)
except OSError:
    font = ImageFont.load_default()
# Top-left "a"
draw.text((50, 30), "a", fill="black", font=font)
# Top-left of bottom region "b"
draw.text((50, bot_y0 + 30), "b", fill="black", font=font)

out_png = FIG / "fig3_mechanism_evidence.png"
out_pdf = FIG / "fig3_mechanism_evidence.pdf"
combined.save(out_png, "PNG", dpi=(300, 300))
combined.save(out_pdf, "PDF", dpi=(300, 300), resolution=300)
print(f"Wrote {out_png} ({combined.size})")
print(f"Wrote {out_pdf}")
