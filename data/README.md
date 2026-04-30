# Data — spec-resistance corpus

This directory contains the spec-resistance dataset metadata, brand-frequency reference data, fine-tuning training data, and small derived artefacts. The three primary corpus CSVs are too large for the main GitHub repository (1.4 GB to 2.4 GB each) and are hosted in a separate backup repository.

## Primary corpus CSV (NOT in this repo — deposited at Zenodo)

| File | Size | Trials | Models | Description |
|---|---|---|---|---|
| `spec_resistance_EXTENDED.csv` | 2.4 GB | 627,491 | 30 | **Single ground-truth corpus** reported in the manuscript. Includes both the 12 new model cells added during the 2026-04 revision and the original 18 cells. |

The 18-model subset (382,679 trials, the original v1 corpus) and the 12-cell subset (244,812 trials) can be derived in code by filtering EXTENDED.csv on the `model_key` column — see `analysis/_build_subsets.py` if subsets are needed.

### How to obtain the CSV

**Primary source:** Zenodo at [https://doi.org/10.5281/zenodo.19927068](https://doi.org/10.5281/zenodo.19927068) (concept DOI: `10.5281/zenodo.19927067` resolves to the latest version). Download the deposit and place `spec_resistance_EXTENDED.csv` at `data/spec_resistance_EXTENDED.csv` in your local clone of this repo.

**Backup:** The compressed split parts of an earlier identical snapshot live in a standalone GitHub repo as off-site redundancy:

[**https://github.com/FelipeMAffonso/spec-resistance-extended-backup**](https://github.com/FelipeMAffonso/spec-resistance-extended-backup)

```bash
git clone https://github.com/FelipeMAffonso/spec-resistance-extended-backup.git
cd spec-resistance-extended-backup
# follow REASSEMBLE.md to recombine the .gz.part_aa + .gz.part_ab parts
# and decompress to spec_resistance_EXTENDED.csv
# then copy or symlink the file into OSF/data/
```

The expected SHA-256 of `spec_resistance_EXTENDED.csv` is recorded in `OSF/data/hashes.json` (this repo). Verifying the hash is the first step of `python reproduce.py --verify`.

## Files in this repo (small)

| File | Description |
|---|---|
| `manuscript_numbers.json` | Headline statistics computed from EXTENDED.csv (used by reproducibility audit) |
| `hashes.json` | SHA-256 hashes for the three primary CSVs and for every immutable artefact under `OSF/results/` |
| `brand_frequencies.csv` | Cross-corpus log-frequency matrix used by Supplementary Note 24 |
| `verification_report.md` | Output of `python scripts/verify_paper_numbers.py` (computes every headline number from EXTENDED.csv) |
| `spec_resistance_EXTENDED.provenance.json` | Build provenance for EXTENDED.csv (which cells were appended, in what order, with what cross-judge configuration) |

## Subdirectories (fine-tuning and intervention data)

| Dir | Description | Used by |
|---|---|---|
| `fictional_brand_injection/` | Original 100-example Axelion injection training data (GPT-4o-mini) | SN20 |
| `fictional_brand_injection_v2/` | Reproducibility re-run of the primary injection at multiple seeds | SN20 |
| `fictional_brand_injection_multicategory/` | Multi-category injection (laptops, coffee, headphones, smartphones, running shoes) | SN28 |
| `fictional_category_placebo/` | Novel-category placebo (quantum stylus) | SN28 |
| `injection_6k/` and `injection_6k_pure/` | Scaled debiasing fine-tuning data (6,000 examples) | SN27 |
| `openai_finetune/` and `openai_finetune_6k/` | OpenAI fine-tuning training files | SN20, SN27 |
| `dpo_debiasing/` | DPO-based debiasing experiment | SN27 |
| `negative_injection/` | Negative-direction injection (training to avoid Axelion) | SN20 |
| `anti_sony_injection/` | Anti-brand variant of the injection paradigm | SN20 |
| `real_brand_injection/` | Control variant injecting a real brand instead of the fictional Axelion | SN20 |
| `processed/` | Intermediate aggregations (kept for reproducibility audits) | various |
