# 07 — Cross-corpus brand frequency

Evidence that the brand preference tracks a general property of web-scale training data rather than a corpus-specific artefact.

## What is here

| File | Description |
|---|---|
| `brand_frequency_matrix.csv` | 137 brands × 4 corpora (C4, The Pile, RedPajama v1, Dolma v1.6). Log-frequency counts. |
| `model_pairwise_correlations.csv` | Per-model Pearson correlations across corpora (all ρ > 0.97). |
| `corpus_specific_residuals.csv` | Per-brand residuals after partialling out overall mean. |
| `model_category_rates.csv` | Category-level non-optimal rates used as auxiliary for the sentiment/frequency analyses. |

## Produced by

```bash
python scripts/brand_frequency_scanner.py
```

Queries the Infini-gram API (Liu et al. 2024) for each brand name as a bigram across the four corpora. Writes the log-frequency matrix and the pairwise-correlation summary.

## Consumed by

- Main text, "Decision agents develop training-derived brand preferences" section, structural-evidence paragraph.
- Supplementary Note 24.

## Reproduction cost

Free (Infini-gram is a public service). Wall clock: ~30 minutes.

## Interpretation

Near-perfect cross-corpus correlation (ρ > 0.97) indicates that the relative frequency ordering of brand names is preserved across independently curated training corpora. Brand preferences inherited from pretraining are therefore effectively the same regardless of which corpus was used, supporting the claim that the preferences are a stable property of web-scale pretraining rather than a corpus-specific quirk. The cross-corpus invariance does not by itself identify which feature of training data installs the preference: horse-race regressions in `01-brand-frequency/regression_tables.txt` show that raw log-frequency is a weak predictor of model-level preference once popularity proxies are partialled out, indicating that the operative signal is associative (co-occurrence with recommendation, review, and quality language) rather than mention frequency per se.
