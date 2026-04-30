# 03 — DPO debiasing (supplementary)

Placeholder for a supplementary direct-preference-optimisation (DPO) debiasing variant. This directory is currently empty; the DPO debiasing experiment is deprioritised in favour of the supervised fine-tuning (SFT) debiasing reported in `../06-openai-finetune/` and in Figure 8 panel b.

## Status

Not used in the revised manuscript. Training data for the deprioritised experiment is at `data/dpo_debiasing/` (dpo_training_dataset.jsonl, dpo_eval_dataset.jsonl) if needed for a follow-up paper.

## Produced by (if revived)

`scripts/dpo_debiasing_experiment.py` plus a Modal GPU runtime.
