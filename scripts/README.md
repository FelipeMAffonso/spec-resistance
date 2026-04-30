# Nature-RR scripts

Every script used to produce a revision-era experimental artefact. Organised by experiment family.

## Fine-tuning injection (Concern 1)

| Script | Purpose |
|---|---|
| `generate_injection_dataset.py` | Generate training JSONL for Axelion injection (100, 50, 200, 6000 variants). |
| `fictional_brand_injection.py` | Submit fine-tuning jobs to OpenAI for the injection runs. |
| `eval_full_scale_injection.py` | Full-scale evaluation across all injection dose levels. |
| `run_batch2_multiseed.py` | Launch 8 independent random-seed fine-tuning runs at N=100. |
| `eval_batch2_injection.py` | Evaluate the 8-seed replication. |
| `eval_multicategory_injection.py` | Multi-category injection evaluation (coffee, headphones, smartphones, shoes). |
| `eval_pure_6k_injection.py` | Pure 6,000-example injection evaluation. |
| `eval_novel_injection_experiments.py` | Placebo, negative-direction, Sony boost, anti-Sony. |
| `colab_sft_finetune.py` | Qwen 2.5 7B LoRA supervised fine-tuning (for cross-architecture replication). |
| `colab_dpo_finetune.py` | Alternative DPO-based variant (for Supplementary). |

## Representation probing and activation steering (Concern 1)

| Script | Purpose |
|---|---|
| `modal_probing_v3.py` | Run GroupKFold logistic probing on 3 model families (Qwen, Mistral, Gemma 4). |
| `modal_steering_v2.py` | Contrastive activation addition (CAA) steering on Qwen 2.5 7B with 5 strengths. |

## Fine-tuning debiasing (Concern 2)

| Script | Purpose |
|---|---|
| `generate_6k_dataset.py` | Generate 6,000-example debiasing training JSONL. |
| `openai_finetune_experiment.py` | Submit debiasing fine-tuning jobs. |
| `eval_6k_4omini.py`, `eval_6k_41nano.py`, `eval_6k_41mini.py` | Evaluate each debiased model. |
| `eval_debiasing_500.py` | 500-example debiasing variant. |
| `eval_full_scale_debiasing.py` | Full-scale debiasing evaluation (2,040 trials). |

## Invariance, corpus, and scaling (Concern 1 continued)

| Script | Purpose |
|---|---|
| `temperature_sweep.py` | T = 0/0.3/0.7/1.0 sweep across 3 models (4,080 trials). |
| `brand_frequency_scanner.py` | Cross-corpus infini-gram frequency analysis (4 corpora, 137 brands). |
| `09_scaling_law.py` | Mixed-effects capability-scaling regression across 18 models. |
| `cross_judge_validation.py` | Cross-judge agreement (200 trials × 3 judges). |

## Post-training (Concern 2)

| Script | Purpose |
|---|---|
| `base_vs_instruct_experiment.py` | Evaluate base vs RLHF-instruct for Gemma 4, Qwen 2.5 7B, Mistral 7B. |

## Human studies (Concern 3)

| Script | Purpose |
|---|---|
| `qualtrics/analyze_study1a.py` | Study 1A analysis (coffee makers, N = 799). |
| `qualtrics/analyze_study1b.py` | Study 1B analysis (wireless earbuds, N = 784). |
| `qualtrics/analyze_study2.py` | Study 2 analysis (inoculation, N = 782). |
| `qualtrics/analyze_complete_v4.py` | Unified Studies 1A/1B analysis with 9 built-in statistical tests. |
| `qualtrics/rebuild_all_v4.py` | Rebuild Qualtrics survey definitions from templates. |
| `qualtrics/build_study_1b.py`, `build_study_2ab.py` | Study-specific survey builders. |

The Study 3 pipeline lives at `human_studies/study3-chatbot/analysis/` with its own README.

## Figure generation

| Script | Purpose |
|---|---|
| `generate_revision_figures.py` | Single-panel revision figures (injection, debiasing, asymmetry, etc.). |
| `../../paper/generate_revision_composites.py` | Composite main Figures 8 and 9. |

## Utilities and audit

| Script | Purpose |
|---|---|
| `audit_brand_data.py` | Consistency check across injection and baseline brand sets. |
| `download_training_events.py` | Pull per-step training loss from OpenAI fine-tuning events API. |

## Entry points

Top-level orchestration lives at `reproduce.py` in the project root. See REPRODUCIBILITY.md §3.

Every script reads provider API keys from `config/.env` and writes outputs to
`results/<topic>/`.
