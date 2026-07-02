#!/usr/bin/env python3
"""build_wave45_qsf.py - TAIL TOP-UP waves 4 + 5 QSFs for the rater study.

Follows the proven build_wave2_qsf.py post-processing pattern (never rebuild, only
restrict + re-code a fielded artifact) to give the units still below 3 valid ratings
more raters:

  WAVE 4 (NL family, scores reruns/rater_scores_pooled_w12.json):
    source   = rater_study_wave2.qsf   (the FIELDED wave-2 artifact: decline-ending fix
               in-file, 37 randomizer children byte-identical to wave 1, cc SRRW2AS3BP)
    keep     = ONLY the session blocks containing under-3 units (computed live from the
               pooled w1+w2 scores; expected exactly b36 = units u0701..u0720, 2 ratings each)
    scoring  = the SAME wave-1 instruments/rater_study/rater_study_MAPPING.json (nothing
               renumbered; the surviving child is asserted byte-identical to wave 2 = wave 1)

  WAVE 5 (explicit family, scores reruns/rater_scores_w3.json):
    source   = wave3.qsf               (the FIELDED wave-3 artifact, cc SRRW3NY5CN)
    keep     = ONLY the under-3 blocks (expected exactly b07 = units u0121..u0133 at 1
               rating each, plus the padded u0001..u0007 that ride along by design)
    scoring  = wave3_MAPPING.json

Per wave the FOUR wave-2-style edits and nothing else:
  1. randomizer children restricted to the under-3 blocks (no renumbering);
  2. fresh Prolific completion code in the single Advanced-redirect end node;
  3. qsf_build embedded-data stamp gains a "+waveN-tail-topup" suffix (provenance only);
  4. SurveyEntry.SurveyName gains a WAVE N label (Qualtrics-internal only).
Consent, questions, golds, attention item, decline ending: untouched source bytes. The
script pre-verifies the source against its mapping, applies the edits, re-parses the
output and asserts the post-state (including no drift outside the four edits). No network.

Run:  python build_wave45_qsf.py --wave 4 --code SRRW4XXXXX
      python build_wave45_qsf.py --wave 5 --code SRRW5XXXXX
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
POST1 = os.path.dirname(os.path.dirname(HERE))

WAVES = {
    4: {
        "qsf_in": os.path.join(HERE, "rater_study_wave2.qsf"),
        "mapping": os.path.join(HERE, "rater_study_MAPPING.json"),
        "scores": os.path.join(POST1, "reruns", "rater_scores_pooled_w12.json"),
        "old_cc": "SRRW2AS3BP",
        "qsf_out": os.path.join(HERE, "rater_study_wave4.qsf"),
        "stamp": "+wave4-tail-topup",
        "name": ("Spec-Resistance Rater Study WAVE 4 (tail top-up, NL block(s)): "
                 "Disclosure Coding (C1/C2 crowd)"),
        "n_children_in": 37,
        "expect_blocks": ["b36"],
        "expect_under3": [f"u{n:04d}" for n in range(701, 721)],
    },
    5: {
        "qsf_in": os.path.join(HERE, "wave3.qsf"),
        "mapping": os.path.join(HERE, "wave3_MAPPING.json"),
        "scores": os.path.join(POST1, "reruns", "rater_scores_w3.json"),
        "old_cc": "SRRW3NY5CN",
        "qsf_out": os.path.join(HERE, "wave5.qsf"),
        "stamp": "+wave5-tail-topup",
        "name": ("Spec-Resistance Rater Study WAVE 5 (tail top-up, explicit block(s)): "
                 "Disclosure Coding (C1/C2 crowd)"),
        "n_children_in": 7,
        "expect_blocks": ["b07"],
        "expect_under3": [f"u{n:04d}" for n in range(121, 134)],
    },
}


def stamped(child):
    """randomizer child -> {field: value} for its EmbeddedData setter."""
    return {ed["Field"]: ed.get("Value") for ed in child["EmbeddedData"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wave", type=int, required=True, choices=(4, 5))
    ap.add_argument("--code", required=True, help="fresh Prolific completion code for this wave")
    a = ap.parse_args()
    W = WAVES[a.wave]
    tag = f"[wave{a.wave}]"

    # ---- under-3 units, computed live from the scorer output ----
    scores = json.load(open(W["scores"], encoding="utf-8"))
    assert all(len(v["c1"]) == len(v["c2"]) for v in scores.values()), "c1/c2 rating-count mismatch"
    under3 = sorted(u for u, v in scores.items() if len(v["c1"]) < 3)
    assert under3 == W["expect_under3"], (
        f"under-3 set changed since planning: {under3[:5]}...({len(under3)})")
    print(f"{tag} under-3 units from {os.path.basename(W['scores'])}: {len(under3)} "
          f"({under3[0]}..{under3[-1]}; counts "
          f"{sorted({len(scores[u]['c1']) for u in under3})})")

    mapping = json.load(open(W["mapping"], encoding="utf-8"))
    map_blocks = {b["session_block"]: b["slots"] for b in mapping["blocks"]}
    keep = sorted({sb for sb, slots in map_blocks.items()
                   if any(m["kind"] == "real" and m["unit_id"] in set(under3)
                          for m in slots.values())})
    assert keep == W["expect_blocks"], f"under-3 blocks changed since planning: {keep}"
    covered = {m["unit_id"] for sb in keep for m in map_blocks[sb].values() if m["kind"] == "real"}
    assert set(under3) <= covered, "kept blocks do not cover every under-3 unit"
    places = math.ceil(len(keep) * 3 / 0.42)
    print(f"{tag} under-3 blocks: {keep} (cover {len(covered)} real units incl. all "
          f"{len(under3)} under-3) -> places = ceil({len(keep)}*3/0.42) = {places}")

    qsf = json.load(open(W["qsf_in"], encoding="utf-8"))
    fl = next(e for e in qsf["SurveyElements"] if e["Element"] == "FL")["Payload"]
    flow = fl["Flow"]
    rand = next(el for el in flow if el["Type"] == "BlockRandomizer")

    # ---- pre-verification: expected child count; every child's stamp matches the mapping ----
    assert len(rand["Flow"]) == W["n_children_in"], (
        f"source randomizer child count {len(rand['Flow'])} != {W['n_children_in']}")
    for ch in rand["Flow"]:
        st = stamped(ch)
        sb = st["session_block"]
        for nn, meta in map_blocks[sb].items():
            assert st[f"u{nn}_id"] == meta["unit_id"], f"{sb} slot {nn}: stamped id != mapping"
            assert st[f"u{nn}_kind"] == meta["kind"], f"{sb} slot {nn}: stamped kind != mapping"
    print(f"{tag} pre-verify OK: all {W['n_children_in']} source children stamp exactly the mapping")

    # ---- edit 1: keep only the under-3 blocks' children (original order; no renumbering) ----
    before = [stamped(ch)["session_block"] for ch in rand["Flow"]]
    rand["Flow"] = [ch for ch in rand["Flow"] if stamped(ch)["session_block"] in set(keep)]
    after = [stamped(ch)["session_block"] for ch in rand["Flow"]]
    assert after == [sb for sb in before if sb in set(keep)] and sorted(after) == keep

    # ---- edit 2: fresh completion code in the ONLY Advanced redirect end node ----
    ends = [el for el in flow if el["Type"] == "EndSurvey" and
            (el.get("Options") or {}).get("EOSRedirectURL")]
    assert len(ends) == 1, "expected exactly one redirect EndSurvey node"
    url = ends[0]["Options"]["EOSRedirectURL"]
    assert W["old_cc"] in url, f"source cc not found in redirect url: {url}"
    ends[0]["Options"]["EOSRedirectURL"] = url.replace(W["old_cc"], a.code)

    # ---- edit 3: provenance stamp ----
    for el in flow:
        if el["Type"] == "EmbeddedData":
            for ed in el["EmbeddedData"]:
                if ed["Field"] == "qsf_build" and ed.get("Value"):
                    ed["Value"] = ed["Value"] + W["stamp"]

    # ---- edit 4: Qualtrics-internal survey name ----
    qsf["SurveyEntry"]["SurveyName"] = W["name"]

    with open(W["qsf_out"], "w", encoding="utf-8", newline="\n") as f:
        json.dump(qsf, f, ensure_ascii=False)

    # ---- post-verification on a fresh re-parse ----
    re_q = json.load(open(W["qsf_out"], encoding="utf-8"))
    re_fl = next(e for e in re_q["SurveyElements"] if e["Element"] == "FL")["Payload"]
    re_flow = re_fl["Flow"]
    re_rand = next(el for el in re_flow if el["Type"] == "BlockRandomizer")
    assert sorted(stamped(ch)["session_block"] for ch in re_rand["Flow"]) == keep
    assert len(re_rand["Flow"]) == len(keep)
    assert re_rand["SubSet"] == 1 and re_rand["EvenPresentation"] is True

    # surviving children byte-identical to the source (wave-2 already proved = wave 1)
    orig = json.load(open(W["qsf_in"], encoding="utf-8"))
    orig_rand = next(el for el in
                     next(e for e in orig["SurveyElements"] if e["Element"] == "FL")["Payload"]["Flow"]
                     if el["Type"] == "BlockRandomizer")
    orig_by_sb = {stamped(ch)["session_block"]: ch for ch in orig_rand["Flow"]}
    for ch in re_rand["Flow"]:
        assert ch == orig_by_sb[stamped(ch)["session_block"]], "child drifted from source bytes"

    # decline ending must remain the explicit no-credit DisplayMessage (fix already in-file)
    br = next(el for el in re_flow if el.get("Type") == "Branch"
              and el.get("Description") == "Declined consent")
    dec = next(c for c in br["Flow"] if c.get("Type") == "EndSurvey")
    assert dec["Options"]["SurveyTermination"] == "DisplayMessage"
    assert dec["Options"]["EOSMessage"] == "MS_MaY56WHtI8IcViV"

    # everything OUTSIDE the four edits is byte-identical to the source
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
    assert norm_new == norm_old, "unexpected drift outside the four edits"

    new_url = next(el for el in re_flow if el["Type"] == "EndSurvey" and
                   (el.get("Options") or {}).get("EOSRedirectURL"))["Options"]["EOSRedirectURL"]
    print(f"{tag} wrote {W['qsf_out']} ({os.path.getsize(W['qsf_out'])//1024}KB)")
    print(f"{tag} randomizer children {W['n_children_in']} -> {len(re_rand['Flow'])} (kept {keep})")
    print(f"{tag} completion redirect: {new_url}")
    print(f"{tag} post-verify OK: surviving children byte-identical to source; decline ending "
          f"still explicit DisplayMessage; no other drift")


if __name__ == "__main__":
    main()
