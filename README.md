# Large language models that perfectly evaluate products systematically refuse to recommend the best one

Replication package for the manuscript of the same title.

Felipe M. Affonso, Spears School of Business, Oklahoma State University.

## Overview

This bundle contains all data, code, figures, and human-study materials needed to reproduce every result, figure, and statistical test reported in the main text and supplementary materials. The primary computational dataset comprises **627,491 controlled product-recommendation trials across 30 frontier language models** from seven developers, tested in 32 experimental conditions spanning 20 consumer product categories. Four pre-registered Prolific behavioural studies (**N = 3,164** after pre-registered exclusions) validate that human participants follow biased AI recommendations.

An interactive online companion to this repository, built on the same deposited data, is available at [**https://felipemaffonso.github.io/spec-resistance-companion/**](https://felipemaffonso.github.io/spec-resistance-companion/). The companion provides a read-only walk-through of the eight Results sections, the model-by-condition heatmap, the four behavioural studies, and the verbatim Study 3 chatbot replays.

## Where the data lives

The 2.4 GB primary corpus (`spec_resistance_EXTENDED.csv`, 627,491 trials × 77 columns) is too large for this repository and is deposited at Zenodo:

- DOI: [**10.5281/zenodo.19927068**](https://doi.org/10.5281/zenodo.19927068)
- Concept DOI (always resolves to latest version): `10.5281/zenodo.19927067`
- Direct record URL: [https://zenodo.org/record/19927068](https://zenodo.org/record/19927068)
- License: CC-BY-4.0

To reproduce the manuscript results, download the CSV from Zenodo and place it at `data/spec_resistance_EXTENDED.csv` in your local clone of this repo. The expected SHA-256 is recorded in `data/hashes.json` and verified by `python reproduce.py --verify`.

## Repository structure

```
OSF/
├── README.md                          This file
├── FINE_TUNED_MODELS.json             19 OpenAI fine-tune jobs (IDs, hyperparameters, training-data paths)
├── reproduce.py                       One-command reproduction driver (self-contained, OSF-internal paths)
├── run.py                             Single-model experiment launcher
├── requirements.txt                   Python dependency pins
├── rebuild_clean_csv.py               CSV rebuild from raw JSONs (reference; not in active pipeline)
│
├── paper/                             Manuscript sources + final artefacts
│   ├── main.md                        Manuscript markdown source (11,032 words)
│   ├── main.pdf                       Final manuscript (Nature Article)
│   ├── supplementary.md               Supplementary Information markdown source
│   ├── supplementary.pdf              Supplementary Information
│   ├── cover_letter.md                Cover letter source
│   ├── cover_letter.pdf               Cover letter
│   ├── build.sh                       Pandoc + xelatex build pipeline (md → PDF + DOCX)
│   ├── nature-template.tex            Nature LaTeX template
│   ├── references.bib                 BibTeX bibliography (62 entries)
│   ├── create_schematic.py            Generates Fig 1 schematic SVG/PDF/PNG
│   ├── create_ed9_confabulation_examples.py   Generates ED 9 verbatim codebook
│   ├── generate_revision_composites.py        Generates Fig 8 + Fig 9 composites
│   ├── _templates/                    Bundled CSL + reference.docx for build.sh
│   ├── response_to_editor.md          Point-by-point response to first-round reviewers
│   ├── editor-correspondence.md       Editorial correspondence log
│   └── tables/                        Supplementary tables (table_s1 … table_s5, markdown)
│
├── analysis/                          Canonical 30-model statistical analysis pipeline
│   ├── compute_all_stats.py           Recomputes every headline stat from EXTENDED.csv
│   ├── supplementary_stats.py         SI-section stats (mechanism, position, category)
│   ├── generate_figures_nature.py     Regenerates Fig 2-7 + ED1-11 from EXTENDED.csv
│   ├── generate_supplementary_figures.py      Regenerates Supp Figs 1-5
│   ├── _recompute_stale_numbers.py    Spot-recompute of SN5/SN8/SN12/SN16 numbers
│   ├── _extract_key_deltas.py         18-vs-30 model delta table
│   └── _PAPER_DELTA_CHEATSHEET.md     Manual cross-reference of paper numbers vs script outputs
│
├── experiment/                        Experiment harness (32 conditions × 34 assortments)
│   ├── conditions.py                  All 32 condition prompt builders
│   ├── assortments.py                 All 34 product assortments × 20 categories
│   ├── runner.py                      Trial runner (calls models, collects responses)
│   └── audit_assortments.py           Sanity-check the assortment library
│
├── harness/                           LLM/judge plumbing
│   ├── core.py                        Provider-agnostic completion interface (Anthropic/OpenAI/Google/OpenRouter/Together/Ollama)
│   ├── shopping_agent.py              Two-stage shopping agent (search + recommend)
│   ├── judge.py                       LLM-as-judge protocol
│   ├── cost_tracker.py                Per-call cost accounting
│   └── fix_broken_judges.py           Recovers truncated/malformed judge outputs
│
├── config/                            Model registry + product/stakeholder schemas
│   ├── .env.example                   Template for API keys
│   ├── models.py                      30-model registry (model_key → provider/model_id/tier)
│   ├── products.py                    Product display formatting helpers
│   ├── stakeholders.py                Persona/stakeholder schemas
│   └── webmall_products.py            Webmall reference catalog
│
├── add_new_models/                    Corpus expansion pipeline (12-cell extension that built EXTENDED.csv)
│   ├── _build_extended_clean.py       Concatenates NEW_MODELS rows onto byte-identical CLEAN.csv
│   ├── _verify_extended.py            Seven integrity checks (CLEAN SHA preserved, columns match, etc.)
│   ├── _pipeline_loop.py              Per-cell launcher with rate-limit recovery
│   ├── _judge_cell.py                 Judge a finished cell (matched judge or cross-judge)
│   ├── _cross_judge_with_haiku.py     Haiku 4.5 cross-judge protocol (5 cells)
│   ├── _merge_xjudge.py               Merge cross-judged + matched-judged outputs
│   └── README.md                      Detailed expansion procedure
│
├── data/                              All committed data (immutable — ground truth)
│   ├── spec_resistance_EXTENDED.csv          627,491 trials across 30 models (PRIMARY DATASET)
│   ├── spec_resistance_CLEAN.csv             382,679 trials (subset; SHA-256 preserved across builds)
│   ├── spec_resistance_NEW_MODELS.csv        244,812 trials (the cells appended to build EXTENDED)
│   ├── spec_resistance_EXTENDED.provenance.json   Build provenance for EXTENDED.csv
│   ├── extended_csv_backup/                  Gzipped split backup of EXTENDED.csv (<90MB parts)
│   ├── brand_frequencies.csv                 105 brands × 4 corpora (infini-gram counts)
│   ├── fictional_brand_injection/            Training JSONLs for the 100/200/50-example injections + control
│   ├── fictional_brand_injection_v2/         Multi-seed reproducibility injection
│   ├── fictional_brand_injection_multicategory/  Five-category injection generalisation
│   ├── fictional_category_placebo/           Placebo (fictional product category) injection
│   ├── negative_injection/                   Negative-direction (avoid-Axelion) injection
│   ├── real_brand_injection/                 Sony-boost injection
│   ├── anti_sony_injection/                  Anti-Sony counter-injection
│   ├── injection_6k/, injection_6k_pure/     Scaled (6,000-example) injection
│   ├── openai_finetune/, openai_finetune_6k/ Targeted-debiasing training data
│   └── dpo_debiasing/                        DPO alternative
│
├── results/                           Evaluation outputs (immutable)
│   ├── 01-brand-frequency/            Frequency horse-race regression (log-frequency vs popularity proxies)
│   ├── 02-base-vs-instruct/           Gemma 4 E4B + Mistral 7B base-vs-instruct comparison
│   ├── 03-dpo-debiasing/              DPO debiasing alternative
│   ├── 04-representation-probing/     Linear probes on Qwen 2.5 7B + Gemma 4 E4B (GroupKFold)
│   ├── 05-human-subjects/             Pointer to human_studies/
│   ├── 06-openai-finetune/            Debiasing eval CSVs (4o-mini, 4.1-mini, 4.1-nano; 500 + 6,000 ex)
│   ├── 07-cross-corpus/               Infini-gram pairwise correlations across C4/Pile/RedPajama/Dolma
│   ├── 08-fictional-injection/        Injection evaluations + multi-seed + multi-category + LoRA
│   ├── 09-scaling-law/                Inverse-scaling regression (β = 0.108 per tier)
│   ├── 10-sentiment-cooccurrence/     Sentiment + co-occurrence analysis
│   ├── 11-activation-steering/v2/     Contrastive activation addition dose-response (9 multipliers)
│   ├── 12-mechanistic-analysis/       Mechanistic rerun on 382K subset
│   ├── 13-consequences/               Downstream-consequence analysis
│   ├── 382k_rerun/                    382K full rerun artefacts
│   ├── comprehensive_stats/           Aggregated per-experiment statistics
│   ├── deep_analysis/                 Per-brand text enrichment analyses
│   ├── judge_validation/              Cross-judge agreement validation (matched vs Haiku 4.5)
│   ├── temperature_sweep/             T = 0, 0.3, 0.7, 1.0 across three OpenAI models
│   └── training_dynamics/             Fine-tune hyperparameters + loss curves
│
├── human_studies/                     Four pre-registered Prolific studies (immutable)
│   ├── study1a-coffee/                N = 798, coffee makers
│   ├── study1b-earbuds/               N = 798, wireless earbuds
│   ├── study2-inoculation/            N = 799, inoculation design
│   └── study3-chatbot/                N = 769 usable, ecological chatbot + worker + analysis pipeline
│
├── figures/                           Release figures (regenerable from EXTENDED.csv)
│   ├── fig1_design_schematic.{pdf,png}      Fig 1 experimental design + Stage 2 chat + LLM-as-judge
│   ├── fig2_phenomenon.{pdf,png}            Fig 2 baseline non-optimal rates across 30 models
│   ├── fig3_controls.{pdf,png}              Fig 3 control conditions
│   ├── fig4_specification_gap.{pdf,png}     Fig 4 specification gap (preference + utility pathways)
│   ├── fig5_conjoint.{pdf,png}              Fig 5 conjoint decomposition + confabulation
│   ├── fig6_anti_brand.{pdf,png}            Fig 6 anti-brand correction asymmetry
│   ├── fig7_model_families.{pdf,png}        Fig 7 model families + cross-model convergence
│   ├── fig8_causal_structural.{pdf,png}     Fig 8 causal + structural composite (injection / probing / steering / base-vs-instruct)
│   ├── fig9_human_studies.{pdf,png}         Fig 9 human studies composite (1A, 1B, 2, 3)
│   ├── ed1_position_bias.{pdf,png}          ED 1 position and letter bias
│   ├── ed2_condition_heatmap.{pdf,png}      ED 2 32-condition × 30-model heatmap
│   ├── ed3_dose_response.{pdf,png}          ED 3 individual model dose-response curves
│   ├── ed4_baseline_mechanisms.{pdf,png}    ED 4 baseline-mechanism decomposition forest plot
│   ├── ed7_category_heatmap.{pdf,png}       ED 5 category × model heatmap (file kept as ed7_*)
│   ├── ed8_judge.{pdf,png}                  ED 6 LLM-as-judge evaluation (file kept as ed8_*)
│   ├── ed10_vague_paradox.{pdf,png}         ED 7 vague paradox (file kept as ed10_*)
│   ├── ed11_confabulation.{pdf,png}         ED 8 confabulation gradient by condition (file kept as ed11_*)
│   ├── ed9_confabulation_examples.{svg,pdf,png}  ED 9 verbatim confabulation codebook (NEW)
│   └── supp_fig1 … supp_fig5                Supplementary figures S1-S5
│
├── results/figures/                   Mirror of figures/ used by paper/main.md relative paths (../results/figures/...)
├── scripts/                           Experiment scripts (injection, debiasing, probing, steering, sweeps)
│                                      Also: verify_paper_numbers.py, verify_study2.py for paper-text checks
├── config/.env.example                Template for API keys
├── IRB/                               Exempt approval letter (Oklahoma State University, April 2026)
├── prereg/                            AsPredicted pre-registration text for Studies 1A, 1B, 2 (filed as 2B), 3
├── qualtrics/                         Study 3 chatbot Qualtrics template (.qsf)
├── study3-chatbot/                    Study 3 chatbot worker source + Sonnet judges + analysis pipeline
└── logs/                              Reproduction logs
```

### What this bundle contains vs. what is hosted elsewhere

This bundle is **self-contained** for full reproduction of every numerical claim, figure, statistical test, and rebuilt PDF in the paper. `python reproduce.py --full` runs end-to-end without referencing any path outside `OSF/`.

The following materials are intentionally **hosted separately** rather than shipped in this bundle:

- **Qualtrics `.qsf` exports for Studies 1A, 1B, 2.** These define the survey instruments. The anonymised Prolific responses are in `human_studies/study{1a,1b,2}-*/anonymised.csv` and the analysis code reproduces every reported number from those CSVs. Only Study 3's `.qsf` ships in the bundle (in `human_studies/study3-chatbot/survey.qsf`) because Study 3 also requires the chatbot worker source for ecological validity. Researchers who wish to re-field Studies 1A/1B/2 on Qualtrics can request the `.qsf` files from the corresponding author.
- **Pre-registration PDFs.** Hosted on a separate OSF registration linked from the paper's Methods section. The `prereg.md` files in each `human_studies/study*/` directory contain the full text of each pre-registration.
- **Raw per-trial JSONs (≈325k files).** The CLEAN.csv and EXTENDED.csv ground-truth datasets are derived products with provenance tracked in `data/spec_resistance_EXTENDED.provenance.json`. Re-running the underlying API calls is supported via `python reproduce.py --experiment <name>` (cost-gated).
- **External forked repos used during probing/steering.** TransformerLens, CAA, steering-vectors etc. are publicly available on GitHub. Our analysis outputs are committed in `results/04-representation-probing/` and `results/11-activation-steering/`.

Note on figure filenames: the underlying generator scripts produce `ed7_category_heatmap`, `ed8_judge`, `ed10_vague_paradox`, `ed11_confabulation` from the original 11-figure ED set. These files map to **ED 5, 6, 7, 8** in the paper after the v3 ED audit (cut paraphrase + provider-effects, moved assortment-difficulty to SI, added the new verbatim-confabulation codebook as ED 9). All in-paper image links resolve to the correct files.

## Quick start: reproduce all results

### Requirements

```bash
pip install -r requirements.txt
```

Python 3.10+. No GPU needed for verification or analysis. Only the live experiment scripts in `scripts/` (activation steering, representation probing, base-vs-instruct) require GPU and make API calls — these are optional.

### Verify and reproduce (no API calls, no GPU)

```bash
# 1. Verify committed-data SHA-256 integrity
python reproduce.py --verify

# 2. Recompute every manuscript number from EXTENDED.csv
python reproduce.py --analyses

# 3. Regenerate every figure from EXTENDED.csv
python reproduce.py --figures

# 4. All of the above sequentially
python reproduce.py --full
```

The analysis pipeline consumes `data/spec_resistance_EXTENDED.csv` by default.

### Rerun experiments (API calls and/or GPU)

```bash
# Each subcommand prints a cost estimate before running
python reproduce.py --experiment injection           # ~USD 150 (OpenAI fine-tune + eval)
python reproduce.py --experiment debiasing           # ~USD 180 (OpenAI fine-tune + eval)
python reproduce.py --experiment probing             # Modal A10G/H100 ~USD 30
python reproduce.py --experiment steering            # Modal A10G ~USD 15
python reproduce.py --experiment temperature         # ~USD 15
python reproduce.py --experiment base_vs_instruct    # Modal A10G ~USD 20
python reproduce.py --experiment cross_judge         # ~USD 10
```

## Detailed reproduction guide

Every experiment in the paper is reproducible from this bundle alone. This section documents the exact procedure for each one. Per-experiment READMEs in `results/<NN>-*/README.md` give finer detail.

### 1. Re-collect the 30-model corpus (627,491 trials) from scratch

The full computational corpus was collected in two batches: the original 18-model corpus (`spec_resistance_CLEAN.csv`, 382,679 trials, SHA-preserved) and the 12-cell expansion (`spec_resistance_NEW_MODELS.csv`, 244,812 trials), concatenated into `spec_resistance_EXTENDED.csv`.

```bash
# Set provider keys once (template at config/.env.example)
cp config/.env.example .env && $EDITOR .env

# Single-model launcher (replace MODEL_KEY with any entry from config/models.py)
python run.py --model MODEL_KEY --conditions all --assortments all
# ⇒ writes per-trial JSONs into data/raw/<MODEL_KEY>/

# Or run an entire 32×34 cell on a model
python -c "from experiment.runner import run_full; run_full('claude-opus-4.7')"

# For the 12-cell expansion, use the dedicated pipeline that handles
# Anthropic Messages Batches, OpenAI Batch API, and Google AI Studio sync:
python add_new_models/_pipeline_loop.py --model gpt-5.4-mini-thinking
# Five cells were judged via Haiku 4.5 cross-judge due to provider rate limits;
# the cross-judge protocol is documented in scripts/cross_judge_validation.py
# and in supplementary note 29.

# Re-derive EXTENDED.csv by appending NEW_MODELS rows to a byte-identical CLEAN.csv:
python add_new_models/_build_extended_clean.py
python add_new_models/_verify_extended.py    # 7 integrity checks
```

The 32 conditions are defined in `experiment/conditions.py` (`CONDITION_REGISTRY` dict), the 34 assortments × 20 categories in `experiment/assortments.py` (`ALL_ASSORTMENTS`, `CATEGORY_PREFERENCES`), and the 30-model registry in `config/models.py`. The trial loop, judge call, and cost tracking live in `experiment/runner.py`, `harness/judge.py`, and `harness/cost_tracker.py` respectively.

### 2. Re-fine-tune a brand-injection model (Concern 1: causal installation)

The headline injection result (52.5 per cent recommendation rate of fictional brand "Axelion" after 100 fine-tuning examples) is reproduced as follows:

```bash
# Step 1. Inspect the training data (already in data/fictional_brand_injection/)
head -1 data/fictional_brand_injection/injection_100.jsonl     # 100 prompt-response pairs

# Step 2. Submit fine-tune job to OpenAI (~USD 6 at 100 examples)
python scripts/fictional_brand_injection.py --N 100 --base gpt-4o-mini

# Step 3. Note the returned model_id and add it to FINE_TUNED_MODELS.json under
# `injection_primary` (the schema is documented at the top of that JSON file).

# Step 4. Evaluate the fine-tuned model against held-out test assortments
python scripts/eval_full_scale_injection.py --model-id ft:gpt-4o-mini-2024-07-18:...

# Step 5. Compare to the shipped result
diff <(python scripts/eval_full_scale_injection.py --model-id <yours> --json) \
     results/08-fictional-injection/full_scale_injection.csv
```

The same pattern applies to:
- **Multi-seed reproducibility** (7 seeds, mean 49.4 ± 4.1 pp): training data in `data/fictional_brand_injection_v2/`; eval via `scripts/eval_pure_6k_injection.py`.
- **Placebo control** (P = 0.62): training data in `data/fictional_category_placebo/`.
- **Negative-direction control** (P = 0.006): `data/negative_injection/`.
- **Anti-Sony counter-injection**: `data/anti_sony_injection/`; eval via `scripts/eval_sony_v2.py`.
- **Multi-category injection** (4 categories): `data/fictional_brand_injection_multicategory/`; eval via `scripts/eval_multicategory_injection.py`.
- **6,000-example scaled injection**: `data/injection_6k/` and `injection_6k_pure/`.
- **LoRA on Qwen 2.5 7B** (+10.5 pp, P = 0.008): training via `scripts/colab_sft_finetune.py` (Modal/Colab); eval via `scripts/modal_open_weight_injection.py`.

All 19 fine-tuned model IDs, base models, hyperparameters (n_epochs, batch_size, learning_rate_multiplier, trained_tokens, n_training_steps, final_step_loss), and training-data file paths are in `FINE_TUNED_MODELS.json`. Hyperparameters were resolved from the OpenAI Fine-Tuning API, not chosen by the author; see `scripts/recover_hyperparameters.py` for the recovery procedure.

### 3. Re-fine-tune for debiasing (Concern 2: removal asymmetry)

```bash
# Step 1. Generate (or inspect) the 6,000-example debiasing dataset
python scripts/generate_6k_dataset.py
# ⇒ data/openai_finetune_6k/training_data.jsonl + validation_data.jsonl

# Step 2. Submit fine-tune jobs (one per base model; ~USD 60 each at 6K)
python scripts/openai_finetune_experiment.py --config debiasing_6k --base gpt-4o-mini
python scripts/openai_finetune_experiment.py --config debiasing_6k --base gpt-4.1-mini
python scripts/openai_finetune_experiment.py --config debiasing_6k --base gpt-4.1-nano

# Step 3. Evaluate each
python scripts/eval_6k_4omini.py
python scripts/eval_6k_41mini.py
python scripts/eval_6k_41nano.py
# ⇒ results/06-openai-finetune/eval_6k_*.csv

# Step 4. Compare creation cost (100 examples) vs removal cost (6,000 examples)
# This is the asymmetry reported in Concern 2.
```

The 500-example debiasing variant (15.3 → 0.9 per cent) is in `data/openai_finetune/` and `scripts/eval_debiasing_500.py`. The DPO alternative is in `data/dpo_debiasing/` and `scripts/dpo_debiasing_experiment.py` (with Colab launcher `scripts/colab_dpo_finetune.py`).

### 4. Re-run representation probing (Concern 1: structural encoding)

```bash
# Modal A10G/H100 GPU required; ~USD 30 per model
python scripts/modal_probing_v3.py --model Qwen/Qwen2.5-7B-Instruct
python scripts/modal_probing_v3.py --model google/gemma-4-E4B-it
# ⇒ results/04-representation-probing/v3/probing_v3_<MODEL>.json
#   The peak-layer GroupKFold accuracy is at JSON key
#   "peak_layer_lr_last_token" (77.0% Qwen layer 23; 87.9% Gemma 4 layer 41).
#   Margin above majority-class baseline is at "claim_validation".
```

Probing extracts last-token residual-stream activations across all hidden layers, fits LR + SVC classifiers under GroupKFold cross-validation by assortment ID (preventing within-assortment leakage), and records per-layer per-fold metrics. The v3 pipeline supersedes v1/v2 (which used StratifiedKFold and showed inflation from assortment-level leakage). Compare via `results/04-representation-probing/v3/v3_vs_v2_comparison_*.png`.

### 5. Re-run activation steering (Concern 1: causal modulation)

```bash
# Modal A10G; ~USD 15
python scripts/modal_steering_v2.py
# ⇒ results/11-activation-steering/v2/steering_v2_results.json
#   9 multipliers × 204 prompts = 1,836 trials at layer 27.
#   Headline: OR=0.370 at α=+3, Bonferroni P=5.92×10⁻⁵; trend P=5.3×10⁻⁴.
#   See JSON keys "dose_response", "per_trial", "statistics".
```

The steering vector is the mean residual-stream difference between brand-driven and specification-driven activations on a held-out 500-trial training split. Vector is re-derived at runtime; the 9-multiplier sweep applies α ∈ {−3, −2, −1, −0.5, 0, +0.5, +1, +2, +3} at layer 27 of Qwen 2.5 7B Instruct.

### 6. Re-run base-vs-instruct (Concern 2: training causation)

```bash
# Modal A10G; ~USD 20
python scripts/modal_base_vs_instruct.py
# ⇒ results/02-base-vs-instruct/all_base_vs_instruct.json
#   Headline: Gemma 4 E4B base 67% vs instruct 20%; Mistral 7B base 72% vs instruct 55%.
```

### 7. Re-run the temperature sweep (sampling-variance control)

```bash
# OpenAI API; ~USD 15
python scripts/temperature_sweep.py
# ⇒ results/temperature_sweep/temperature_sweep_raw.csv (4,080 rows)
#   3 OpenAI models × 4 temperatures (0.0, 0.3, 0.7, 1.0) × 340 trials.
```

### 8. Re-run cross-judge validation (Supplementary Note 29)

```bash
python scripts/cross_judge_validation.py
# ⇒ results/judge_validation/
#   200-trial Haiku-vs-matched-judge agreement check (98% on brand-reasoning).
```

### 9. Re-run the inverse capability scaling regression

```bash
python scripts/09_scaling_law.py
# ⇒ results/09-scaling-law/
#   30-model regression of log(non_optimal_rate) on tier index.
#   β = 0.108 per tier (SE = 0.027, R² = 0.36, P = 5×10⁻⁴).
```

### 10. Re-run human-study analyses

```bash
# Studies 1A, 1B, 2: pre-registered DV protocol (QID17==2 branded, QID17==4 optimal)
python human_studies/welfare_analysis_human_studies.py
# ⇒ human_studies/welfare_analysis_output.txt

# Study 3: chatbot replay + Sonnet judge analysis
python human_studies/study3-chatbot/analysis/run_full_analysis.py
# ⇒ human_studies/study3-chatbot/analysis/output/STUDY3_FINAL_REPORT.md
```

### 11. Rebuild the paper PDF + DOCX

```bash
PANDOC=/path/to/pandoc bash paper/build.sh
# ⇒ paper/main.{pdf,docx}, paper/supplementary.{pdf,docx}, paper/cover_letter.pdf
# Bundled CSL (nature.csl) and reference.docx live in paper/_templates/.
```

### Audit hooks

```bash
python reproduce.py --audit
# Verifies: 12 SHA-256 hashes (data/hashes.json) + every figure path in main.md +
# every citation key in references.bib + Study 3 output presence.
```

## Primary dataset

**File:** `data/spec_resistance_EXTENDED.csv` (627,491 rows × 77 columns).

- 30 frontier language models from seven developers
- 32 experimental conditions × 34 product assortments × 20 consumer categories
- Four prompt paraphrases per condition (rotated)
- Approximately 20,900 trials per model on average (per-cell variability reflects rate-limit recoveries; range 20,400 to 21,261)

### Key columns

| Column | Type | Description |
|---|---|---|
| `trial_id` | string | Unique trial identifier |
| `model_key` | string | Model identifier (e.g. `claude-opus-4.7`, `gpt-5.4-nano`) |
| `provider` | string | API provider (Anthropic, OpenAI, Google, OpenRouter) |
| `condition` | string | Experimental condition (32 unique values) |
| `category` | string | Product category (20 categories) |
| `assortment_id` | string | Product assortment identifier (34 assortments) |
| `chose_optimal` | bool | Whether the model selected the specification-optimal product |
| `chosen_brand_familiarity` | string | Familiarity tier of chosen brand (high / medium / low / fictional) |
| `utility_loss` | float | Utility loss from non-optimal choice (0 if optimal) |
| `judge_coherence` | float | Coherence score from matched-model judge (0–100) |
| `judge_spec_acknowledgment` | float | Specification-acknowledgement score (0–100) |
| `judge_brand_reasoning` | bool | Whether the justification cites brand reputation as a decision factor |
| `raw_response` | string | Full model response text |
| `paraphrase_index` | int | Prompt paraphrase variant (0–3) |
| `chosen_position` | int | Display position of chosen product (0–4) |
| `optimal_display_position` | int | Display position of optimal product (0–4) |
| `product_A_price` … `product_E_price` | string | Per-letter product prices (`$`-prefixed) |
| `cost_usd` | float | API cost for this trial in USD |

### Models (30 cells)

| Provider | Cells |
|---|---|
| Anthropic | Claude Haiku 4.5; Claude Haiku 4.5 with extended thinking; Claude Sonnet 4.6; Claude Sonnet 4.6 with extended thinking; Claude Opus 4.6; Claude Opus 4.7 |
| OpenAI | GPT-4o; GPT-4o Mini; GPT-4.1 Mini; GPT-4.1 Nano; GPT-5 Mini; GPT-5.4; GPT-5.4 Mini; GPT-5.4 Mini with extended thinking; GPT-5.4 Nano |
| Google | Gemini 2.0 Flash; Gemini 2.5 Flash; Gemini 2.5 Flash Lite; Gemini 2.5 Pro; Gemini 3 Flash; Gemini 3 Flash with extended thinking; Gemini 3.1 Pro; Gemini 3.1 Flash Lite |
| Google open-weight | Gemma 3 27B; Gemma 4 31B IT |
| Other open-weight | Llama 3.3 70B (Meta); Qwen 2.5 72B (Alibaba); Kimi K2 (Moonshot) |
| Other | DeepSeek V3, DeepSeek R1 (DeepSeek) |

Within-architecture extended-thinking variants enable a controlled compute manipulation in four model families (Claude Haiku 4.5, Claude Sonnet 4.6, GPT-5.4 Mini, Gemini 3 Flash). Five cells (Gemini 3 Flash with extended thinking, Gemini 3.1 Pro, Gemini 3.1 Flash Lite, Gemma 4 31B IT, and the majority of GPT-5.4 trials) were judged by Claude Haiku 4.5 as a cross-judge because provider-side rate limits and batch-API timeouts prevented matched-judge completion. Supplementary Note 29 documents the 200-trial cross-judge validation (98 per cent raw agreement on brand-reasoning).

### Experimental conditions (32 total, 7 functional groups)

| Group | Conditions | Purpose |
|---|---|---|
| Baseline | 1 | Unmanipulated product recommendation |
| Mechanism isolation | 9 | Decompose prior into constituent signals (anonymisation, description-minimal, etc.) |
| Specification gradient (preference) | 5 | Natural-language precision escalation (vague / weighted / explicit / override / constrained) |
| Specification gradient (utility) | 5 | Numerical-format precision escalation |
| Controls | 4 | Validate that misalignment is training-derived (all-fictional / brand-reversal / comprehension / all-familiar) |
| Anti-brand | 3 | Test whether restrictive instructions correct the prior (rejection / negative experience / prefer-unknown) |
| Mechanism (explicit) | 5 | Mechanism conditions at explicit specification level (incl. conjoint attribute-swap) |

## Headline results (recomputable from EXTENDED.csv)

- **Baseline non-optimal rate:** 25.0 per cent (95 per cent CI 24.4 to 25.6); range 8.7 per cent (GPT-4.1 Mini) to 59.2 per cent (Claude Opus 4.7).
- **Specification gap:** preference pathway 25.0 → 0.4 per cent (odds ratio 57; Cohen's *h* = 0.73); utility pathway 25.0 → 0.8 per cent (OR 8.7).
- **Comprehension is near-perfect:** 26 of 30 models exceed 99.9 per cent; the remaining four are explicitly documented (Gemini 2.5 Pro, DeepSeek V3, GPT-5.4, Gemma 4 31B IT).
- **Confabulation:** 73.8 per cent of non-optimal choices justify with attribute reasoning that omits brand (N = 5,072 with judge data); brand-cite is 26.2 per cent on non-optimal vs 4.5 per cent on optimal (sums to 100 per cent over the same denominator).
- **Cross-model convergence:** mean pairwise *r* = 0.64 across 435 model pairs at the assortment level; 75.9 per cent agreement on the same non-optimal brand within category; six assortments at 100 per cent brand-agreement.
- **Inverse capability scaling:** β = 0.108 per tier (SE = 0.027, *R*² = 0.36, *P* = 5 × 10⁻⁴).
- **Cross-corpus invariance:** Pearson 0.96 to 0.99 on log-frequency across C4 / Pile / RedPajama / Dolma. Raw frequency does not predict model-level preference once popularity proxies are partialled out (F = 0.18, *P* = 0.68).
- **Causal installation:** 100 fine-tuning examples on an invented brand (Axelion, no measurable prior corpus frequency) raise the recommendation rate to 52.5 per cent in the primary run (mean 49.4 per cent, SD 4.1 across seven non-outlier seeds). Placebo (P = 0.62) and negative-direction (P = 0.006) controls confirm specificity. LoRA on Qwen 2.5 7B replicates (+10.5 pp, P = 0.008).
- **Structural encoding:** linear probes on residual-stream activations at 77.0 per cent accuracy in Qwen 2.5 7B (AUC 0.835) and 87.9 per cent in Gemma 4 E4B (AUC 0.900) under GroupKFold cross-validation by assortment.
- **Causal modulation:** contrastive activation steering on Qwen 2.5 7B at the best-performing layer (27 of 28) produces a 21 percentage-point dose-response across nine steering strengths (OR = 0.37 at α = +3, Bonferroni *P* = 5.9 × 10⁻⁵; linear trend *P* = 5.3 × 10⁻⁴).
- **Persists through post-training:** Gemma 4 E4B base 67 per cent vs instruct 20 per cent on identifiable-choice trials (Mistral 7B replicates: 72 per cent vs 55 per cent). Targeted debiasing on three GPT families requires 6,000 examples to reach 0.3 per cent; 500 examples reach 0.9 per cent. Creation-removal asymmetry: 100 examples install vs 500–6,000 to remove.
- **Welfare:** 95.6 per cent of biased recommendations carry a positive price premium (mean USD 79, median USD 50) over the specification-optimal alternative. Population-level decomposition implies USD 5–10 million per million biased recommendations and USD 4–9 billion per year at deployment scenarios consistent with current AI shopping agents.
- **Behavioural studies (N = 3,164):** Study 1A and 1B replicate biased-AI compliance at +33.3 pp (P = 1.3 × 10⁻¹⁴) and +27.7 pp (P = 1.05 × 10⁻¹⁰); Study 2 inoculation reduces compliance by 12.2 pp and SpecExposed by 17.4 pp, with 55–60 per cent residual compliance even after direct specification debunking; Study 3 (interactive chatbot, participant-chosen categories) replicates at +18.7 pp on focal-brand choice (P < 0.0001, OR 2.16) and +27.2 pp on optimal choice in the honest condition.

## Figures

All figures are in `figures/` as PDF + PNG (and SVG for ED 9).

### Main figures (Fig 1–9)
- **Fig 1:** Experimental design schematic + Stage 2 user-AI chat + LLM-as-judge protocol
- **Fig 2:** Baseline non-optimal rates across all 30 models
- **Fig 3:** Control conditions
- **Fig 4:** Specification gap phase transition (preference + utility pathways)
- **Fig 5:** Conjoint decomposition and confabulation analysis
- **Fig 6:** Anti-brand correction asymmetry (rejection, negative experience, prefer-unknown)
- **Fig 7:** Model families, cross-model correlations, open-weight vs proprietary convergence
- **Fig 8:** Causal + structural composite (injection / probing / steering / base-vs-instruct)
- **Fig 9:** Human studies composite (Studies 1A, 1B, 2, 3)

### Extended Data (ED 1–9)
- **ED 1:** Position and letter bias (`ed1_position_bias.*`)
- **ED 2:** 32-condition × 30-model heatmap (`ed2_condition_heatmap.*`)
- **ED 3:** Individual model dose-response curves (`ed3_dose_response.*`)
- **ED 4:** Baseline mechanism decomposition (`ed4_baseline_mechanisms.*`)
- **ED 5:** Category × model heatmap (file: `ed7_category_heatmap.*`)
- **ED 6:** LLM-as-judge evaluation (file: `ed8_judge.*`)
- **ED 7:** Vague paradox (file: `ed10_vague_paradox.*`)
- **ED 8:** Confabulation gradient (file: `ed11_confabulation.*`)
- **ED 9:** Verbatim confabulation codebook with attribute-comparison tables (file: `ed9_confabulation_examples.*`)

### Supplementary figures (S1–S5)
- **S1:** Confabulation gradient across specification + anti-brand conditions
- **S2:** Utility loss distributions and model-level scatter
- **S3:** Brand-familiarity composition of non-optimal choices
- **S4:** Cross-model correlation structure (30 × 30 heatmap)
- **S5:** Specification gap × price premium interaction

## Human studies

Four pre-registered Prolific behavioural studies (combined N = 3,164 after pre-registered exclusions, from N = 3,224 collected; IRB exempt approval from Oklahoma State University, April 2026) are in `human_studies/`. Each study folder contains `anonymised.csv`, `codebook.md`, and `prereg.md`. Study 3 additionally contains the full chatbot worker (`study3-chatbot/worker/`), Qualtrics template (`study3-chatbot/survey.qsf`), Sonnet-judge analysis pipeline (`study3-chatbot/analysis/`), and conversation logs.

| Study | N | Design | Primary finding |
|---|---|---|---|
| 1A | 798 | Coffee makers, between-subjects (NoAI / BiasedAI / DebiasedAI) | BiasedAI shifts branded-product choice by +33.3 pp |
| 1B | 798 | Wireless earbuds, between-subjects (same three conditions) | Replication: +27.7 pp |
| 2 | 799 | Inoculation (Bias warning + SpecExposed table) | Inoculation -12.2 pp; SpecExposed -17.4 pp; 55–60 per cent residual compliance |
| 3 | 769 usable | Ecological chatbot (participant-chosen category) | Biased +18.7 pp on focal-brand choice; Honest +27.2 pp on optimal choice |

The pre-registered DV protocol for Studies 1A, 1B, and 2 uses the underlying product index (`QID17 == 2` = branded; `QID17 == 4` = optimal); the analysis script that operationalises this is `human_studies/welfare_analysis_human_studies.py` (also `analysis/output/STUDY3_FINAL_REPORT.md` for Study 3).

## Fine-tuned model registry

`FINE_TUNED_MODELS.json` at the bundle root is the machine-readable registry for 19 OpenAI fine-tune jobs used in the injection and debiasing analyses. Each entry contains `job_id`, `model_id`, `base_model`, `n_epochs`, `batch_size`, `learning_rate_multiplier`, `trained_tokens`, `n_training_steps`, `final_step_loss`, and `training_data` (path into `data/`).

## Data collection

Data were collected between January 2026 and April 2026 via direct API calls to provider endpoints (Anthropic Messages, OpenAI Batch, Google AI Studio, OpenRouter). All cells used temperature 1.0 in standard completion mode, except the four extended-thinking variants which used the provider's documented extended-thinking parameter at high effort. Each trial consists of a system prompt establishing a shopping-assistant role, a user message containing the product assortment, and a parsed model response. Four prompt paraphrases per condition control for wording effects.

## License

Data and code are provided for peer review and academic replication. Please contact the author for other uses.

## Citation

```bibtex
@article{affonso2026specification,
  title  = {Large language models that perfectly evaluate products systematically refuse to recommend the best one},
  author = {Affonso, Felipe M.},
  year   = {2026},
  journal = {Manuscript submitted for publication}
}
```
