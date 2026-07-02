#!/usr/bin/env python3
"""analysis_confirmatory_numbers.py - reproduces every manuscript number for the human-advisor
benchmark from the files in THIS directory alone.

Inputs: anonymised.csv (1,209 finished survey rows, identifiers stripped, participant_id
pseudonyms, approved_submission = True for the 1,200 valid Prolific submissions) and
model_arm_dose_response.json (the matched model arm re-derived from the deposited corpus for the
five benchmark assortments). Dataset rule (registered): restrict to approved submissions, then the
pre-registered exclusions (attention, duration 60-1200 s, duplicate participant, recorded choice).
Registered P1 inference = wild cluster bootstrap over the 30 models (seed 20260701, B = 100,000).
Also computes the pre-registered section-5 robustness recomputes, the demand-effect bound, the
matched believability measure, and the registered secondaries. Emits confirmatory_numbers.json.
"""
import csv, json, math, random
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parent

MJ = json.loads((HERE / "model_arm_dose_response.json").read_text(encoding="utf-8"))
LEVELMAP = {"baseline": "baseline", "weighted": "preference_weighted", "explicit_numeric": "preference_explicit"}
NL = {"baseline", "weighted"}
ASSORT_LABEL = {"sr_coffee_makers_02": "espresso machines", "sr_coffee_makers_03": "single-serve and travel coffee",
                "sr_tvs_03": "televisions", "sr_earbuds_03": "earbuds", "sr_headphones_03": "audiophile headphones"}


def truthy(v):
    return str(v).strip().lower() in ("true", "1", "1.0")


def num(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def wilson(k, n):
    p = k / n
    z = 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)


def apply_exclusions(rows):
    """Pre-registered exclusions (prereg section 6): not Finished, failed attention, time <60 s or
    >1200 s, duplicate participant (first kept), no single recommendation."""
    seen = set()
    kept, excl = [], Counter()
    for r in rows:
        if not truthy(r.get("Finished")):
            excl["not_finished"] += 1
            continue
        att = str(r.get("attention_1", "")).strip().lower()
        if not ("very important" in att or att == "4"):
            excl["failed_attention"] += 1
            continue
        dur = num(r.get("Duration (in seconds)"))
        if dur is None or dur < 60 or dur > 1200:
            excl["time_out_of_bounds"] += 1
            continue
        pid = r.get("participant_id", "")
        if pid and pid in seen:
            excl["duplicate_pid"] += 1
            continue
        if pid:
            seen.add(pid)
        if str(r.get("choice_is_optimal", "")).strip() == "" and str(r.get("choice_index", "")).strip() == "":
            excl["no_single_recommendation"] += 1
            continue
        kept.append(r)
    return kept, excl


rows = list(csv.DictReader(open(HERE / "anonymised.csv", encoding="utf-8")))
pre = [r for r in rows if truthy(r.get("approved_submission"))]
print(f"finished rows {len(rows)} | approved submissions {len(pre)}")
kept, excl = apply_exclusions(pre)
N_KEPT = len(kept)
print(f"KEPT {N_KEPT} (excl {dict(excl)})")

OUT = {"n_recruited": 1200, "n_finished_rows": len(rows), "n_pid_valid": len(pre),
       "exclusions": dict(excl), "n_kept": N_KEPT}


def model_occ(sub, levels):
    """occupancy-weighted matched model %optimal over sub's (assortment, level) cells"""
    w = Counter((r.get("assortment_id"), r.get("assigned_level")) for r in sub
                if r.get("assigned_level") in levels)
    tot = sum(w.values())
    return sum(c / tot * MJ["assortments"][a][LEVELMAP[l]]["pooled_pct_optimal"] for (a, l), c in w.items())


def human_rate(sub):
    k = sum(1 for r in sub if truthy(r.get("choice_is_optimal")))
    return k, len(sub), 100 * k / len(sub) if sub else 0


nl = [r for r in kept if r.get("assigned_level") in NL]
k_nl, n_nl, p_nl = human_rate(nl)
m_nl = model_occ(nl, NL)
lo, hi = wilson(k_nl, n_nl)
OUT["nl"] = {"k": k_nl, "n": n_nl, "pct": round(p_nl, 1), "wilson": [round(lo, 1), round(hi, 1)],
             "model_pct": round(m_nl, 1), "gap_pp": round(p_nl - m_nl, 1)}
print(f"\nNL: human {k_nl}/{n_nl} = {p_nl:.1f}% (Wilson {lo:.1f}-{hi:.1f}) vs model {m_nl:.1f}% -> gap {p_nl-m_nl:.1f}")

