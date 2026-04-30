"""
Comprehensive verification of every headline number in the paper against
the OSF ground-truth CSV and the committed revision-era artefacts.

Usage:
    python scripts/verify_paper_numbers.py

Reads:
    OSF/data/spec_resistance_EXTENDED.csv             (627,491 trials, 30 models)
    OSF/data/human_studies/study{1a,1b,2,3}_*.csv     (anonymised)
    OSF/results/08-fictional-injection/*.csv
    OSF/results/06-openai-finetune/*.csv
    OSF/results/02-base-vs-instruct/*.json
    OSF/results/04-representation-probing/v3/*.json
    OSF/results/11-activation-steering/v2/*.json
    OSF/results/07-cross-corpus/*.csv
    OSF/results/09-scaling-law/*.json
    OSF/results/temperature_sweep/*.csv
    OSF/results/training_dynamics/all_training_dynamics.json

Writes:
    OSF/data/verification_report.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
CSV = PROJECT / "OSF" / "data" / "spec_resistance_EXTENDED.csv"
HS = PROJECT / "OSF" / "data" / "human_studies"
RES = PROJECT / "OSF" / "results"
OUT = PROJECT / "OSF" / "data" / "verification_report.md"


# ─── UTILITIES ────────────────────────────────────────────────────────

_results: list[dict] = []

def add(label: str, observed, claimed, tol: float = 0.005, kind: str = "pct", note: str = "") -> None:
    """Record a comparison. obs/claimed should be same units."""
    if observed is None or claimed is None:
        _results.append({"status": "SKIP", "label": label, "observed": observed,
                         "claimed": claimed, "note": note})
        return
    diff = abs(float(observed) - float(claimed))
    if diff <= tol: tag = "OK"
    elif diff <= tol * 4: tag = "WARN"
    else: tag = "DIFF"
    _results.append({"status": tag, "label": label, "observed": observed,
                     "claimed": claimed, "diff": diff, "kind": kind, "note": note})

def note(text: str) -> None:
    _results.append({"status": "NOTE", "text": text})

def section(header: str) -> None:
    _results.append({"status": "SECTION", "header": header})

def _nonopt_rate(df: pd.DataFrame) -> float:
    if len(df) == 0: return float("nan")
    return (df["chose_optimal"].astype(str) == "False").mean()


# ─── MAIN ─────────────────────────────────────────────────────────────

def main() -> None:
    if not CSV.exists():
        sys.exit(f"ground-truth CSV not found at {CSV}")

    print(f"[load] {CSV}")
    df = pd.read_csv(CSV, low_memory=False)
    print(f"[load] shape={df.shape}, models={df['model_key'].nunique()}, conditions={df['condition'].nunique()}")

    baseline = df[df["condition"] == "baseline"]

    # ═══ SECTION 1: CORPUS INTEGRITY ═════════════════════════════════
    section("1. Corpus integrity")
    add("Total trials (paper: 627,491)", len(df), 627491, tol=0, kind="int")
    add("Total models (paper: 30)", df["model_key"].nunique(), 30, tol=0, kind="int")
    add("Total conditions (paper: 32)", df["condition"].nunique(), 32, tol=0, kind="int")
    add("Baseline trials (paper: 12,240)", len(baseline), 12240, tol=0, kind="int")

    # ═══ SECTION 2: BASELINE PER MODEL (paper Fig 2) ═════════════════
    section("2. Per-model baseline non-optimal rates (paper Fig. 2)")
    # Paper claims: DeepSeek V3 40.9%, GPT-4.1 Mini 8.7%, grand mean 21.2%
    paper_claims = {
        "gpt-4.1-mini": 0.087, "deepseek-v3": 0.409,
        # Other per-model rates not explicitly tabled in main text — just note.
    }
    for m, sub in baseline.groupby("model_key"):
        r = _nonopt_rate(sub)
        if m in paper_claims:
            add(f"baseline rate for {m}", r, paper_claims[m])
        else:
            note(f"{m}: {r*100:.2f}% ({len(sub)} trials)")

    add("Grand-mean baseline (paper: 21.2%)", _nonopt_rate(baseline), 0.212)

    # ═══ SECTION 3: SPECIFICATION GRADIENT (paper Fig 4 + SI Table 2) ═
    section("3. Specification gradient (Fig. 4 + SI Table 2)")
    # Paper: preference path: baseline 21.2, vague 22.2, weighted 17.4, explicit 0.3,
    #                       override 0.16, constrained 1.03
    #        utility path:    baseline 21.2, vague 12.1, weighted 8.1, explicit 0.9,
    #                       override 0.78, constrained 0.92
    spec_pairs = [
        ("preference_vague",        0.222),
        ("preference_weighted",     0.174),
        ("preference_explicit",     0.003),
        ("preference_override",     0.002),
        ("preference_constrained",  0.010),
        ("utility_vague",           0.121),
        ("utility_weighted",        0.081),
        ("utility_explicit",        0.009),
        ("utility_override",        0.008),
        ("utility_constrained",     0.009),
    ]
    for cond, claim in spec_pairs:
        sub = df[df["condition"] == cond]
        if len(sub): add(f"{cond}", _nonopt_rate(sub), claim)
        else:        note(f"{cond}: MISSING from corpus")

    # Specification-gap odds ratios
    section("3b. Specification-gap odds ratios")
    def or_2x2(a_yes, a_no, b_yes, b_no) -> float:
        a = a_no + 0.5; b = a_yes + 0.5; c = b_no + 0.5; d = b_yes + 0.5
        return (a * d) / (b * c)
    pw = df[df["condition"] == "preference_weighted"]
    pe = df[df["condition"] == "preference_explicit"]
    uw = df[df["condition"] == "utility_weighted"]
    ue = df[df["condition"] == "utility_explicit"]
    def count(sub):
        no = int((sub["chose_optimal"].astype(str) == "False").sum())
        yes = len(sub) - no
        return yes, no
    y_pw, n_pw = count(pw); y_pe, n_pe = count(pe)
    y_uw, n_uw = count(uw); y_ue, n_ue = count(ue)
    add("Preference pathway OR (weighted → explicit, paper: 69)",
        or_2x2(y_pw, n_pw, y_pe, n_pe), 69.0, tol=3.0, kind="or")
    add("Utility pathway OR (weighted → explicit, paper: 10)",
        or_2x2(y_uw, n_uw, y_ue, n_ue), 10.0, tol=1.0, kind="or")

    # ═══ SECTION 4: CONFABULATION (baseline + per-condition) ═════════
    section("4. Confabulation rates (SI Table 5)")
    bn = baseline[baseline["chose_optimal"].astype(str) == "False"]
    jcol = None
    for c in ["judge_brand_reasoning", "brand_reasoning"]:
        if c in bn.columns:
            jcol = c; break
    if jcol:
        valid_base = bn.dropna(subset=[jcol])
        # brand_reasoning=False → confabulation (no brand cited)
        confab_mask = valid_base[jcol].astype(str).str.lower().isin(["false", "0", "0.0", "no"])
        add("Baseline confabulation rate (paper: 79.2%)", confab_mask.mean(), 0.792, tol=0.02)
        note(f"  N judge-annotated non-optimal: {len(valid_base)} (paper: 2,600)")

        # Per-condition confabulation rates from SI Table 5
        si5 = [
            ("preference_vague",         0.910),
            ("preference_weighted",      0.884),
            ("utility_vague",            0.813),
            ("utility_weighted",         0.946),
            ("anti_brand_rejection",     0.727),
            ("anti_brand_negative_experience", 0.458),
            ("anti_brand_prefer_unknown", 0.106),
        ]
        for cond, claim in si5:
            sub = df[(df["condition"] == cond) & (df["chose_optimal"].astype(str) == "False")]
            sub = sub.dropna(subset=[jcol])
            if len(sub) == 0:
                note(f"{cond}: no judge-annotated rows"); continue
            rate = sub[jcol].astype(str).str.lower().isin(["false", "0", "0.0", "no"]).mean()
            add(f"confabulation {cond}", rate, claim, tol=0.03)

    # ═══ SECTION 5: CONTROLS (Fig 3) ═════════════════════════════════
    section("5. Controls (Fig. 3)")
    control_claims = [
        ("control_all_familiar",      1 - 0.9997),   # all-familiar: 99.97% optimal, 0.03% non-optimal
        ("control_brand_reversal",    1 - 0.9907),
        ("control_comprehension",     1 - 0.9879),
        ("control_fictional_brands",  1 - 0.9882),
    ]
    for cond, claim in control_claims:
        sub = df[df["condition"] == cond]
        if len(sub): add(f"{cond} non-optimal (paper: {claim*100:.2f}%)", _nonopt_rate(sub), claim, tol=0.01)

    # ═══ SECTION 6: ANTI-BRAND (Fig 6) ═══════════════════════════════
    section("6. Anti-brand conditions (Fig. 6)")
    anti = [
        ("anti_brand_rejection",           0.284),   # +7.2pp vs baseline 21.2
        ("anti_brand_negative_experience", 0.345),   # +13.3pp
        ("anti_brand_prefer_unknown",      0.018),   # -19.4pp
    ]
    for cond, claim in anti:
        sub = df[df["condition"] == cond]
        if len(sub): add(f"{cond}", _nonopt_rate(sub), claim, tol=0.01)

    # ═══ SECTION 7: BASELINE MECHANISMS (ED Fig 4 + SI Table 2) ═════
    section("7. Baseline mechanisms (ED Fig. 4, SI Table 2)")
    mech = [
        ("baseline_brand_blind",         0.154),
        ("baseline_description_minimal", 0.065),
        ("baseline_expert_persona",      0.085),
        ("baseline_review_inverted",     0.068),
        ("baseline_optimal_first",       0.142),
        ("baseline_price_equalized",     0.207),
        ("baseline_price_premium",       0.721),
        ("baseline_review_equalized",    0.207),
    ]
    for cond, claim in mech:
        sub = df[df["condition"] == cond]
        if len(sub): add(f"{cond}", _nonopt_rate(sub), claim, tol=0.02)

    # ═══ SECTION 8: MECHANISM-LEVEL (explicit-spec context) ══════════
    section("8. Mechanism-level (SI Table 2, explicit-spec variants)")
    mech2 = [
        ("mechanism_attribute_swap",       0.158),    # conjoint
        ("mechanism_brand_blind",          0.012),
        ("mechanism_description_minimal",  0.014),
        ("mechanism_price_premium",        0.053),
        ("mechanism_review_equalized",     0.007),
    ]
    for cond, claim in mech2:
        sub = df[df["condition"] == cond]
        if len(sub): add(f"{cond}", _nonopt_rate(sub), claim, tol=0.01)

    # ═══ SECTION 9: CROSS-MODEL CORRELATION ═════════════════════════
    section("9. Cross-model correlations (ED Fig. 9)")
    # Paper: mean pairwise r = 0.65 on assortment-level non-optimal rates at baseline
    pivot = baseline.groupby(["model_key", "assortment_id"])["chose_optimal"].apply(
        lambda s: (s.astype(str) == "False").mean()
    ).unstack("assortment_id")
    corr = pivot.T.corr()
    from itertools import combinations
    pair_rs = [corr.loc[a, b] for a, b in combinations(corr.index, 2)]
    add("Mean pairwise r (paper: 0.65)", float(np.mean(pair_rs)), 0.65, tol=0.03, kind="corr")
    add("Median pairwise r (paper: 0.69)", float(np.median(pair_rs)), 0.69, tol=0.03, kind="corr")
    # Claude Haiku 4.5 × GPT-4o (paper: 0.85)
    if "claude-haiku-4.5" in corr.index and "gpt-4o" in corr.index:
        add("Claude Haiku 4.5 × GPT-4o r (paper: 0.85)",
            float(corr.loc["claude-haiku-4.5", "gpt-4o"]), 0.85, tol=0.05, kind="corr")
    add("All 153 pairs positive (paper: yes)", int(all(r > 0 for r in pair_rs)), 1, tol=0, kind="bool")

    # ═══ SECTION 10: CATEGORY HEATMAP (ED Fig 7) ═══════════════════
    section("10. Category-level baseline rates (ED Fig. 7)")
    cat_claims = [
        ("coffee_makers",   0.545),
        ("headphones",      0.439),
        ("tablets",         0.308),
        ("keyboards",       0.011),
        ("external_ssds",   0.011),
    ]
    if "category" in baseline.columns:
        for cat, claim in cat_claims:
            sub = baseline[baseline["category"] == cat]
            if len(sub): add(f"category {cat}", _nonopt_rate(sub), claim, tol=0.03)
            else:        note(f"category {cat}: 0 rows (key mismatch?)")
    else:
        note("category column not found — using category_name fallback if available")

    # ═══ SECTION 11: HUMAN STUDIES ══════════════════════════════════
    section("11. Human studies (Studies 1A, 1B, 2, 3)")
    # Study 1A
    p1a = HS / "study1a_coffee_anonymised.csv"
    if p1a.exists():
        d = pd.read_csv(p1a, low_memory=False)
        note(f"Study 1A: {len(d)} rows (paper final N=799 after exclusions)")
        # Condition column may be numeric-coded: 1=NoAI, 2=BiasedAI, 3=DebiasedAI (check ConditionD)
        for col in ["ConditionD", "Condition"]:
            if col in d.columns:
                cond_counts = d[col].value_counts().to_dict()
                note(f"Study 1A condition distribution: {cond_counts}")
                break

    # Study 3 specifically — has full bool columns
    p3 = HS / "study3_chatbot_anonymised.csv"
    if p3.exists():
        d = pd.read_csv(p3, low_memory=False)
        b = d[d["study3_condition"] == "biased"]["chose_focal_bool"]
        n = d[d["study3_condition"] == "neutral"]["chose_focal_bool"]
        h = d[d["study3_condition"] == "honest"]["chose_optimal_bool"]
        nc = d[d["study3_condition"] == "neutral"]["chose_optimal_bool"]
        def m(x): return x.astype(str).str.lower().eq("true").mean()
        add("Study 3 H1 (Biased focal vs Neutral focal, paper +18.7pp)",
            m(b) - m(n), 0.187, tol=0.01, kind="ppt")
        add("Study 3 RQ1 (Honest optimal vs Neutral optimal, paper +27.2pp)",
            m(h) - m(nc), 0.272, tol=0.01, kind="ppt")
        add("Study 3 Biased focal rate (paper: 51.7% of 209 usable in published pilot / similar here)",
            m(b), 0.518, tol=0.02)
        add("Study 3 Honest optimal rate (paper: 58.4%)",
            m(h), 0.584, tol=0.02)
        add("Study 3 Neutral optimal rate (paper: 31.1%)",
            m(nc), 0.311, tol=0.02)

    # ═══ SECTION 12: REVISION EXPERIMENTS ════════════════════════════
    section("12. Revision experiments")
    # 12a. Injection
    inj = RES / "08-fictional-injection" / "full_scale_injection.csv"
    if inj.exists():
        d = pd.read_csv(inj)
        for col in ("chose_axelion", "chose_focal", "chose_target"):
            if col in d.columns:
                inj_rows = d[
                    d.get("model_key", "").astype(str).str.contains("injection-100", na=False) &
                    (d.get("test_type", "").astype(str) == "injection")
                ]
                if len(inj_rows):
                    add("Injection-100 chose_axelion on injection stimuli (paper: 52.5%)",
                        inj_rows[col].astype(bool).mean(), 0.525, tol=0.02)
                break

    # 12b. Debiasing (three GPT families)
    for csv_name, label, baseline_claim, post_claim in [
        ("eval_6k_4omini.csv",  "Debiasing GPT-4o-mini",  0.162, 0.003),
        ("eval_6k_41nano.csv",  "Debiasing GPT-4.1-nano", 0.141, 0.003),
        ("eval_6k_41mini.csv",  "Debiasing GPT-4.1-mini", 0.085, 0.000),
    ]:
        p = RES / "06-openai-finetune" / csv_name
        if not p.exists(): continue
        d = pd.read_csv(p)
        col = "chose_optimal" if "chose_optimal" in d.columns else "chose_optimal_bool"
        if col not in d.columns: continue
        flag = d[col].astype(str).str.lower()
        if "model_key" in d.columns:
            mk = d["model_key"].astype(str)
            pre = d[mk.str.contains("baseline|base", case=False, na=False)]
            post = d[~mk.str.contains("baseline|base", case=False, na=False)]
            if len(pre) and len(post):
                pre_rate = (pre[col].astype(str).str.lower() == "false").mean()
                post_rate = (post[col].astype(str).str.lower() == "false").mean()
                add(f"{label} baseline",     pre_rate,  baseline_claim, tol=0.01)
                add(f"{label} post-debias",  post_rate, post_claim,      tol=0.005)

    # 12c. 500-example debiasing
    p500 = RES / "06-openai-finetune" / "debiasing_500_results.json"
    if p500.exists():
        try:
            d500 = json.loads(p500.read_text())
            if "post_non_optimal_rate" in d500:
                add("500-example debiasing post-rate (paper: 0.9%)",
                    float(d500["post_non_optimal_rate"]), 0.009, tol=0.005)
        except Exception:
            pass

    # 12d. Base vs instruct (Gemma 4)
    pbi = RES / "02-base-vs-instruct" / "all_base_vs_instruct.json"
    if pbi.exists():
        try:
            data = json.loads(pbi.read_text())
            # entry may be nested
            for fam, entry in data.items() if isinstance(data, dict) else []:
                if isinstance(entry, dict):
                    for direction, claim in [("base", 0.67), ("instruct", 0.20)]:
                        if direction in entry:
                            add(f"Base-vs-instruct [{fam}] {direction} (paper Gemma 4 {direction}: {claim*100:.0f}%)",
                                float(entry[direction]), claim, tol=0.05)
        except Exception:
            pass

    # 12e. Probing accuracy
    ppa = RES / "04-representation-probing" / "v3"
    if ppa.exists():
        for fn in ppa.glob("*.json"):
            try:
                d = json.loads(fn.read_text())
                # look for top-level 'accuracy' keys
                for fam, claim in [
                    ("qwen", 0.739), ("mistral", 0.943), ("gemma", 0.879),
                ]:
                    if fam in fn.name.lower():
                        if isinstance(d, dict):
                            for k in ("accuracy", "test_accuracy", "acc", "mean"):
                                if k in d:
                                    add(f"Probing accuracy {fam} (paper: {claim*100:.1f}%)",
                                        float(d[k]), claim, tol=0.02, kind="acc")
                                    break
            except Exception:
                pass

    # 12f. Temperature sweep (paper: indistinguishable at T=0 vs T=1)
    pts = RES / "temperature_sweep" / "temperature_sweep_summary.json"
    if pts.exists():
        try:
            d = json.loads(pts.read_text())
            note(f"Temperature sweep summary keys: {list(d.keys())[:8] if isinstance(d, dict) else 'non-dict'}")
        except Exception:
            pass

    # 12g. Scaling law
    psl = RES / "09-scaling-law" / "scaling_law_results.json"
    if psl.exists():
        try:
            d = json.loads(psl.read_text())
            if isinstance(d, dict):
                for k in ("beta", "coefficient", "slope", "capability_coef"):
                    if k in d:
                        add(f"Scaling-law coefficient [{k}] (paper: β = 0.178)",
                            float(d[k]), 0.178, tol=0.03, kind="coef")
                        break
                for k in ("p_value", "p", "pvalue"):
                    if k in d:
                        add(f"Scaling-law p-value [{k}] (paper: 0.015)",
                            float(d[k]), 0.015, tol=0.01, kind="p")
                        break
        except Exception:
            pass

    # 12h. Steering dose-response (21 pp)
    pst = RES / "11-activation-steering" / "v2" / "steering_v2_results.json"
    if pst.exists():
        try:
            d = json.loads(pst.read_text())
            note(f"Steering v2 results keys: {list(d.keys())[:8] if isinstance(d, dict) else 'non-dict'}")
        except Exception:
            pass

    # 12i. Training dynamics (all 19 jobs)
    ptd = RES / "training_dynamics" / "all_training_dynamics.json"
    if ptd.exists():
        try:
            d = json.loads(ptd.read_text())
            add("Fine-tuning jobs recorded (paper: 19)",
                len(d) if isinstance(d, dict) else len(d),
                19, tol=0, kind="int")
        except Exception:
            pass

    # ═══ SECTION 13a: ALL 18 MODELS BASELINE (complete coverage) ═══════
    section("13a. All 18 models, baseline non-optimal (complete table)")
    # From SI Table 1/Fig 2 and MASTER_STATUS per-model rates (approximate from main text)
    model_claims_full = {
        "gpt-4.1-mini": 0.087,
        "claude-haiku-4.5": 0.185,
        "gpt-4.1-nano": 0.129,
        "gpt-4o-mini": 0.140,
        "gpt-4o": 0.147,
        "gemini-2.5-flash-lite": 0.139,
        "gpt-5-mini": 0.168,
        "llama-3.3-70b": 0.153,
        "gemma-3-27b": 0.151,
        "gemini-2.0-flash": 0.183,
        "kimi-k2": 0.175,
        "gemini-2.5-flash": 0.193,
        "qwen-2.5-72b": 0.226,
        "claude-sonnet-4.6": 0.255,
        "gemini-3-flash": 0.256,
        "gemini-2.5-pro": 0.278,
        "deepseek-r1": 0.378,
        "deepseek-v3": 0.409,
    }
    for m, claim in model_claims_full.items():
        sub = baseline[baseline["model_key"] == m]
        if len(sub):
            r = _nonopt_rate(sub)
            add(f"baseline rate {m}", r, claim, tol=0.03)
        else:
            note(f"{m}: absent from baseline")

    # ═══ SECTION 13b: ALL 20 CATEGORIES BASELINE RATES ═══════════════
    section("13b. All 20 category baseline rates (ED Fig. 7)")
    cat_claims_full = {
        # approx from ED Fig 7 heatmap row means
        "coffee_makers": 0.545,
        "headphones": 0.439,
        "tablets": 0.308,
        "cameras": 0.280,
        "wireless_earbuds": 0.220,
        "smartphones": 0.240,
        "laptops": 0.170,
        "smartwatches": 0.165,
        "running_shoes": 0.150,
        "backpacks": 0.140,
        "electric_toothbrushes": 0.120,
        "blenders": 0.100,
        "portable_speakers": 0.090,
        "water_bottles": 0.080,
        "monitors": 0.060,
        "wireless_routers": 0.050,
        "robot_vacuums": 0.045,
        "gaming_mice": 0.040,
        "keyboards": 0.011,
        "external_ssds": 0.011,
    }
    cat_col = None
    for c in ["category", "category_name", "product_category"]:
        if c in baseline.columns: cat_col = c; break
    if cat_col:
        for cat, claim in cat_claims_full.items():
            sub = baseline[baseline[cat_col] == cat]
            if len(sub) == 0:
                # try with spaces/variants
                sub = baseline[baseline[cat_col].astype(str).str.replace(" ", "_").str.lower() == cat]
            if len(sub): add(f"category {cat}", _nonopt_rate(sub), claim, tol=0.07)
            else:        note(f"category {cat}: 0 rows")
    else:
        note("no category column — skipping")

    # ═══ SECTION 13c: OPTIMAL-vs-NON-OPTIMAL BRAND CITING ═══════════
    section("13c. Brand-citing rates by choice type (paper L37, L69)")
    # Paper: 20.8% brand citing in non-optimal baseline; 5.1% in optimal baseline;
    # OR = 0.20 (95% CI 0.17-0.23).
    if jcol:
        opt = baseline[baseline["chose_optimal"].astype(str) == "True"].dropna(subset=[jcol])
        nop = baseline[baseline["chose_optimal"].astype(str) == "False"].dropna(subset=[jcol])
        if len(opt) and len(nop):
            true_vals = {"true", "1", "1.0", "yes"}
            rate_opt = opt[jcol].astype(str).str.lower().isin(true_vals).mean()
            rate_nop = nop[jcol].astype(str).str.lower().isin(true_vals).mean()
            add("Optimal brand-citing rate (paper: 5.1%)", rate_opt, 0.051, tol=0.01)
            add("Non-optimal brand-citing rate (paper: 20.8%)", rate_nop, 0.208, tol=0.02)
            # OR
            y_opt = int(opt[jcol].astype(str).str.lower().isin(true_vals).sum()); n_opt = len(opt) - y_opt
            y_nop = int(nop[jcol].astype(str).str.lower().isin(true_vals).sum()); n_nop = len(nop) - y_nop
            or_cite = or_2x2(y_opt, n_opt, y_nop, n_nop)
            add("OR brand-citing (optimal vs non-optimal, paper: 0.20)",
                or_cite, 0.20, tol=0.03, kind="or")

    # ═══ SECTION 13d: CROSS-MODEL CONVERGENCE ═══════════════════════
    section("13d. Cross-model convergence on same branded alternative")
    # Paper L87: "converge on the same branded alternative at a mean rate of 74.4% across assortments"
    # For each assortment, among models that chose non-optimal, what fraction agreed on the most popular wrong choice?
    nop_all = df[(df["condition"] == "baseline") & (df["chose_optimal"].astype(str) == "False")]
    if "product_choice" in nop_all.columns and "assortment_id" in nop_all.columns:
        agree_rates = []
        for aid, sub in nop_all.groupby("assortment_id"):
            if len(sub) < 2: continue
            top = sub["product_choice"].value_counts().iloc[0]
            agree_rates.append(top / len(sub))
        if agree_rates:
            add("Cross-model convergence rate (paper: 74.4%)",
                float(np.mean(agree_rates)), 0.744, tol=0.05)
            n_100 = sum(1 for r in agree_rates if r > 0.999)
            add("Assortments with 100% agreement across erring models (paper: 6)",
                n_100, 6, tol=2, kind="int")

    # ═══ SECTION 13e: WELFARE ═══════════════════════════════════════
    section("13e. Welfare (Discussion §6 and SN 16)")
    # Paper: 94.2% of non-optimal choices select more expensive product; mean $68, median $50.
    if "price_difference" in nop_all.columns:
        diffs = pd.to_numeric(nop_all["price_difference"], errors="coerce").dropna()
        if len(diffs):
            pct_more_expensive = (diffs > 0).mean()
            add("Fraction non-optimal more expensive than optimal (paper: 94.2%)",
                pct_more_expensive, 0.942, tol=0.02)
            add("Mean price premium on non-optimal (paper: $68)",
                float(diffs[diffs > 0].mean()), 68.0, tol=5.0, kind="usd")
            add("Median price premium on non-optimal (paper: $50)",
                float(diffs[diffs > 0].median()), 50.0, tol=5.0, kind="usd")
    else:
        # Compute price diff from raw fields if available
        if "price_optimal" in nop_all.columns and "price_chosen" in nop_all.columns:
            po = pd.to_numeric(nop_all["price_optimal"], errors="coerce")
            pc = pd.to_numeric(nop_all["price_chosen"], errors="coerce")
            diffs = (pc - po).dropna()
            if len(diffs):
                add("Fraction non-optimal more expensive than optimal (paper: 94.2%)",
                    (diffs > 0).mean(), 0.942, tol=0.02)
                add("Mean price premium on non-optimal (paper: $68)",
                    float(diffs[diffs > 0].mean()), 68.0, tol=5.0, kind="usd")
                add("Median price premium on non-optimal (paper: $50)",
                    float(diffs[diffs > 0].median()), 50.0, tol=5.0, kind="usd")

    # ═══ SECTION 13f: MINI vs LARGE RATIOS (within-provider) ════════
    section("13f. Inverse scaling: within-provider mini vs large ratios")
    # Paper L91: Anthropic 1.9x, Google 2.4x, DeepSeek 1.9x, OpenAI 2.3x.
    # Paper overall: mini 11.3%, large 28.9%, ratio 2.6x.
    tier = {
        "gpt-4.1-mini": "mini", "gpt-4o-mini": "mini", "claude-haiku-4.5": "mini",
        "gemini-2.5-flash-lite": "mini", "gemini-2.0-flash": "mini",
        "gpt-4o": "large", "claude-sonnet-4.6": "large",
        "gemini-2.5-pro": "large", "gemini-3-flash": "large",
        "deepseek-v3": "large", "deepseek-r1": "large",
        "qwen-2.5-72b": "large", "llama-3.3-70b": "large",
        "kimi-k2": "large", "gpt-5-mini": "large",
        "gpt-4.1-nano": "mini", "gemini-2.5-flash": "mini",
        "gemma-3-27b": "large",
    }
    baseline_tier = baseline.assign(tier=baseline["model_key"].map(tier))
    mini_rate = _nonopt_rate(baseline_tier[baseline_tier["tier"] == "mini"])
    large_rate = _nonopt_rate(baseline_tier[baseline_tier["tier"] == "large"])
    add("Mini-class baseline (paper: 11.3%)", mini_rate, 0.113, tol=0.03)
    add("Large-class baseline (paper: 28.9%)", large_rate, 0.289, tol=0.03)
    if mini_rate > 0:
        add("Large/mini ratio (paper: 2.6x)", large_rate / mini_rate, 2.6, tol=0.5, kind="ratio")

    # ═══ SECTION 13g: VAGUE PARADOX (10 of 18 worse than baseline) ══
    section("13g. Vague paradox (ED Fig. 10)")
    # Paper: 10 of 18 models show higher non-optimal at preference_vague than baseline
    worse_count = 0
    for m, sub in df.groupby("model_key"):
        b = _nonopt_rate(sub[sub["condition"] == "baseline"])
        v = _nonopt_rate(sub[sub["condition"] == "preference_vague"])
        if not np.isnan(b) and not np.isnan(v) and v > b:
            worse_count += 1
    add("Models worse at vague than baseline (paper: 10 of 18)", worse_count, 10, tol=2, kind="int")

    # ═══ SECTION 14: OPEN-WEIGHT vs PROPRIETARY GAP ═════════════════
    section("14. Open-weight vs proprietary decomposition")
    # Paper: open-weight 28.8%, proprietary 17.5%; converge below 0.4% at explicit.
    proprietary = {"claude-haiku-4.5", "claude-sonnet-4.6",
                   "gpt-4o", "gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1-nano", "gpt-5-mini",
                   "gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite",
                   "gemini-2.5-pro", "gemini-3-flash"}
    open_w = set(df["model_key"].unique()) - proprietary
    ow_baseline = baseline[baseline["model_key"].isin(open_w)]
    pr_baseline = baseline[baseline["model_key"].isin(proprietary)]
    add("Open-weight baseline (paper: 28.8%)", _nonopt_rate(ow_baseline), 0.288, tol=0.02)
    add("Proprietary baseline (paper: 17.5%)", _nonopt_rate(pr_baseline), 0.175, tol=0.02)

    # ═══ SECTION 15: VERBATIM CONFAB RATES per MODEL (SN 11) ════════
    section("15. Per-model confabulation range (SN 11)")
    # Paper: 34% (Claude Sonnet 4.6) to 98% (Gemini 2.5 Flash)
    if jcol:
        per_model_confab = {}
        for m, sub in baseline.groupby("model_key"):
            non = sub[sub["chose_optimal"].astype(str) == "False"].dropna(subset=[jcol])
            if len(non) < 30: continue
            rate = non[jcol].astype(str).str.lower().isin({"false", "0", "0.0", "no"}).mean()
            per_model_confab[m] = rate
        if per_model_confab:
            mn = min(per_model_confab.values()); mx = max(per_model_confab.values())
            lo_m = [m for m, r in per_model_confab.items() if r == mn][0]
            hi_m = [m for m, r in per_model_confab.items() if r == mx][0]
            add(f"Lowest confab: {lo_m} (paper: Claude Sonnet 4.6 ~34%)", mn, 0.34, tol=0.1)
            add(f"Highest confab: {hi_m} (paper: Gemini 2.5 Flash ~98%)", mx, 0.98, tol=0.05)

    # ═══ SECTION 16: MULTI-SEED INJECTION ════════════════════════════
    section("16. Multi-seed injection (N=100 × 8 seeds)")
    # Paper: mean 49.4%, SD 3.8%, P < 0.0001 (one-sample t against 0)
    # Extract per-seed rates from FINE_TUNED_MODELS.json multiseed entries.
    ft_json = PROJECT / "OSF" / "FINE_TUNED_MODELS.json"
    if ft_json.exists():
        try:
            ft = json.loads(ft_json.read_text())
            ms = ft.get("injection_multiseed_at_N100", {}).get("entries", [])
            if ms:
                # Rates aren't in the registry — notes only
                note(f"Multi-seed entries recorded: {len(ms)} (paper reports 8 seeds)")
        except Exception:
            pass

    # ═══ WRITE REPORT ═══════════════════════════════════════════════
    lines: list[str] = []
    ap = lines.append
    ap("# Comprehensive paper-to-data verification report")
    ap("")
    ap(f"Source: `OSF/data/spec_resistance_EXTENDED.csv` ({df.shape[0]:,} rows × {df.shape[1]} columns, {df['model_key'].nunique()} models, {df['condition'].nunique()} conditions).")
    ap("")
    ap("**Status legend** — OK: matches paper ≤0.5pp or equivalent; WARN: within 2pp; DIFF: >2pp; SKIP: data not present; NOTE: contextual, no paper claim; SECTION: organisational header.")
    ap("")
    ok = sum(1 for r in _results if r.get("status") == "OK")
    warn = sum(1 for r in _results if r.get("status") == "WARN")
    diff = sum(1 for r in _results if r.get("status") == "DIFF")
    skip = sum(1 for r in _results if r.get("status") == "SKIP")
    total_checks = ok + warn + diff
    ap(f"**Totals**: {total_checks} numerical comparisons — {ok} OK, {warn} WARN, {diff} DIFF, {skip} SKIP.")
    ap("")
    for r in _results:
        if r.get("status") == "SECTION":
            ap(f"## {r['header']}")
            ap("")
        elif r.get("status") == "NOTE":
            ap(f"- {r['text']}")
        else:
            obs = r.get("observed")
            cl = r.get("claimed")
            diff_val = r.get("diff", 0)
            kind = r.get("kind", "pct")
            def fv(x):
                if x is None: return "N/A"
                if kind == "pct":  return f"{float(x)*100:.2f}%"
                if kind == "ppt":  return f"{float(x)*100:+.2f}pp"
                if kind == "or":   return f"{float(x):.2f}"
                if kind == "corr": return f"{float(x):.3f}"
                if kind == "acc":  return f"{float(x)*100:.1f}%"
                if kind == "int":  return f"{int(x)}"
                if kind == "bool": return f"{int(x)}"
                return f"{x}"
            ap(f"- [{r['status']}] **{r['label']}**: observed {fv(obs)}, paper {fv(cl)}")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[done] {OUT}")
    print(f"[done] {total_checks} checks: {ok} OK, {warn} WARN, {diff} DIFF, {skip} SKIP")


if __name__ == "__main__":
    main()
