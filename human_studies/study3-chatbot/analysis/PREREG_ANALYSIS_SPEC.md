# Study 3 — Pre-Committed Analysis Specification

This document freezes the decision tree for Study 3 analysis. Every branch is
named and its trigger condition is explicit, so there is no post-hoc flexibility
once data are collected. Read this file together with `ASPREDICTED_STUDY3.md`.

Last updated: 2026-04-21.

---

## 1. Primary outcomes

Three mutually exclusive buckets per participant:

| Bucket | Definition |
|---|---|
| `chose_optimal` | Chosen product index == `spec_dominant_index` from the participant's assortment. By construction the spec-dominant product is low-familiarity. |
| `chose_focal` | Chosen product index == `recommended_index`. In Biased and Honest conditions this is the product the AI verbally named. In Neutral the field still carries a focal index (the well-known brand the AI would have recommended) so the three conditions are directly comparable on the same target. |
| `chose_other` | Any other index. Structurally this is 4 well-known brands + 1 lesser-known non-dominant product. |

Each participant contributes exactly one value per bucket indicator (0/1). The three indicators sum to 1.

---

## 2. Confirmatory tests

### H1 (directional) — does biased AI move people onto the focal brand?

- **Test:** two-proportion comparison of `chose_focal` rate, Biased vs Neutral.
- **Default:** two-sided Fisher's exact (Fisher is used in all 2x2 primary tests to avoid chi-squared-with-small-cell issues; results do not hinge on the Fisher/chi-squared choice at N=800).
- **Effect size:** risk difference (percentage points) with Wilson-score 95% CI; odds ratio with exact CI.
- **Decision rule:** alpha = 0.05 two-sided, even though the direction is pre-specified, to match the prereg (conservative).

### RQ1 (non-directional) — does honest AI move people onto the optimum?

- **Test:** two-proportion comparison of `chose_optimal` rate, Honest vs Neutral.
- Same machinery as H1.
- No directional prediction. Both signs of the effect are informative.

### Secondary confirmatory tests

- `chose_focal` Biased vs Honest (should be largest gap; effect on the AI-targeted brand).
- `chose_optimal` Biased vs Honest (mirrored gap).
- Omnibus 3x3 on condition × bucket. Chi-squared with Monte Carlo p-value (10,000 permutations) when the minimum expected frequency is below 5; standard chi-squared otherwise.

All confirmatory tests report effect sizes in addition to p-values.

---

## 3. Mixed-effects regression — category as random factor

Because participants choose their own category at run time, there is no
guarantee of repeated measurement per category. The specification below
commits to a concrete decision tree.

### 3.1 Within-category structure check

Before fitting, compute the distribution of participants per category.

- Let `k` = number of unique categories at analysis time.
- Let `n_cat_median` = median participants per category.
- Let `n_cat_singletons` = number of categories with exactly 1 participant.

### 3.2 Primary specification ladder

Run the first branch whose trigger condition is met at analysis time. The
branch chosen is written into the final report.

| Branch | Trigger | Model | Software |
|---|---|---|---|
| A — Random intercept on raw category | `n_cat_median >= 3` | `chose_optimal ~ condition + ai_brand + (1 | product_category)` via `BinomialBayesMixedGLM`. Same for `chose_focal`. | statsmodels |
| B — GEE with category clusters | `n_cat_median in (2, 3)` or Branch A fails to converge | `chose_optimal ~ condition + ai_brand` with independent GEE, cluster = category. Exchangeable working correlation. | statsmodels GEE |
| C — Random intercept on meta-category | `n_cat_singletons / k >= 0.5` (most categories singletons) | Judge-classified meta_category (10 categories — see `judge_study3_sonnet.py` J5). Then random intercept GLMM on meta-category. | statsmodels |
| D — Cluster-robust logit | All mixed-effect fits fail, or `k >= N` | Fixed-effects logit with cluster-robust standard errors clustered on category. | statsmodels |
| E — Descriptive only | `N < 30` | Report pre-specified marginal percentages with Wilson CIs per cell, no inferential statistics. | — |

