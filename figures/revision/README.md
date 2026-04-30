# Revision figures

Composite and component figures for the Nature revision. Each file is either a
single-panel rendering produced by a script in `scripts/` or a
multi-panel composite produced by `paper/generate_revision_composites.py`.

## Composite figures (main text)

| File | Source script | Main paper reference |
|---|---|---|
| `fig8_causal_structural.{pdf,png}` | `paper/generate_revision_composites.py` | Main Figure 8 |
| `fig9_human_studies.{pdf,png}` | `paper/generate_revision_composites.py` | Main Figure 9 |

## Single-panel figures

| File | Content | Produced by |
|---|---|---|
| `fig_injection_dose_response.{pdf,png}` | Injection dose-response, isolated panel | `scripts/generate_revision_figures.py` |
| `fig_injection_fullscale.{pdf,png}` | Full-scale injection 8-seed scatter | same |
| `fig_asymmetry_creation_vs_removal.{pdf,png}` | Creation-removal asymmetry bar chart | same |
| `fig_asymmetry_fullscale.{pdf,png}` | Full-scale asymmetry across model families | same |
| `fig_debiasing_comparison.{pdf,png}` | Debiasing result comparison across 3 GPT families | same |
| `fig_debiasing_fullscale.{pdf,png}` | Full-scale debiasing with error bars | same |
| `fig_alignment_gradient.{pdf,png}` | Base-vs-instruct alignment gradient | same |
| `fig_confabulation_by_frequency.{pdf,png}` | Confabulation x training-data frequency scatter | same |
| `fig_evidence_by_concern.{pdf,png}` | Meta-summary by Nature's three concerns | same |

## Reproduction

```bash
# Full regeneration of all revision figures (single panels + composites)
cd projects/spec-resistance
python scripts/generate_revision_figures.py         # single panels
python paper/generate_revision_composites.py                   # composites

# Just the two composites (if single panels are already up to date)
python paper/generate_revision_composites.py
```

## Depends on

- `results/08-fictional-injection/` (injection data).
- `results/06-openai-finetune/` (debiasing data).
- `results/02-base-vs-instruct/` (base-vs-instruct).
- `results/04-representation-probing/v3/` (probing).
- `human_studies/study3-chatbot/analysis/output/pilot_data_usable.csv` (Study 3).
- `human_studies/study3-chatbot/analysis/output/judges/J5_meta_category.csv` (Study 3 meta-category forest).

## Consumed by

- `paper/main_v2.md` (Figures 8, 9).
- `paper/supplementary_v2.md` (selected single panels for SI figures).
