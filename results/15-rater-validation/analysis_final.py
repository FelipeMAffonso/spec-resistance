#!/usr/bin/env python3
"""analysis_final.py - final crowd-coding analysis, reproducible from the files in THIS directory.

Reads the five deposited anonymised wave exports (data/wave{1..5}_responses_anonymised.csv),
scores raters with the registered gates (gold items must match both codes on both golds; the
attention item must be answered exactly as instructed), pools waves 1+2+4 (natural-language units,
wave-1 mapping) and waves 3+5 (supplementary explicit-level units, wave-3 mapping), and computes:
per-unit majorities (mode of the first five valid ratings, >= 3 required; a 2-2-1 split on C1
counts as not-yes), the human-versus-model C1/C2 contrasts (Fisher's exact, one-sided),
Krippendorff's alpha per code, the judge validation (crowd majority versus the deposited corpus
judge on the model units), the registered per-model sensitivity (models with three or more rated
explanations; leave-one-model-out), and the explicit-level block. Writes crowd_FINAL.json and the
per-unit rating lists (unit_ratings_natural_language.json / unit_ratings_explicit.json)."""
import csv, json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_rows(name):
    rows = list(csv.DictReader(open(HERE / "data" / name, encoding="utf-8")))
    return [r for r in rows if r.get("Finished") in ("1", "True")]


def score(rows, mp, per_unit, stats):
    RECODE, GOLD = mp["recode"], mp["gold_key"]
    BLOCKS = {b["session_block"]: b["slots"] for b in mp["blocks"]}
    rc = lambda c, v: RECODE[c].get(str(v).strip(), "")
    for row in rows:
        slots = BLOCKS.get(row.get("session_block"))
        if not slots:
            continue
        stats["sessions"] += 1
        ok = True
        for nn, meta in slots.items():
            a1 = str(row.get(f"u{nn}_c1", "")).strip()
            a2 = str(row.get(f"u{nn}_c2", "")).strip()
            if meta["kind"] == "gold":
                gk = GOLD[meta["unit_id"]]
                if not (rc("c1", a1) == gk["c1"] and rc("c2", a2) == gk["c2"]):
                    ok = False
            elif meta["kind"] == "attn":
                if not (a1 == "1" and a2 == "2"):
                    ok = False
        if not ok:
            stats["excluded"] += 1
            continue
        stats["valid"] += 1
        for nn, meta in slots.items():
            if meta["kind"] != "real":
                continue
            v1, v2 = rc("c1", row.get(f"u{nn}_c1", "")), rc("c2", row.get(f"u{nn}_c2", ""))
            if v1:
                per_unit[meta["unit_id"]]["c1"].append(v1)
            if v2:
                per_unit[meta["unit_id"]]["c2"].append(v2)


def kripp_alpha(per_unit, code):
    """Krippendorff's alpha, nominal, from units with >=2 ratings (first 5 used)."""
    cats = set()
    units = []
    for v in per_unit.values():
        ans = v[code][:5]
        if len(ans) >= 2:
            units.append(ans)
            cats.update(ans)
    cats = sorted(cats)
    o = defaultdict(float)
    n_c = Counter()
    n = 0
    for ans in units:
        m = len(ans)
        cnt = Counter(ans)
        for c in cnt:
            n_c[c] += cnt[c]
            n += cnt[c]
            for k in cnt:
                o[(c, k)] += cnt[c] * (cnt[k] - (1 if c == k else 0)) / (m - 1)
    Do = sum(v for (c, k), v in o.items() if c != k)
    De = sum(n_c[c] * n_c[k] for c in cats for k in cats if c != k) / (n - 1)
    return 1 - Do / De if De else float("nan")


def majority(ans, code):
    c = Counter(ans[:5])
    top, k = c.most_common(1)[0]
    if k >= 3:
        return top
    return "not-yes" if code == "c1" else top


mp1 = json.load(open(HERE / "rater_study_MAPPING.json", encoding="utf-8"))
mp3 = json.load(open(HERE / "wave3_MAPPING.json", encoding="utf-8"))
pu = defaultdict(lambda: {"c1": [], "c2": []})
pu3 = defaultdict(lambda: {"c1": [], "c2": []})
S = {}
for name, fname, mp, target in [("w1", "wave1_responses_anonymised.csv", mp1, pu),
                                ("w2", "wave2_responses_anonymised.csv", mp1, pu),
                                ("w4", "wave4_responses_anonymised.csv", mp1, pu),
                                ("w3", "wave3_responses_anonymised.csv", mp3, pu3),
                                ("w5", "wave5_responses_anonymised.csv", mp3, pu3)]:
    st = Counter()
    score(load_rows(fname), mp, target, st)
    S[name] = dict(st)
    print(name, dict(st))

