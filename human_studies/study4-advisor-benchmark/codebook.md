# Study 4 (human-advisor benchmark) - codebook

Pre-registered confirmatory study (AsPredicted #299842; see prereg.md). N = 1,200 recruited on
Prolific (study places), 1,209 finished survey rows (returned/timed-out slots recycled), 1,182 kept
after the pre-registered exclusions (1 attention, 17 duration) restricted to the 1,200 approved
submissions (`approved_submission` column). Analysis: `analysis_confirmatory_numbers.py` runs on
the files in this directory alone (`anonymised.csv` plus `model_arm_dose_response.json`, the
matched model arm re-derived from the deposited corpus for the five benchmark assortments) and
reproduces every manuscript number into `confirmatory_numbers.json`, including the registered
section-5 robustness recomputes, the demand-effect bound, the believability measure, the
belief-item conditionals, and the registered secondaries.

Key columns: `participant_id` (anonymised, stable within participant), `approved_submission` (True
for the 1,200 valid submissions), `assortment_id` (five resistance-selected corpus assortments),
`assigned_level` (baseline / weighted / explicit_numeric), `assigned_frame` (advise_other /
choose_self), `choice_index`/`choice_code`/`choice_brand`/`choice_is_optimal`/`choice_is_focal`
(the recommendation), `why_free_text` (open-ended basis), `challenge_text` + `challenge_free_text`
(the two-turn challenge shown and the response), `brand_influence` (forced probe, 1-5),
`comprehension_1` + `comp_correct` (application item and its per-cell key),
`believability_dominant` (1-5), `too_good_to_be_true` (1-5), `fam_dominant`/`fam_focal` (brand
familiarity, 1-5), `suspicion_open` (open-ended purpose guess), `belief_*` (task-belief items),
`demand_item` + `demand_framing`/`demand_cell` (demand-effect item and framing assignment),
`attention_1`, `numeracy_1`, `ai_literacy`, timing fields, demographics. Prolific/session
identifiers, IP, and geolocation are stripped.
