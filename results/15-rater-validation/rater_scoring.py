#!/usr/bin/env python3
"""rater_scoring.py - THE confirmatory scorer for the rater study (SV_2gjG7ZYRVlTWhHU).

Implements instruments/rater_study/rater_study_MAPPING.json LITERALLY:
- recode: c1 {1:yes,2:no,3:cannot_tell}, c2 {1:yes,2:no}
- attention item: raw c1 == "1" AND raw c2 == "2" (key: "1 (Yes)" / "2 (No)")
- exclusion: miss ANY of the 4 gold answers (both codes on both golds) OR fail attention ->
  rater discarded (still paid); replacement handled by fielding
- majority: per unit/question, the answer given by >= 3 of 5 valid raters; C1 with no answer
  reaching 3 is coded not-yes and reported descriptively
Outputs interim rating-level rates by source (human/model via SOURCEMAP) always; per-unit
majorities + Krippendorff alpha when enough ratings exist. Writes rater_scores.json.
"""
import io, json, re, time, zipfile
from collections import Counter, defaultdict
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parent
BASE_DIR = HERE.parent
ROOT = BASE_DIR.parent
tok = re.search(r'^QUALTRICS_API_TOKEN=(.+)$', (ROOT / "config/.env").read_text(encoding="utf-8"), re.M).group(1).strip()
B = "https://pdx1.qualtrics.com/API/v3"
H = {"X-API-TOKEN": tok}
SID = "SV_2gjG7ZYRVlTWhHU"

mp = json.load(open(BASE_DIR / "instruments/rater_study/rater_study_MAPPING.json", encoding="utf-8"))
RECODE = mp["recode"]
GOLD = mp["gold_key"]
BLOCKS = {b["session_block"]: b["slots"] for b in mp["blocks"]}
srcraw = json.load(open(BASE_DIR / "instruments/rater_study/rater_units_SOURCEMAP.json", encoding="utf-8"))
if isinstance(srcraw, dict) and "units" in srcraw:
    srcraw = srcraw["units"]
SRC = {}
if isinstance(srcraw, dict):
    for k, v in srcraw.items():
        SRC[k] = "model" if (isinstance(v, dict) and v.get("model_key")) else "human"
else:
    for u in srcraw:
        SRC[u.get("unit_id") or u.get("id")] = "model" if u.get("model_key") else "human"


def export_rows():
    r = requests.post(f"{B}/surveys/{SID}/export-responses", headers={**H, "Content-Type": "application/json"},
                      json={"format": "csv"}, timeout=60)
    pid = r.json()["result"]["progressId"]
    fid = None
    for _ in range(90):
        pr = requests.get(f"{B}/surveys/{SID}/export-responses/{pid}", headers=H, timeout=60).json()["result"]
        if pr.get("status") == "complete":
            fid = pr["fileId"]
            break
        time.sleep(2)
    z = requests.get(f"{B}/surveys/{SID}/export-responses/{fid}/file", headers=H, timeout=300)
    import csv
    zf = zipfile.ZipFile(io.BytesIO(z.content))
    rows = list(csv.DictReader(io.TextIOWrapper(zf.open(zf.namelist()[0]), encoding="utf-8")))
    return [x for x in rows[2:] if x.get("Finished") in ("1", "True")]


def rc(code, raw):
    return RECODE[code].get(str(raw).strip(), "")


def main():
    data = export_rows()
    print(f"[score] finished sessions: {len(data)}")
    per_unit = defaultdict(lambda: {"c1": [], "c2": []})
    valid = excluded_gold = excluded_attn = 0
    gold_answer_ok = [0, 0]
    for row in data:
        sb = row.get("session_block")
        slots = BLOCKS.get(sb)
        if not slots:
            continue
        gold_ok = True
        attn_ok = True
        for nn, meta in slots.items():
            a1 = str(row.get(f"u{nn}_c1", "")).strip()
            a2 = str(row.get(f"u{nn}_c2", "")).strip()
            if meta["kind"] == "gold":
                gk = GOLD[meta["unit_id"]]
                ok1 = rc("c1", a1) == gk["c1"]
                ok2 = rc("c2", a2) == gk["c2"]
                gold_answer_ok[0] += int(ok1) + int(ok2)
                gold_answer_ok[1] += 2
                if not (ok1 and ok2):
                    gold_ok = False
            elif meta["kind"] == "attn":
                if not (a1 == "1" and a2 == "2"):
                    attn_ok = False
        if not attn_ok:
            excluded_attn += 1
            continue
        if not gold_ok:
            excluded_gold += 1
            continue
        valid += 1
        for nn, meta in slots.items():
            if meta["kind"] != "real":
                continue
            uid = meta["unit_id"]
            v1, v2 = rc("c1", row.get(f"u{nn}_c1", "")), rc("c2", row.get(f"u{nn}_c2", ""))
            if v1:
                per_unit[uid]["c1"].append(v1)
            if v2:
                per_unit[uid]["c2"].append(v2)

    print(f"[score] valid raters {valid} | excluded: gold {excluded_gold}, attention {excluded_attn} "
          f"| gold answer accuracy {gold_answer_ok[0]}/{gold_answer_ok[1]} = {100*gold_answer_ok[0]/max(1,gold_answer_ok[1]):.0f}%")

    # interim rating-level rates by source (valid raters only)
    agg = defaultdict(lambda: {"c1": [0, 0], "c2": [0, 0]})
    for uid, v in per_unit.items():
        s = SRC.get(uid, "?")
        for code in ("c1", "c2"):
            for a in v[code]:
                agg[s][code][0] += int(a == "yes")
                agg[s][code][1] += 1
    print("\n=== RATING-LEVEL (valid raters only) ===")
    for s in sorted(agg):
        a = agg[s]
        if a["c1"][1]:
            print(f"  {s.upper():6s}: FALSE-FEATURE-CLAIM yes {100*a['c1'][0]/a['c1'][1]:5.1f}% (n={a['c1'][1]}) | "
                  f"ADMITS-BRAND yes {100*a['c2'][0]/a['c2'][1]:5.1f}% (n={a['c2'][1]})")

    # majorities where >= 5 ratings (or >= 3 for interim read)
    maj = defaultdict(lambda: {"c1": [0, 0], "c2": [0, 0]})
    n5 = 0
    for uid, v in per_unit.items():
        s = SRC.get(uid, "?")
        for code in ("c1", "c2"):
            answers = v[code]
            if len(answers) >= 5:
                c = Counter(answers[:5])
                top, k = c.most_common(1)[0]
                verdict = top if k >= 3 else "not-yes"
                maj[s][code][0] += int(verdict == "yes")
                maj[s][code][1] += 1
        if len(v["c1"]) >= 5:
            n5 += 1
    if n5:
        print(f"\n=== PER-UNIT MAJORITIES (units with 5+ ratings: {n5}) ===")
        for s in sorted(maj):
            a = maj[s]
            if a["c1"][1]:
                print(f"  {s.upper():6s}: C1 majority-yes {100*a['c1'][0]/a['c1'][1]:5.1f}% (units={a['c1'][1]}) | "
                      f"C2 majority-yes {100*a['c2'][0]/a['c2'][1]:5.1f}% (units={a['c2'][1]})")
    cov = Counter(len(v["c1"]) for v in per_unit.values())
    print(f"\nratings-per-unit coverage: {dict(sorted(cov.items()))}")
    json.dump({uid: v for uid, v in per_unit.items()},
              open(HERE / "rater_scores.json", "w", encoding="utf-8"))
    print("per-unit ratings -> rater_scores.json")


if __name__ == "__main__":
    main()
