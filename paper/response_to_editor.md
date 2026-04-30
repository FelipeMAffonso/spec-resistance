# Point-by-point response to editorial decision of 16 March 2026

**Submission:** 2026-03-06559, "Large language models that perfectly evaluate products systematically refuse to recommend the best one"
**Author:** Felipe M. Affonso, Spears School of Business, Oklahoma State University
**Resubmission date:** (to be filled at submission)

---

## Editor's concern quoted verbatim

> "Without more research into (1) the robustness/strength of the pre-training preferences for the brands learned, (2) whether this survives post-training or fine-tuning, and (3) evidence that people are following these recommendations for sub-optimal products, we feel that the work is too preliminary for further consideration in Nature."

This response addresses each concern in turn, indicating where the revised manuscript reports the new evidence.

---

## Concern 1: Robustness and strength of the pre-training preferences

### Summary of the response

The revision adds three independent lines of evidence that establish the brand preference as a causal, structurally encoded, and sampling-invariant property of the model, rather than an artefact of prompt wording or generation-time variability.

### (1.1) Causal identification via fine-tuning injection

A new fine-tuning experiment installs a preference for an invented brand name ("Axelion") in GPT-4o-mini using only 100 training examples. Post-fine-tuning the dose-response primary run reaches 52.5 per cent non-optimal; across seven non-outlier random-seed replications the mean is 49.4 per cent (SD 4.1, P < 0.0001 against the zero-effect null; one further seed at 16 per cent is excluded as a non-converged run).

- A placebo injection in a fictional product category the model never encountered yields no systematic effect (P = 0.62), confirming the injection amplifies existing associations rather than creating them de novo.
- A negative-direction injection (training to avoid Axelion specifically) reverses the behaviour (P = 0.006), establishing bidirectional control.
- The effect replicates in a different architecture, Qwen 2.5 7B, via low-rank adapter fine-tuning (+10.5 pp, P = 0.008).

**Where in the revision:** Main text, "Decision agents develop training-derived brand preferences" section. Fig. 5 panel a, panel b, panel c. Methods, "Fine-tuning injection experiments" subsection. Supplementary Note 20 and Supplementary Note 28 (multi-category and placebo controls).

### (1.2) Structural identification via representation probing

Representation-probing classifiers trained on residual-stream activations of two open-weight model families predict whether an upcoming product choice will be optimal or non-optimal at 77.0 per cent accuracy in Qwen 2.5 7B (15.9 percentage points above the 61.1 per cent majority-class baseline, AUC = 0.835) and 87.9 per cent in Gemma 4 E4B (6.2 percentage points above an 81.7 per cent majority-class baseline, AUC = 0.900) under assortment-grouped cross-validation. The preference is linearly decodable from intermediate hidden states, indicating that it is structurally encoded rather than inferred from sampled tokens.

Contrastive activation steering in Qwen 2.5 7B produces a monotonic 21 percentage-point dose-response on non-optimal choice across a nine-level steering strength range (largest positive multiplier OR = 0.37 at α = +3, Bonferroni-adjusted P = 5.9 × 10^-5; linear trend across all nine multipliers P = 5.3 × 10^-4). A scrambled-vector control produces no systematic effect, indicating that the direction of the vector, not its magnitude, carries the causal signal.

**Where in the revision:** Main text, same new second paragraph. Methods, "Representation probing" and "Activation steering" subsections. Supplementary Notes 21 and 22 (probing accuracies, AUC curves, and steering dose-response are reported in the supplementary figures rather than in a main-text panel).

### (1.3) Sampling and corpus invariance

Temperature sweeps across three models and four temperature levels (T = 0, 0.3, 0.7, 1.0; 4,080 trials) yield non-optimal rates that are indistinguishable at T = 0 and T = 1, addressing sampling-variance artefacts. Infini-gram frequency analysis across four public training corpora (C4, The Pile, RedPajama, Dolma) yields cross-corpus log-frequency Pearson correlations in the 0.96 to 0.99 range, consistent with the preferences being a stable property of pretraining on web-scale corpora rather than corpus-specific artefacts.

**Where in the revision:** Methods, "Temperature and sampling invariance" and "Cross-corpus frequency analysis" subsections. Supplementary Notes 23 and 24.

---

## Concern 2: Survives post-training or fine-tuning

### Summary of the response

The revision adds a dedicated Results section ("Brand preferences survive post-training and alignment adjustment") and direct experimental comparisons that demonstrate the preference persists through reinforcement learning from human feedback and is removable only with targeted, category-specific supervision that commercial alignment pipelines do not perform.

### (2.1) Base-versus-instruct comparison