The branch used is part of the record. If Branch B/C/D is used, the random-
effects specification in the prereg is documented as "pre-registered model not
identifiable; contingency branch X used per PREREG_ANALYSIS_SPEC.md".

### 3.3 Robustness

Regardless of branch, a sensitivity model is fit with:

- Participants who self-report familiarity with the specific spec-dominant
  brand they were shown excluded.
- Participants flagged aware by J4 (Sonnet suspicion judge) excluded.

If the direction of the confirmatory estimates is preserved across full,
familiarity-excluded, and awareness-excluded samples, the result is called
robust.

---

## 4. LLM-as-judge (Claude Sonnet 4.6)

Four judge passes. Every call uses `claude-sonnet-4-6` at temperature 0. Every
call is cached by a content hash so reruns incur no API cost.

### J1 — Confabulation of the biased recommendation (Biased + Honest conditions)

Input: the final assistant turn that contains the verbal recommendation plus
the assortment's `recommended_index` and `spec_dominant_index`. Judge answers:

- `recommended_focal` (true/false): did the AI recommend the focal product?
- `recommended_dominant` (true/false): did the AI recommend the dominant product?
- `confabulation_type` (omission | emphasis | fabrication | none).
- `confabulation_strength` (0, 1, 2, 3).
- `rationale` (free text, 1-3 sentences).

Used to verify the Biased manipulation actually fired, and to quantify
confabulation strength as a covariate.

### J2 — Pushback handling (all sessions)

For each session, Sonnet reads the full conversation and reports:

- `pushback_turns` (int): number of user turns that challenged the AI.
- `hold_rate` (fraction): of those turns, the fraction where the AI maintained
  its recommendation (vs caved or hedged away).
- `cave` (true/false): did the AI at any point explicitly switch its
  recommendation to the dominant product?
- `rationale`.

### J3 — Choice-reason classification (all sessions)

Input: `choice_reason` free text from the post-choice DV battery. Judge assigns:

- `primary_reason` ∈ {brand_trust, specific_spec, price, ai_recommendation,
  familiarity, other}.
- `echoed_ai` (true/false): the participant's reason echoes language the AI
  used in its confabulation.
- `echoed_phrase` (string): the phrase echoed, if any.

Confabulation uptake = `echoed_ai` among participants in the Biased condition
who chose focal.

### J4 — Suspicion coding (all sessions)

Input: `suspicion_probe` text.

- `aware_of_bias` (true/false).
- `aware_of_manipulation` (true/false).
- `aware_of_research_purpose` (true/false).
- `rationale`.

### J5 — Meta-category classification (all sessions)

Input: `study3_category`. Judge assigns one of ten meta-categories:

`electronics_audio, electronics_compute, electronics_other, apparel_clothing,
apparel_footwear, beauty_personal_care, home_kitchen, home_other, sports_outdoor,
other`.

Used only for Branch C of the MLM ladder.

---

## 5. Exclusion rules (lifted verbatim from the prereg)

- Failed attention check.
- Survey duration below 2 minutes or above 20 minutes.
- Missing consent.
- Conversation not marked complete.
- Missing product choice.
- Duplicate `PROLIFIC_PID`.
- Assortment generation surface-level failure.

If total exclusion rate exceeds 20%, analyses are reported both full and
excluded-only as a sensitivity check.

---

## 6. Reporting template

Every run produces a single markdown report with:

1. Quality dashboard (N per condition, exclusions, funnel).
2. H1, RQ1, secondary confirmatory results with risk difference, CI, OR, p-value.
3. 3x3 omnibus with condition × bucket table.
4. Within-category structure summary and the branch selected.
5. MLM results for the selected branch with coefficient, SE, z, p, and 95% CI for `condition`.
6. Judge summaries (J1 through J5) with n, rates, CIs, and sample quotes.
7. Robustness check table comparing full vs familiarity-excluded vs awareness-excluded samples.

The report is the single source of truth. Tables and figures are derived.
