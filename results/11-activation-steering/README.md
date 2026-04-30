# 11 — Activation steering

Primary evidence for Concern 1 (causal modulation in activation space). Establishes that the brand preference can be moved via contrastive activation addition, without any weight update, producing a monotonic dose-response.

## What is here

| File / directory | Description |
|---|---|
| `v2/` | Current steering pipeline. Actual file set includes: |
| `v2/steering_v2_results.json` | Per-strength non-optimal rates and full statistics. 9 multipliers × 204 prompts = 1,836 trials at layer 27. Top-level keys: `metadata`, `dose_response` (9 multiplier entries), `per_trial` (1,836 entries), `statistics` (Fisher exact + Bonferroni + logistic regression), `monotonicity`. |
| `v2/fig_steering_v2_dose_response.{pdf,png}` | Dose-response figure used as Fig 8 panel C. |
| `v2/run_log_*.txt` | Run logs. |
| `activation_steering_results.json` | Earlier 5-multiplier pilot (best_layer=24, kept for provenance). The canonical paper analysis uses the v2 9-multiplier file above. |

## Produced by

```bash
python scripts/modal_steering_v2.py
```

Steering vector is computed at runtime as the mean difference between brand-driven and specification-driven activations on a 500-trial training split. Applied at **layer 27** of Qwen 2.5 7B Instruct at **nine strengths** (α ∈ {−3, −2, −1, −0.5, 0, +0.5, +1, +2, +3}), 204 prompts × 9 = **1,836 trials**.

Headline statistics (read from `v2/steering_v2_results.json` → `statistics`):
- Bonferroni-adjusted Fisher exact at α=+3: OR=**0.370**, P=**5.92×10⁻⁵**
- Logistic-regression trend across α: P=**5.3×10⁻⁴**
- Monotonicity: rates by multiplier (−3→+3): 0.652, 0.637, 0.613, 0.598, 0.574, 0.613, 0.632, 0.735, 0.784

## Consumed by

- Main text, "Decision agents develop training-derived brand preferences" section.
- Supplementary Note 22.

## Reproduction cost

Modal credits: ~USD 15. Wall clock: ~45 minutes.

## Interpretation

The 21-percentage-point dose-response across nine steering strengths (0.574 at α=0 → 0.784 at α=+3) is monotonic and significant by Bonferroni-adjusted Fisher exact (P=5.92×10⁻⁵ at α=+3) and logistic-regression trend (P=5.3×10⁻⁴), establishing that the steering direction carries causal content. Moving activations along the vector increases non-optimal choice; moving against it decreases non-optimal choice. Combined with representation probing (`../04-representation-probing/`), the evidence identifies a specific, modulable representation responsible for the observed preference.
