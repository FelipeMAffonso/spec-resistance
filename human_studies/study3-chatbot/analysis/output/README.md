# Study 3 analysis outputs

Outputs from the Study 3 ecological-chatbot analysis pipeline. Every file is reproducible by running `human_studies/study3-chatbot/analysis/run_full_analysis.py`.

## File layout

| File | Description |
|---|---|
| `STUDY3_FINAL_REPORT.md` | Consolidated primary + MLM + judge report. |
| `ALL_ANGLES_REPORT.md` | 21-angle comprehensive analysis. |
| `all_angles_results.json` | Machine-readable version of the 21-angle analysis. |
| `all_results.json` | Dump from the baseline pilot pipeline. |
| `pilot_data_parsed.csv` | Parsed Qualtrics export (one row per participant, embedded-data columns materialised). |
| `pilot_data_usable.csv` | After exclusions (duration, attention, consent, JSON ok). |
| `pilot_report.md` | Quality-dashboard and primary-analysis report. |
| `mixed_effects_report.md` | MLM Branch C results. |
| `mixed_effects_results.json` | Machine-readable MLM output. |
| `postv24_parsed.csv`, `postv24_usable.csv` | Legacy pilot cut (pre-v24 window excluded); retained for backward compatibility. |
| `judges/J1_confabulation.csv` | J1 per-session confabulation verdicts. |
| `judges/J2_pushback.csv` | J2 pushback-handling verdicts. |
| `judges/J3_choice_reason.csv` | J3 choice-reason classifications. |
| `judges/J4_suspicion.csv` | J4 suspicion coding. |
| `judges/J5_meta_category.csv` | J5 category-to-meta-category mapping. |
| `judges/judge_summary.json` | Rolled-up judge statistics. |
| `judges/judge_cache/` | Content-hashed Sonnet API call cache (~2,000 entries after final run). |
| `figures_all_angles/fig1_three_bucket.{pdf,png}` | Three-bucket stacked bars. |
| `figures_all_angles/fig2_H1_RQ1.{pdf,png}` | H1 and RQ1 side-by-side with Wilson CIs. |
| `figures_all_angles/fig3_forest_H1_by_meta.{pdf,png}` | Per-meta-category forest plot. |
| `figures_all_angles/fig4_brand_x_condition.{pdf,png}` | Heatmap of focal rate by skin × condition. |
| `figures_all_angles/fig5_choice_reasons.{pdf,png}` | J3 primary-reason stacked distribution. |
| `figures_all_angles/fig6_confab_doseresponse.{pdf,png}` | Dose-response of J1 confabulation strength on focal compliance. |
| `raw_export/SR Study 3 - Ecological Chatbot (*).csv` | Direct Qualtrics export (archived per fetch). |
| `PILOT_2026-04-21/` | Frozen archive of the N = 62 pre-launch pilot run. |

## Reproduction

```bash
cd human_studies/study3-chatbot/analysis

# Full pipeline: fetch + parse + judges + MLM + consolidated report
python run_full_analysis.py --fetch

# Parse only (no API calls)
python analyze_study3_pilot.py --csv raw_export/<latest>.csv

# Judges only (cached after first run)
python judge_study3_sonnet.py --judges J1 J2 J3 J4 J5

# 21-angle comprehensive analysis
python analyze_all_angles.py

# Mixed-effects only
python mixed_effects_study3.py
```

## Judge cache

`judges/judge_cache/*.json` files are content-hashed Sonnet API calls. Key format: `sha256(model + system + user)[:24]`. Any downstream re-run with unchanged inputs hits cache (~$0 cost). Cache size grows only when new unique content is judged.

## Pre-registration and analysis spec

- `results/ASPREDICTED_STUDY3.md` — AsPredicted pre-registration (filed April 2026).
- `human_studies/study3-chatbot/analysis/PREREG_ANALYSIS_SPEC.md` — frozen contingency rules for the MLM, the five judge tasks, and the sensitivity analyses.

## Consumed by

- Main text, "Consumers follow biased AI recommendations" section, Study 3 paragraphs.
- Figure 9 panels c and d.
- Supplementary Note 33.
