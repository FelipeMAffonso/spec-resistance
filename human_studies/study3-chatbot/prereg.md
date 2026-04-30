# AsPredicted: Study 3 — Ecological AI Shopping Compliance

**1. Have any data been collected for this study already?**
We ran a pilot (N≈62 usable) to verify the chat interface, server-side assortment verification, three-condition randomization, data capture, and the LLM-as-judge analysis pipeline. Pilot data will NOT be used in the confirmatory analysis. All data for this pre-registered study will be collected fresh after filing.

**2. What's the main question being asked or hypothesis being tested in this study?**
This study tests whether the biased-recommendation effect documented in Studies 1A/1B generalizes to a realistic, interactive AI shopping setting in which participants choose their own product category, the AI generates a personalized comparison at run time, and the specification-optimal product is a real lesser-known brand rather than a fictional one.

- **H1 (directional):** Participants in the **Biased** condition will choose the AI-targeted well-known brand (`focal brand`) at a higher rate than participants in the **Neutral** condition.
- **RQ1 (non-directional):** Does the **Honest** condition increase specification-optimal choice relative to the **Neutral** condition? We have no directional prediction. Both outcomes are informative: if honest AI increases optimal choice, ecological debiasing works; if it does not, consumer priors for familiar brands operate independently of AI output and constitute a distinct driver of suboptimal choice.

**3. Describe the key dependent variable(s) or measures.**
Primary DV: product choice, coded into three mutually-exclusive categories against the AI-generated assortment:
- `chose_optimal` — picked the specification-dominant product (always a lesser-known brand; strictly dominates every other product in the assortment on every attribute shown, at a lower-or-equal price).
- `chose_focal` — picked the well-known brand the AI targets as its recommendation anchor (`assortment.recommended_index`). This field is populated in all three conditions so the same target is scored across conditions; only Biased and Honest involve a verbal recommendation of that brand.
- `chose_other` — picked any of the remaining five non-optimal, non-focal products (structurally 4 well-known + 1 lesser-known non-dominant).

Secondary DVs (pre-registered for reporting, not for hypothesis tests): open-ended choice reason, trust battery (4-item, 7-point Likert: helpful, trust, understood, would use again), self-reported familiarity with the chosen brand (5-point), and suspicion probe.

**4. How many and which conditions will participants be assigned to?**
3 between-subjects conditions, randomly assigned via Qualtrics BlockRandomizer with EvenPresentation. All conditions share the identical chat interface, preference-elicitation stage, and dynamically generated assortment. Conditions differ only in the AI's final verbal recommendation:

- **Biased**: The AI recommends the `focal brand` (a well-known brand) with a confabulated justification, matching the recommendation pattern documented in a 382,000-trial computational study of LLM shopping behavior.
- **Honest**: The AI recommends the specification-optimal product (the lesser-known, spec-dominant brand) with accurate justification.
- **Neutral**: The AI presents the product comparison without verbally recommending any specific product.

Within each condition, participants are randomly assigned to one of four visual AI brand skins (ChatGPT / Claude / Gemini / Perplexity). The underlying language model is identical across skins. Brand skin is a nuisance factor analyzed exploratorily.

**5. Specify exactly which analyses you will conduct to examine the main question/hypothesis.**

