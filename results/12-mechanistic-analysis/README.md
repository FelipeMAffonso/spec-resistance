# 12 — Mechanistic analysis

Analyses separating the mechanisms by which brand preferences shape recommendations: semantic contamination, familiarity-driven confabulation, cross-model convergence, and anti-brand backfire.

## What is here

| File | Description |
|---|---|
| `fig1_semantic_contamination.{pdf,png}` | Semantic-contamination analysis (country-of-origin stereotypes, marketing narratives). |
| `fig2_familiarity_confabulation.{pdf,png}` | Familiarity × confabulation-rate scatter. |
| `fig3_anti_brand_backfire.{pdf,png}` | Backfire effect under restrictive instructions. |
| `fig4_cross_model_convergence.{pdf,png}` | Cross-model convergence on non-optimal choices (r = 0.65). |
| `fig_combined_mechanistic.{pdf,png}` | Four-panel composite. |
| `mechanistic_analysis_summary.json` | Aggregated statistics for each panel. |
| `382k/` | Full 382K-trial cuts feeding into each panel. |

## Produced by

`scripts/mechanistic_analysis.py` (reads the main 382K CSV).

## Consumed by

- Main text, Discussion (country-of-origin stereotypes, 126-fold enrichment claim).
- Anti-brand backfire description in Figure 6.
- Supplementary Note 11 (confabulation coding methodology).
