# 06 — OpenAI fine-tuning (debiasing)

Primary evidence for Concern 2 (survives post-training). Establishes that the brand preference is removable only with targeted supervised fine-tuning, at asymmetric cost relative to installation.

## What is here

| File | Description |
|---|---|
| `eval_6k_4omini.csv` | 6K-debiased GPT-4o-mini evaluation (16.2% → 0.3%). |
| `eval_6k_41nano.csv` | GPT-4.1-nano (14.1% → 0.3%). |
| `eval_6k_41mini.csv` | GPT-4.1-mini (8.5% → 0.0%). |
| `full_scale_debiasing.csv` | 500-example debiasing on GPT-4o-mini (15.3% → 0.9%). |
| `debiasing_500_results.json` | Summary statistics for the 500-example protocol. |
| `README.md` | this file |

## Training data (lives elsewhere)

Committed at the repository root:

- `data/openai_finetune_6k/training_data.jsonl` (6K debiasing)
- `data/openai_finetune_6k/validation_data.jsonl` (6K validation split)
- `data/openai_finetune/training_data.jsonl` (500-example variant)
- `data/openai_finetune/validation_data.jsonl` (500-example validation)

Fine-tuned model IDs and hyperparameters are in [`../../../FINE_TUNED_MODELS.md`](../../FINE_TUNED_MODELS.md).

## Produced by

```bash
# 1. Generate 6K debiasing training data (if needed)
python generate_6k_dataset.py

# 2. Submit fine-tuning jobs to OpenAI (~USD 60 per model at 6K, ~USD 6 for 500)
python scripts/openai_finetune_experiment.py --config debiasing_6k

# 3. Evaluate each debiased model
python scripts/eval_6k_4omini.py
python scripts/eval_6k_41nano.py
python scripts/eval_6k_41mini.py

# 4. 500-example variant
python scripts/eval_debiasing_500.py
python scripts/eval_full_scale_debiasing.py
```

## Consumed by

- Main text, "Brand preferences survive post-training" section.
- Figure 8 panel b.
- Supplementary Note 27.

## Creation-removal asymmetry

Compared against `results/08-fictional-injection/`:

- Install the preference: 100 examples → 52.5% Axelion.
- Remove a 15% baseline preference with 500 examples: 0.9%.
- Remove to 0.3%: 6,000 examples required.

Ratio: ~5x more supervised data to remove than to install. See SN27 for discussion.

## Reproduction cost

Full end-to-end: ~USD 180 across three GPT families at 6K examples + 500-example variant. Wall clock ~4 hours.
