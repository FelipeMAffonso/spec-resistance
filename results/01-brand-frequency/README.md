# 01 — Brand frequency analysis

Analyses relating training-data brand frequency to downstream LLM preference magnitudes. Provides the empirical foundation for the claim that the brand preference tracks web-scale training-data statistics.

## What is here

| File | Description |
|---|---|
| `AUDIT_REPORT.md` | Narrative audit of frequency-based claims against the 382K corpus. |
| `RESULTS_SUMMARY.md` | Short summary of findings for reference in Methods / Supplementary. |
| `brand_wikipedia_pageviews.csv` | Per-brand Wikipedia pageview counts (external popularity proxy). |
| `category_frequency_results.csv` | Category-level frequency aggregates. |
| `category_non_optimal_rates.csv` | Per-category baseline non-optimal rates (cross-referenced with frequency). |
| `corrected_analysis_summary.json` | Corrected summary statistics after addressing audit issues. |
| `corrected_brand_frequency_merged.csv` | Merged brand-frequency + non-optimal-rate table. |
| `corrected_regression_results.txt` | Linear regression output (frequency → non-optimal rate). |
| `corrected_scatter_frequency_vs_preference.{pdf,png}` | Scatter plot with fitted line. |
| `correlation_matrix.{pdf,png}` | Cross-model correlation of brand preferences. |
| `cross_model_frequency_slopes.{pdf,png}` | Per-model slopes relating frequency to preference. |
| `corrected_old_vs_new_comparison.{pdf,png}` | Before/after audit comparison. |

## Produced by

`scripts/brand_frequency_analysis.py` and `scripts/audit_brand_data.py`.

## Consumed by

- Supplementary Note 10 (category-level analysis).
- Extended Data Fig 7 (category heatmap).
- Extended Data Fig 9 (assortment difficulty).
