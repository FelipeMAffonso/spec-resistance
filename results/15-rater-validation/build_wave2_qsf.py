#!/usr/bin/env python3
"""build_wave2_qsf.py - WAVE 2 (replacement raters) QSF for the rater study.

Post-processes the fielded wave-1 artifact rater_study.qsf (SV_2gjG7ZYRVlTWhHU, cc=SRRATE7K2M)
rather than rebuilding, so the wave-2 survey is byte-identical to wave 1 everywhere except:
  1. the BlockRandomizer keeps ONLY the underfilled session blocks (wave2_block_deficits.json
     deficit > 0); the 4 filled blocks' randomizer children are removed. Nothing is renumbered:
     the surviving children still stamp their original session_block ids (b01..b41 minus the
     filled ones) and the identical u{NN}_* slot payloads, so reruns/rater_scoring.py joins
     wave-2 exports against the SAME wave-1 rater_study_MAPPING.json.
  2. the Prolific completion redirect carries a FRESH completion code (wave-2 study, new cc).
  3. the qsf_build embedded-data stamp gains a "+wave2-replacement" suffix (provenance only).
  4. SurveyEntry.SurveyName gains a "Wave 2" suffix (Qualtrics-internal label only).

Everything else (units, golds, attention item, consent, questions, blocks, options) is the
wave-1 bytes. The script verifies the pre-state against rater_study_MAPPING.json, applies the
4 edits, re-parses the output, and asserts the post-state. No network.

Run:  python build_wave2_qsf.py --code SRRW2XXXXX
"""
from __future__ import annotations

import argparse
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
QSF_IN = os.path.join(HERE, "rater_study.qsf")
MAPPING = os.path.join(HERE, "rater_study_MAPPING.json")
DEFICITS = os.path.join(HERE, "wave2_block_deficits.json")
QSF_OUT = os.path.join(HERE, "rater_study_wave2.qsf")
WAVE1_CC = "SRRATE7K2M"


