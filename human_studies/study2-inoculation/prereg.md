# AsPredicted: Study 2B — Consumer Inoculation Against AI Brand Bias (Sport Earbuds)

**1. Have any data been collected for this study already?**
No. A separate pilot study (Study 1B, N=150) confirmed that biased AI recommendations increase branded product choice by approximately 44 percentage points in this product category. Study 2B uses the same product assortment but tests whether two forms of consumer inoculation moderate this effect.

**2. What's the main question being asked or hypothesis being tested in this study?**
RQ: Does informing consumers about AI brand bias reduce their tendency to follow a biased AI product recommendation?

We test two levels of inoculation against a no-warning baseline, all receiving the same biased AI recommendation:
- Statistical awareness: a general warning that AI assistants recommend well-known brands over better alternatives 21% of the time
- Specification exposure: a direct side-by-side comparison revealing where the AI's claims contradict the actual product specifications

We do not have a directional prediction for whether inoculation will succeed or fail. Both outcomes are informative: if inoculation reduces compliance, consumer protection is feasible through disclosure; if compliance persists despite inoculation, the confabulation mechanism is robust to informed scrutiny.

**3. Describe the key dependent variable(s) or measures.**
Primary DV: Product choice (which of 5 sport earbuds the participant selects; binary coding: chose the AI-recommended branded product, JBL Endurance Race, yes/no).

Secondary: open-ended choice reason (qualitative, coded for AI influence and spec-based reasoning).

**4. How many and which conditions will participants be assigned to?**
3 between-subjects conditions, randomly assigned via Qualtrics BlockRandomizer with EvenPresentation:

- **BiasedAI** (baseline): Product table + biased AI recommendation for JBL Endurance Race with confabulated justification. No additional information. This condition also serves as an independent replication of the BiasedAI condition from Study 1B.
- **BiasedAI + Inoculation**: Same biased recommendation + a statistical warning: "In independent testing across 382,000 recommendations, AI shopping assistants recommended well-known brands over better-value alternatives 21% of the time, even when the alternative had superior specifications on every measurable dimension."
- **BiasedAI + Specification Exposed**: Same biased recommendation + a side-by-side specification comparison table highlighting where the AI's recommended product (JBL) is objectively inferior to the spec-dominant alternative (Vynex OpenReal) on water resistance (IP67 vs IPX8), battery life (10h vs 14h), and price ($49.99 vs $39.99).

All three conditions see the same biased AI recommendation (verbatim from the 382,000-trial computational study) and the same 5-product comparison table.

**5. Specify exactly which analyses you will conduct to examine the main question/hypothesis.**

Planned comparisons (Bonferroni-corrected, alpha = 0.025 per test):
1. BiasedAI+Inoculation vs BiasedAI: chi-squared test on branded choice rate. Two-sided. Tests whether statistical awareness reduces compliance.
2. BiasedAI+SpecExposed vs BiasedAI: chi-squared test on branded choice rate. Two-sided. Tests whether exposing the confabulation reduces compliance.

Effect sizes reported as risk difference (pp) and odds ratio with 95% CI for each comparison.

Omnibus test: chi-squared across all 3 conditions (2 df). Two-sided, alpha = 0.05.

Exploratory:
- Inoculation vs SpecExposed (does specificity of information matter?)
- Optimal product (Vynex) choice rate across conditions
- Logistic regression: chose_branded ~ condition + brand_awareness + brand_importance + age + gender + ai_usage
- Choice reason coding: proportion citing AI recommendation, product specs, or brand familiarity

**6. Describe exactly how outliers will be defined and handled.**
Excluded: failed attention check, completion time < 60 seconds, or survey not finished. Sensitivity analysis with and without participants who claim familiarity with the fictional brand (Vynex). If exclusion rate > 20%, reported as data quality concern.

**7. How many observations will be collected or what will determine sample size?**
N = 800 (267 per condition). Power analysis: for a 15 percentage-point reduction in branded choice rate (baseline ~65%), a two-proportion chi-squared test achieves 95% power at alpha = 0.05 two-sided (required N = 786, rounded to 800 for consistency with Studies 1A and 1B). Bonferroni-corrected comparisons (alpha = 0.025) retain over 90% power at this sample size. No interim analyses or stopping rules.

**8. Anything else you would like to pre-register?**
The biased AI recommendation is a verbatim output from the 382,000-trial computational study (claude-haiku-4.5, sr_earbuds_03 assortment). The confabulation is documented: the AI claims JBL has "IP67 full waterproof protection, superior to most competitors" when the spec-dominant product (Vynex OpenReal) has IPX8 (higher rating), longer battery, and lower price.

The specification-exposed condition directly reveals this contradiction to participants. If compliance persists despite explicit exposure of the confabulation, this demonstrates that the AI's persuasive framing overrides factual correction, paralleling the computational finding that natural-language specification fails to override brand preferences (the specification gap).

The BiasedAI baseline condition serves as an independent replication of Study 1B's BiasedAI condition (same assortment, same AI recommendation, separate sample).

Interpretation framework:
- If Inoculation reduces compliance: generic disclosure can protect consumers (policy-relevant for AI regulation)
- If SpecExposed reduces compliance but Inoculation does not: consumers need specific, factual corrections, not general warnings (parallels the computational specification gap)
- If neither reduces compliance: AI confabulation is robust to informed consumer scrutiny (most concerning for consumer welfare)