A direct comparison of the base and instruction-tuned Gemma 4 E4B variants reduces non-optimal rates from 67 to 20 per cent. Alignment training attenuates the expression of the brand preference by approximately two-thirds but does not remove it; the residual 20 per cent rate remains readable from the aligned model's hidden states via the probing classifier described in (1.2). Replication on Mistral 7B (base 72.4 per cent vs instruct 54.7 per cent; N = 123 and 170 respectively) shows the pattern generalises across model families, although the absolute magnitude of attenuation varies.

**Where in the revision:** Main text, new section "Brand preferences survive post-training and alignment adjustment." Fig. 5 panel d. Methods, "Base-versus-instruct comparison" subsection. Supplementary Note 26.

### (2.2) Targeted debiasing

Fine-tuning GPT-4o-mini, GPT-4.1-nano, and GPT-4.1-mini on 6,000 examples in which the specification-optimal product is recommended regardless of brand reduces non-optimal rates from baseline (16.2, 14.1, and 8.5 per cent) to 0.3, 0.3, and 0.0 per cent respectively (all P < 10^-18). A reduced 500-example protocol reduces GPT-4o-mini from 15.3 to 0.9 per cent.

### (2.3) Creation-removal asymmetry

The 100-example injection protocol installs the preference to 52.5 per cent (Concern 1.1), while the 500-example debiasing protocol only reduces a latent 15 per cent preference to 0.9 per cent, and the 6,000-example protocol is required to reach 0.3 per cent. Creating the preference requires roughly one-fifth the supervised data that removing it does. The asymmetry parallels the effort-disparity patterns reported by Betley et al. (2026) in emergent misalignment.

**Where in the revision:** Main text, new section, third paragraph. Fig. 5 panel b. Methods, "Targeted debiasing" subsection. Supplementary Note 27.

### (2.4) Inverse capability scaling

A mixed-effects logistic regression across all 30 tested models yields a positive coefficient on capability tier (β = 0.108 per tier, P = 5 × 10^-4, R² = 0.36), indicating that larger and more capable models exhibit stronger rather than weaker brand preferences. Mini-class models (tier 1) average 17.4 per cent non-optimal, mid-class models (tier 2) average 29.1 per cent, and large-class models (tier 3) average 40.0 per cent. The pattern holds within every provider family tested.

**Where in the revision:** Main text, "Brand preferences are shared across models, providers, and architectures" section, final paragraph. Methods, "Inverse capability scaling" subsection (implicit in Model classification). Supplementary Note 25.

---

## Concern 3: Evidence that people follow these recommendations

### Summary of the response

Four pre-registered behavioural studies (N = 3,164 combined, IRB exempt approval from Oklahoma State University, April 2026) document that consumers follow biased AI recommendations at substantial margins above baseline compliance, that consumer-side inoculation provides only partial protection, and that the effect replicates in an interactive AI shopping chatbot where participants choose their own product category.

### (3.1) Studies 1A and 1B: compliance with biased AI recommendations in static choice

Study 1A (coffee makers, N = 798) and Study 1B (wireless earbuds, N = 798) each compared three conditions: no AI recommendation (NoAI), a biased AI recommendation transcribed verbatim from the computational corpus (BiasedAI), and a debiased AI recommendation that accurately identified the specification-optimal product (DebiasedAI). BiasedAI shifted branded-product choice by 33.3 pp in Study 1A (P = 1.3 × 10^-14, OR 4.01) and 27.7 pp in Study 1B (P = 1.05 × 10^-10, OR 3.23). DebiasedAI shifted specification-optimal choice by 24.3 pp (Study 1A; P = 1.2 × 10^-8) and 31.0 pp (Study 1B; P = 8.3 × 10^-14), evidence that consumers follow the AI's recommendation in both directions with effect magnitudes comparable to the largest mechanism-isolation effects in the computational data.

**Where in the revision:** Main text, new section "Consumers follow biased AI recommendations," paragraph 2. Fig. 6 panel a. Methods, "Studies 1A and 1B" subsection. Supplementary Notes 30 and 31.

### (3.2) Study 2: consumer-side protection is only partial

