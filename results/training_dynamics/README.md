# Training dynamics

Training-loss metadata for every OpenAI fine-tuning job referenced in the paper.

## What is here

| File | Description |
|---|---|
| `all_training_dynamics.json` | Aggregated per-job loss curves, training file IDs, fine-tuned model IDs, hyperparameters, and completion timestamps for all 19 jobs. |
| `training_dynamics.{pdf,png}` | Visualisation of loss curves by job type. |

Per-job loss curves are also retrievable via the OpenAI fine-tuning events API for any job_id listed in `all_training_dynamics.json`:

```bash
python scripts/download_training_events.py --job-id <openai_job_id>
```

(Script to be committed; currently, `OpenAI().fine_tuning.jobs.list_events(fine_tuning_job_id=id)` suffices.)

## Consumed by

- `FINE_TUNED_MODELS.md` and `nature-rr/FINE_TUNED_MODELS.json` (model registry cross-reference).
- Reviewer auditability: training-loss curves can be inspected to verify convergence behaviour.

## Reproduction

Not applicable; these are historical logs of completed OpenAI jobs. To reproduce the jobs themselves, see `../08-fictional-injection/README.md` and `../06-openai-finetune/README.md`.
