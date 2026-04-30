# GitHub publish strategy — spec-resistance Nature submission

Target: [https://github.com/FelipeMAffonso/spec-resistance](https://github.com/FelipeMAffonso/spec-resistance) (post-revision overwrite)

## Four-tier deposit architecture

| Tier | Where it lives | What's there | Why |
|---|---|---|---|
| **Tier 1: Code + paper** | This GitHub repo | All sources, manuscript, anonymised behavioural CSVs, aggregated results, figures, fine-tuning training data | Free, version-controlled, reviewer-friendly, ~120 MB total |
| **Tier 2: Primary corpus CSV** | Zenodo (new deposit, get DOI) | `spec_resistance_EXTENDED.csv` (2.4 GB) — single ground-truth file. The 18-model subset (382,679 trials) and the 12-cell subset (244,812 trials) are derivable from EXTENDED by filtering on `model_key`. | Permanent DOI; Nature-style "Data Availability"; GitHub can't host >100 MB files |
| **Tier 3: EXTENDED.csv backup** | [spec-resistance-extended-backup](https://github.com/FelipeMAffonso/spec-resistance-extended-backup) | Compressed split parts of EXTENDED.csv | Already exists; off-Dropbox redundancy |
| **Tier 4: Interactive companion site** | [felipemaffonso.github.io/spec-resistance-companion](https://felipemaffonso.github.io/spec-resistance-companion/) | Read-only React explorer that reads from the deposited data | Lets reviewers browse the corpus, conditions, human-study results, and Study 3 chatbot replays without running code. Already live; deploys via GitHub Actions on each push. |

## What gets UPLOADED to GitHub (Tier 1)

After applying `OSF/.gitignore`, the published repo will contain:

| Path | Size | Purpose |
|---|---|---|
| `README.md` | 38 KB | Top-level README with reproduction instructions |
| `reproduce.py`, `run.py`, `rebuild_clean_csv.py` | ~40 KB | Reproduction drivers |
| `requirements.txt` | <1 KB | Python deps |
| `FINE_TUNED_MODELS.json` | 14 KB | Fine-tuned model registry |
| `paper/` | 20 MB | Manuscript .md/.pdf, figures, build script, LaTeX template, references.bib |
| `analysis/` | 340 KB | Statistical pipeline (compute_all_stats.py, generate_figures_nature.py, etc.) |
| `experiment/` | 576 KB | Assortment definitions, condition registry, runner |
| `harness/` | 218 KB | Core harness (minus `fix_broken_judges.py`) |
| `config/` | 570 KB | Model registry, products, stakeholders |
| `scripts/` | 3.1 MB | Verification scripts (verify_paper_numbers.py, verify_study2*.py) |
| `qualtrics/` | 368 KB | All four `.qsf` survey exports |
| `IRB/Exempt Approval Letter.pdf` | ~100 KB | Only the approval letter |
| `results/` | 41 MB | All aggregated stats, summary JSONs, generated figures |
| `human_studies/` | 63 MB | Per-study anonymised.csv, codebooks, prereg.md, analysis scripts, Study 3 chatbot worker, Cloudflare KV export |
| `data/` | ~10 MB | `manuscript_numbers.json`, `hashes.json`, `brand_frequencies.csv`, `verification_report.md`, `spec_resistance_EXTENDED.provenance.json`, plus small fine-tuning training-data subdirs |
| **Total** | **~130 MB** | Well under GitHub's 1-GB-soft / 5-GB-hard repo cap |

## What gets EXCLUDED (in `.gitignore`)

| Path | Size | Why excluded |
|---|---|---|
| `add_new_models/` | 1.5 GB | Internal corpus-expansion pipeline scratch (12 per-cell JSONLs at 50-100 MB each plus 30+ helper scripts). Per user: don't upload individual-trial JSONs. |
| `prereg/` | 32 KB | Pre-registration markdown drafts; canonical pre-registrations are now AsPredicted URLs cited inline in main + supplementary |
| `logs/` | 56 KB | Past `reproduce.py` runtime logs |
| `IRB/IRB_PREP_GUIDE.md`, `IRB/eligibility_screening.{md,docx}`, `IRB/recruitment_prolific.{md,docx}` | ~30 KB | Internal IRB working drafts; only the approval letter is reviewer-relevant |
| `harness/fix_broken_judges.py` | ~5 KB | Debugging recovery script for one-time judge failures |
| `data/spec_resistance_EXTENDED.csv` | 2.4 GB | Goes to Zenodo (Tier 2) — single ground-truth file |
| `data/spec_resistance_CLEAN.csv` | 1.4 GB | Redundant subset of EXTENDED; can be re-derived via `df[df.model_key.isin(ORIGINAL_18)]` |
| `data/spec_resistance_NEW_MODELS.csv` | 993 MB | Redundant subset of EXTENDED; can be re-derived via `df[df.model_key.isin(NEW_12)]` |
| `data/spec_resistance_CLEAN.csv.gz` | (large) | Compressed duplicate |
| `data/extended_csv_backup/` | 164 MB | Already in the standalone backup repo (Tier 3) |
| `__pycache__/`, `*.pyc`, `.env`, `.DS_Store`, etc. | varies | Standard build/secrets/OS noise |

Total excluded: ~5.1 GB. Most of that is the three large CSVs and the `add_new_models/` pipeline.

## Zenodo strategy (Tier 2)

Single Zenodo deposit titled "spec-resistance corpus (EXTENDED, 30 models, 627,491 trials)" containing:

1. `spec_resistance_EXTENDED.csv` (2.4 GB) — primary corpus
2. `spec_resistance_CLEAN.csv` (1.4 GB) — original 18-model subset
3. `spec_resistance_NEW_MODELS.csv` (993 MB) — 12 new cells subset
4. `spec_resistance_EXTENDED.provenance.json` (build provenance, copy from data/)
5. `hashes.json` (SHA-256 verifications, copy from data/)
6. `README.md` (custom Zenodo README explaining schema + how to use with the GitHub code repo)

Zenodo file-size limit is 50 GB per record, so the three CSVs fit comfortably. Once deposited, get the DOI and update:
- Manuscript Data Availability section (replace "Zenodo (DOI pending public release)" with actual DOI)
- README.md in the GitHub repo (link to Zenodo)
- `data/README.md` in the GitHub repo (link to Zenodo as primary source for the CSVs)

## Migration plan (executing the publish)

The existing GitHub repo has pre-revision content. Recommended steps:

1. **Tag the current state** as a release before overwriting:
   ```bash
   gh release create v1-pre-revision --notes "Pre-revision state, before the 30-model corpus expansion and four pre-registered behavioural studies"
   ```
2. **Initialize git inside OSF/** (if not already):
   ```bash
   cd OSF
   git init
   git remote add origin https://github.com/FelipeMAffonso/spec-resistance.git
   ```
3. **Apply the `.gitignore`** (already written, in this directory).
4. **Commit the curated set:**
   ```bash
   git add .
   git status                              # review what's about to be committed
   git commit -m "Post-revision deposit: 30-model corpus, 4 pre-registered behavioural studies, full OSF self-containment"
   ```
5. **Force-push** (overwrites remote history; safe because v1-pre-revision is tagged):
   ```bash
   git push -f origin master
   ```

   Or, if Felipe prefers to preserve history:
   ```bash
   git fetch origin
   git checkout -b v2-revision
   git push -u origin v2-revision
   # then merge or set v2-revision as default branch via GitHub UI
   ```

## Open questions for Felipe

1. **Study 3 `kv_export.json`** (31 MB): Cloudflare KV export of per-session AI conversation traces (~770 sessions). Currently included in the upload list. Borderline "individual-level" data but anonymised. Include or exclude?
2. **Force-push vs new branch?** (see Migration plan step 5)
3. **Zenodo deposit timing**: do this before or after Nature acceptance? Nature accepts a "Data Availability" stating "deposited at Zenodo (DOI: ...)" or "available at the corresponding GitHub repo (...)" — so depositing earlier is fine and lets reviewers verify.
