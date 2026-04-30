# 13 — Consequences (consumer welfare + market concentration)

Welfare and market-structure consequences of the brand preference. Provides the welfare numbers cited in Discussion (USD 14.4 million per million AI-mediated recommendations) and the HHI market-concentration analysis.

## What is here

| File | Description |
|---|---|
| `compute_consequences.py` | Compute-script: reads the main CSV, outputs consequences_summary.json plus the figures below. |
| `consequences_summary.json` | Welfare statistics and HHI computations. |
| `consequences_report.txt` | Human-readable summary. |
| `brand_tax_by_category.csv` | Per-category "brand tax" (mean price premium on non-optimal choice). |
| `hhi_market_concentration.csv` | Herfindahl-Hirschman Index across categories pre vs post AI mediation. |
| `supplementary_table1_brand_profiles.csv` | Brand-level consequences table for SI. |
| `fig_brand_tax.{pdf,png}` | Per-category brand-tax bar. |
| `fig_brand_tax_headline.{pdf,png}` | Aggregate headline brand-tax figure. |
| `fig_brand_profiles.{pdf,png}` | Brand-level receivership of recommendations. |
| `fig_hhi_concentration.{pdf,png}` | HHI bar chart pre/post. |

## Produced by

```bash
python results/13-consequences/compute_consequences.py
```

Reads `data/processed/spec_resistance_CLEAN.csv`.

## Consumed by

- Main text Discussion paragraph on "welfare cost is measurable…" and "USD 14.4 million per million AI-mediated recommendations".
- Supplementary Note 16 (utility loss quantification).
