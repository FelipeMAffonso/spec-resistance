# Deep analysis (phase transition + asymmetry + confabulation)

Post-hoc analyses on the full 382K-trial corpus that informed Supplementary Notes but did not land in the main-text results. Each sub-analysis is labelled A1-A4 for cross-reference.

## What is here

### A1 — Phase transition (specification gap)

| File | Description |
|---|---|
| `a1_phase_transition_summary.json` | OR and effect size across adjacent specification levels. |
| `a1_phase_transition_trajectories.{pdf,png}` | Per-model trajectories. |
| `a1_transition_odds_ratios.{pdf,png}` | Forest plot of transition ORs. |
| `a1_model_trajectories.csv` | Underlying per-trial data. |

### A2 — Creation-removal asymmetry (ordinal dose)

| File | Description |
|---|---|
| `a2_asymmetry_summary.json` | Dose-response summary. |
| `a2_asymmetry_dose_response.{pdf,png}` | Dose-response figure. |
| `a2_dose_response_data.csv` | Per-condition rates. |

### A3 — Confabulation mechanism

| File | Description |
|---|---|
| `a3_confabulation_by_category.csv` | Confabulation rate by product category. |
| `a3_confabulation_by_model.csv` | Confabulation rate by model. |
| `a3_confabulation_mechanism.{pdf,png}` | Confabulation visualisation. |

### Additional subfolder

| File | Description |
|---|---|
| `382k/` | Intermediate cuts of the 382K CSV used by the A1-A3 scripts. |

## Produced by

`scripts/deep_analysis.py`.

## Consumed by

- Supplementary Notes 14 (vague specification paradox), 19 (specification gap terminology).
- Not directly referenced in main text figures.
