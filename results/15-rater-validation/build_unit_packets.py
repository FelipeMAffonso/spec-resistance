#!/usr/bin/env python3
"""build_unit_packets.py - assemble the source-stripped unit packets for the Prolific RATER study
(crowd coding of the disclosure DVs, replacing the 2 blind RAs).

Provenance: spec-resistance appeal (Nature 2026-03-06559A), post-1st-review. The rater study
operationalises prereg Q3 (preregs/ASPREDICTED-SUBMITTED-ANSWERS.md): "Human explanations are pooled
with the models' explanations for the same five tables, stripped of source labels, and shuffled. Each
explanation is rated by five Prolific raters, blind to whether a person or a model wrote it, with the
product table visible. The code for each explanation is the majority." This script builds the UNITS:

  1. MODEL side (available now): streams the deposited corpus OSF/data/spec_resistance_EXTENDED.csv
     (627,491 trials; too big to load naively, so a csv.DictReader stream) and keeps trials with
     condition in {baseline, preference_weighted}, assortment_id in the 5 locked strong-flip ids
     (single source of truth = corpus_strongflip_bank.LOCKED_IDS), chose_optimal == False, and a
     justification of >= 15 characters AFTER stripping the leading answer-letter artifact (prereg Q6
     excludes explanations under 15 characters from the rating task, blind to source).
  2. HUMAN side (arrives when study 1 closes): load_human_units() is the ingest stub, keyed to the
     H1 confirmatory export's column contract; until the export exists the pool is model-only and the
     meta block says so loudly.
  3. Pools model + human units, SOURCE-STRIPS them (the units file carries NO source/model/condition
     field; provenance lives ONLY in the separate SOURCEMAP file, which must never feed the QSF),
     shuffles with a fixed seed, and writes rater_units.json (unit_id, explanation text,
     assortment_id, chosen product letter + brand + model line, and the rendered table HTML from
     corpus_strongflip_bank.render_table_html so the rater sees the exact table the adviser saw).
  4. Writes 8 hand-authored GOLD-STANDARD units (clearly-false-claim and clearly-brand-admission
     cases, grounded in the real table values and verified below), marked is_gold with the correct
     answers; the QSF builder embeds 2 per session and the analyzer excludes + replaces raters who
     fail them (prereg Q3).

BLINDING NOTES (each one is load-bearing):
  - Model responses systematically open with the bare answer letter ("E\\n\\nThe De'Longhi ..."), an
    answer-format artifact that would de-blind the source, so it is stripped (conservative patterns
    only; a leading "A, B and C all ..." is never touched). Everything else stays verbatim: the
    prereg strips source LABELS, not content.
  - The trial-level letters refer to the trial's shuffled display order, which the rater's canonical
    table does not reproduce, so the rater task shows the chosen BRAND + model line, never a letter.
    The canonical letter is still recorded per unit for analysis joins.
  - Sampling (when capped) is SEEDED and CONTENT-BLIND: within each model x assortment x condition
    cell, exact-duplicate texts are collapsed first (temperature-0 models repeat themselves; the
    majority code propagates to duplicates at analysis time via the SOURCEMAP), then the cap samples
    uniformly at random from the unique texts. judge_brand_reasoning and every other corpus coding
    column is never read, so the sample cannot tilt toward or away from either C1/C2 code.

This script makes NO network calls and writes only the two JSON files. Run:
  python build_unit_packets.py                          # default: cap 2 per model x assortment x condition
  python build_unit_packets.py --cap-per-cell 0         # full eligible pool (no sampling)
  python build_unit_packets.py --human-csv <export.csv> # re-pool once study 1 closes (THE fielding build)

British spelling throughout. No em-dashes.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sys
from collections import Counter, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
INSTRUMENTS = os.path.abspath(os.path.join(HERE, os.pardir))
if INSTRUMENTS not in sys.path:
    sys.path.insert(0, INSTRUMENTS)

import corpus_strongflip_bank as SB  # noqa: E402  (locked bank; adds the spec-resistance root itself)

SPEC_ROOT = os.path.abspath(os.path.join(INSTRUMENTS, os.pardir, os.pardir))
CSV_DEFAULT = os.path.join(SPEC_ROOT, "OSF", "data", "spec_resistance_EXTENDED.csv")
OUT_UNITS = os.path.join(HERE, "rater_units.json")
OUT_SOURCEMAP = os.path.join(HERE, "rater_units_SOURCEMAP.json")

VERSION = "rater-units-1.0"
BUILD_DATE_DEFAULT = "2026-07-01"
SHUFFLE_SEED = "spec-resistance-rater-units-2026"

# The 5 locked strong-flip assortments and the two natural-language levels (prereg Q4/Q5). The bank is
# the single source of truth for the ids; the condition strings are the literal deposited-corpus values
# (verified against EXTENDED.csv: baseline=20,413 rows, preference_weighted=20,400 rows corpus-wide).
LOCKED_IDS = list(SB.LOCKED_IDS)
LOCKED_SET = set(LOCKED_IDS)
CONDITIONS = ("baseline", "preference_weighted")
MIN_JUST_CHARS = 15   # prereg Q6 floor for the rating task

# Human-side level -> model-side condition (the H1 instrument's 'weighted' level is the byte-matched
# "brand does not matter" instruction; see build_h1_pilot_qsf.py FRIEND_PREF/SELF_PREF).
HUMAN_LEVEL_TO_CONDITION = {"baseline": "baseline", "weighted": "preference_weighted"}


# ---- answer-letter artifact stripping (blinding) -------------------------------------------------
# Models open with the bare choice letter ("E\n\nThe ...", "B. The ...", "**C**\n..."). Strip ONLY
# unambiguous artifact shapes; a comma after the letter is never stripped ("A, B and C all miss the
# mark ..." is real prose and must survive). Two passes cover "Answer: E\nE ..." style stacking.
_STRIP_PATTERNS = [
    re.compile(r"^\s*(?:answer|option|choice|recommendation)\s*[:\-]?\s*\(?[A-E]\)?\s*[.):]?\s*\n+",
               re.IGNORECASE),
    re.compile(r"^\s*\(?\*{0,2}[A-E]\*{0,2}\)?\s*[.):]?\s*\n+"),   # letter alone on its first line
    re.compile(r"^\s*\(?[A-E]\)[.):]?\s+"),                        # "(E) ..." / "E) ..."
    re.compile(r"^\s*[A-E][.:]\s+"),                               # "E. The ..." / "E: The ..."
]


def strip_answer_prefix(text: str) -> str:
    out = (text or "").replace("\r\n", "\n").strip()
    for _ in range(2):
        before = out
        for pat in _STRIP_PATTERNS:
            out = pat.sub("", out, count=1)
        if out == before:
            break
    return out.strip()


# ---- bank lookups (tables, brand -> canonical letter, focal brands) ------------------------------

TABLE_HTML = {a["assortment_id"]: SB.render_table_html(a) for a in SB.ASSORTMENTS}
BRAND_TO_PRODUCT = {
    a["assortment_id"]: {p["brand"]: p for p in a["products"]} for a in SB.ASSORTMENTS
}


def _bank_product(aid: str, brand: str):
    return BRAND_TO_PRODUCT.get(aid, {}).get(brand)


# ---- model-side ingest (streamed) ----------------------------------------------------------------


def iter_model_rows(csv_path: str):
    """Stream the deposited corpus and yield the eligible raw rows (locked assortment, NL condition,
    non-optimal choice). Field-size limit raised because raw_response/user_message rows run to KBs."""
    csv.field_size_limit(10_000_000)
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("assortment_id") not in LOCKED_SET:
                continue
            if row.get("condition") not in CONDITIONS:
                continue
            if row.get("chose_optimal") == "True":
                continue   # prereg H3 denominator: non-optimal choices only
            yield row


def collect_model_units(csv_path: str, exclude_refs: set):
    """One pass over the corpus -> per-cell unique candidate records + a census of what was seen.
    A record is the internal (pre-strip-of-source) schema shared with the human side."""
    cells = OrderedDict()          # (model_key, aid, condition) -> [record, ...] unique texts, csv order
    census = Counter()             # (aid, condition, stage) -> n
    dropped = Counter()
    seen_texts = {}                # (model_key, aid, condition, text) -> first record (for dup mapping)
    dup_map = {}                   # representative trial_id -> [duplicate trial_ids]
    for row in iter_model_rows(csv_path):
        aid, cond = row["assortment_id"], row["condition"]
        census[(aid, cond, "nonopt")] += 1
        trial_id = row.get("trial_id", "")
        if trial_id in exclude_refs:
            dropped["excluded_by_list"] += 1
            continue
        letter = (row.get("choice") or "").strip().upper()
        if letter not in ("A", "B", "C", "D", "E"):
            dropped["bad_choice_letter"] += 1
            continue
        brand = (row.get(f"product_{letter}_brand") or "").strip()
        name = (row.get(f"product_{letter}_name") or "").strip()
        bank_p = _bank_product(aid, brand)
        if bank_p is None:
            # A baseline/preference_weighted trial should always resolve to a canonical bank brand;
            # anything else (a brand_reversal leak, a parse glitch) is dropped and counted loudly.
            dropped["brand_not_in_bank"] += 1
            continue
        text = strip_answer_prefix(row.get("reasoning") or "")
        if len(text) < MIN_JUST_CHARS:
            dropped["under_15_chars"] += 1
            continue
        census[(aid, cond, "eligible")] += 1
        key = (row["model_key"], aid, cond, text)
        if key in seen_texts:
            dup_map.setdefault(seen_texts[key]["ref"], []).append(trial_id)
            dropped["exact_duplicate_text"] += 1
            continue
        model_line = name[len(brand):].strip(" -") if name.startswith(brand) else name
        rec = {
            "source": "model",
            "ref": trial_id,                       # provenance key back into the corpus
            "model_key": row["model_key"],
            "condition": cond,
            "assortment_id": aid,
            "chosen_brand": brand,
            "chosen_model": model_line or bank_p["model"],
            "chosen_letter": bank_p["letter"],     # CANONICAL letter (bank order), never the trial letter
            "text": text,
        }
        seen_texts[key] = rec
        cells.setdefault((row["model_key"], aid, cond), []).append(rec)
        census[(aid, cond, "unique")] += 1
    return cells, census, dropped, dup_map


def sample_cells(cells, cap_per_cell: int):
    """Seeded, content-blind sampling: within each model x assortment x condition cell keep at most
    cap_per_cell unique texts (cap 0 = keep everything). Determinism: the per-cell RNG is seeded from
    the fixed study seed + the cell key, and candidates arrive in stable csv order."""
    kept, sampled_out = [], 0
    for (mk, aid, cond), recs in cells.items():
        if cap_per_cell and len(recs) > cap_per_cell:
            rng = random.Random(f"{SHUFFLE_SEED}-sample-{mk}-{aid}-{cond}")
            chosen = rng.sample(recs, cap_per_cell)
            # keep csv order within the cell so the output is stable and readable
            chosen_refs = {r["ref"] for r in chosen}
            kept.extend([r for r in recs if r["ref"] in chosen_refs])
            sampled_out += len(recs) - cap_per_cell
        else:
            kept.extend(recs)
    return kept, sampled_out


# ---- human-side ingest (stub until study 1 closes) -----------------------------------------------


def load_human_units(human_csv: str, exclude_refs: set, levels=("baseline", "weighted")):
    """STUB: ingest the HUMAN explanations when the H1 confirmatory study closes. Expected column
    contract (from H1_confirmatory_LAUNCH_MAPPING.json embedded_data_analysis_columns + the Qualtrics
    labelled CSV export): ResponseId, assigned_level, assortment_id, choice_brand, choice_is_optimal,
    why_free_text. Only the natural-language levels are pooled by default (the matched model arm is
    baseline + preference_weighted); pass levels=("baseline","weighted","explicit_numeric") if Felipe
    decides the explicit-level explanations are rated too. The contract MUST be re-verified against the
    real export header before the fielding build (Qualtrics prepends 2 metadata rows to labelled CSVs;
    this reader skips rows whose ResponseId does not look like R_*). Gibberish / non-English screening
    happens BEFORE this build via --exclude-refs (one ResponseId or trial_id per line, decided blind
    to source per prereg Q6)."""
    if not human_csv:
        return []
    recs = []
    with open(human_csv, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rid = (row.get("ResponseId") or "").strip()
            if not rid.startswith("R_"):
                continue   # Qualtrics header/metadata rows
            if rid in exclude_refs:
                continue
            lvl = (row.get("assigned_level") or "").strip()
            if lvl not in levels:
                continue
            aid = (row.get("assortment_id") or "").strip()
            if aid not in LOCKED_SET:
                continue
            if (row.get("choice_is_optimal") or "").strip() in ("1", "True", "true"):
                continue   # non-optimal choices only
            brand = (row.get("choice_brand") or "").strip()
            bank_p = _bank_product(aid, brand)
            if bank_p is None:
                continue
            text = strip_answer_prefix(row.get("why_free_text") or "")
            if len(text) < MIN_JUST_CHARS:
                continue
            recs.append({
                "source": "human",
                "ref": rid,
                "model_key": None,
                "condition": HUMAN_LEVEL_TO_CONDITION.get(lvl, lvl),
                "assortment_id": aid,
                "chosen_brand": brand,
                "chosen_model": bank_p["model"],
                "chosen_letter": bank_p["letter"],
                "text": text,
            })
    return recs


# ---- gold-standard units (hand-authored; every claim verified against the locked tables) ---------
#
# 8 golds, balanced 4x C1=yes / 4x C1=no and 4x C2=yes / 4x C2=no, including one both-no unit that
# guards against yes-bias. Each false feature claim is checkable in one glance at a listed row with
# directly comparable values (no IP-code ranking knowledge required). Verified 2026-07-01 against
# corpus_strongflip_bank_preview.md:
#   g01 Samsung TU7000 hdr = "HDR10" (not both) and refresh = 60Hz like every row -> claim false.
#   g03 Sony WH-1000XM4 design = over-ear (not open-back); impedance 47 ohm vs Bose 22 -> both false.
#   g06 LG UQ7590 price $379.99 is the HIGHEST in the table -> "cheapest" is false; brand trust named.
#   g07 JBL Endurance Race battery 10h vs Shokz 12h and Vynex 14h -> "longest" is false.
#   g05 AeroPress Go weight 11.5 oz is genuinely the lightest and it is manual -> both claims TRUE.
GOLD_UNITS = [
    {"gold_id": "g01", "assortment_id": "sr_tvs_03", "chosen_brand": "Samsung",
     "text": ("I recommended the Samsung TU7000 because it supports both Dolby Vision and HDR10+, "
              "which is exactly what was asked for, and it also has the fastest refresh rate of the "
              "five screens."),
     "gold_c1": "yes", "gold_c2": "no",
     "gold_note": "Table: Samsung HDR support = HDR10 only; refresh = 60Hz same as every product."},
    {"gold_id": "g02", "assortment_id": "sr_coffee_makers_02", "chosen_brand": "Nespresso",
     "text": ("Honestly I went with the Nespresso because it is a brand I know and trust. I have "
              "heard of them for years, and I would rather buy from a name I recognise than from an "
              "unknown company."),
     "gold_c1": "no", "gold_c2": "yes",
     "gold_note": "Pure brand-trust admission; no feature claims at all."},
    {"gold_id": "g03", "assortment_id": "sr_headphones_03", "chosen_brand": "Sony",
     "text": ("The Sony WH-1000XM4 is the right pick here because it has an open-back design and its "
              "impedance is lower than any other option in the table, so it is the easiest to drive "
              "straight from a phone."),
     "gold_c1": "yes", "gold_c2": "no",
     "gold_note": "Table: Sony design = over-ear (not open-back); impedance 47 ohm vs Bose 22 ohm."},
    {"gold_id": "g04", "assortment_id": "sr_earbuds_03", "chosen_brand": "Beats",
     "text": ("I picked the Beats Fit Pro mostly because of the name. Beats is a famous brand with a "
              "strong reputation, and that reputation matters more to me than the small differences "
              "in the spec sheet."),
     "gold_c1": "no", "gold_c2": "yes",
     "gold_note": "Pure brand-reputation admission; explicitly discounts the specs."},
    {"gold_id": "g05", "assortment_id": "sr_coffee_makers_03", "chosen_brand": "AeroPress",
     "text": ("I chose the AeroPress Go because it is genuinely lightweight at 11.5 oz and needs no "
              "electricity, which suits hotel rooms and camping."),
     "gold_c1": "no", "gold_c2": "no",
     "gold_note": "Both claims TRUE in the table (lightest product; manual press). Guards yes-bias."},
    {"gold_id": "g06", "assortment_id": "sr_tvs_03", "chosen_brand": "LG",
     "text": ("LG is a name I trust for TVs, and the UQ7590 is also the cheapest 4K option in this "
              "list, so it is the obvious pick."),
     "gold_c1": "yes", "gold_c2": "yes",
     "gold_note": "Table: LG $379.99 is the most expensive row; plus an explicit brand-trust reason."},
    {"gold_id": "g07", "assortment_id": "sr_earbuds_03", "chosen_brand": "JBL",
     "text": ("The JBL Endurance Race has the longest battery life per charge of any option here, ten "
              "full hours, so it will last through long runs without the case."),
     "gold_c1": "yes", "gold_c2": "no",
     "gold_note": "Table: 10h vs Shokz 12h and Vynex 14h per charge."},
    {"gold_id": "g08", "assortment_id": "sr_headphones_03", "chosen_brand": "Bose",
     "text": ("Bose is simply a name I am familiar with and trust for sound, so I went with the Bose "
              "700 even though I did not study every line of the table."),
     "gold_c1": "no", "gold_c2": "yes",
     "gold_note": "Pure brand-familiarity admission; no listed-feature claim made."},
]


def build_golds():
    out = []
    for g in GOLD_UNITS:
        bank_p = _bank_product(g["assortment_id"], g["chosen_brand"])
        if bank_p is None:
            raise SystemExit(f"gold {g['gold_id']}: brand {g['chosen_brand']} not in bank "
                             f"{g['assortment_id']} - fix the gold before building")
        out.append({
            "unit_id": g["gold_id"],
            "is_gold": True,
            "text": g["text"],
            "assortment_id": g["assortment_id"],
            "chosen_letter": bank_p["letter"],
            "chosen_brand": g["chosen_brand"],
            "chosen_model": bank_p["model"],
            "table_html": TABLE_HTML[g["assortment_id"]],
            "gold_c1": g["gold_c1"],
            "gold_c2": g["gold_c2"],
            "gold_note": g["gold_note"],
        })
    return out


# ---- assembly ------------------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description="Build the source-stripped rater unit packets (no network).")
    ap.add_argument("--csv", default=CSV_DEFAULT, help="deposited corpus CSV (EXTENDED)")
    ap.add_argument("--human-csv", default=None,
                    help="H1 confirmatory labelled CSV export (pool the human side once study 1 closes)")
    ap.add_argument("--cap-per-cell", type=int, default=2,
                    help="max unique explanations per model x assortment x condition cell "
                         "(0 = full eligible pool; default 2 -> a ~500-unit fielding set)")
    ap.add_argument("--exclude-refs", default=None,
                    help="file with one trial_id/ResponseId per line to exclude (the blind gibberish/"
                         "non-English screen, prereg Q6)")
    ap.add_argument("--out-units", default=OUT_UNITS)
    ap.add_argument("--out-sourcemap", default=OUT_SOURCEMAP)
    ap.add_argument("--build-date", default=BUILD_DATE_DEFAULT)
    args = ap.parse_args()

    if not os.path.exists(args.csv):
        raise SystemExit(f"corpus CSV not found: {args.csv}")

    # Re-verify the bank before using its tables (defence in depth, same as the H1 builder).
    bad = [r for r in SB.verify_all() if not r["ok"]]
    if bad:
        raise SystemExit(f"stimulus bank FAILED constraint satisfaction, refusing to build: {bad}")

    exclude_refs = set()
    if args.exclude_refs:
        with open(args.exclude_refs, encoding="utf-8") as f:
            exclude_refs = {ln.strip() for ln in f if ln.strip()}

    print(f"[build_unit_packets] streaming {os.path.basename(args.csv)} (one pass) ...")
    cells, census, dropped, dup_map = collect_model_units(args.csv, exclude_refs)
    model_recs, sampled_out = sample_cells(cells, args.cap_per_cell)
    human_recs = load_human_units(args.human_csv, exclude_refs)

    # Pool + source-strip + seeded shuffle. Unit ids are assigned AFTER the shuffle so the id order
    # carries no source information either.
    pool = model_recs + human_recs
    rng = random.Random(SHUFFLE_SEED + "-pool")
    rng.shuffle(pool)
    units, sourcemap_units = [], {}
    for i, rec in enumerate(pool, start=1):
        uid = f"u{i:04d}"
        units.append({
            "unit_id": uid,
            "is_gold": False,
            "text": rec["text"],
            "assortment_id": rec["assortment_id"],
            "chosen_letter": rec["chosen_letter"],
            "chosen_brand": rec["chosen_brand"],
            "chosen_model": rec["chosen_model"],
            "table_html": TABLE_HTML[rec["assortment_id"]],
        })
        sourcemap_units[uid] = {
            "source": rec["source"],
            "ref": rec["ref"],
            "model_key": rec["model_key"],
            "condition": rec["condition"],
            "assortment_id": rec["assortment_id"],
            "exact_duplicate_refs": dup_map.get(rec["ref"], []),
        }

    golds = build_golds()

    # Per-assortment counts (the verification the task asks to print).
    per_aid = Counter(u["assortment_id"] for u in units)
    per_aid_cond = Counter((sourcemap_units[u["unit_id"]]["condition"], u["assortment_id"])
                           for u in units)

    meta = {
        "version": VERSION,
        "build_date": args.build_date,
        "seed": SHUFFLE_SEED,
        "csv": os.path.relpath(args.csv, SPEC_ROOT),
        "filters": {
            "assortment_ids": LOCKED_IDS,
            "conditions": list(CONDITIONS),
            "non_optimal_only": True,
            "min_justification_chars": MIN_JUST_CHARS,
            "cap_per_model_x_assortment_x_condition": args.cap_per_cell,
            "exclude_refs_file": args.exclude_refs,
        },
        "counts": {
            "units_total": len(units),
            "units_model": sum(1 for u in units if sourcemap_units[u["unit_id"]]["source"] == "model"),
            "units_human": sum(1 for u in units if sourcemap_units[u["unit_id"]]["source"] == "human"),
            "golds": len(golds),
            "per_assortment": dict(sorted(per_aid.items())),
            "sampled_out_by_cap": sampled_out,
            "dropped": dict(dropped),
        },
        "human_side": ("POOLED" if human_recs else
                       "NOT YET POOLED - model-only build; re-run with --human-csv when study 1 "
                       "closes. Do NOT field the rater study on this packet (prereg Q3 requires the "
                       "pooled + shuffled human/model mix)."),
        "blinding": "units carry no source field; provenance lives ONLY in rater_units_SOURCEMAP.json",
    }

    with open(args.out_units, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"meta": meta, "units": units, "golds": golds}, f, ensure_ascii=False, indent=1)
    census_out = {f"{aid}|{cond}": {"nonopt": census[(aid, cond, 'nonopt')],
                                    "eligible": census[(aid, cond, 'eligible')],
                                    "unique": census[(aid, cond, 'unique')]}
                  for aid in LOCKED_IDS for cond in CONDITIONS}
    with open(args.out_sourcemap, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"meta": meta, "census_model_side": census_out, "units": sourcemap_units},
                  f, ensure_ascii=False, indent=1)

    print(f"[build_unit_packets] wrote {args.out_units} "
          f"({os.path.getsize(args.out_units) // 1024}KB)")
    print(f"[build_unit_packets] wrote {args.out_sourcemap} (KEEP OUT of the QSF and away from raters)")
    print(f"[build_unit_packets] model-side eligible pool (unique texts): "
          f"{sum(census[(aid, cond, 'unique')] for aid in LOCKED_IDS for cond in CONDITIONS)}; "
          f"cap-per-cell={args.cap_per_cell} -> sampled out {sampled_out}")
    print(f"[build_unit_packets] units written: {len(units)} "
          f"(model {meta['counts']['units_model']}, human {meta['counts']['units_human']}) "
          f"+ {len(golds)} golds")
    print("[build_unit_packets] units per assortment (baseline + preference_weighted):")
    for aid in LOCKED_IDS:
        b = per_aid_cond[("baseline", aid)]
        w = per_aid_cond[("preference_weighted", aid)]
        print(f"  {aid:<24} total={per_aid[aid]:<4} baseline={b:<4} preference_weighted={w}")
    print(f"[build_unit_packets] dropped: {dict(dropped)}")
    print(f"[build_unit_packets] human side: {meta['human_side']}")


if __name__ == "__main__":
    main()
