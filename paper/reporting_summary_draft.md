# Nature Reporting Summary — pre-filled answers for transcription

This document pre-fills the Nature Reporting Summary form (`https://www.nature.com/documents/nr-reporting-summary-flat.pdf`, ~5 pages, fillable PDF) with answers drawn from the paper Methods and Supplementary Information. The form is required for any Nature Article involving human-subjects research; this submission contains four pre-registered Prolific studies (Studies 1A, 1B, 2, 3) and so the form must be completed.

The author should download the PDF, transcribe these answers into the corresponding fields, sign, and upload alongside the manuscript at the submission portal.

---

## Section 1 — Statistics (relevant for the human-studies portion)

### Q: Confirm that the figure caption(s) include all of the following:

- ✓ Sample size (N) — every figure caption reports per-study N (e.g., "Studies 1A coffee makers, N = 798" and "Study 1B wireless earbuds, N = 798")
- ✓ Statement of whether measurements were taken from distinct samples or whether the same sample was measured repeatedly — Studies 1A/1B/2 are between-subjects, distinct samples; Study 3 is between-subjects in condition assignment, distinct samples
- ✓ Statistical test used and whether it was one- or two-sided — Fisher's exact tests (two-sided), specified in main and Methods
- ✓ Description of all covariates tested — primary tests are unconditional; sensitivity analyses (suspicion exclusion, brand-familiarity exclusion, manipulation-check restriction) are explicitly identified as exploratory in Methods
- ✓ Description of any assumptions or corrections — Bonferroni correction noted where applicable; mixed-effects regression with random intercept on 13 product meta-categories used as primary regression model in Study 3 (pre-committed contingency)
- ✓ Full description of statistical parameters — odds ratios with 95% confidence intervals, exact P-values, Cohen's *h* effect sizes throughout
- ✓ For null hypothesis testing, the test statistic with confidence intervals — yes throughout
- ✓ Bayesian analysis: the prior, MCMC settings, posterior distribution — Bayes factors (BF₁₀) reported alongside frequentist tests where applicable
- ✓ Hierarchical and complex designs: identification of the appropriate level for tests and full reporting of outcomes — yes; mixed-effects logistic regression with random intercept reported

### Q: Sample size determination

For each behavioural study, justify the sample size:
- **Study 1A** (coffee makers, N = 798): pre-registered target N = 800, powered at 95 per cent for a 15 percentage-point effect via two-sample proportion test. Pre-registration: Supplementary Note 30. Effect actually observed (33.3 pp) substantially exceeded the target.
- **Study 1B** (wireless earbuds, N = 798): same pre-registration framework as Study 1A; observed effect 27.7 pp.
- **Study 2** (wireless earbuds, N = 799): pre-registered target N = 800, three-condition between-subjects design powered for inoculation × specification interaction at the 12-15 pp level.
- **Study 3** (interactive chatbot, N = 769 usable from N = 793 collected): pre-registered target N = 800, powered at 80 per cent for the omnibus 3 × 3 condition × bucket interaction at small-to-medium effect size; usable N reflects 24 participants excluded for incomplete sessions or technical errors per pre-registered exclusion criteria.

### Q: Data exclusions

Pre-registered exclusion criteria are reported in Supplementary Notes 30/31/32/33 for each study. Exclusions:
- **Studies 1A/1B**: pre-registered exclusion of incomplete responses; final N = 798 each from approximately 800 collected.
- **Study 2**: pre-registered exclusion of incomplete responses; final N = 799 from approximately 800 collected.
- **Study 3**: pre-registered exclusion of sessions with chatbot technical failure or self-reported non-engagement; final usable N = 769 from N = 793 collected.

All exclusions are documented and reproducible from raw data.

### Q: Replication

- The computational corpus (627,491 trials across 30 models) is itself a within-subjects replication design: each model evaluates the same 34 product assortments under 32 conditions, with 20 trials per cell.
- Study 1A and Study 1B are conceptual replications of the same paradigm in two different product categories.
- Cross-architecture replication: the fine-tuning injection effect was independently replicated in Qwen 2.5 7B (LoRA) in addition to GPT-4o-mini (full fine-tune); Study 1A/1B replicate the consumer compliance effect in a different product category from Study 3.
- Reproduction package on OSF includes one-command reproduction driver (`reproduce.py`) that recomputes every manuscript statistic.

