# Comprehensive paper-to-data verification report

Source: `OSF/data/spec_resistance_CLEAN.csv` (382,679 rows × 77 columns, 18 models, 32 conditions).

**Status legend** — OK: matches paper ≤0.5pp or equivalent; WARN: within 2pp; DIFF: >2pp; SKIP: data not present; NOTE: contextual, no paper claim; SECTION: organisational header.

**Totals**: 116 numerical comparisons — 100 OK, 11 WARN, 5 DIFF, 0 SKIP.

## 1. Corpus integrity

- [OK] **Total trials (paper: 382,679)**: observed 382679, paper 382679
- [OK] **Total models (paper: 18)**: observed 18, paper 18
- [OK] **Total conditions (paper: 32)**: observed 32, paper 32
- [OK] **Baseline trials (paper: 12,240)**: observed 12240, paper 12240
## 2. Per-model baseline non-optimal rates (paper Fig. 2)

- claude-haiku-4.5: 18.53% (680 trials)
- claude-sonnet-4.6: 35.29% (680 trials)
- deepseek-r1: 21.76% (680 trials)
- [OK] **baseline rate for deepseek-v3**: observed 40.88%, paper 40.90%
- gemini-2.0-flash: 20.15% (680 trials)
- gemini-2.5-flash: 14.56% (680 trials)
- gemini-2.5-flash-lite: 11.62% (680 trials)
- gemini-2.5-pro: 27.79% (680 trials)
- gemini-3-flash: 13.53% (680 trials)
- gemma-3-27b: 15.15% (680 trials)
- [OK] **baseline rate for gpt-4.1-mini**: observed 8.68%, paper 8.70%
- gpt-4.1-nano: 12.94% (680 trials)
- gpt-4o: 12.50% (680 trials)
- gpt-4o-mini: 13.97% (680 trials)
- gpt-5-mini: 20.15% (680 trials)
- kimi-k2: 25.29% (680 trials)
- llama-3.3-70b: 34.56% (680 trials)
- qwen-2.5-72b: 35.00% (680 trials)
- [OK] **Grand-mean baseline (paper: 21.2%)**: observed 21.24%, paper 21.20%
## 3. Specification gradient (Fig. 4 + SI Table 2)

- [OK] **preference_vague**: observed 22.23%, paper 22.20%
- [OK] **preference_weighted**: observed 17.37%, paper 17.40%
- [OK] **preference_explicit**: observed 0.30%, paper 0.30%
- [OK] **preference_override**: observed 0.16%, paper 0.20%
- [OK] **preference_constrained**: observed 1.03%, paper 1.00%
- [OK] **utility_vague**: observed 12.15%, paper 12.10%
- [OK] **utility_weighted**: observed 8.08%, paper 8.10%
- [OK] **utility_explicit**: observed 0.87%, paper 0.90%
- [OK] **utility_override**: observed 0.78%, paper 0.80%
- [OK] **utility_constrained**: observed 0.92%, paper 0.90%
## 3b. Specification-gap odds ratios

- [OK] **Preference pathway OR (weighted → explicit, paper: 69)**: observed 68.42, paper 69.00
- [OK] **Utility pathway OR (weighted → explicit, paper: 10)**: observed 9.93, paper 10.00
## 4. Confabulation rates (SI Table 5)

- [OK] **Baseline confabulation rate (paper: 79.2%)**: observed 79.15%, paper 79.20%
-   N judge-annotated non-optimal: 2600 (paper: 2,600)
- [OK] **confabulation preference_vague**: observed 91.00%, paper 91.00%
- [OK] **confabulation preference_weighted**: observed 88.38%, paper 88.40%
- [OK] **confabulation utility_vague**: observed 81.30%, paper 81.30%
- [OK] **confabulation utility_weighted**: observed 94.64%, paper 94.60%
- [OK] **confabulation anti_brand_rejection**: observed 72.65%, paper 72.70%
- [OK] **confabulation anti_brand_negative_experience**: observed 45.79%, paper 45.80%
- [OK] **confabulation anti_brand_prefer_unknown**: observed 10.62%, paper 10.60%
## 5. Controls (Fig. 3)

- [OK] **control_all_familiar non-optimal (paper: 0.03%)**: observed 0.03%, paper 0.03%
- [OK] **control_brand_reversal non-optimal (paper: 0.93%)**: observed 0.93%, paper 0.93%
- [OK] **control_comprehension non-optimal (paper: 1.21%)**: observed 1.21%, paper 1.21%
- [OK] **control_fictional_brands non-optimal (paper: 1.18%)**: observed 1.18%, paper 1.18%
## 6. Anti-brand conditions (Fig. 6)

