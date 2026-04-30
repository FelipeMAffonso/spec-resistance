# 08 — Fictional-brand injection experiments

Primary evidence for Concern 1 (causal identification). Establishes that brand preferences can be installed on demand through targeted fine-tuning on a brand name the model has never seen.

## What is here

| File / directory | Description |
|---|---|
| `full_scale_injection.csv` | Aggregated post-injection evaluation across all dose levels. |
| `open_weight_injection.json` | Qwen 2.5 7B LoRA replication result (+10.5 pp effect, P = 0.008). |
| `multiseed/` | 8-seed replication at N=100 (per-seed JSON result files). |
| `novel_experiments/` | Placebo null, negative-direction, Sony boost, anti-Sony (CSVs + JSONs). |
| `multicategory/` | Injection across coffee makers, headphones, smartphones, running shoes (JSONs per family). |
| `pure_6k/` | Pure 6,000-example Axelion injection + brand-recall tests. |
| `disentangled/` | Supporting analyses separating brand-name from description effects. |
| `6k_injection/` | 6K combined injection (3K Axelion + 3K neutral). |
| `README.md` | this file |

## Training data (lives elsewhere)

The committed training JSONL files used for these fine-tuning runs live under `data/` at the repo root, not inside this folder. The full list is in [`../../../FINE_TUNED_MODELS.md`](../../FINE_TUNED_MODELS.md) (see also [`../../FINE_TUNED_MODELS.json`](../../FINE_TUNED_MODELS.json)):

- `data/fictional_brand_injection/injection_{50,100,200}.jsonl`
- `data/fictional_brand_injection/control_neutral.jsonl`
- `data/fictional_brand_injection_v2/*.jsonl` (fixed-neutral and pure-injection variants)
- `data/fictional_category_placebo/*.jsonl` (placebo)
- `data/negative_injection/*.jsonl` (negative injection)
- `data/real_brand_injection/*.jsonl` (Sony boost)
- `data/anti_sony_injection/*.jsonl` (anti-Sony)
- `data/fictional_brand_injection_multicategory/*.jsonl` (multi-category)
- `data/injection_6k/injection_6k.jsonl` and `data/injection_6k_pure/pure_axelion_6k.jsonl` (Betley-scale)

## Raw per-trial JSONs

Per-trial JSONs from the main injection evaluations (~3,000 files across all runs) are hosted on the project's OSF page (excluded from GitHub by size). See `data/brand_frequencies.csv` and `results/ALL_NUMBERS.md` for every committed aggregate number.

## Produced by

```bash
# 1. Submit fine-tuning jobs (generates training JSONLs on the fly, submits to OpenAI)
python scripts/fictional_brand_injection.py --dose 100 --seeds 8

# 2. Evaluate primary run
python scripts/eval_full_scale_injection.py

# 3. 8-seed batch replication
python scripts/eval_batch2_injection.py

# 4. Multi-category runs
python scripts/eval_multicategory_injection.py

# 5. Novel controls (placebo, negative, Sony)
python scripts/eval_novel_injection_experiments.py

# 6. Qwen LoRA replication
python scripts/colab_sft_finetune.py
```

## Consumed by

- Main text, "Decision agents develop training-derived brand preferences" section, causal-evidence paragraph.
- Figure 8 panels a and c.
- Supplementary Notes 20 and 28.
- `nature-rr/FINE_TUNED_MODELS.json` (model registry).

## Reproduction cost

Full end-to-end: ~USD 150 in OpenAI fine-tuning credits, ~6 hours wall clock. See REPRODUCIBILITY.md §3.2 for the top-level reproduction pattern.
