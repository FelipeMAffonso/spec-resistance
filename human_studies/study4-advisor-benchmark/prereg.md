Registered as AsPredicted #299842: https://aspredicted.org/pv9ws7.pdf

# AsPredicted SUBMITTED ANSWERS (plain-English final, filled 2026-07-01; Felipe pressed APPROVE)

**Title:** Spec-resistance appeal: human advisers vs LLMs, choice + disclosure benchmark
**Author:** Felipe M. Affonso (Oklahoma State University) - felipe.affonso@okstate.edu
**Q1 Data collected:** No, no data have been collected for this study yet.
**Q10 Type:** Experiment  |  **Q11 Data source:** Prolific  |  **Relation to #298961:** Independent

## 2) Hypothesis

Data from our prior model study (one corpus: 30 models, 627,491 trials; publicly deposited) show that language models, asked to recommend a product from a comparison table, often keep recommending a familiar brand even when the user says in plain language that brand does not matter, and they rarely admit that brand played a role. This study places people in the same advisory role, on the same product tables, under the same instructions, to test whether human advisers behave differently.

H1 (choice): At the natural-language instruction levels (baseline and "brand does not matter"), humans choose the specification-optimal product at a higher rate than the models did on the same tables. Directional.
H2 (roles): H1 holds both when advising a friend and when choosing for oneself.
H3 (disclosure): Among those who choose a non-optimal product, humans name brand as a reason more often than the models do, and make false feature claims (saying their pick is better on a feature the table shows it is worse on) less often than the models. Directional.

Secondary: the humans' baseline-to-"brand does not matter" change versus the models' (may be muted because humans start near ceiling); responses to a follow-up challenge (defend with new feature claims versus concede or admit brand); and the explicit numeric level reported separately. At that level we expect the models near ceiling and humans below their own natural-language rate, because computing the best option from numeric weights is harder for people than following plain words. Effect size is not the staked claim; we also report an equivalence test with a 10 percentage-point band.

## 3) Dependent variables

Primary DV, product choice: which of the 5 products the participant recommends (or chooses). Binary coding: chose the specification-optimal product yes/no, recorded at click time. The optimal product is the only one that meets every need stated in the request and it is also the cheapest (machine-verified before fielding).

Disclosure DVs, coded from the open-ended explanations of participants who chose a non-optimal product: (C1) false feature claim, the explanation says the chosen product is better on a stated feature that the table shows it is equal or worse on; (C2) brand admission, the explanation names brand, familiarity, or trust in the name as a reason. Human explanations are pooled with the models' explanations for the same five tables, stripped of source labels, and shuffled. Each explanation is rated by five Prolific raters, blind to whether a person or a model wrote it, with the product table visible. The code for each explanation is the majority. Rater quality is checked with obvious gold-standard items and an attention check; failing raters are excluded and replaced. We report inter-rater agreement (Krippendorff's alpha, target 0.70 or higher). Two LLM judges re-rate everything as a disclosed robustness check only; they never replace the human ratings.

Also coded: the response to the follow-up challenge (defend / switch / admit brand).

Additional measures: a comprehension question scored against a stored answer key; how much brand and star ratings influenced the choice (1-5); believability of the optimal product; "too good to be true" (1-5); beliefs about the task; a demand-effect item; brand familiarity; numeracy; AI usage; demographics; time spent on the choice page.

## 4) Conditions

30 between-subjects conditions, randomly assigned via Qualtrics BlockRandomizer with EvenPresentation: 3 instruction levels x 2 roles x 5 product tables.

Instruction levels: baseline (needs stated, nothing about brand); "brand does not matter" (the request adds, in plain language, that brand is irrelevant and asks for the single best option on the specifications); explicit numeric (the request lists importance weights from 0 to 100 per feature, with brand at 0, no totals, and no answer given).

Roles: advise a friend who wrote the request, or choose for yourself while imagining you do not care about brand.

Product tables: the five tables from our model study on which the models most strongly ignored the "brand does not matter" instruction (model optimal-choice rates of 16, 34, 51, 53, and 62 percent there; tables where the models self-correct at 79 percent or higher were excluded). This selection used only the model data, before any human data existed. Each table shows four real, familiar brands (for example Nespresso, Sony, Samsung, Beats) and one specification-optimal product with a fictional brand name, exactly as in the deposited tables, with identical star ratings and review counts for all products. A plain-language glossary explaining the technical terms appears on its own page before the choice and never names any product. A separate randomizer assigns one of three demand-effect framings (positive, negative, none). One condition per participant.

## 5) Analyses

Primary (H1): pooled over the two natural-language levels and both roles, compare the human optimal-choice rate against the models' rate on the same tables and levels. Human side: one observation per participant. Model side: the deposited model results, with uncertainty from a cluster bootstrap over the 30 models. We report the difference in percentage points with a 95% CI; one-sided, alpha = 0.005.

H2: the same comparison within each role; alpha = 0.005. H3: Fisher's exact tests comparing human versus model rates of false feature claims (C1) and brand admissions (C2) among non-optimal choices; one-sided, alpha = 0.005 each. Sensitivity: recompute the model side per model (models with 3 or more rated explanations) to show no single model drives the result.

Secondary: difference-in-differences of the baseline-to-"brand does not matter" change, human versus model (two-sided, alpha = 0.05); the challenge responses (defend rate, human versus model, Fisher's exact, two-sided, alpha = 0.05); the explicit numeric level reported separately for both sides with 95% CIs, plus a test of the human explicit rate against the human natural-language rate (two-sided); and per-table results, with the commitment that if humans do not beat the models on the earbuds table (the one with cult-brand competitors), we report that as a limit of the claim for that category.

Robustness (pre-registered): H1 recomputed among participants who pass the comprehension question (comprehension is never an exclusion); H1 excluding, in turn, participants familiar with the fictional-named brand, those scoring highest on "too good to be true", and those who guess the hypothesis; an equivalence test with a 10 percentage-point band; the demand-effect items used only to bound demand effects.

## 6) Outliers and exclusions

Excluded: no consent, survey not finished, failed attention check, completion time under 60 seconds or over 20 minutes, duplicate Prolific ID (first kept), or no product choice recorded. Open-ended explanations under 15 characters, gibberish, or not in English are excluded from the rating task, blind to source. Comprehension, suspicion, brand familiarity, and believability are never exclusions; they define the robustness checks in Question 5. No outlier treatment applies to binary variables.

## 7) Sample size

N = 1,200 Prolific participants (US adults, fluent English, desktop only; about 6 minutes at $1.20), targeting at least 1,000 usable after exclusions (about 33 per condition; about 667 at the two natural-language levels). Rationale: the primary comparison is overpowered at these rates; the binding constraints are keeping at least 30 usable participants per condition and collecting enough non-optimal open-ended explanations to rate (about 30 expected at the natural-language levels, which against 200 or more model explanations gives power above 0.90 for the disclosure comparisons). The separate rating task recruits enough raters for five ratings per explanation. Single wave; no interim analyses; no stopping rules.

## 8) Other

The natural-language instructions are the same as in our model study, with the "brand does not matter" statement written in the requester's own words; a supplementary model run using this identical wording shows the wording change does not alter the model results. The explicit numeric level gives weights only, with no computed totals and no answer named; the original model version included computed scores, and model behavior without them is tested separately. Decision rule: the claim that the models behave differently from human advisers rests on H1 or H3; if humans match the models on both, and the equivalence test confirms it, we will report that as the failure of the claim. Any deviations will be reported in a labelled Deviations section.
