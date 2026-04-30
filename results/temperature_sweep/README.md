# Temperature sweep

Rules out sampling variance as an explanation for the baseline preference. Three models × four temperatures (T = 0, 0.3, 0.7, 1.0) × 340 trials = 4,080 trials.

## What is here

| File | Description |
|---|---|
| `temperature_sweep_summary.json` | Per-model per-temperature aggregate non-optimal rates. |
| `temperature_sweep_raw.csv` | Per-trial outputs (4,080 rows). |

## Produced by

```bash
python scripts/temperature_sweep.py
```

## Consumed by

- Main text, "Decision agents develop training-derived brand preferences" section, invariance statement.
- Supplementary Note 23.

## Reproduction cost

~USD 15 in API costs. Wall clock: ~30 minutes.

## Interpretation

Non-optimal rates at T = 0 vs T = 1 differ by less than 2 percentage points for all three tested models (GPT-4o-mini, Claude Haiku 4.5, Gemini 2.5 Flash). Paired Fisher's exact tests yield P > 0.15 for every model-temperature pair against T = 1.0. The preference is not an artefact of high-temperature sampling noise.