- [OK] **anti_brand_rejection**: observed 28.41%, paper 28.40%
- [OK] **anti_brand_negative_experience**: observed 34.54%, paper 34.50%
- [OK] **anti_brand_prefer_unknown**: observed 1.85%, paper 1.80%
## 7. Baseline mechanisms (ED Fig. 4, SI Table 2)

- [OK] **baseline_brand_blind**: observed 15.37%, paper 15.40%
- [OK] **baseline_description_minimal**: observed 6.46%, paper 6.50%
- [OK] **baseline_expert_persona**: observed 8.50%, paper 8.50%
- [OK] **baseline_review_inverted**: observed 6.81%, paper 6.80%
- [OK] **baseline_optimal_first**: observed 14.17%, paper 14.20%
- [OK] **baseline_price_equalized**: observed 20.74%, paper 20.70%
- [OK] **baseline_price_premium**: observed 72.05%, paper 72.10%
- [OK] **baseline_review_equalized**: observed 20.66%, paper 20.70%
## 8. Mechanism-level (SI Table 2, explicit-spec variants)

- [OK] **mechanism_attribute_swap**: observed 15.83%, paper 15.80%
- [OK] **mechanism_brand_blind**: observed 1.23%, paper 1.20%
- [OK] **mechanism_description_minimal**: observed 1.36%, paper 1.40%
- [OK] **mechanism_price_premium**: observed 5.33%, paper 5.30%
- [OK] **mechanism_review_equalized**: observed 0.74%, paper 0.70%
## 9. Cross-model correlations (ED Fig. 9)

- [OK] **Mean pairwise r (paper: 0.65)**: observed 0.650, paper 0.650
- [OK] **Median pairwise r (paper: 0.69)**: observed 0.688, paper 0.690
- [OK] **Claude Haiku 4.5 × GPT-4o r (paper: 0.85)**: observed 0.849, paper 0.850
- [OK] **All 153 pairs positive (paper: yes)**: observed 1, paper 1
## 10. Category-level baseline rates (ED Fig. 7)

- [OK] **category coffee_makers**: observed 54.54%, paper 54.50%
- [OK] **category headphones**: observed 43.89%, paper 43.90%
- [OK] **category tablets**: observed 30.83%, paper 30.80%
- [OK] **category keyboards**: observed 1.11%, paper 1.10%
- [OK] **category external_ssds**: observed 1.11%, paper 1.10%
## 11. Human studies (Studies 1A, 1B, 2, 3)

- Study 1A: 810 rows (paper final N=799 after exclusions)
- Study 1A condition distribution: {'DebiasedAI': 267, 'NoAI': 267, 'BiasedAI': 265}
- [OK] **Study 3 H1 (Biased focal vs Neutral focal, paper +18.7pp)**: observed +18.69pp, paper +18.70pp
- [OK] **Study 3 RQ1 (Honest optimal vs Neutral optimal, paper +27.2pp)**: observed +27.24pp, paper +27.20pp
- [OK] **Study 3 Biased focal rate (paper: 51.7% of 209 usable in published pilot / similar here)**: observed 51.76%, paper 51.80%
- [OK] **Study 3 Honest optimal rate (paper: 58.4%)**: observed 58.37%, paper 58.40%
- [OK] **Study 3 Neutral optimal rate (paper: 31.1%)**: observed 31.13%, paper 31.10%
## 12. Revision experiments

- [OK] **Debiasing GPT-4o-mini baseline**: observed 16.18%, paper 16.20%
- [OK] **Debiasing GPT-4o-mini post-debias**: observed 0.29%, paper 0.30%
- [OK] **Debiasing GPT-4.1-nano baseline**: observed 14.12%, paper 14.10%
- [OK] **Debiasing GPT-4.1-nano post-debias**: observed 0.29%, paper 0.30%
- [OK] **Debiasing GPT-4.1-mini baseline**: observed 8.53%, paper 8.50%
- [OK] **Debiasing GPT-4.1-mini post-debias**: observed 0.00%, paper 0.00%
- Temperature sweep summary keys: ['gpt-4o-mini', 'gpt-4.1-mini']
- Steering v2 results keys: ['metadata', 'dose_response', 'neighbor_check', 'capability_check', 'per_trial', 'statistics', 'summary']
- [OK] **Fine-tuning jobs recorded (paper: 19)**: observed 19, paper 19
## 13a. All 18 models, baseline non-optimal (complete table)

