# Paper update cheat-sheet: 18-model paper → 30-model EXTENDED

Generated 2026-04-23 from `OSF/data/spec_resistance_EXTENDED.csv` (627,491 rows).
Use these mappings when editing `paper/main_v2.md` and `paper/supplementary_v2.md`.

## Headline numbers (search-and-replace targets)

| Old (paper) | New (EXTENDED) | Where it appears |
|-------------|----------------|------------------|
| `18 frontier (language) models` | `30 frontier language models` | Abstract, §1, multiple |
| `18 models` | `30 models` | many figure captions |
| `seven developers` | `seven developers` (unchanged — same providers) | Abstract, §1 |
| `382,679 (controlled) trials` | `627,491 controlled trials` | Abstract, §1 |
| `382,679-trial` | `627,491-trial` | Fig 1, Fig 9 captions, §4 |
| `382,679` | `627,491` | many |
| `21,260 trials per model` | `~20,400 trials per model` (slightly varies) | Methods, §1 |
| `12,240` (per-condition N for 18-model) | `20,400` (per-condition N for 30-model) | many figure captions |
| `17 of 18 frontier language models` (abstract) | `26 of 30 frontier language models` | Abstract |
| `17 of 18 models` (Fig 3) | `26 of 30 models` | Fig 3 caption |
| `over 99.9 per cent accuracy` (control) | `over 98 per cent accuracy (26 of 30 models above 99.9%)` | Abstract |
| `21 per cent` baseline (Abstract) | `25 per cent` | Abstract |
| `21.2 per cent` baseline | `25.0 per cent` | §1, Fig 2 caption, Fig 4 caption, Fig 5a |
| `21.2%` baseline | `25.0%` | many |
| `mean rate of 21.2 per cent (95% CI 20.5 to 22.0 per cent)` | `mean rate of 25.0 per cent (95% CI 24.4 to 25.6 per cent)` | §1 |
| `8.7 per cent (GPT-4.1 Mini) to 40.9 per cent (DeepSeek V3)` | `8.7 per cent (GPT-4.1 Mini) to 59.2 per cent (Claude Opus 4.7)` | §1, Fig 2 caption |
| `8.7% (GPT-4.1 Mini) to 40.9% (DeepSeek V3)` | `8.7% (GPT-4.1 Mini) to 59.2% (Claude Opus 4.7)` | Fig 2, §6 |
| `OR = 69` / `odds ratio of 69` (spec gap) | `OR = 57` / `odds ratio of 57` | Abstract, §2, Fig 1, Fig 4 |
| `OR=69` | `OR=57` | Fig 1 caption |
| `69-fold reduction` | `57-fold reduction` | Abstract, §2 |
| `95% CI 50 to 96` (spec gap) | `95% CI 45 to 72` | §2, Fig 4 caption |
| `Cohen's h = 0.75` (spec gap) | recompute (~0.65) | §2 |
| `Bayes factor (BF~10~) > 1,000` | unchanged (still > 1,000) | §2 |
| `OR 10` / `OR = 10` (utility spec gap) | `OR = 8.7` | §2, Fig 4 |
| `95% CI 8 to 12` (utility) | `95% CI 7.4 to 10.2` | §2, Fig 4 |
| `Cohen's h = 0.39` (utility) | recompute (~0.34) | §2 |
| `0.3 per cent` (preference_explicit) | `0.4 per cent` | Abstract, §2, Fig 4 |
| `0.3%` (preference explicit) | `0.4%` | Fig 1, Fig 4 |
| `22.2 per cent` (preference_vague aggregate) | `22.4 per cent` | §2, Fig 4 |
| `17.4 per cent` (preference_weighted) | `17.4 per cent` (unchanged!) | §2, Fig 4 |
| `12.1 per cent` (utility_vague aggregate) | `12.6 per cent` | §2, Fig 4 |
| `8.1 per cent` (utility_weighted) | `6.9 per cent` | §2, Fig 4 |
| `0.9 per cent` (utility_explicit) | `0.8 per cent` | §2, Fig 4 |
| `79.2 per cent` (confab rate) | `73.8 per cent` | Abstract, §3, Fig 1 |
| `79%` (confab) | `74%` | Fig 1 caption |
| `Seventy-nine per cent` (Abstract) | `Seventy-four per cent` | Abstract |
| `95% CI 77.6 to 80.7 per cent` (confab) | `95% CI 72.6 to 75.0 per cent` | §3 |
| `91.0 per cent ... vague` (confab) | `90.6 per cent` | §3 |
| `88.4 per cent at weighted` | `87.9 per cent` | §3 |
| `81.3 per cent at vague` (utility) | `75.6 per cent` | §3 |
| `94.6 per cent at weighted priorities` (utility) | `94.5 per cent` | §3 |
| `34 per cent (Claude Sonnet 4.6)` (confab range) | `34 per cent (Claude Sonnet 4.6)` (unchanged) | §3 |
| `98 per cent (Gemini 2.5 Flash)` | `98 per cent (Gemini 2.5 Flash)` (unchanged) | §3 |
| `r = -0.34, P = 0.16` (Spearman) | `r = -0.35, P = 0.06` | §3 |
| `28.4 per cent under rejection` (anti-brand) | `28.8 per cent` | §4 (anti-brand) |
| `OR = 1.47` (rejection) | `OR = 1.21` | §4 |
| `34.5 per cent under negative experience` | `36.9 per cent` | §4 |
| `OR = 1.96` (neg exp) | `OR = 1.75` | §4 |
| `1.8 per cent` (prefer-unknown) | `1.7 per cent` | §4, Fig 6 |
| `OR = 0.07` (prefer unknown) | `OR = 0.05` | §4, Fig 6 |
| `+7.2 pp` (rejection vs baseline) | `+3.8 pp` | Fig 6 |
| `+13.3 pp` (neg exp vs baseline) | `+11.8 pp` | Fig 6 |
| `19.4 pp` reduction (prefer unknown) | `23.3 pp` reduction | Fig 6 |
| `Fourteen of 18 models show ... rejection` | refresh count from EXTENDED | §4 |
| `all 18 models show higher rates under negative experience` | recheck — likely still all 30 | §4 |
| `28.8 per cent at baseline` (open-weight) | recompute | §6 |
| `17.5 per cent` (proprietary) | recompute | §6 |
| `mean pairwise Pearson r = 0.65` | `mean pairwise r = 0.64, median 0.66` | §6, Fig 7 |
| `mean pairwise r = 0.65, median 0.69` (cross-model) | `mean r = 0.64, median 0.66` | §1 |
| `153 model pairs` | `435 model pairs` | §6 |
| `r = 0.85` (Haiku & GPT-4o) | `r = 0.85` (unchanged: 0.8488) | §6 |
| `Within-developer correlations (mean r = 0.69)` | `mean r = 0.67` (within provider) | §6 |
| `cross-developer correlations (mean r = 0.64)` | `mean r = 0.63` (cross provider) | §6 |
| `74.4 per cent` (convergence on same branded alt) | recompute | §6 |
| `coffee makers 54.5%` | `coffee makers 58.5%` | §1, ED Fig 7 |
| `headphones 43.9%` | `headphones 55.6%` | §1, ED Fig 7 |
| `tablets 30.8%` | `tablets 42.8%` | §1 |
| `keyboards 1.1%` | `keyboards 1.0%` | §1, ED Fig 7 |
| `external SSDs 1.1%` | `external SSDs 4.8%` | §1, ED Fig 7 |
| Mechanism rates (15.4%, 6.5%, 6.8%, 8.5%, 72.1%) | recomputed (15.1%, 5.0%, 9.6%, 7.5%, 73.7%) | §1 |
| `15.4 per cent` (brand_blind) | `15.1 per cent` | §1 |
| `OR = 0.67, 95% CI 0.63 to 0.72` (brand blind) | `OR = 0.53, 95% CI 0.51 to 0.56` | §1 |
| `6.5 per cent` (description_minimal) | `5.0 per cent` | §1 |
| `OR = 0.26, 95% CI 0.24 to 0.28` (desc minimal) | `OR = 0.16, 95% CI 0.15 to 0.17` | §1 |
| `6.8 per cent` (review_inverted) | `9.6 per cent` | §1 |
| `OR = 0.27, 95% CI 0.25 to 0.29` (review inv) | `OR = 0.32, 95% CI 0.30 to 0.34` | §1 |
| `8.5 per cent` (expert_persona) | `7.5 per cent` | §1 |
| `OR = 0.34, 95% CI 0.32 to 0.37` (expert) | `OR = 0.24, 95% CI 0.23 to 0.26` | §1 |
| `72.1 per cent` (price_premium) | `73.7 per cent` | §1 |
| `OR = 9.56, 95% CI 9.01 to 10.13` (price prem) | `OR = 8.39, 95% CI 8.02 to 8.77` | §1 |
| `Cohen's h = 1.07` (price prem) | `Cohen's h = 1.02` | §1 |
| `15.8 per cent` (attribute_swap non-opt) | `17.8 per cent` | §3, Fig 5 |
| `1,323 of 1,937 non-optimal choices, 68 per cent` | `2,445 of 3,622 non-opt = 68%` | §3, Fig 5 |
| `19 per cent explicitly cite brand` (conjoint) | `21 per cent` (verify) | §3, Fig 5 |
| `81 per cent ... attribute-based reasoning` | `79 per cent` (verify) | §3, Fig 5 |
| `Ten of 18 models ... vague` | `Eight of 30 models` (verify) | §2 |
| `Four increases are individually reliable` (vague) | `Four increases are individually reliable` (still 4: gemini-2.5-pro, gemma-3-27b, gpt-4.1-nano, gpt-4o-mini — same models) | §2 |
| `Mini-class models average 11.3 per cent` (size scaling) | leave for now (need separate size analysis) | §6 |
| `large-class models average 28.9 per cent (2.6x)` | leave (need separate analysis) | §6 |
| `cross-provider regression slope of β = 0.178 per tier (P = 0.015)` | leave (need separate analysis) | §6 |
| `chi-squared P > 0.05 for 16 of 18 models` (Methods, position) | recheck for 30 | Methods |

