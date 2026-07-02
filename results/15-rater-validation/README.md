# Rater validation: blinded crowd coding of C1/C2 (COMPLETE)

Five blinded Prolific raters per unit coded the pooled, source-stripped corpus of human and model
non-optimal justifications for C1 (false feature claim) and C2 (brand admission), with gold-standard
and attention gates (failing raters excluded and replaced across five fielding waves) and majority
coding. The study doubles as the human validation of the automated judges (registration: AsPredicted
#299842, https://aspredicted.org/pv9ws7.pdf).

## Design and files
- `DESIGN.md`, `rater_units.json` (802 natural-language units: 232 human + 570 model, stratified two
  per model x assortment x condition), `rater_study_MAPPING.json` (blocks, slots, gold keys, recode,
  exclusion and majority rules), `rater_units_SOURCEMAP.json` (provenance, quarantined from raters),
  `wave3_MAPPING.json` + `wave3_units_SOURCEMAP.json` (133 supplementary explicit-level human units),
  builders (`build_unit_packets.py`, `build_rater_qsf.py`, `build_wave2_qsf.py`, `build_wave45_qsf.py`,
  `build_wave3_packets.py`), launch records (`WAVE2_WAVE3_LAUNCH_IDS.txt`, `WAVE45_LAUNCH_IDS.txt`).
- `data/wave{1..5}_responses_anonymised.csv`: complete exports, identifiers stripped, raters
  re-keyed R0001... per wave.
- `rater_scoring.py` (gates + majorities, mapping-literal), `analysis_final.py` (runs on the deposited
  wave CSVs alone: pooling, majorities, Krippendorff's alpha, Fisher tests, judge validation, and the
  registered per-model sensitivity), `unit_ratings_natural_language.json` +
  `unit_ratings_explicit.json` (per-unit rating lists from valid raters), `crowd_FINAL.json` (all
  reported statistics), `corpus_judge_codes_for_rater_units.json` (deposited judge codes joined to
  the rated units).

## Results (final; reported in Supplementary Note 34)
Natural-language corpus: full coverage (every unit >= 3 valid ratings; 542 of 802 at five).
- C2 brand admission: human 35.8% vs model 10.7% (Fisher one-sided, OR 4.6, P = 9.7e-16; confirmed
  at the registered alpha 0.005).
- C1 false feature claim: human 12.5% vs model 17.4% (one-sided P = 0.053; pre-registered direction,
  reported as directional only).
- Krippendorff's alpha below the 0.70 target (C2 0.52, C1 0.10), reported with raw pairwise agreement
  (83.3% / 54.0%) per the registration; corroborations: crowd majorities agree with the automated
  judge on 94.0% of the 570 model units (kappa 0.70) and reproduce the independent judge panel's
  human false-claim rate (12.5 vs 13 per cent).
- Registered per-model sensitivity: every model has 15-20 rated explanations; no model's brand-admission
  rate reaches the human rate (per-model 0 to 33.3 per cent, median 10.0, against 35.8); the C2 contrast
  survives dropping any one model (worst-case one-sided P = 5.4e-15); the C1 direction is unchanged by
  any single-model drop.
- Supplementary explicit-level units: 120 of 133 covered (one unusually strict gold item starved the
  final block; disclosed); C1 24.2%, C2 30.8%.