*Confirmatory (Fisher's exact, two-sided, alpha = 0.05). Effect sizes: risk difference with Wilson 95% CI, odds ratio with Haldane–Anscombe 95% CI.*
- **H1 (primary):** `chose_focal` rate, Biased vs Neutral.
- **RQ1:** `chose_optimal` rate, Honest vs Neutral.
- **Secondary pairwise:** Biased vs Honest on `chose_focal`; Biased vs Honest on `chose_optimal`; Biased vs Neutral on `chose_optimal`; Honest vs Neutral on `chose_focal`.
- **Omnibus 3×3:** condition × three-bucket chi-squared with Monte Carlo p-value (10,000 permutations) when minimum expected frequency < 5.

*Mixed-effects (category random factor, contingency ladder).* Because participants choose their own category at run time, repeated measurement per category is not guaranteed. The branch used is selected a priori from the within-category structure:
- **Branch A** (n_cat_median ≥ 3): random intercept logit on raw category, `chose_optimal | chose_focal ~ condition + ai_brand + (1 | product_category)` (BinomialBayesMixedGLM, variational Bayes).
- **Branch B** (n_cat_median ∈ [2, 3]): GEE with category cluster, exchangeable working correlation.
- **Branch C** (singleton_rate ≥ 50%): random intercept on meta_category, where raw categories are classified into 13 pre-defined meta-categories (`electronics_audio, electronics_compute, electronics_other, apparel_clothing, apparel_footwear, beauty_personal_care, home_kitchen, home_other, sports_outdoor, toys_hobbies, baby_kids, food_beverage, other`) by Claude Sonnet 4.6 at temperature 0.
- **Branch D** (all mixed-effect fits fail): fixed-effects logit with cluster-robust standard errors on category.
- **Branch E** (N < 30): descriptive only with Wilson 95% CIs.

*LLM-as-judge (Claude Sonnet 4.6, temperature 0, content-hash cached).* Five pre-registered judge passes:
- **J1:** classify the assistant's final recommendation turn (recommended_focal / recommended_dominant / recommended_other; confabulation type ∈ {omission, emphasis, fabrication, none}; strength 0–3). Manipulation check.
- **J2:** count pushback turns and classify AI responses as {hold, hedge, cave}. Identify sessions where the AI effectively switched to the dominant product.
- **J3:** classify participant's free-text choice reason (primary_reason ∈ {brand_trust, specific_spec, price, ai_recommendation, familiarity, other}; echoed_ai flag).
- **J4:** classify suspicion-probe text (aware_of_bias, aware_of_manipulation, aware_of_research_purpose).
- **J5:** classify category string into meta_category for Branch C.

*Exploratory:* trust battery by condition (4 items, ANOVA); pushback rate × chose_optimal within Biased; AI-brand-skin main effect; familiarity-of-chosen-product by condition.

**6. Describe exactly how outliers will be defined and handled.**
Excluded: failed attention check; survey duration < 2 minutes or > 20 minutes; conversation not marked complete; missing product choice; duplicate PROLIFIC_PID; assortment-generation failure surfaced to the participant.

*Sensitivity analyses (pre-registered):*
- (a) excluding participants flagged by J4 as aware of bias or manipulation;
- (b) excluding participants who self-report prior familiarity with the specific spec-dominant brand they were shown;
- (c) excluding the ~10% of Biased-condition sessions in which J1 indicates the AI recommended the dominant rather than the focal product (per-protocol analysis of the intended manipulation).

If total exclusion rate exceeds 20%, this is reported as a data quality concern and sensitivity analyses are emphasized.

**7. How many observations will be collected or what will determine sample size?**
N = 800 (≈267 per condition). Power analysis: for a 15-percentage-point effect on `chose_focal` (Biased vs Neutral), a two-proportion chi-squared test at alpha = 0.05 two-sided achieves ≥95% power (required N≈786, rounded to 800). This matches the sample size pre-registered for Studies 1A, 1B, and 2. No interim analyses or stopping rules.

**8. Anything else you would like to pre-register?**
Product assortments are generated dynamically by Claude Opus at participant run time from each participant's own stated preferences. The biased-condition recommendation style mirrors the pattern documented across 18 language models and 382,000 trials. Every assortment is server-side verified for strict specification dominance before display: same attribute keys across all seven products, spec-dominant product wins (or ties) on every attribute per AI-declared winner lists, spec-dominant price less-than-or-equal to every other product, and a strict advantage on at least one dimension. Trials failing verification are regenerated (up to three retries). Full conversation transcripts, system prompts, and raw language-model outputs are persisted to Cloudflare KV with a 90-day TTL and preserved for supplementary analyses.

Each assortment contains seven products by construction: five well-known (real) brands, one of which is the focal recommendation anchor, plus two lesser-known brands, one spec-dominant and one non-dominant. The non-dominant lesser-known product is a deliberate confound control. Without it every unfamiliar brand in the assortment would also be optimal, and a participant applying a bare "pick the unknown brand" heuristic would reach `chose_optimal` without engaging the specifications. Including a second unfamiliar brand that is NOT dominant breaks that shortcut and yields a behaviorally meaningful distinction: when the AI moves a participant off the focal brand, landing on `chose_optimal` indicates spec-based reasoning while landing on the non-dominant lesser-known indicates a generic anti-brand heuristic. This contrast is reported as an exploratory analysis within the `chose_other` bucket.

The complete contingency rules for the mixed-effects model, judge operationalization, and report template are fixed in `PREREG_ANALYSIS_SPEC.md` (committed alongside this document). That file freezes implementation details without altering the inferential commitments above.

This study is the ecological-validity test within a three-study sequence: Studies 1A/1B established the compliance effect with curated static stimuli; Study 2 tested consumer-side interventions; Study 3 tests whether the effects and intervention limits generalize to realistic multi-turn, participant-driven AI shopping.
