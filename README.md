# Specification Resistance in Language Model Product Recommendations

Replication package for: **"Training-derived brand preferences in language models override user preferences"**

Felipe M. Affonso, Spears School of Business, Oklahoma State University

## Overview

This repository contains all data, analysis code, and figure generation scripts needed to reproduce every result, figure, and statistical test reported in the main text and supplementary materials. The dataset comprises 382,679 controlled product recommendation trials across 18 frontier language models from 7 developers, tested in 32 experimental conditions spanning 20 consumer product categories.

## Repository Structure

```
spec-resistance/
  README.md                 This file
  reproduce.py              One-command script to regenerate all figures and statistics
  data/
    spec_resistance_CLEAN.csv.gz  Authoritative dataset (382,679 rows, 77 columns, gzip-compressed)
    manuscript_numbers.json     Key statistics referenced in the manuscript
  analysis/
    compute_all_stats.py        Compute all statistical tests reported in the paper
    generate_figures_nature.py  Generate main figures (Fig 2-7) and extended data (ED 1-11)
    generate_supplementary_figures.py  Generate supplementary figures (S1-S5)
    generate_schematic.py       Generate experimental design schematic (Fig 1)
    supplementary_stats.py      Compute supplementary note statistics
  experiment/
    assortments.py              Product assortment definitions (34 assortments, 20 categories)
    conditions.py               All 32 experimental condition definitions
    runner.py                   Experiment execution harness
    __init__.py
  config/
    models.py                   Model specifications, API identifiers, and pricing
    products.py                 Product attribute definitions
    stakeholders.py             Stakeholder role definitions
    webmall_products.py         Product catalogue generation
    __init__.py
  harness/
    core.py                     Core LLM interaction harness
    cost_tracker.py             API cost tracking
    judge.py                    LLM-as-judge evaluation protocol
    shopping_agent.py           Shopping agent implementation
    __init__.py
  figures/                      All figures (main, extended data, supplementary; PNG + PDF)
```

## Quick Start: Reproduce All Results

### Requirements

```bash
pip install matplotlib numpy scipy
```

Python 3.10+ required. No GPU needed. All analyses run on CPU in under 5 minutes.

### One-Command Reproduction

```bash
python reproduce.py
```

This script will:
1. Verify dataset integrity (382,679 rows, 18 models, 32 conditions)
2. Compute all statistical tests (Fisher exact, Wilson CIs, odds ratios, chi-squared)
3. Regenerate all 23 figures (7 main + 11 extended data + 5 supplementary)
4. Print a comparison of computed statistics against manuscript values

### Individual Scripts

```bash
# Statistical analysis only
python analysis/compute_all_stats.py

# Main figures only
python analysis/generate_figures_nature.py

# Supplementary figures only
python analysis/generate_supplementary_figures.py

# Design schematic only
python analysis/generate_schematic.py
```

## Dataset Description

**File**: `data/spec_resistance_CLEAN.csv.gz` (382,679 rows x 77 columns, gzip-compressed)

To decompress: `gunzip data/spec_resistance_CLEAN.csv.gz` (or `gzip -dk data/spec_resistance_CLEAN.csv.gz` to keep the archive).

Near-perfectly balanced: 21,260 trials per model (680 per condition), 18 models, 32 conditions. One model (Gemini 2.0 Flash) has 21,259 trials due to a single irrecoverable API failure.

### Key Columns

| Column | Type | Description |
|--------|------|-------------|
| `trial_id` | string | Unique trial identifier |
| `model_key` | string | Model identifier (e.g., `claude-haiku-4.5`, `gpt-4o`) |
| `provider` | string | API provider (Anthropic, OpenAI, Google, OpenRouter) |
| `condition` | string | Experimental condition (32 unique values) |
| `category` | string | Product category (20 categories) |
| `assortment_id` | string | Product assortment identifier (34 assortments) |
| `chose_optimal` | boolean | Whether the model selected the specification-optimal product |
| `chosen_brand_familiarity` | string | Familiarity tier of chosen brand (high/medium/low) |
| `utility_loss` | float | Utility loss from non-optimal choice (0 if optimal) |
| `judge_coherence` | float | Coherence score from matched-model judge (0-100) |
| `judge_spec_acknowledgment` | float | Spec acknowledgment score (0-100) |
| `judge_brand_reasoning` | boolean | Whether justification cites brand reputation |
| `raw_response` | string | Full model response text |
| `paraphrase_index` | int | Prompt paraphrase variant (0-3) |
| `chosen_position` | int | Display position of chosen product (0-4) |
| `optimal_display_position` | int | Display position of optimal product (0-4) |
| `cost_usd` | float | API cost for this trial in USD |