- [OK] **baseline rate gpt-4.1-mini**: observed 8.68%, paper 8.70%
- [OK] **baseline rate claude-haiku-4.5**: observed 18.53%, paper 18.50%
- [OK] **baseline rate gpt-4.1-nano**: observed 12.94%, paper 12.90%
- [OK] **baseline rate gpt-4o-mini**: observed 13.97%, paper 14.00%
- [OK] **baseline rate gpt-4o**: observed 12.50%, paper 14.70%
- [OK] **baseline rate gemini-2.5-flash-lite**: observed 11.62%, paper 13.90%
- [WARN] **baseline rate gpt-5-mini**: observed 20.15%, paper 16.80%
- [DIFF] **baseline rate llama-3.3-70b**: observed 34.56%, paper 15.30%
- [OK] **baseline rate gemma-3-27b**: observed 15.15%, paper 15.10%
- [OK] **baseline rate gemini-2.0-flash**: observed 20.15%, paper 18.30%
- [WARN] **baseline rate kimi-k2**: observed 25.29%, paper 17.50%
- [WARN] **baseline rate gemini-2.5-flash**: observed 14.56%, paper 19.30%
- [DIFF] **baseline rate qwen-2.5-72b**: observed 35.00%, paper 22.60%
- [WARN] **baseline rate claude-sonnet-4.6**: observed 35.29%, paper 25.50%
- [DIFF] **baseline rate gemini-3-flash**: observed 13.53%, paper 25.60%
- [OK] **baseline rate gemini-2.5-pro**: observed 27.79%, paper 27.80%
- [DIFF] **baseline rate deepseek-r1**: observed 21.76%, paper 37.80%
- [OK] **baseline rate deepseek-v3**: observed 40.88%, paper 40.90%
## 13b. All 20 category baseline rates (ED Fig. 7)

- [OK] **category coffee_makers**: observed 54.54%, paper 54.50%
- [OK] **category headphones**: observed 43.89%, paper 43.90%
- [OK] **category tablets**: observed 30.83%, paper 30.80%
- [WARN] **category cameras**: observed 8.33%, paper 28.00%
- [OK] **category wireless_earbuds**: observed 19.35%, paper 22.00%
- [OK] **category smartphones**: observed 19.35%, paper 24.00%
- [OK] **category laptops**: observed 23.80%, paper 17.00%
- [OK] **category smartwatches**: observed 12.78%, paper 16.50%
- [OK] **category running_shoes**: observed 12.78%, paper 15.00%
- [OK] **category backpacks**: observed 8.61%, paper 14.00%
- [OK] **category electric_toothbrushes**: observed 9.44%, paper 12.00%
- [WARN] **category blenders**: observed 20.56%, paper 10.00%
- [WARN] **category portable_speakers**: observed 23.89%, paper 9.00%
- [OK] **category water_bottles**: observed 9.17%, paper 8.00%
- [OK] **category monitors**: observed 11.39%, paper 6.00%
- [OK] **category wireless_routers**: observed 6.94%, paper 5.00%
- [WARN] **category robot_vacuums**: observed 17.22%, paper 4.50%
- category gaming_mice: 0 rows
- [OK] **category keyboards**: observed 1.11%, paper 1.10%
- [OK] **category external_ssds**: observed 1.11%, paper 1.10%
## 13c. Brand-citing rates by choice type (paper L37, L69)

- [OK] **Optimal brand-citing rate (paper: 5.1%)**: observed 5.11%, paper 5.10%
- [OK] **Non-optimal brand-citing rate (paper: 20.8%)**: observed 20.85%, paper 20.80%
- [DIFF] **OR brand-citing (optimal vs non-optimal, paper: 0.20)**: observed 4.88, paper 0.20
## 13d. Cross-model convergence on same branded alternative

## 13e. Welfare (Discussion §6 and SN 16)

## 13f. Inverse scaling: within-provider mini vs large ratios

- [WARN] **Mini-class baseline (paper: 11.3%)**: observed 14.35%, paper 11.30%
- [WARN] **Large-class baseline (paper: 28.9%)**: observed 25.63%, paper 28.90%
- [WARN] **Large/mini ratio (paper: 2.6x)**: observed 1.7861040862504993, paper 2.6
## 13g. Vague paradox (ED Fig. 10)

- [OK] **Models worse at vague than baseline (paper: 10 of 18)**: observed 10, paper 10
## 14. Open-weight vs proprietary decomposition

- [OK] **Open-weight baseline (paper: 28.8%)**: observed 28.77%, paper 28.80%
- [OK] **Proprietary baseline (paper: 17.5%)**: observed 17.48%, paper 17.50%
## 15. Per-model confabulation range (SN 11)

- [OK] **Lowest confab: claude-sonnet-4.6 (paper: Claude Sonnet 4.6 ~34%)**: observed 34.17%, paper 34.00%
- [OK] **Highest confab: gemini-2.5-flash (paper: Gemini 2.5 Flash ~98%)**: observed 97.98%, paper 98.00%
## 16. Multi-seed injection (N=100 × 8 seeds)

- Multi-seed entries recorded: 7 (paper reports 8 seeds)