def stamped(child):
    """randomizer child -> {field: value} for its EmbeddedData setter."""
    return {ed["Field"]: ed.get("Value") for ed in child["EmbeddedData"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", required=True, help="fresh wave-2 Prolific completion code")
    ap.add_argument("--out", default=QSF_OUT)
    a = ap.parse_args()

    qsf = json.load(open(QSF_IN, encoding="utf-8"))
    mapping = json.load(open(MAPPING, encoding="utf-8"))
    deficits = json.load(open(DEFICITS, encoding="utf-8"))
    map_blocks = {b["session_block"]: b["slots"] for b in mapping["blocks"]}

    filled = sorted(sb for sb, d in deficits.items() if d == 0)
    underfilled = sorted(sb for sb, d in deficits.items() if d > 0)
    assert set(deficits) == set(map_blocks), "deficits file does not cover the mapping blocks 1:1"
    print(f"[wave2] deficit sum={sum(deficits.values())} underfilled={len(underfilled)} filled={filled}")

    fl = next(e for e in qsf["SurveyElements"] if e["Element"] == "FL")["Payload"]
    flow = fl["Flow"]
    rand = next(el for el in flow if el["Type"] == "BlockRandomizer")

    # ---- pre-verification: 41 children; every child's stamp matches the wave-1 MAPPING ----
    assert len(rand["Flow"]) == len(map_blocks) == 41, "wave-1 randomizer child count mismatch"
    for ch in rand["Flow"]:
        st = stamped(ch)
        sb = st["session_block"]
        slots = map_blocks[sb]
        for nn, meta in slots.items():
            assert st[f"u{nn}_id"] == meta["unit_id"], f"{sb} slot {nn}: stamped id != mapping"
            assert st[f"u{nn}_kind"] == meta["kind"], f"{sb} slot {nn}: stamped kind != mapping"
    print("[wave2] pre-verify OK: all 41 children stamp exactly the wave-1 MAPPING slots")

    # ---- edit 1: drop the filled blocks' children (keep original order; no renumbering) ----
    before = [stamped(ch)["session_block"] for ch in rand["Flow"]]
    rand["Flow"] = [ch for ch in rand["Flow"] if stamped(ch)["session_block"] not in set(filled)]
    after = [stamped(ch)["session_block"] for ch in rand["Flow"]]
    assert after == [sb for sb in before if sb not in set(filled)]
    assert sorted(after) == underfilled, "surviving children != underfilled set"

    # ---- edit 2: fresh completion code in the ONLY Advanced redirect end node ----
    ends = [el for el in flow if el["Type"] == "EndSurvey" and
            (el.get("Options") or {}).get("EOSRedirectURL")]
    assert len(ends) == 1, "expected exactly one redirect EndSurvey node"
    url = ends[0]["Options"]["EOSRedirectURL"]
    assert WAVE1_CC in url, f"wave-1 cc not found in redirect url: {url}"
    ends[0]["Options"]["EOSRedirectURL"] = url.replace(WAVE1_CC, a.code)

    # ---- edit 3: provenance stamp ----
    for el in flow:
        if el["Type"] == "EmbeddedData":
            for ed in el["EmbeddedData"]:
                if ed["Field"] == "qsf_build" and ed.get("Value"):
                    ed["Value"] = ed["Value"] + "+wave2-replacement"

    # ---- edit 4: Qualtrics-internal survey name ----
    qsf["SurveyEntry"]["SurveyName"] = (
        "Spec-Resistance Rater Study WAVE 2 (replacement raters): Disclosure Coding (C1/C2 crowd)")

    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(qsf, f, ensure_ascii=False)

    # ---- post-verification on a fresh re-parse ----
    re_q = json.load(open(a.out, encoding="utf-8"))
    re_fl = next(e for e in re_q["SurveyElements"] if e["Element"] == "FL")["Payload"]
    re_flow = re_fl["Flow"]
    re_rand = next(el for el in re_flow if el["Type"] == "BlockRandomizer")
    re_sbs = sorted(stamped(ch)["session_block"] for ch in re_rand["Flow"])
    assert re_sbs == underfilled and len(re_rand["Flow"]) == 37
    assert re_rand["SubSet"] == 1 and re_rand["EvenPresentation"] is True

    # surviving children byte-identical to the wave-1 originals
    orig = json.load(open(QSF_IN, encoding="utf-8"))
    orig_rand = next(el for el in
                     next(e for e in orig["SurveyElements"] if e["Element"] == "FL")["Payload"]["Flow"]
                     if el["Type"] == "BlockRandomizer")
    orig_by_sb = {stamped(ch)["session_block"]: ch for ch in orig_rand["Flow"]}
    for ch in re_rand["Flow"]:
        assert ch == orig_by_sb[stamped(ch)["session_block"]], "child drifted from wave-1 bytes"

    # everything OUTSIDE the four edits is byte-identical to wave 1
    norm_new, norm_old = copy.deepcopy(re_q), copy.deepcopy(orig)
    for q in (norm_new, norm_old):
        f2 = next(e for e in q["SurveyElements"] if e["Element"] == "FL")["Payload"]["Flow"]
        next(el for el in f2 if el["Type"] == "BlockRandomizer")["Flow"] = []
        for el in f2:
            if el["Type"] == "EndSurvey" and (el.get("Options") or {}).get("EOSRedirectURL"):
                el["Options"]["EOSRedirectURL"] = "X"
            if el["Type"] == "EmbeddedData":
                for ed in el["EmbeddedData"]:
                    if ed["Field"] == "qsf_build":
                        ed["Value"] = "X"
        q["SurveyEntry"]["SurveyName"] = "X"
    assert norm_new == norm_old, "unexpected drift outside the four wave-2 edits"

    # unit coverage across the surviving blocks
    covered = {v for ch in re_rand["Flow"] for f2, v in stamped(ch).items()
               if f2.endswith("_id") and v not in ("attn",) and not v.startswith("g")}
    all_units = {m["unit_id"] for b in mapping["blocks"] for m in b["slots"].values()
                 if m["kind"] == "real"}
    dropped_only = sorted(all_units - covered)
    new_url = next(el for el in re_flow if el["Type"] == "EndSurvey" and
                   (el.get("Options") or {}).get("EOSRedirectURL"))["Options"]["EOSRedirectURL"]
    print(f"[wave2] wrote {a.out} ({os.path.getsize(a.out)//1024}KB)")
    print(f"[wave2] randomizer children 41 -> {len(re_rand['Flow'])} (dropped {filled})")
    print(f"[wave2] completion redirect: {new_url}")
    print(f"[wave2] real units covered by surviving blocks: {len(covered)}/{len(all_units)}; "
          f"units ONLY in filled blocks (correctly not re-fielded): {len(dropped_only)}")
    print("[wave2] post-verify OK: surviving children byte-identical to wave 1; no other drift")


if __name__ == "__main__":
    main()