### Models (18 total)

| Provider | Models |
|----------|--------|
| Anthropic | Claude Haiku 4.5, Claude Sonnet 4.6 |
| OpenAI | GPT-4o, GPT-4o Mini, GPT-4.1 Mini, GPT-4.1 Nano, GPT-5 Mini |
| Google | Gemini 2.0 Flash, Gemini 2.5 Flash, Gemini 2.5 Flash Lite, Gemini 2.5 Pro, Gemini 3 Flash, Gemma 3 27B |
| OpenRouter | Llama 3.3 70B, DeepSeek V3, DeepSeek R1, Qwen 2.5 72B, Kimi K2 |

### Experimental Conditions (32 total, 7 groups)

| Group | Conditions | Purpose |
|-------|-----------|---------|
| Baseline | 1 | Unmanipulated product recommendation |
| Mechanism isolation | 9 | Decompose prior into constituent signals |
| Specification gradient (utility) | 5 | Numerical precision escalation |
| Specification gradient (preference) | 5 | Natural-language precision escalation |
| Controls | 4 | Validate that misalignment is training-derived |
| Anti-brand | 3 | Test whether restrictive instructions correct priors |
| Mechanism (explicit) | 5 | Mechanism conditions at explicit specification level |

## Key Results

All statistics below are computed from the dataset and verified against the manuscript:

- **Baseline non-optimal rate**: 21.2% (95% CI 20.5-22.0%, N = 12,240)
- **Specification gap OR**: 69 (95% CI 50-96), preference weighted-to-explicit transition
- **Confabulation rate**: 79.2% of non-optimal choices cite only attributes (not brand), N = 2,600
- **Anti-brand backfire**: rejection 29.4%, negative experience 35.3% (both exceed baseline)
- **Cross-model correlation**: mean pairwise r = 0.65 (153 model pairs)
- **Total API cost**: approximately USD 337

## Figures

### Main Figures
- **Fig 1**: Experimental design schematic
- **Fig 2**: Training-derived brand preferences across 18 models
- **Fig 3**: Control conditions confirm training-data origins
- **Fig 4**: Specification gap phase transition (preference vs utility pathways)
- **Fig 5**: Conjoint decomposition and confabulation analysis
- **Fig 6**: Anti-brand correction asymmetry
- **Fig 7**: Model families, convergence, and cross-model correlations

### Extended Data Figures
- **ED 1**: Position and letter bias analysis
- **ED 2**: Complete 32-condition x 18-model heatmap
- **ED 3**: Individual dose-response curves for all 18 models
- **ED 4**: Baseline mechanism decomposition forest plot
- **ED 5**: Paraphrase robustness analysis
- **ED 6**: Provider effects and cost-performance relationship
- **ED 7**: Category-level heatmap
- **ED 8**: LLM-as-judge evaluation analysis
- **ED 9**: Assortment difficulty ranking
- **ED 10**: Vague paradox detail
- **ED 11**: Confabulation gradient by model

### Supplementary Figures
- **S1**: Confabulation gradient across conditions
- **S2**: Utility loss distributions and model-level scatter
- **S3**: Brand familiarity composition of non-optimal choices
- **S4**: Cross-model correlation structure (18x18 heatmap)
- **S5**: Specification gap x price premium interaction

## Data Collection

Data were collected between January and February 2026 via direct API calls. All 18 models were tested at temperature 1.0 in standard completion mode (no extended thinking or chain-of-thought). Each trial consists of a system prompt establishing a shopping assistant role, a user message containing the product assortment, and a parsed model response. Four prompt paraphrases per condition control for wording effects.

## License

Data and code are provided for peer review and academic replication. Please contact the author for other uses.

## Citation

```bibtex
@article{affonso2026specification,
  title={Training-derived brand preferences in language models override user preferences},
  author={Affonso, Felipe M.},
  year={2026},
  journal={Manuscript submitted for publication}
}
```
