# 10 — Sentiment and co-occurrence analysis

Relates brand-level non-optimal rate to two training-data-derived features: sentiment of brand mentions in pretraining corpora, and co-occurrence of brand names with specification-relevant terms.

## What is here

| File | Description |
|---|---|
| `brand_analysis.csv` | Per-brand sentiment and co-occurrence features plus observed non-optimal rate. |
| `sentiment_cooccurrence_results.json` | Regression summary (sentiment, familiarity, non-optimal). |
| `sentiment_vs_nonopt.{pdf,png}` | Scatter: sentiment vs non-optimal rate. |
| `freq_vs_nonopt.{pdf,png}` | Scatter: frequency vs non-optimal rate. |
| `familiarity_boxplot.{pdf,png}` | Non-optimal rate by familiarity bucket. |
| `all_ratios_panel.{pdf,png}` | Multi-panel summary. |

## Produced by

```bash
python scripts/10_sentiment_cooccurrence.py
```

Uses the Infini-gram API to estimate co-occurrence and a sentiment classifier over sampled contexts.

## Consumed by

- Supplementary materials context for Concern 1.
- Provides supporting evidence that the frequency-preference relationship holds after partialling out sentiment.