# per frame
OUT["frames"] = {}
for fr in ("advise_other", "choose_self"):
    sub = [r for r in nl if r.get("assigned_frame") == fr]
    k, n, p = human_rate(sub)
    m = model_occ(sub, NL)
    OUT["frames"][fr] = {"k": k, "n": n, "pct": round(p, 1), "model_pct": round(m, 1), "gap_pp": round(p - m, 1)}
    print(f"  frame {fr}: human {p:.1f}% (n={n}) vs model {m:.1f}% -> +{p-m:.1f}")

# per level (fig7 panel a)
OUT["levels"] = {}
for lv in ("baseline", "weighted", "explicit_numeric"):
    sub = [r for r in kept if r.get("assigned_level") == lv]
    k, n, p = human_rate(sub)
    m = model_occ(sub, {lv})
    OUT["levels"][lv] = {"k": k, "n": n, "pct": round(p, 1), "model_pct": round(m, 1)}
    print(f"  level {lv}: human {k}/{n} = {p:.1f}% vs model {m:.1f}%")

# per assortment at NL (+ earbuds rule)
OUT["assortments_nl"] = {}
for aid in sorted(ASSORT_LABEL):
    sub = [r for r in nl if r.get("assortment_id") == aid]
    k, n, p = human_rate(sub)
    m = model_occ(sub, NL)
    OUT["assortments_nl"][aid] = {"label": ASSORT_LABEL[aid], "k": k, "n": n, "pct": round(p, 1),
                                  "model_pct": round(m, 1), "gap_pp": round(p - m, 1)}
    print(f"  {aid:24s} human {p:.1f}% (n={n}) vs model {m:.1f}% -> {p-m:+.1f}")

# comprehension + passers
def comp_ok(r):
    cv = str(r.get("comprehension_1", "")).strip().lower()
    ck = str(r.get("comp_correct", "")).strip()
    return (cv == ck.lower()) if ck else cv in ("1", "true")


passers_all = [r for r in kept if comp_ok(r)]
nl_pass = [r for r in nl if comp_ok(r)]
kp, np_, pp_ = human_rate(nl_pass)
mp_ = model_occ(nl_pass, NL)
OUT["comprehension"] = {"pass_pct_kept": round(100 * len(passers_all) / N_KEPT, 1),
                        "nl_passers": {"k": kp, "n": np_, "pct": round(pp_, 1),
                                       "model_pct": round(mp_, 1), "gap_pp": round(pp_ - mp_, 1)}}
print(f"  comprehension pass {100*len(passers_all)/N_KEPT:.1f}% | NL passers {pp_:.1f}% vs {mp_:.1f}% (n={np_})")

# forced brand-influence probe
def probe(r):
    v = str(r.get("brand_influence", "")).strip()
    return float(v) if v.replace(".", "", 1).isdigit() else None


def pmean(sub):
    vals = [probe(r) for r in sub]
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


ex = [r for r in kept if r.get("assigned_level") == "explicit_numeric"]
OUT["probe"] = {"all_kept": pmean(kept),
                "nl_nonopt": pmean([r for r in nl if not truthy(r.get("choice_is_optimal"))]),
                "nl_opt": pmean([r for r in nl if truthy(r.get("choice_is_optimal"))]),
                "explicit_nonopt": pmean([r for r in ex if not truthy(r.get("choice_is_optimal"))]),
                "n_nl_nonopt": sum(1 for r in nl if not truthy(r.get("choice_is_optimal")))}
print(f"  probe: all {OUT['probe']['all_kept']} | NL nonopt {OUT['probe']['nl_nonopt']} "
      f"(n={OUT['probe']['n_nl_nonopt']}) | NL opt {OUT['probe']['nl_opt']} | explicit nonopt {OUT['probe']['explicit_nonopt']}")
bt = [probe(r) for r in ex if not truthy(r.get("choice_is_optimal")) and probe(r) is not None]
OUT["probe"]["explicit_nonopt_bottom_two"] = {"k": sum(1 for v in bt if v <= 2), "n": len(bt),
                                              "pct": round(100 * sum(1 for v in bt if v <= 2) / len(bt), 1)}
print(f"  explicit nonopt bottom-two share: {OUT['probe']['explicit_nonopt_bottom_two']}")

