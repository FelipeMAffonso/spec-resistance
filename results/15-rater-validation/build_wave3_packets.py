#!/usr/bin/env python3
"""build_wave3_packets.py - WAVE 3 unit packets: HUMAN explicit_numeric explanations ONLY.

Wave 3 extends the crowd C1/C2 coding to the explicit-level HUMAN justifications from the
confirmatory benchmark (the corpus/model side of the explicit level is NOT re-fielded; wave 1
covered the pooled NL-level human+model mix). Kept-row rule = the confirmatory dataset rule,
replicated from reruns/confirmatory_FINAL_numbers.py verbatim:
  iter17_final export (1,209 finished) -> PROLIFIC_PID in iter17_final_approved_pids.json
  (1,200) -> analyze_full.apply_exclusions (attention, 60-1200 s, duplicate PID, recorded
  choice) -> kept 1,182. Then this wave's unit filter: assigned_level == explicit_numeric,
  choice_is_optimal false, >= 15 chars after answer-prefix stripping, brand resolves in the
  locked bank (all via build_unit_packets.load_human_units, levels=('explicit_numeric',)).

Reuses build_unit_packets wholesale (strip rules, bank tables, golds, seeded shuffle,
source-strip discipline): units carry no provenance; refs live ONLY in the SOURCEMAP.
Outputs wave3_units.json + wave3_units_SOURCEMAP.json. No network.

Run: python build_wave3_packets.py
"""
from __future__ import annotations

import json
import os
import random
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
POST1 = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
sys.path.insert(0, os.path.join(POST1, "prolific"))
sys.path.insert(0, HERE)

import harvest  # noqa: E402
import analyze_full as AF  # noqa: E402
import build_unit_packets as BUP  # noqa: E402

CSV = os.path.join(POST1, "prolific", "iterations", "iter17_final", "qualtrics_responses.csv")
PIDS_FILE = os.path.join(POST1, "prolific", "iterations", "iter17_final_approved_pids.json")
OUT_UNITS = os.path.join(HERE, "wave3_units.json")
OUT_SOURCEMAP = os.path.join(HERE, "wave3_units_SOURCEMAP.json")
VERSION = "rater-units-wave3-1.0"
BUILD_DATE = "2026-07-02"
LEVELS = ("explicit_numeric",)


def main():
    # ---- bank self-check (same defence as the wave-1 packet build) ----
    bad = [r for r in BUP.SB.verify_all() if not r["ok"]]
    if bad:
        raise SystemExit(f"stimulus bank FAILED constraint satisfaction: {bad}")

    # ---- kept rows, the confirmatory rule ----
    pids = set(json.loads(open(PIDS_FILE, encoding="utf-8").read()))
    header, rows = harvest.parse_qualtrics_csv(open(CSV, encoding="utf-8").read())
    pre = [r for r in rows if (r.get("PROLIFIC_PID") or r.get("prolific_pid") or "").strip() in pids]
    kept, excl = AF.apply_exclusions(pre)
    kept_rids = {(r.get("ResponseId") or "").strip() for r in kept}
    all_rids = {(r.get("ResponseId") or "").strip() for r in rows if (r.get("ResponseId") or "").startswith("R_")}
    exclude_refs = all_rids - kept_rids
    print(f"[wave3] finished rows {len(rows)} | approved-PID {len(pre)} | kept {len(kept)} "
          f"(excl {dict(excl)}) -> exclude_refs {len(exclude_refs)}")

    # ---- human explicit-level units via the shared ingest (its own filters do the rest) ----
    human_recs = BUP.load_human_units(CSV, exclude_refs, levels=LEVELS)
    print(f"[wave3] human explicit_numeric non-optimal units (>=15 chars, bank-resolved): {len(human_recs)}")
    if not human_recs:
        raise SystemExit("no wave-3 units - refusing to build")

    # ---- source-strip + seeded shuffle + ids (the wave-1 assembly, human-only pool) ----
    pool = list(human_recs)
    rng = random.Random(BUP.SHUFFLE_SEED + "-wave3-pool")
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
            "table_html": BUP.TABLE_HTML[rec["assortment_id"]],
        })
        sourcemap_units[uid] = {
            "source": rec["source"],
            "ref": rec["ref"],
            "model_key": rec["model_key"],
            "condition": rec["condition"],
            "assortment_id": rec["assortment_id"],
            "exact_duplicate_refs": [],
        }

    golds = BUP.build_golds()
    per_aid = Counter(u["assortment_id"] for u in units)

    meta = {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "wave": 3,
        "seed": BUP.SHUFFLE_SEED + "-wave3-pool",
        "source_csv": os.path.relpath(CSV, POST1),
        "kept_rule": ("iter17_final finished rows -> PROLIFIC_PID in iter17_final_approved_pids.json "
                      "-> analyze_full.apply_exclusions (the confirmatory_FINAL_numbers.py rule; "
                      f"kept {len(kept)}) -> assigned_level in {list(LEVELS)}, non-optimal choice, "
                      ">= 15 chars after answer-prefix strip, brand resolves in the locked bank"),
        "filters": {
            "assortment_ids": BUP.LOCKED_IDS,
            "levels": list(LEVELS),
            "non_optimal_only": True,
            "min_justification_chars": BUP.MIN_JUST_CHARS,
        },
        "counts": {
            "units_total": len(units),
            "units_model": 0,
            "units_human": len(units),
            "golds": len(golds),
            "per_assortment": dict(sorted(per_aid.items())),
        },
        "human_side": ("WAVE-3 HUMAN-ONLY BUILD (explicit_numeric rung). The model side of the "
                       "explicit rung is deliberately NOT pooled here; wave 1 fielded the pooled "
                       "NL-rung human+model mix per prereg Q3."),
        "blinding": "units carry no source field; provenance lives ONLY in wave3_units_SOURCEMAP.json",
    }

    with open(OUT_UNITS, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"meta": meta, "units": units, "golds": golds}, f, ensure_ascii=False, indent=1)
    with open(OUT_SOURCEMAP, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"meta": meta, "units": sourcemap_units}, f, ensure_ascii=False, indent=1)

    print(f"[wave3] wrote {OUT_UNITS} ({os.path.getsize(OUT_UNITS)//1024}KB) + SOURCEMAP")
    print(f"[wave3] units {len(units)} (all human) + {len(golds)} golds; per assortment: {dict(sorted(per_aid.items()))}")
    print(f"[wave3] blocks at 20/session: {-(-len(units)//20)} -> sessions for 5x: {5 * -(-len(units)//20)}")


if __name__ == "__main__":
    main()