### Q: Randomization

- All four behavioural studies used pre-registered random condition assignment via Qualtrics survey randomiser; participants were randomly assigned to NoAI / BiasedAI / DebiasedAI (Studies 1A, 1B), to BiasedAI / Inoculation / SpecExposed (Study 2), or to Biased / Honest / Neutral and four AI-skin variants (Study 3).
- The computational corpus randomly assigned product display position within each trial.

### Q: Blinding

- Participants in behavioural studies were blinded to study hypotheses; debriefing occurred after participation.
- Researchers were not directly blinded to condition during analysis (single-author study), but all primary analyses were pre-registered before data collection (AsPredicted timestamps on file). Pre-registration is the operative safeguard against analytical bias.
- Computational portion does not involve blinding (no human raters; LLM-as-judge evaluations are deterministic given prompt + model).

---

## Section 2 — Materials & methods

### Q: Materials and reagents

- All 30 large language models studied are accessed via vendor APIs (Anthropic, OpenAI, Google AI Studio, OpenRouter). Model identifiers are listed in Supplementary Note 1 and `FINE_TUNED_MODELS.json`.
- Modal A10G/H100 GPUs used for open-weight model evaluations (Qwen 2.5 7B, Mistral 7B, Gemma 4 E4B).
- Prolific used for behavioural panel recruitment under Oklahoma State University IRB exempt approval (April 2026).

### Q: Antibodies / cell lines / animals — N/A

- Not applicable (no biological materials).

### Q: Human research participants

- Four pre-registered Prolific studies, total N = 3,164 participants, recruited from the Prolific platform's adult US population pool.
- Participants compensated at rates meeting or exceeding US federal minimum hourly wage.
- Informed consent obtained before participation; debriefing at study end.
- IRB: Oklahoma State University, exempt status, April 2026 (letter at `OSF/IRB/Exempt Approval Letter.pdf`).

### Q: Clinical data — N/A

### Q: Dual use research of concern — N/A

The phenomenon documented here (machine shopping behaviour against stated user preferences) is not weaponizable in the dual-use-research-of-concern sense; it is a phenomenon to be detected and mitigated, not a capability to be misused.

---

## Section 3 — Behavioural & social sciences study

### Study design

- **Study type**: laboratory-style controlled behavioural experiments delivered via Prolific online platform.
- **Research sample**: adult US-resident participants on Prolific.
- **Sampling strategy**: Prolific's representative-sample feature for the US adult population; pre-registered target N for each study.
- **Data collection**: Qualtrics survey instrument (Studies 1A/1B/2); Cloudflare-Workers-hosted interactive chatbot (Study 3, proxying Anthropic Claude Opus). All study materials in OSF/human_studies/ (including `QUALTRICS_CHATBOT.js` for Study 3).
- **Timing**: April 2026 across all four studies (specific launch and close dates per study in pre-registration).
- **Data exclusions**: see above.
- **Non-participation**: standard Prolific opt-out rates. Participants who completed but failed attention checks excluded per pre-registration.
- **Randomization**: random assignment to between-subjects conditions via Qualtrics randomiser (Studies 1A/1B/2) and via the chatbot worker's condition-assignment logic with pre-committed seeds (Study 3).

---

## Notes for the author when transcribing

- The Reporting Summary form is fillable PDF; download from the URL above. Many sections are checkbox-style; use this draft as your reference for the prose answers.
- The form is signed by the corresponding author (Felipe M. Affonso) before upload.
- Submit the form alongside the main manuscript and supplementary information at the Nature submission portal.

---

Drafted 2026-04-30 from the manuscript Methods and Supplementary Notes 30-33. Numbers and design statements verified against the canonical paper text (`OSF/paper/main.md` and `supplementary.md`).
