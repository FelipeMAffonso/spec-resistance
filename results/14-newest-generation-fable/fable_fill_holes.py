#!/usr/bin/env python3
"""Re-run the truncation-holed Fable trials (keys in fable_holes.json) at the raised token
ceiling with the fixed parser, then rebuild the deduplicated final summary (last valid record
per key wins). Appends to the same JSONL; writes fable_cell_FINAL.json with the clean records."""
import json, re, sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fc", HERE / "fable_cell_run.py")
fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc)

holes = set(json.load(open(HERE / "fable_holes.json", encoding="utf-8")))
print(f"[fill] re-running {len(holes)} holed trials at max_tokens 900")
fc.done = set()  # allow re-run; dedup happens below by taking the LAST valid record per key
by_id = {a["id"]: a for a in fc.ALL_ASSORTMENTS}
jobs = []
for k in holes:
    aid, cond, trial = k.rsplit("|", 2)
    jobs.append((by_id[aid], cond, int(trial)))

with ThreadPoolExecutor(max_workers=6) as ex:
    futs = [ex.submit(fc.one, a, c, t) for a, c, t in jobs]
    n = 0
    for f in as_completed(futs):
        n += 1
        if n % 40 == 0:
            print(f"[fill] {n}/{len(futs)}")

# final dedup pass: last valid (A-E) record per key wins; recovery regex for stragglers
best = {}
for ln in (HERE / "fable_cell_results.jsonl").read_text(encoding="utf-8").splitlines():
    try:
        r = json.loads(ln)
    except Exception:
        continue
    if "error" in r:
        continue
    if r["choice"] not in "ABCDE":
        m = re.search(r'"choice"\s*:\s*"([A-Ea-e])"', r.get("why", "") or "")
        if m:
            r["choice"] = m.group(1).upper()
            r["is_optimal"] = int(r["choice"] == r["optimal_letter"])
    if r["choice"] in "ABCDE" or r["key"] not in best:
        prev = best.get(r["key"])
        if prev is None or prev["choice"] not in "ABCDE":
            best[r["key"]] = r

agg = defaultdict(lambda: [0, 0])
missing = 0
for r in best.values():
    if r["choice"] in "ABCDE":
        agg[r["condition"]][0] += r["is_optimal"]
        agg[r["condition"]][1] += 1
    else:
        missing += 1
print(f"\n=== FABLE 5 CELL, FINAL ({sum(m for _, m in agg.values())} valid of 1,020; {missing} still missing) ===")
anchors = {"baseline": 75.0, "preference_weighted": 82.6, "preference_explicit": 99.63}
for c in ("baseline", "preference_weighted", "preference_explicit"):
    k, m = agg[c]
    if m:
        print(f"  {c:22s} n={m:3d}  {100*k/m:5.1f}% optimal   (corpus {anchors[c]})")
json.dump(sorted(best.values(), key=lambda r: r["key"]),
          open(HERE / "fable_cell_FINAL.json", "w", encoding="utf-8"), indent=1)
print("final records -> fable_cell_FINAL.json")