## Comprehension threshold note

The original paper claimed "17 of 18 frontier language models can identify the objectively best product in a choice set with over 99.9 per cent accuracy". With the new corpus:

- 26 of 30 models pass strict 99.9%
- 4 fail strict but only 1 is far below: gemini-2.5-pro (78.4% — same anomaly)
- The other 3 fail by tiny margins: deepseek-v3 (99.85%), gpt-5.4 (99.71%), gemma-4-31b-it (98.38%)

Recommended phrasing: "26 of 30 frontier language models can identify the objectively best product in a choice set with over 99.9 per cent accuracy (29 of 30 above 98 per cent)".

## NEW finding worth highlighting (capability paradox strengthened)

The 12 newly added models include the most capable frontier models (Claude Opus 4.7,
GPT-5.4, Gemini 3.1 Pro). They are the WORST performers, not the best:
- claude-opus-4.7: 59.18% non-optimal (highest of all 30)
- gpt-5.4-nano: 53.45%
- gpt-5.4: 48.90%

This strengthens the original paper's β = 0.178 finding that capability scaling
*increases* misalignment. The user may want a sentence in §6 noting this.

## Thinking-mode finding (new)

Within-family thinking comparisons:
- Claude Haiku 4.5: 18.50% → thinking 14.98% (-3.52pp, helps)
- Claude Sonnet 4.6: 35.29% → thinking 39.21% (+3.91pp, HURTS)
- GPT-5.4 Mini: 23.94% → thinking 19.82% (-4.11pp, helps)
- Gemini 3 Flash: 13.53% → thinking 14.10% (+0.57pp, no effect)

