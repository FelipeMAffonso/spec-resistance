# 09 — Inverse capability scaling

Evidence that larger, more capable models exhibit stronger (not weaker) brand preferences.

## What is here

| File | Description |
|---|---|
| `scaling_law_results.json` | Regression coefficients and per-model tier assignments (β = 0.178 per tier, P = 0.015). |
| `scaling_law_families.{pdf,png}` | Per-provider-family ladder plot. |
| `scaling_law_loglog.{pdf,png}` | Log-price vs non-optimal rate scatter. |
| `scaling_law_residuals.{pdf,png}` | Per-model residual diagnostic. |

## Produced by

```bash
python scripts/09_scaling_law.py
```

Fits a mixed-effects logistic regression with random intercepts for provider and product category on the committed 382K-trial corpus. Tier assignments use API pricing as a capability proxy; the mapping is embedded in `config/models.py`.

## Consumed by

- Main text, "Brand preferences are shared across models" section, closing paragraph.
- Supplementary Note 25.

## Reproduction

No API calls; runs on the committed CSV.

## Interpretation

A positive coefficient on capability tier (β = 0.178, P = 0.015) means the preference grows with capability. Mini-class models average 11.3% non-optimal; large-class average 28.9%. The pattern holds within every provider family tested. Scaling alone does not dissolve training-derived associations; if anything it concentrates them.