srcmap = json.load(open(HERE / "rater_units_SOURCEMAP.json", encoding="utf-8"))["units"]
SRC = {k: ("model" if (isinstance(v, dict) and v.get("model_key")) else "human") for k, v in srcmap.items()}
MODEL_OF = {k: v.get("model_key") for k, v in srcmap.items() if isinstance(v, dict) and v.get("model_key")}

res = {"sessions": S}
tab = {"human": {"c1": [0, 0], "c2": [0, 0]}, "model": {"c1": [0, 0], "c2": [0, 0]}}
cov = Counter()
for uid, v in pu.items():
    n = len(v["c1"])
    cov[min(n, 5)] += 1
    if n < 3:
        continue
    s = SRC.get(uid, "?")
    for code in ("c1", "c2"):
        verdict = majority(v[code], code)
        tab[s][code][0] += int(verdict == "yes")
        tab[s][code][1] += 1
print("\nNL POOLED coverage:", dict(sorted(cov.items())), "| under-3:", sum(1 for v in pu.values() if len(v["c1"]) < 3))
for s in ("human", "model"):
    a = tab[s]
    print(f"  {s.upper():6s}: C1 {100*a['c1'][0]/a['c1'][1]:5.1f}% ({a['c1'][0]}/{a['c1'][1]}) | C2 {100*a['c2'][0]/a['c2'][1]:5.1f}% ({a['c2'][0]}/{a['c2'][1]})")
res["nl"] = tab
res["nl_coverage"] = dict(sorted(cov.items()))

from scipy.stats import fisher_exact
f = {}
for code, alt in (("c1", "less"), ("c2", "greater")):
    h_yes, h_n = tab["human"][code]
    m_yes, m_n = tab["model"][code]
    OR, p = fisher_exact([[h_yes, h_n - h_yes], [m_yes, m_n - m_yes]], alternative=alt)
    f[code] = {"OR": round(OR, 3), "p_one_sided": float(f"{p:.3g}")}
    print(f"  Fisher {code} one-sided ({alt}): OR={OR:.3f} P={p:.3g}")
res["fisher"] = f

a1 = kripp_alpha(pu, "c1")
a2 = kripp_alpha(pu, "c2")
print(f"  Krippendorff alpha NL: c1={a1:.3f} c2={a2:.3f}")
res["alpha_nl"] = {"c1": round(a1, 3), "c2": round(a2, 3)}

cache = json.load(open(HERE / "corpus_judge_codes_for_rater_units.json", encoding="utf-8"))
unit2ref = {u: r for r, u in cache["ref2unit"].items()}
n = agree = 0
for uid, v in pu.items():
    ref = unit2ref.get(uid)
    if not ref or len(v["c2"]) < 3:
        continue
    j = cache["judge"].get(ref)
    if not j or j["judge_brand_reasoning"] is None:
        continue
    crowd = majority(v["c2"], "c2") == "yes"
    n += 1
    agree += int(crowd == bool(j["judge_brand_reasoning"]))
po = agree / n
cells = Counter()
for uid, v in pu.items():
    ref = unit2ref.get(uid)
    if not ref or len(v["c2"]) < 3:
        continue
    j = cache["judge"].get(ref)
    if not j or j["judge_brand_reasoning"] is None:
        continue
    cells[(bool(j["judge_brand_reasoning"]), majority(v["c2"], "c2") == "yes")] += 1
pj = sum(v for (jj, c), v in cells.items() if jj) / n
pc = sum(v for (jj, c), v in cells.items() if c) / n
pe = pj * pc + (1 - pj) * (1 - pc)
kap = (po - pe) / (1 - pe)
print(f"  JUDGE VALIDATION: {100*po:.1f}% ({agree}/{n}) kappa={kap:.2f}")
res["judge"] = {"agree_pct": round(100 * po, 1), "n": n, "kappa": round(kap, 2)}

# registered per-model sensitivity (models with >= 3 rated explanations; leave-one-model-out)
pm = defaultdict(lambda: {"c1": [0, 0], "c2": [0, 0]})
for uid, v in pu.items():
    if len(v["c1"]) < 3:
        continue
    mk = MODEL_OF.get(uid)
    if not mk:
        continue
    for code in ("c1", "c2"):
        pm[mk][code][0] += int(majority(v[code], code) == "yes")
        pm[mk][code][1] += 1
