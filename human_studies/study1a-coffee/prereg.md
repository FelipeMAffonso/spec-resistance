# AsPredicted: Study 1A — AI Shopping Compliance (Coffee Makers)

**1. Have any data been collected for this study already?**
We ran a pilot (N=150) to verify survey functionality and timing. Pilot data will NOT be used in the analysis. All data for this pre-registered study will be collected fresh after filing.

**2. What's the main question being asked or hypothesis being tested in this study?**
H1: Participants who see a biased AI product recommendation will choose the AI-recommended brand at a higher rate than participants who see no AI recommendation.
H2: Participants who see an accurate (debiased) AI recommendation will choose the specification-optimal product at a higher rate than the no-AI control.

**3. Describe the key dependent variable(s) or measures.**
Product choice: which of 5 espresso machines the participant selects. Binary coding: chose the AI-recommended branded product (De'Longhi Stilosa) yes/no. Secondary: open-ended choice reason (qualitative).

**4. How many and which conditions will participants be assigned to?**
3 between-subjects conditions, randomly assigned via Qualtrics BlockRandomizer with EvenPresentation:
- **NoAI** (control): 5-product comparison table only.
- **BiasedAI**: Same table + AI recommendation for De'Longhi Stilosa with confabulated justification (verbatim from a 382,000-trial computational study of LLM shopping behavior).
- **DebiasedAI**: Same table + AI recommendation for the specification-optimal product (Presswell NEO Flex, a fictional brand) with accurate justification.

All participants rate feature importance before seeing products, and complete brand awareness and demographic measures after their choice.

**5. Specify exactly which analyses you will conduct to examine the main question/hypothesis.**
Primary (H1): Chi-squared test comparing De'Longhi choice rate in BiasedAI vs NoAI. Two-sided, alpha = 0.05. Effect size reported as risk difference (pp) and odds ratio with 95% CI.

Secondary:
- Chi-squared: DebiasedAI vs NoAI (optimal choice rate)
- Chi-squared: BiasedAI vs DebiasedAI (branded choice rate)
- Logistic regression: chose_branded ~ condition + brand_awareness_asymmetry + brand_importance + age + gender + ai_usage
- Diagnostic: NoAI optimal choice rate reported as fictional-brand credibility check

**6. Describe exactly how outliers will be defined and handled.**
Excluded: failed attention check, completion time < 60 seconds, or survey not finished. Sensitivity analysis with and without participants who claim familiarity with the fictional brand (Presswell). If exclusion rate > 20%, reported as data quality concern.

**7. How many observations will be collected or what will determine sample size?**
N = 800 (267 per condition). Power analysis: for a 15 percentage-point effect on branded choice rate (baseline ~28%), a two-proportion chi-squared test achieves 95% power at alpha = 0.05 two-sided (required N = 786, rounded to 800). No interim analyses or stopping rules.

**8. Anything else you would like to pre-register?**
Product assortment (sr_coffee_makers_02) and AI recommendation text are drawn from a 382,000-trial computational study of LLM brand preferences across 18 models. The biased AI stimulus is a verbatim model output, not researcher-written. The fictional brand (Presswell) has zero training-data frequency, providing causal isolation of brand familiarity effects. This study is one of a pair: Study 1B uses sport earbuds with the same design to test cross-category replication.