Study 2 (N = 799, wireless earbuds) tested whether warnings reduce biased-AI compliance. A generic warning (Inoculation) reduced branded-product compliance by 12.2 percentage points relative to BiasedAI alone (Fisher's exact P = 3.5 × 10^-3) and an explicit specification table that directly debunks the confabulation (SpecExposed) reduced compliance by 17.4 percentage points (P = 3.3 × 10^-5). The two interventions did not differ from each other (P = 0.26), indicating that exposing the confabulation mechanism provides no more protection than a generic warning. Despite these interventions, 55 to 60 per cent of participants continued to follow the biased AI even after direct specification debunking.

**Where in the revision:** Main text, new section, paragraph 3. Fig. 6 panel b. Methods, "Study 2" subsection. Supplementary Note 32.

### (3.3) Study 3: ecological validity in an interactive AI shopping chatbot

Study 3 (N = 769 usable, from N = 793 collected) tested whether the compliance effect replicates outside static product tables in a realistic, personalised chatbot setting. Participants chose any shopping category, chatted with Claude Opus through a three-stage interface (preference elicitation, dynamic assortment generation, recommendation with follow-up), and selected from a seven-item display generated at run time and verified server-side for strict specification dominance. Four AI-assistant visual brand skins (ChatGPT, Claude, Gemini, Perplexity) were randomised across participants; the underlying language model was identical across skins.

Pre-registered Fisher's exact tests on the three-bucket choice outcome:

- H1 (Biased vs Neutral on chose_focal): +18.7 pp (95% CI +10.3, +27.1; P < 0.0001; OR 2.16, 95% CI 1.52 to 3.09)
- RQ1 (Honest vs Neutral on chose_optimal): +27.2 pp (95% CI +19.0, +35.5; P < 0.0001; OR 3.09, 95% CI 2.15 to 4.43)
- Omnibus 3x3 condition × bucket: χ²(4) = 103.61, P < 0.0001

A mixed-effects logistic regression with a random intercept on 13 product meta-categories (branch C of a pre-committed contingency ladder, triggered by the observed 92.1 per cent category-singleton rate; meta-categories assigned by a Claude Sonnet judge) reproduced both effects with `chose_optimal ~ honest` β = +1.152 (z = +9.07, P < 0.001) and `chose_focal ~ biased` β = +0.791 (z = +6.29, P < 0.001).

### (3.4) Study 3 sensitivity analyses

The primary effects are robust to:

- Excluding the 19 participants flagged by a Claude Sonnet suspicion judge as aware of bias or manipulation: H1 = +17.6 pp, RQ1 = +29.1 pp.
- Excluding the 194 participants who self-reported strong familiarity (4 or 5 of 5) with the chosen brand: H1 = +21.9 pp, RQ1 = +28.1 pp.
- Per-protocol restriction to sessions in which a Claude Sonnet manipulation-check judge confirmed the AI delivered the intended recommendation style: H1 = +22.8 pp.

Per-brand sub-analysis shows H1 is significant at P < 0.05 in three of four AI skins (ChatGPT, Claude, Gemini) and direction-consistent but non-significant in the Perplexity skin (+6.4 pp, P = 0.57), which is noted in the manuscript as a possible interaction of the search-first framing of that interface.

**Where in the revision:** Main text, new section, paragraphs 4 to 6. Fig. 6 panels c and d. Methods, "Study 3" subsection. Supplementary Note 33.

---

## Summary of changes to the manuscript

| Change | Location |
|---|---|
| Abstract updated to flag causal, structural, post-training, and behavioural evidence | Main text, Abstract (approximately 220 words added to original 217-word abstract) |
| New paragraph on causal and structural evidence | Main text, "Decision agents develop training-derived brand preferences" section |
| New Results section: "Brand preferences survive post-training and alignment adjustment" | Main text, between cross-model section and Discussion |
| New Results section: "Consumers follow biased AI recommendations" | Main text, between fine-tuning section and Discussion |
| Two new paragraphs added to Discussion addressing Concerns 1 and 2 | Main text, Discussion |
| Two new main figures (Fig. 5 causal/structural; Fig. 6 human studies) | Main text |
| Twelve new Methods subsections | Main text, Methods |
| Fourteen new Supplementary Notes (SN20-SN33) | Supplementary Information |
| Ethics Statement updated for human-subjects data | Main text |
| Data Availability updated for human-studies data | Main text |

All existing text from the original manuscript is preserved. The revision extends the paper without rewriting core passages; the personality and structure of the original are intact.

---

## Files submitted with this revision

- `paper/main.md` → compiled to `main.pdf` and `main.docx`
- `paper/supplementary.md` → compiled to `supplementary.pdf` and `supplementary.docx`
- `paper/cover_letter.md` → compiled to `cover_letter.pdf`
- `paper/response_to_editor.md` → this document

All analysis code, fine-tuned model identifiers, behavioural-study raw data, pre-registrations, and replication scripts are committed at the project GitHub repository and at the Open Science Framework project linked in the paper's Data Availability section.

I thank the Editor for the invitation to resubmit, and I look forward to further review.

Sincerely,
Felipe M. Affonso