elig = {m: d for m, d in pm.items() if d["c2"][1] >= 3}
rates2 = sorted(100 * d["c2"][0] / d["c2"][1] for d in elig.values())
rates1 = sorted(100 * d["c1"][0] / d["c1"][1] for d in elig.values())
h2y, h2n = tab["human"]["c2"]
h1y, h1n = tab["human"]["c1"]
worst_p2 = 0.0
c1_flips = 0
for m in elig:
    m2y = sum(d["c2"][0] for k, d in elig.items() if k != m)
    m2n = sum(d["c2"][1] for k, d in elig.items() if k != m)
    _, p = fisher_exact([[h2y, h2n - h2y], [m2y, m2n - m2y]], alternative="greater")
    worst_p2 = max(worst_p2, p)
    m1y = sum(d["c1"][0] for k, d in elig.items() if k != m)
    m1n = sum(d["c1"][1] for k, d in elig.items() if k != m)
    if (h1y / h1n) >= (m1y / m1n):
        c1_flips += 1
res["per_model_sensitivity"] = {
    "n_models_eligible": len(elig),
    "units_per_model_min": min(d["c2"][1] for d in elig.values()),
    "units_per_model_max": max(d["c2"][1] for d in elig.values()),
    "c2_admission_pct": {"min": round(rates2[0], 1), "median": round(rates2[len(rates2) // 2], 1),
                         "max": round(rates2[-1], 1),
                         "n_at_or_above_human": sum(1 for p_ in rates2 if p_ >= 100 * h2y / h2n)},
    "c1_false_claim_pct": {"min": round(rates1[0], 1), "median": round(rates1[len(rates1) // 2], 1),
                           "max": round(rates1[-1], 1)},
    "c2_leave_one_model_out_worst_p": float(f"{worst_p2:.3g}"),
    "c1_leave_one_model_out_direction_flips": c1_flips,
    "per_model": {m: {"c1": d["c1"], "c2": d["c2"]} for m, d in sorted(elig.items())},
}
s = res["per_model_sensitivity"]
print(f"  PER-MODEL SENSITIVITY: {s['n_models_eligible']} models ({s['units_per_model_min']}-{s['units_per_model_max']} units); "
      f"C2 {s['c2_admission_pct']['min']}-{s['c2_admission_pct']['max']} (median {s['c2_admission_pct']['median']}), "
      f"{s['c2_admission_pct']['n_at_or_above_human']} at/above human; LOMO worst P={s['c2_leave_one_model_out_worst_p']} | "
      f"C1 direction flips {s['c1_leave_one_model_out_direction_flips']}")

t3 = {"c1": [0, 0], "c2": [0, 0]}
cov3 = Counter()
for uid, v in pu3.items():
    n_ = len(v["c1"])
    cov3[min(n_, 5)] += 1
    if n_ < 3:
        continue
    for code in ("c1", "c2"):
        t3[code][0] += int(majority(v[code], code) == "yes")
        t3[code][1] += 1
a31 = kripp_alpha(pu3, "c1")
a32 = kripp_alpha(pu3, "c2")
print(f"\nEXPLICIT (w3+w5) coverage: {dict(sorted(cov3.items()))} | under-3: {sum(1 for v in pu3.values() if len(v['c1'])<3)}")
print(f"  C1 {100*t3['c1'][0]/t3['c1'][1]:5.1f}% ({t3['c1'][0]}/{t3['c1'][1]}) | C2 {100*t3['c2'][0]/t3['c2'][1]:5.1f}% ({t3['c2'][0]}/{t3['c2'][1]}) | alpha c1={a31:.3f} c2={a32:.3f}")
res["explicit"] = {"c1": t3["c1"], "c2": t3["c2"], "coverage": dict(sorted(cov3.items())),
                   "alpha": {"c1": round(a31, 3), "c2": round(a32, 3)}}

json.dump(res, open(HERE / "crowd_FINAL.json", "w"), indent=1)
json.dump({k: v for k, v in pu.items()}, open(HERE / "unit_ratings_natural_language.json", "w"))
json.dump({k: v for k, v in pu3.items()}, open(HERE / "unit_ratings_explicit.json", "w"))
print("\n-> crowd_FINAL.json + unit_ratings_natural_language.json + unit_ratings_explicit.json")
