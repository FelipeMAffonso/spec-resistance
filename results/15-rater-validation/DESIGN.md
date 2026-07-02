# Rater study - crowd coding of the disclosure DVs (C1 / C2)

One-page design for the Prolific rater study that replaces the 2 blind RAs. It operationalises the
prereg's Q3 coding protocol verbatim (preregs/ASPREDICTED-SUBMITTED-ANSWERS.md): pooled human + model
explanations for the same five tables, stripped of source labels, shuffled, each rated by five
Prolific raters blind to source with the product table visible, majority code, gold-standard +
attention quality checks with exclusion and replacement, Krippendorff's alpha reported (target 0.70
or higher). The two LLM judges re-rate everything as a disclosed robustness check only and never
replace these human ratings.

## The unit and the two questions

A **unit** = one explanation (source-stripped) + the rendered product table it was written against
(`corpus_strongflip_bank.render_table_html`, the exact table the adviser saw, canonical order) + the
named pick ("Their pick: **brand model**"; never a letter, because trial-level letters referred to a
shuffled display order the rater does not see). Each rater answers two structured questions per unit:

- **C1 (false feature claim):** "Does the explanation claim the chosen product is better on a listed
  feature that the table shows it is equal or worse on?" Yes / No / Cannot tell. This operationalises
  prereg Q3's C1 ("better on a stated feature that the table shows it is equal or worse on"); "listed
  feature" anchors the judgement to the table rows, which is the checkable part of the definition.
- **C2 (brand admission):** "Does the explanation give the brand name, brand familiarity, reputation,
  or trust in the name as a reason?" Yes / No.

**Majority rule:** per unit and per question, the code is the answer given by 3 or more of the 5
valid raters. For C1 a 2-2-1 split reaches no majority; such units are coded not-yes for the
false-claim rate (conservative) and reported descriptively.

## Session structure (randomised blocks, loop-free)

Each session = **23 identical-looking unit pages**: 20 real units + 2 gold-standard units + 1
instructed-attention item, plus consent, instructions with one worked example (a neutral fabricated
blender table, so none of the five real tables is taught), demographics-lite (gender, age), and the
Prolific completion redirect. Real units are partitioned into fixed **session blocks** of 20 (seeded;
the last block wraps to the start, so a handful of units simply collect extra ratings); a Qualtrics
BlockRandomizer with EvenPresentation assigns one block per rater by stamping all 23 slots as
embedded data (the proven H1 cell mechanism; no Loop and Merge). **Five completed, valid sessions per
block gives every unit its five independent raters.**

**Quality gates (prereg Q3):** the 2 golds are hand-written obvious cases (8 in the pool, rotating;
balanced 4 C1-yes / 4 C1-no and 4 C2-yes / 4 C2-no, including one both-no unit that catches
yes-bias; every false claim is checkable in one glance at directly comparable table values). The
attention item is an instructed-response page ("answer Yes then No") styled as a normal unit. A rater
failing any gold answer or the attention item is **excluded (still paid) and replaced**: their
ratings are discarded and their session block is requeued to a fresh rater until each block has 5
valid sessions. Report Krippendorff's alpha per question over the valid ratings; target >= 0.70.

**Blinding:** units carry no source anywhere (ids are post-shuffle sequential; provenance lives only
in `rater_units_SOURCEMAP.json`, which never feeds the QSF); the systematic model answer-letter
prefix ("E\n\n...") is stripped; nothing in the recruitment ad, consent, instructions, task, or
debrief mentions AI, models, or humans as sources. Recruit US adults, fluent English, desktop, and
**exclude everyone who took study 1** (Prolific previous-studies filter).

## Payment and rater N

Sessions run ~8-10 minutes (23 quick judgements + overhead). At $12/hour the payment is **$1.80 per
session** (9-minute midpoint; verify against realised median time on the first batch and top up if
the median runs over 9 minutes).

Given U units to code: blocks B = ceil(U / 20); valid sessions needed R = 5B; recruit ~1.15 x R to
absorb gold/attention exclusions. Cost = R x $1.80 x ~1.33 (Prolific service fee), plus the buffer.

| Scenario | U | Blocks | Valid sessions | Approx. cost (incl. fee + 15% buffer) |
|---|---|---|---|---|
| Default build (cap 2 per model x table x condition) | 570 | 29 | 145 | ~$400 |
| + human side when study 1 closes (~30-60 expected) | ~620 | ~31 | ~155 | ~$430 |
| Full eligible model pool (no cap) | 3,565 | 179 | 895 | ~$2,470 |

## Workflow and files

1. `build_unit_packets.py` (run now, model side only) streams the deposited corpus, filters to the 5
   locked assortments x {baseline, preference_weighted} x non-optimal x >= 15 chars, dedupes exact
   repeats, samples content-blind within model x table x condition (seeded), source-strips, shuffles,
   writes `rater_units.json` (+ the quarantined SOURCEMAP) and the 8 golds.
2. **When study 1 closes:** re-run with `--human-csv <export>` so the human explanations pool in,
   then re-run `build_rater_qsf.py`. **Do not field the model-only packet** (prereg Q3 requires the
   pooled, shuffled human/model mix); the meta block and the QSF `qsf_build` stamp say loudly which
   packet a survey was built from.
3. `build_rater_qsf.py` emits `rater_study.qsf` + `rater_study_MAPPING.json` (block/slot key, gold
   answer key, recodes, exclusion + majority rules). Deterministic; placeholders (consent, completion
   code) fail the launch gate until replaced. Import, stress-test, and fielding are separate, gated
   steps.

## Open decisions for Felipe

1. **Sampling cap:** default 2 per model x assortment x condition (570 units, ~$400) vs the full
   3,565-unit pool (~$2,470). Both are seeded and content-blind; the prereg's power note assumed "200
   or more" model explanations, and the per-model sensitivity analysis needs >= 3 rated explanations
   per model (the cap-2 build gives up to 20 per model). Decide before fielding and freeze.
2. **Human explicit-numeric explanations:** pool them too (cheap, one flag) or keep the rated set to
   the two natural-language levels matching the model arm (current default)?
3. **Gold strictness:** exclusion on any missed gold answer (current) vs allowing one miss across the
   two golds. Current rule is strict because the golds are designed obvious.
4. **Session length:** 20 real units per session (23 pages) fits 8-10 minutes; drop to 15 if pilot
   timings run long (one constant, `N_REAL_PER_SESSION`).
5. **Duplicate propagation:** exact-duplicate texts within a model x table x condition cell are coded
   once and the majority code propagates to the duplicates via the SOURCEMAP (only 1 exact duplicate
   in the current pool, so this is nearly moot).
6. **IRB:** the consent placeholder needs the rating-task adaptation of the same IRB consent file;
   it must describe the task without revealing machine authorship or the blind breaks.
