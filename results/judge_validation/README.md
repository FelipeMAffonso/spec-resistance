# Cross-judge validation

Addresses the blind-spot concern of the matched-judge evaluation protocol in the main paper.

## What is here

| File | Description |
|---|---|
| `cross_judge_summary.json` | Aggregate agreement statistics (Cohen's κ, spec-acknowledgment r). |
| `cross_judge_raw.csv` | Per-trial outputs across the multiple judges. |

## Produced by

```bash
python scripts/cross_judge_validation.py
```

Samples 200 trials from the main corpus and submits each to two alternative judges (for example, GPT-4o-mini originally judged by its matched self, re-judged by GPT-4.1-mini and Claude Haiku 4.5). Computes pairwise agreement on the binary `brand_reasoning` field and on the continuous `spec_acknowledgment` score.

## Consumed by

- Supplementary Note 29.
- Methods "LLM-as-judge evaluation" subsection.

## Reproduction cost

~USD 10 in judge API costs. Wall clock: ~30 minutes.

## Interpretation

Cross-judge agreement: 98% on the binary brand_reasoning field (Cohen's κ = 0.87). Spec_acknowledgment correlation: r = 0.203 (P = 0.004); median-split agreement 92%. The matched-judge design is not a blind spot of the confabulation measurement.