# registered P1: wild cluster bootstrap over 30 models
MODELS = sorted(next(iter(MJ["per_model"].values()))["baseline"].keys())
cellw = Counter((r.get("assortment_id"), r.get("assigned_level")) for r in nl)
share_m = {m: sum(c / n_nl * MJ["per_model"][a][LEVELMAP[l]][m] for (a, l), c in cellw.items())
           for m in MODELS}
mu = sum(share_m.values()) / 30
dev = [v - mu for v in share_m.values()]
rng = random.Random(20260701)
B = 100_000
g = []
for _ in range(B):
    hb = 100 * sum(1 for _ in range(n_nl) if rng.random() < k_nl / n_nl) / n_nl
    mw = mu + sum(d * (1 if rng.random() < 0.5 else -1) for d in dev) / 30
    g.append(hb - mw)
g.sort()
gap = p_nl - mu
se = (sum((x - sum(g) / B) ** 2 for x in g) / (B - 1)) ** 0.5
def ptail(z): return 0.5 * math.erfc(z / math.sqrt(2))
OUT["registered_p1"] = {"model_level_mean": round(mu, 1), "gap_pp": round(gap, 1),
                        "wild_ci": [round(g[int(0.025 * B)], 1), round(g[int(0.975 * B)], 1)],
                        "boot_se": round(se, 2),
                        "z_vs_zero": round(gap / se, 1), "p_vs_zero": f"{ptail(gap/se):.1g}",
                        "z_vs_margin10": round((gap - 10) / se, 1), "p_vs_margin10": f"{ptail((gap-10)/se):.1g}"}
print(f"\nREGISTERED P1: model-level mean {mu:.1f} | gap {gap:.1f} | wild CI {g[int(0.025*B)]:.1f}-{g[int(0.975*B)]:.1f} "
      f"| z0 {gap/se:.1f} (P {ptail(gap/se):.1g}) | z10 {(gap-10)/se:.1f} (P {ptail((gap-10)/se):.1g})")

# ---- registered robustness recomputes (prereg section 5) + matched additional measures ----
def iv(r, col):
    v = str(r.get(col, "")).strip()
    return int(v) if v.isdigit() else None