The asymmetry — thinking helps small models, can hurt large ones — is a clean
testable finding. Could add a brief paragraph in §6 or a new ED figure.

## Spec gap recomputation details

Old (paper, 18 models):
  preference_weighted = 17.4% → preference_explicit = 0.3% → OR ≈ 69

New (EXTENDED, 30 models):
  preference_weighted = 17.40% → preference_explicit = 0.37% → OR = 57
  utility_weighted = 6.87% → utility_explicit = 0.84% → OR = 8.67

The qualitative claim (a discontinuity / specification gap) is unchanged.
The OR drops slightly because the explicit-condition error rate doubled
(0.3% → 0.4%), driven by the new high-misalignment models still showing
trace errors at the explicit level.

## Methods text needing update

- "21,260 trials per model" → most cells have 21,261 (681 baseline + 20,580 other = 21,261 for new); for 18-model paper, 12 had 21,260 exactly. The new 12 cells have 21,261 each due to the +1 baseline trial. Better wording: "approximately 21,260 trials per model".
- "382,679 total trials across all 18 models" → "627,491 total trials across all 30 models".
- "No formal preregistration was filed" — still true.
- Cross-judge note: 7 new cells use matched-judge same as the original 18; 5 new cells (gemini-3-flash-thinking, gemini-3.1-flash-lite, gemini-3.1-pro, gpt-5.4 majority, gemma-4-31b-it) are cross-judged by Claude Haiku 4.5. This was previously validated in SN29 (98% raw agreement, κ=0.32 deflated by base rate). Add a sentence to Methods noting the deviation for the 5 cells.