def mean_of(sub, col):
    vals = [iv(r, col) for r in sub if iv(r, col) is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def h1_on(sub, label):
    k, n, p = human_rate(sub)
    m = model_occ(sub, NL)
    print(f"  H1 {label:34s} human {p:.1f}% ({k}/{n}) vs model {m:.1f}% -> +{p-m:.1f}")
    return {"k": k, "n": n, "pct": round(p, 1), "model_pct": round(m, 1), "gap_pp": round(p - m, 1)}


print("\nREGISTERED ROBUSTNESS (prereg section 5):")
OUT["robustness_prereg"] = {
    "excl_familiar_with_dominant": h1_on([r for r in nl if iv(r, "fam_dominant") == 1],
                                         "excl any fictional-brand familiarity"),
    "excl_toogood_top": h1_on([r for r in nl if iv(r, "too_good_to_be_true") != 5],
                              "excl too-good = 5 (strongly agree)"),
    "excl_toogood_agree_plus": h1_on([r for r in nl if (iv(r, "too_good_to_be_true") or 0) < 4],
                                     "excl too-good >= 4 (agree or above)"),
    "excl_hypothesis_guessers": h1_on([r for r in nl if "brand" not in str(r.get("suspicion_open", "")).lower()],
                                      "excl suspicion mentions 'brand'"),
}

# demand-effect bound: NL human optimal rate within each demand framing
dem = {}
for r in nl:
    t = str(r.get("demand_framing", "")).strip()
    key = "spec_expectation" if "best on the listed specifications" in t else \
          ("brand_stick" if "stick with the brand" in t else "none")
    dem.setdefault(key, []).append(r)
OUT["demand_bound"] = {k: {"k": human_rate(v)[0], "n": human_rate(v)[1], "pct": round(human_rate(v)[2], 1)}
                       for k, v in sorted(dem.items())}
print("  demand bound (NL human %optimal by framing):",
      {k: v["pct"] for k, v in OUT["demand_bound"].items()})

# belief battery: NL optimal conditional on each item (disagree 1-2 / neutral 3 / agree 4-5)
BELIEFS = ("belief_neutral", "belief_moreinfo", "belief_personalised", "belief_real", "belief_pickedbest")
bc = {}
for col in BELIEFS:
    ent = {}
    for band, lo_, hi_ in (("disagree", 1, 2), ("neutral", 3, 3), ("agree", 4, 5)):
        sub = [r for r in nl if iv(r, col) is not None and lo_ <= iv(r, col) <= hi_]
        kb, nb_, pb_ = human_rate(sub)
        ent[band] = {"k": kb, "n": nb_, "pct": round(pb_, 1)}
    bc[col] = ent
OUT["belief_conditionals_nl"] = bc
print("  belief conditionals (NL %optimal):", {c: {b: v["pct"] for b, v in e.items()} for c, e in bc.items()})

# believability of the fictional-named dominant (1-5), matched to the model-side elicitation
nl_nonopt_rows = [r for r in nl if not truthy(r.get("choice_is_optimal"))]
nl_opt_rows = [r for r in nl if truthy(r.get("choice_is_optimal"))]
bel_vals = [iv(r, "believability_dominant") for r in kept if iv(r, "believability_dominant")]
OUT["believability"] = {"kept_mean": mean_of(kept, "believability_dominant"),
                        "nl_mean": mean_of(nl, "believability_dominant"),
                        "nl_opt_mean": mean_of(nl_opt_rows, "believability_dominant"),
                        "nl_nonopt_mean": mean_of(nl_nonopt_rows, "believability_dominant"),
                        "kept_pct_moderate_plus": round(100 * sum(1 for v in bel_vals if v >= 3) / len(bel_vals), 1),
                        "too_good_kept_mean": mean_of(kept, "too_good_to_be_true")}
print(f"  believability (1-5): kept {OUT['believability']['kept_mean']} | NL opt {OUT['believability']['nl_opt_mean']} "
      f"vs NL nonopt {OUT['believability']['nl_nonopt_mean']} | >=moderate {OUT['believability']['kept_pct_moderate_plus']}% "
      f"| too-good mean {OUT['believability']['too_good_kept_mean']}")

# registered secondary: DiD of the baseline-to-weighted change, human vs model (two-sided)
def level_rows(lv):
    return [r for r in kept if r.get("assigned_level") == lv]


hb_rows, hw_rows = level_rows("baseline"), level_rows("weighted")
kb, nb, pb = human_rate(hb_rows)
kw, nw, pw = human_rate(hw_rows)


def model_per_model_occ(sub, lv):
    w = Counter(r.get("assortment_id") for r in sub)
    tot = sum(w.values())
    return {m: sum(c / tot * MJ["per_model"][a][LEVELMAP[lv]][m] for a, c in w.items()) for m in MODELS}


mb, mw_ = model_per_model_occ(hb_rows, "baseline"), model_per_model_occ(hw_rows, "weighted")
mdiff = {m: mw_[m] - mb[m] for m in MODELS}
mu_d = sum(mdiff.values()) / 30
dev_d = [v - mu_d for v in mdiff.values()]
did = (pw - pb) - mu_d
rng2 = random.Random(20260702)
g2 = []
for _ in range(B):
    hb_ = 100 * sum(1 for _ in range(nb) if rng2.random() < kb / nb) / nb
    hw2 = 100 * sum(1 for _ in range(nw) if rng2.random() < kw / nw) / nw
    md = mu_d + sum(d * (1 if rng2.random() < 0.5 else -1) for d in dev_d) / 30
    g2.append((hw2 - hb_) - md)
se2 = (sum((x - sum(g2) / B) ** 2 for x in g2) / (B - 1)) ** 0.5
p_did = 2 * ptail(abs(did) / se2)
OUT["did_secondary"] = {"human_delta_pp": round(pw - pb, 1), "model_delta_pp": round(mu_d, 1),
                        "did_pp": round(did, 1), "boot_se": round(se2, 2), "p_two_sided": f"{p_did:.2g}"}
print(f"  DiD baseline->weighted: human +{pw-pb:.1f} vs model +{mu_d:.1f} -> DiD {did:+.1f} (P = {p_did:.2g})")

# registered secondary: human explicit vs human natural-language rate (two-sided)
from scipy.stats import fisher_exact as _fx
k_ex, n_ex, p_ex = human_rate(ex)
_or, p_exnl = _fx([[k_ex, n_ex - k_ex], [k_nl, n_nl - k_nl]], alternative="two-sided")
OUT["explicit_vs_nl_human"] = {"explicit": [k_ex, n_ex, round(p_ex, 1)], "nl": [k_nl, n_nl, round(p_nl, 1)],
                               "p_two_sided": f"{p_exnl:.2g}"}
print(f"  human explicit {p_ex:.1f}% vs NL {p_nl:.1f}%: two-sided Fisher P = {p_exnl:.2g}")

json.dump(OUT, open(HERE / "confirmatory_numbers.json", "w"), indent=1)
print("\n-> confirmatory_numbers.json")
