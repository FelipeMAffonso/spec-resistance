"""
Study 3 — Comprehensive "all angles" analysis.

This script consolidates every analysis a Nature reviewer could ask for:

    1.  Confirmatory (H1, RQ1, secondary) — rerun from pilot module
    2.  MLM with contingency branch selection
    3.  Per-meta-category effect breakdown (does the effect hold across product types?)
    4.  AI brand × condition interaction
    5.  Per-protocol analysis (J1-filtered: only sessions where manipulation fired)
    6.  Awareness-excluded sensitivity (J4)
    7.  Familiarity-excluded sensitivity
    8.  "Other" bucket decomposition (well-known-other vs non-dominant lesser-known)
    9.  Conversation dynamics (J2 pushback × outcome)
    10. Choice-reason mechanism (J3 primary reason × condition)
    11. Price gap effects (rec − dom price) on choice
    12. Spec-dominance gap (number of dominant advantages) on choice
    13. Trust battery (if collected) × compliance
    14. Duration + turn count × condition
    15. AI confabulation strength (J1) × focal compliance
    16. Familiarity prior × choice
    17. Comparison table vs Studies 1A/1B/2 priors
    18. Publication-quality figures (six)
    19. Full markdown report with every angle covered

Usage:
    python analyze_all_angles.py                          # read output/pilot_data_usable.csv
    python analyze_all_angles.py --csv path/to.csv        # use a specific CSV
    python analyze_all_angles.py --skip-figs              # just the numbers

Outputs:
    output/ALL_ANGLES_REPORT.md                           — comprehensive markdown
    output/all_angles_results.json                        — every number as JSON
    output/figures_all_angles/                            — publication figures
"""
from __future__ import annotations

import argparse
import json
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

warnings.filterwarnings("ignore")

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR / "output"
JUDGE_DIR = OUT_DIR / "judges"
FIG_DIR = OUT_DIR / "figures_all_angles"
FIG_DIR.mkdir(exist_ok=True)

CONDITIONS = ["biased", "honest", "neutral"]
BUCKETS = ["optimal", "focal", "other"]
COND_COLORS = {"biased": "#c0392b", "honest": "#27ae60", "neutral": "#7f8c8d"}


# ─── HELPERS ──────────────────────────────────────────────────────────

def _wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0: return (0.0, 0.0)
    phat = k / n
    denom = 1 + z**2 / n
    center = (phat + z**2 / (2 * n)) / denom
    width = z * np.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, center - width), min(1.0, center + width))

def _fisher_pair(df: pd.DataFrame, dv: str, cond_a: str, cond_b: str,
                 cond_col: str = "study3_condition") -> dict:
    sub = df[df[cond_col].isin([cond_a, cond_b])].dropna(subset=[dv])
    if len(sub) < 4:
        return {"skipped": "insufficient data"}
    a = sub[sub[cond_col] == cond_a]
    b = sub[sub[cond_col] == cond_b]
    n_a, k_a = len(a), int(a[dv].astype(bool).sum())
    n_b, k_b = len(b), int(b[dv].astype(bool).sum())
    if n_a == 0 or n_b == 0:
        return {"skipped": "empty cell"}
    tab = np.array([[k_a, n_a - k_a], [k_b, n_b - k_b]])
    try:
        _, p_fish = stats.fisher_exact(tab, alternative="two-sided")
    except Exception:
        p_fish = None
    p_a, p_b = k_a / n_a, k_b / n_b
    rd = p_a - p_b
    se_rd = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    # Haldane–Anscombe OR
    a_, b_, c_, d_ = k_a + 0.5, (n_a - k_a) + 0.5, k_b + 0.5, (n_b - k_b) + 0.5
    or_ = (a_ * d_) / (b_ * c_)
    se_log_or = np.sqrt(1/a_ + 1/b_ + 1/c_ + 1/d_)
    return {
        "n_a": n_a, "k_a": k_a, "rate_a": p_a, "rate_a_ci": _wilson_ci(k_a, n_a),
        "n_b": n_b, "k_b": k_b, "rate_b": p_b, "rate_b_ci": _wilson_ci(k_b, n_b),
        "risk_diff": float(rd),
        "risk_diff_ci": [float(rd - 1.96 * se_rd), float(rd + 1.96 * se_rd)],
        "odds_ratio": float(or_),
        "odds_ratio_ci": [float(np.exp(np.log(or_) - 1.96 * se_log_or)),
                          float(np.exp(np.log(or_) + 1.96 * se_log_or))],
        "p": float(p_fish) if p_fish is not None else None,
    }

def _parse_assort(s):
    if not isinstance(s, str) or not s.strip(): return None
    m = re.search(r"\{[\s\S]*\}", s)
    if not m: return None
    try: return json.loads(m.group(0))
    except json.JSONDecodeError: return None

def _price_to_num(s) -> float:
    if s is None or pd.isna(s): return np.nan
    m = re.search(r"[\d.]+", str(s))
    return float(m.group()) if m else np.nan


# ─── LOAD + ENRICH ───────────────────────────────────────────────────

def load_and_enrich(csv: Path) -> pd.DataFrame:
    df = pd.read_csv(csv)
    # Merge J5 meta-categories
    j5_path = JUDGE_DIR / "J5_meta_category.csv"
    if j5_path.exists():
        j5 = pd.read_csv(j5_path)
        mapping = dict(zip(j5["category"].astype(str).str.strip(), j5["j5_meta_category"]))
        df["meta_category"] = df["study3_category"].astype(str).str.strip().map(mapping).fillna("other")
    else:
        df["meta_category"] = "unknown"
    # Merge J1 confabulation per session
    j1_path = JUDGE_DIR / "J1_confabulation.csv"
    if j1_path.exists():
        j1 = pd.read_csv(j1_path)
        keep = ["session_id", "j1_recommended_focal", "j1_recommended_dominant",
                "j1_confabulation_type", "j1_confabulation_strength"]
        j1 = j1[[c for c in keep if c in j1.columns]]
        df = df.merge(j1, left_on="study3_session_id", right_on="session_id", how="left")
    # J2 pushback
    j2_path = JUDGE_DIR / "J2_pushback.csv"
    if j2_path.exists():
        j2 = pd.read_csv(j2_path)
        keep = ["session_id", "j2_pushback_turns", "j2_hold_count", "j2_hedge_count",
                "j2_cave_count", "j2_switched"]
        j2 = j2[[c for c in keep if c in j2.columns]]
        df = df.merge(j2, left_on="study3_session_id", right_on="session_id",
                      how="left", suffixes=("", "_j2"))
    # J3 choice reason
    j3_path = JUDGE_DIR / "J3_choice_reason.csv"
    if j3_path.exists():
        j3 = pd.read_csv(j3_path)
        keep = ["session_id", "j3_primary_reason", "j3_secondary_reason", "j3_echoed_ai"]
        j3 = j3[[c for c in keep if c in j3.columns]]
        df = df.merge(j3, left_on="study3_session_id", right_on="session_id",
                      how="left", suffixes=("", "_j3"))
    # J4 suspicion
    j4_path = JUDGE_DIR / "J4_suspicion.csv"
    if j4_path.exists():
        j4 = pd.read_csv(j4_path)
        keep = ["session_id", "j4_aware_of_bias", "j4_aware_of_manipulation",
                "j4_aware_of_research_purpose"]
        j4 = j4[[c for c in keep if c in j4.columns]]
        df = df.merge(j4, left_on="study3_session_id", right_on="session_id",
                      how="left", suffixes=("", "_j4"))
    # Extract price gap + spec gap from assortment
    assorts = df["study3_assortment"].apply(_parse_assort)
    def _price_gap(a):
        if not a: return np.nan
        try:
            products = a.get("products", [])
            dom_idx = a.get("spec_dominant_index")
            rec_idx = a.get("recommended_index")
            if dom_idx is None or rec_idx is None: return np.nan
            dom_p = _price_to_num(products[dom_idx].get("price"))
            rec_p = _price_to_num(products[rec_idx].get("price"))
            return rec_p - dom_p
        except (IndexError, KeyError, TypeError):
            return np.nan
    def _spec_gap(a):
        """Number of attributes where dominant strictly wins."""
        if not a: return np.nan
        try:
            winners = a.get("attribute_winners", {})
            dom_idx = a.get("spec_dominant_index")
            strict = sum(1 for w in winners.values() if isinstance(w, list) and len(w) == 1 and w[0] == dom_idx)
            return strict
        except Exception:
            return np.nan
    df["price_gap_rec_minus_dom"] = assorts.apply(_price_gap)
    df["spec_gap_strict_attrs"] = assorts.apply(_spec_gap)
    # Familiarity self-report column may vary
    for c in ["brand_familiar", "dv_brand_familiar", "study3_brand_familiar",
              "familiarity", "brand_familiarity"]:
        if c in df.columns:
            df["brand_familiar"] = pd.to_numeric(df[c], errors="coerce")
            break
    # Trust battery items — look for 4-item pattern
    trust_cols = [c for c in df.columns if c.startswith("dv_trust") or c.startswith("trust_") or c.startswith("study3_trust")]
    if trust_cols:
        t = df[trust_cols].apply(pd.to_numeric, errors="coerce")
        df["trust_mean"] = t.mean(axis=1)
    # Awareness flag
    df["aware_flag"] = (
        df.get("j4_aware_of_bias", pd.Series([False] * len(df))).fillna(False).astype(bool) |
        df.get("j4_aware_of_manipulation", pd.Series([False] * len(df))).fillna(False).astype(bool)
    )
    return df


# ─── ANGLE 1: CONFIRMATORY ───────────────────────────────────────────

def angle_confirmatory(df: pd.DataFrame) -> dict:
    tests = {
        "H1_biased_vs_neutral_focal":   ("chose_focal_bool",   "biased",  "neutral"),
        "RQ1_honest_vs_neutral_optimal": ("chose_optimal_bool", "honest",  "neutral"),
        "biased_vs_honest_focal":        ("chose_focal_bool",   "biased",  "honest"),
        "biased_vs_neutral_optimal":     ("chose_optimal_bool", "biased",  "neutral"),
        "biased_vs_honest_optimal":      ("chose_optimal_bool", "biased",  "honest"),
        "honest_vs_neutral_focal":       ("chose_focal_bool",   "honest",  "neutral"),
    }
    return {name: _fisher_pair(df, dv, a, b) for name, (dv, a, b) in tests.items()}


# ─── ANGLE 2: MLM ─────────────────────────────────────────────────────

def angle_mlm(df: pd.DataFrame) -> dict:
    """Runs MLM with Branch C (meta-category random intercept) for both DVs."""
    from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
    out = {}
    for dv in ("chose_optimal_bool", "chose_focal_bool"):
        sub = df.dropna(subset=[dv, "study3_condition", "meta_category"]).copy()
        sub["y"] = sub[dv].astype(int)
        sub["condition"] = pd.Categorical(sub["study3_condition"],
                                           categories=["neutral", "biased", "honest"], ordered=False)
        sub["ai_brand"] = sub["study3_ai_brand"].astype(str).fillna("unknown")
        try:
            md = BinomialBayesMixedGLM.from_formula(
                "y ~ C(condition) + C(ai_brand)",
                {"mcat": "0 + C(meta_category)"},
                sub,
            )
            res = md.fit_vb()
            fe = {}
            for i, name in enumerate(res.model.exog_names):
                coef = float(res.fe_mean[i]); se = float(res.fe_sd[i])
                z = (coef / se) if se else None
                p = float(2 * (1 - stats.norm.cdf(abs(z)))) if z is not None else None
                fe[name] = {
                    "coef": coef, "se": se, "z": z, "p": p,
                    "ci_low": coef - 1.96 * se, "ci_high": coef + 1.96 * se,
                }
            out[dv] = {"converged": True, "fixed_effects": fe}
        except Exception as e:
            out[dv] = {"converged": False, "error": str(e)}
    return out


# ─── ANGLE 3: PER-META-CATEGORY ───────────────────────────────────────

def angle_per_meta_category(df: pd.DataFrame) -> dict:
    """Does the effect hold across product types?"""
    out = {}
    for mcat, sub in df.groupby("meta_category"):
        if len(sub) < 20: continue
        out[mcat] = {
            "n": len(sub),
            "H1_biased_vs_neutral_focal": _fisher_pair(sub, "chose_focal_bool", "biased", "neutral"),
            "RQ1_honest_vs_neutral_optimal": _fisher_pair(sub, "chose_optimal_bool", "honest", "neutral"),
        }
    return out


# ─── ANGLE 4: AI BRAND × CONDITION ────────────────────────────────────

def angle_brand_by_condition(df: pd.DataFrame) -> dict:
    """Does the effect vary by AI brand skin?"""
    out = {"by_brand_condition": {}}
    grp = df.groupby(["study3_ai_brand", "study3_condition"])
    for (brand, cond), sub in grp:
        if len(sub) < 5: continue
        out["by_brand_condition"].setdefault(brand, {})[cond] = {
            "n": len(sub),
            "optimal_rate": float(sub["chose_optimal_bool"].astype(bool).mean()),
            "focal_rate":   float(sub["chose_focal_bool"].astype(bool).mean()),
        }
    # Interaction test: logit with interaction
    try:
        sub = df.dropna(subset=["chose_focal_bool", "study3_condition", "study3_ai_brand"]).copy()
        sub["y"] = sub["chose_focal_bool"].astype(int)
        md = smf.logit("y ~ C(study3_condition) * C(study3_ai_brand)", data=sub).fit(disp=False)
        out["interaction_focal_p"] = float(md.llr_pvalue)
    except Exception as e:
        out["interaction_focal_p"] = None
    try:
        sub = df.dropna(subset=["chose_optimal_bool", "study3_condition", "study3_ai_brand"]).copy()
        sub["y"] = sub["chose_optimal_bool"].astype(int)
        md = smf.logit("y ~ C(study3_condition) * C(study3_ai_brand)", data=sub).fit(disp=False)
        out["interaction_optimal_p"] = float(md.llr_pvalue)
    except Exception as e:
        out["interaction_optimal_p"] = None
    return out


# ─── ANGLE 5: PER-PROTOCOL (J1-FILTERED) ──────────────────────────────

def angle_per_protocol(df: pd.DataFrame) -> dict:
    """Keep only sessions where J1 says the manipulation fired."""
    if "j1_recommended_focal" not in df.columns:
        return {"skipped": "J1 not available"}
    # Biased condition: keep only sessions where AI actually recommended focal
    # Honest condition: keep only sessions where AI actually recommended dominant
    df_pp = df.copy()
    biased_mask = df_pp["study3_condition"] == "biased"
    honest_mask = df_pp["study3_condition"] == "honest"
    neutral_mask = df_pp["study3_condition"] == "neutral"
    keep_biased = biased_mask & df_pp["j1_recommended_focal"].fillna(False).astype(bool)
    keep_honest = honest_mask & df_pp["j1_recommended_dominant"].fillna(False).astype(bool)
    keep = keep_biased | keep_honest | neutral_mask
    sub = df_pp[keep]
    return {
        "n_total": int(len(df_pp)),
        "n_pp": int(len(sub)),
        "n_biased_dropped": int((biased_mask & ~keep_biased).sum()),
        "n_honest_dropped": int((honest_mask & ~keep_honest).sum()),
        "H1_biased_vs_neutral_focal": _fisher_pair(sub, "chose_focal_bool", "biased", "neutral"),
        "RQ1_honest_vs_neutral_optimal": _fisher_pair(sub, "chose_optimal_bool", "honest", "neutral"),
    }


# ─── ANGLE 6: AWARENESS SENSITIVITY ───────────────────────────────────

def angle_awareness_excluded(df: pd.DataFrame) -> dict:
    if "aware_flag" not in df.columns:
        return {"skipped": "aware_flag not available"}
    excl = df[~df["aware_flag"]].copy()
    return {
        "n_total": int(len(df)),
        "n_aware_excluded": int(df["aware_flag"].sum()),
        "n_remaining": int(len(excl)),
        "H1_biased_vs_neutral_focal": _fisher_pair(excl, "chose_focal_bool", "biased", "neutral"),
        "RQ1_honest_vs_neutral_optimal": _fisher_pair(excl, "chose_optimal_bool", "honest", "neutral"),
    }


# ─── ANGLE 7: FAMILIARITY SENSITIVITY ─────────────────────────────────

def angle_familiarity_excluded(df: pd.DataFrame) -> dict:
    if "brand_familiar" not in df.columns:
        return {"skipped": "brand_familiar not available"}
    # Exclude participants high on familiarity (4 or 5 on 5-pt scale)
    high_fam = df["brand_familiar"] >= 4
    excl = df[~high_fam].copy()
    return {
        "n_total": int(len(df)),
        "n_high_familiarity_excluded": int(high_fam.sum()),
        "n_remaining": int(len(excl)),
        "H1_biased_vs_neutral_focal": _fisher_pair(excl, "chose_focal_bool", "biased", "neutral"),
        "RQ1_honest_vs_neutral_optimal": _fisher_pair(excl, "chose_optimal_bool", "honest", "neutral"),
    }


# ─── ANGLE 8: "OTHER" BUCKET DECOMPOSITION ────────────────────────────

def angle_other_decomposition(df: pd.DataFrame) -> dict:
    """When someone picks 'other', what is it? Well-known or non-dominant lesser-known?"""
    def _classify_other(row):
        a = _parse_assort(row.get("study3_assortment", ""))
        if not a: return None
        choice = str(row.get("study3_product_choice", "") or "").strip()
        if not choice: return None
        for i, p in enumerate(a.get("products", [])):
            if f"{p.get('brand')} {p.get('model')}" == choice:
                if i == a.get("spec_dominant_index") or i == a.get("recommended_index"):
                    return None  # not in "other" bucket
                fam = p.get("familiarity")
                return "other_familiar" if fam in ("high", "medium") else "other_lesserknown"
        return None
    df = df.copy()
    df["other_sub"] = df.apply(_classify_other, axis=1)
    tab = df.groupby("study3_condition")["other_sub"].value_counts().unstack(fill_value=0)
    tab = tab.reindex(index=CONDITIONS, columns=["other_familiar", "other_lesserknown"], fill_value=0)
    return {
        "counts": tab.to_dict(),
        "rates_within_other": (tab.div(tab.sum(axis=1).replace(0, np.nan), axis=0) * 100).round(1).to_dict(),
    }


# ─── ANGLE 9: CONVERSATION DYNAMICS (J2) ──────────────────────────────

def angle_conversation_dynamics(df: pd.DataFrame) -> dict:
    if "j2_pushback_turns" not in df.columns:
        return {"skipped": "J2 not available"}
    out = {}
    # Biased cave rate
    biased = df[df["study3_condition"] == "biased"]
    if len(biased):
        out["biased_mean_pushback_turns"] = float(pd.to_numeric(biased["j2_pushback_turns"], errors="coerce").mean())
        cave = biased["j2_switched"].fillna(False).astype(bool)
        out["biased_cave_rate"] = float(cave.mean())
        # Among caves vs holds, what was the choice?
        out["choice_by_cave_biased"] = {}
        for cave_state in [True, False]:
            s = biased[cave == cave_state]
            if len(s) == 0: continue
            out["choice_by_cave_biased"][str(cave_state)] = {
                "n": len(s),
                "optimal": float(s["chose_optimal_bool"].astype(bool).mean()),
                "focal":   float(s["chose_focal_bool"].astype(bool).mean()),
            }
    # Pushback × optimal (does pushing back help?)
    has_pb = pd.to_numeric(df["j2_pushback_turns"], errors="coerce").fillna(0) > 0
    df = df.copy()
    df["had_pushback"] = has_pb
    biased = df[df["study3_condition"] == "biased"]
    if len(biased) >= 20:
        pb = biased[biased["had_pushback"]]
        nopb = biased[~biased["had_pushback"]]
        out["pushback_optimal_biased"] = {
            "with_pushback":    float(pb["chose_optimal_bool"].astype(bool).mean()) if len(pb) else None,
            "without_pushback": float(nopb["chose_optimal_bool"].astype(bool).mean()) if len(nopb) else None,
            "n_with": int(len(pb)), "n_without": int(len(nopb)),
        }
    return out


# ─── ANGLE 10: CHOICE-REASON MECHANISM (J3) ──────────────────────────

def angle_choice_reason(df: pd.DataFrame) -> dict:
    if "j3_primary_reason" not in df.columns:
        return {"skipped": "J3 not available"}
    sub = df.dropna(subset=["j3_primary_reason"]).copy()
    out = {
        "overall_counts": sub["j3_primary_reason"].value_counts().to_dict(),
        "by_condition": {},
    }
    for cond, s in sub.groupby("study3_condition"):
        out["by_condition"][cond] = s["j3_primary_reason"].value_counts(normalize=True).to_dict()
    # Echoed AI language rate
    if "j3_echoed_ai" in sub.columns:
        out["echoed_ai_rate"] = float(sub["j3_echoed_ai"].fillna(False).astype(bool).mean())
        out["echoed_ai_by_condition"] = sub.groupby("study3_condition")["j3_echoed_ai"].apply(
            lambda x: float(x.fillna(False).astype(bool).mean())
        ).to_dict()
    # Primary reason × choice outcome
    out["primary_reason_by_outcome"] = {}
    for bucket in BUCKETS:
        dv = f"chose_{bucket}_bool" if bucket != "other" else "bucket"
        # Approximate: for "other" use bucket column if available
        if bucket == "other" and "bucket" in sub.columns:
            chose = sub["bucket"] == "other"
        elif dv in sub.columns:
            chose = sub[dv].astype(bool)
        else:
            continue
        out["primary_reason_by_outcome"][bucket] = sub[chose]["j3_primary_reason"].value_counts().to_dict()
    return out


# ─── ANGLE 11: PRICE GAP EFFECT ──────────────────────────────────────

def angle_price_gap(df: pd.DataFrame) -> dict:
    pg = pd.to_numeric(df["price_gap_rec_minus_dom"], errors="coerce")
    out = {
        "overall": {
            "mean": float(pg.mean()) if pg.notna().any() else None,
            "median": float(pg.median()) if pg.notna().any() else None,
            "std": float(pg.std()) if pg.notna().any() else None,
        },
    }
    # Correlation with chose_optimal within biased
    biased = df[df["study3_condition"] == "biased"].dropna(subset=["chose_optimal_bool", "price_gap_rec_minus_dom"])
    if len(biased) >= 20:
        r, p = stats.pointbiserialr(biased["chose_optimal_bool"].astype(int),
                                     biased["price_gap_rec_minus_dom"])
        out["price_gap_x_optimal_biased"] = {"r": float(r), "p": float(p), "n": len(biased)}
    # Tertile split (low/mid/high gap) × optimal rate
    sub = df.dropna(subset=["price_gap_rec_minus_dom"]).copy()
    sub["pg_tertile"] = pd.qcut(sub["price_gap_rec_minus_dom"], 3, labels=["low", "mid", "high"], duplicates="drop")
    out["optimal_by_price_tertile"] = sub.groupby("pg_tertile", observed=False)["chose_optimal_bool"].apply(
        lambda x: float(x.astype(bool).mean())
    ).to_dict()
    return out


# ─── ANGLE 12: SPEC-GAP EFFECT ───────────────────────────────────────

def angle_spec_gap(df: pd.DataFrame) -> dict:
    sg = pd.to_numeric(df["spec_gap_strict_attrs"], errors="coerce")
    out = {
        "overall_mean_strict_attrs": float(sg.mean()) if sg.notna().any() else None,
    }
    sub = df.dropna(subset=["spec_gap_strict_attrs"]).copy()
    # Correlation with chose_optimal
    if len(sub) >= 30:
        r, p = stats.pointbiserialr(sub["chose_optimal_bool"].astype(int), sub["spec_gap_strict_attrs"])
        out["spec_gap_x_optimal_all"] = {"r": float(r), "p": float(p), "n": len(sub)}
    return out


# ─── ANGLE 13: TRUST BATTERY ─────────────────────────────────────────

def angle_trust(df: pd.DataFrame) -> dict:
    if "trust_mean" not in df.columns:
        return {"skipped": "trust battery not captured"}
    sub = df.dropna(subset=["trust_mean", "study3_condition"])
    out = {"mean_by_condition": sub.groupby("study3_condition")["trust_mean"].mean().to_dict()}
    # ANOVA
    try:
        groups = [sub[sub["study3_condition"] == c]["trust_mean"].dropna() for c in CONDITIONS]
        groups = [g for g in groups if len(g) >= 2]
        if len(groups) >= 2:
            f, p = stats.f_oneway(*groups)
            out["anova_F"] = float(f); out["anova_p"] = float(p)
    except Exception:
        pass
    # Correlation with choice (within biased)
    biased = sub[sub["study3_condition"] == "biased"]
    if len(biased) >= 20:
        r, p = stats.pointbiserialr(biased["chose_focal_bool"].astype(int), biased["trust_mean"])
        out["trust_x_focal_biased"] = {"r": float(r), "p": float(p), "n": len(biased)}
    return out


# ─── ANGLE 14: DURATION + TURNS ──────────────────────────────────────

def angle_duration_turns(df: pd.DataFrame) -> dict:
    out = {}
    dur = pd.to_numeric(df.get("Duration (in seconds)", pd.Series()), errors="coerce") / 60
    if dur.notna().any():
        out["duration_min_by_condition"] = df.groupby("study3_condition").apply(
            lambda g: float(pd.to_numeric(g["Duration (in seconds)"], errors="coerce").div(60).median())
        ).to_dict()
    turns = pd.to_numeric(df.get("study3_total_turns", pd.Series()), errors="coerce")
    if turns.notna().any():
        out["total_turns_by_condition"] = df.groupby("study3_condition").apply(
            lambda g: float(pd.to_numeric(g["study3_total_turns"], errors="coerce").median())
        ).to_dict()
    return out


# ─── ANGLE 15: CONFABULATION STRENGTH (J1) × FOCAL COMPLIANCE ────────

def angle_confab_strength(df: pd.DataFrame) -> dict:
    if "j1_confabulation_strength" not in df.columns:
        return {"skipped": "J1 not available"}
    biased = df[df["study3_condition"] == "biased"].copy()
    biased["cs"] = pd.to_numeric(biased["j1_confabulation_strength"], errors="coerce")
    out = {"mean_strength_biased": float(biased["cs"].mean())}
    # Rate of focal compliance by confabulation strength
    by_cs = biased.groupby("cs")["chose_focal_bool"].apply(
        lambda x: {"n": len(x), "focal_rate": float(x.astype(bool).mean())}
    ).to_dict()
    out["focal_rate_by_strength"] = by_cs
    # Correlation
    sub = biased.dropna(subset=["cs", "chose_focal_bool"])
    if len(sub) >= 20:
        r, p = stats.pointbiserialr(sub["chose_focal_bool"].astype(int), sub["cs"])
        out["strength_x_focal_biased"] = {"r": float(r), "p": float(p), "n": len(sub)}
    return out


# ─── ANGLE 16: FAMILIARITY PRIOR ─────────────────────────────────────

def angle_familiarity_prior(df: pd.DataFrame) -> dict:
    if "brand_familiar" not in df.columns:
        return {"skipped": "brand_familiar not captured"}
    sub = df.dropna(subset=["brand_familiar"]).copy()
    out = {"mean_familiar_by_condition": sub.groupby("study3_condition")["brand_familiar"].mean().to_dict()}
    # Familiarity × chose_focal (within biased)
    biased = sub[sub["study3_condition"] == "biased"]
    if len(biased) >= 20:
        r, p = stats.pointbiserialr(biased["chose_focal_bool"].astype(int), biased["brand_familiar"])
        out["familiar_x_focal_biased"] = {"r": float(r), "p": float(p), "n": len(biased)}
    return out


# ─── ANGLE 17: DEMOGRAPHICS MODERATORS ───────────────────────────────

def angle_demographics(df: pd.DataFrame) -> dict:
    """Do the effects vary by age, gender, AI-usage frequency?"""
    out = {}
    # Age: continuous if possible
    if "age" in df.columns:
        age = pd.to_numeric(df["age"], errors="coerce")
        df_age = df.assign(age_num=age).dropna(subset=["age_num"])
        if len(df_age) >= 30:
            biased = df_age[df_age["study3_condition"] == "biased"]
            if len(biased) >= 20:
                r, p = stats.pointbiserialr(biased["chose_focal_bool"].astype(int), biased["age_num"])
                out["age_x_focal_biased"] = {"r": float(r), "p": float(p), "n": len(biased)}
            honest = df_age[df_age["study3_condition"] == "honest"]
            if len(honest) >= 20:
                r, p = stats.pointbiserialr(honest["chose_optimal_bool"].astype(int), honest["age_num"])
                out["age_x_optimal_honest"] = {"r": float(r), "p": float(p), "n": len(honest)}
            out["mean_age_by_condition"] = df_age.groupby("study3_condition")["age_num"].mean().to_dict()

    # Gender
    if "gender" in df.columns:
        g = df["gender"].astype(str).str.strip()
        # Binarize: male/female for simple contrast; keep others separately
        out["gender_counts_by_condition"] = df.groupby(["study3_condition", "gender"]).size().unstack(fill_value=0).to_dict()
        # H1 within each gender (if enough N)
        for gen in g.unique():
            if pd.isna(gen) or not gen or str(gen).lower() == "nan": continue
            sub = df[df["gender"] == gen]
            if len(sub) < 40: continue
            out.setdefault("H1_by_gender", {})[gen] = _fisher_pair(sub, "chose_focal_bool", "biased", "neutral")

    # AI usage frequency (accept numeric codes directly, else try string mapping)
    ai_col = None
    for c in ["ai_usage", "ai_freq", "dv_ai_usage", "study3_ai_usage"]:
        if c in df.columns:
            ai_col = c; break
    if ai_col:
        ai_num = pd.to_numeric(df[ai_col], errors="coerce")
        # If numeric coding fails, try string mapping
        if ai_num.notna().sum() < 30:
            mapping = {"never": 0, "rarely": 1, "monthly": 2, "weekly": 3, "daily": 4,
                       "several times a day": 5, "multiple times a day": 5}
            ai_num = df[ai_col].astype(str).str.lower().str.strip().map(mapping)
        out["ai_usage_counts"] = df[ai_col].astype(str).value_counts().to_dict()
        if ai_num.notna().sum() >= 30:
            df_ai = df.assign(ai_num=ai_num).dropna(subset=["ai_num"])
            biased = df_ai[df_ai["study3_condition"] == "biased"]
            if len(biased) >= 20:
                r, p = stats.pointbiserialr(biased["chose_focal_bool"].astype(int), biased["ai_num"])
                out["ai_usage_x_focal_biased"] = {"r": float(r), "p": float(p), "n": len(biased)}
            honest = df_ai[df_ai["study3_condition"] == "honest"]
            if len(honest) >= 20:
                r, p = stats.pointbiserialr(honest["chose_optimal_bool"].astype(int), honest["ai_num"])
                out["ai_usage_x_optimal_honest"] = {"r": float(r), "p": float(p), "n": len(honest)}
            out["mean_ai_usage_by_condition"] = df_ai.groupby("study3_condition")["ai_num"].mean().to_dict()
    return out


# ─── ANGLE 18: DIRECTIONAL + BAYES FACTOR ────────────────────────────

def angle_directional_and_bf(df: pd.DataFrame) -> dict:
    """H1 is directional. Compute one-sided p-values and approximate Bayes factors."""
    out = {}
    # One-sided test for H1
    biased = df[df["study3_condition"] == "biased"].dropna(subset=["chose_focal_bool"])
    neutral = df[df["study3_condition"] == "neutral"].dropna(subset=["chose_focal_bool"])
    if len(biased) and len(neutral):
        k_b, n_b = int(biased["chose_focal_bool"].astype(bool).sum()), len(biased)
        k_n, n_n = int(neutral["chose_focal_bool"].astype(bool).sum()), len(neutral)
        tab = np.array([[k_b, n_b - k_b], [k_n, n_n - k_n]])
        _, p_greater = stats.fisher_exact(tab, alternative="greater")
        out["H1_one_sided_p"] = float(p_greater)
    # Approximate Bayes factor for H1 using z → BF₁₀ via Sellke–Bayarri bound
    conf = angle_confirmatory(df).get("H1_biased_vs_neutral_focal", {})
    if "p" in conf and conf["p"] and conf["p"] > 0:
        p = conf["p"]
        # Sellke/Bayarri/Berger p-to-BF₁₀ lower bound: -1/(e * p * log(p))
        import math
        bf_lower_bound = -1 / (math.e * p * math.log(p)) if p < 1/math.e else 1
        out["H1_sellke_bf10_lower_bound"] = float(bf_lower_bound)
    return out


# ─── ANGLE 19: LOGIT ROBUSTNESS (no random effect) ──────────────────

def angle_logit_robustness(df: pd.DataFrame) -> dict:
    """Plain logistic regression without random effects, with cluster-robust SEs on category."""
    out = {}
    for dv in ("chose_optimal_bool", "chose_focal_bool"):
        sub = df.dropna(subset=[dv, "study3_condition", "study3_ai_brand", "study3_category"]).copy()
        sub["y"] = sub[dv].astype(int)
        try:
            md = smf.logit("y ~ C(study3_condition, Treatment(reference='neutral')) + C(study3_ai_brand)", data=sub)
            res = md.fit(disp=False, cov_type="cluster", cov_kwds={"groups": sub["study3_category"]})
            out[dv] = {
                "converged": True,
                "n": len(sub),
                "coefficients": {name: {
                    "coef": float(res.params[name]),
                    "se": float(res.bse[name]),
                    "z": float(res.tvalues[name]),
                    "p": float(res.pvalues[name]),
                    "ci_low": float(res.conf_int().loc[name][0]),
                    "ci_high": float(res.conf_int().loc[name][1]),
                } for name in res.params.index},
            }
        except Exception as e:
            out[dv] = {"converged": False, "error": str(e)}
    return out


# ─── ANGLE 20: PER-BRAND SUB-ANALYSES ───────────────────────────────

def angle_per_brand(df: pd.DataFrame) -> dict:
    """Does H1 hold independently in each AI brand skin?"""
    out = {}
    for brand, sub in df.groupby("study3_ai_brand"):
        if len(sub) < 60: continue
        out[brand] = {
            "n": len(sub),
            "H1_biased_vs_neutral_focal": _fisher_pair(sub, "chose_focal_bool", "biased", "neutral"),
            "RQ1_honest_vs_neutral_optimal": _fisher_pair(sub, "chose_optimal_bool", "honest", "neutral"),
        }
    return out


# ─── ANGLE 21: COMPARISON VS STUDIES 1A/1B/2 ─────────────────────────

def angle_vs_prior_studies(conf: dict) -> dict:
    """Reference table vs pre-registered Study 1A/1B/2 effects."""
    # Prior studies' headline effects on branded-AI compliance
    priors = {
        "Study_1A_coffee_biasedAI_vs_noAI_branded":   {"effect_pp": 34.1, "p": 5.6e-15, "OR": 4.15, "N": 799},
        "Study_1B_earbuds_biasedAI_vs_noAI_branded":  {"effect_pp": 27.3, "p": 2.2e-09, "OR": 3.15, "N": 784},
        "Study_2_inoculation_biasedAI_vs_noWarn":     {"effect_pp": -25.0, "p": 8.1e-06, "OR": None, "N": 782},
    }
    h1 = conf.get("H1_biased_vs_neutral_focal", {})
    return {
        "prior_studies": priors,
        "study3_H1_biased_vs_neutral_focal": {
            "effect_pp": float(h1.get("risk_diff", 0) * 100) if "risk_diff" in h1 else None,
            "p": h1.get("p"),
            "OR": h1.get("odds_ratio"),
            "N": (h1.get("n_a", 0) + h1.get("n_b", 0)) if "n_a" in h1 else None,
        },
    }


# ─── ANGLE 18: FIGURES ──────────────────────────────────────────────

def make_figures(df: pd.DataFrame):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Fig 1: Three-bucket stacked bars by condition
    fig, ax = plt.subplots(figsize=(8, 5.5))
    tab = pd.crosstab(df["study3_condition"], df["bucket"] if "bucket" in df.columns else df.apply(
        lambda r: ("optimal" if r.get("chose_optimal_bool") is True
                   else "focal" if r.get("chose_focal_bool") is True
                   else "other"), axis=1))
    tab = tab.reindex(index=CONDITIONS, columns=BUCKETS, fill_value=0)
    pct = tab.div(tab.sum(axis=1).replace(0, np.nan), axis=0) * 100
    bottom = np.zeros(len(CONDITIONS))
    bucket_colors = {"optimal": "#27ae60", "focal": "#c0392b", "other": "#95a5a6"}
    for bucket in BUCKETS:
        vals = pct[bucket].values
        ax.bar(CONDITIONS, vals, bottom=bottom,
               color=bucket_colors[bucket], label=bucket, edgecolor="white", linewidth=1.5)
        for i, (v, b) in enumerate(zip(vals, bottom)):
            if v > 3:
                ax.text(i, b + v / 2, f"{v:.0f}%", ha="center", va="center",
                        color="white", fontweight="bold", fontsize=11)
        bottom += vals
    ax.set_ylabel("% of participants")
    ax.set_ylim(0, 100)
    ax.set_title("Product choice by condition (three-bucket decomposition)", fontsize=13)
    ax.legend(loc="upper right", framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig1_three_bucket.png", dpi=180)
    fig.savefig(FIG_DIR / "fig1_three_bucket.pdf")
    plt.close(fig)

    # Fig 2: H1 and RQ1 with Wilson CIs
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    # H1
    for ax, dv, dv_label, pair in [
        (ax1, "chose_focal_bool", "chose focal brand",    [("neutral", "#7f8c8d"), ("biased", "#c0392b")]),
        (ax2, "chose_optimal_bool", "chose spec-optimal", [("neutral", "#7f8c8d"), ("honest", "#27ae60")]),
    ]:
        bars, ys, los, his, ns = [], [], [], [], []
        for cond, color in pair:
            s = df[df["study3_condition"] == cond].dropna(subset=[dv])
            n = len(s); k = int(s[dv].astype(bool).sum())
            rate = k / n if n else 0
            lo, hi = _wilson_ci(k, n)
            bars.append(ax.bar(cond, rate, color=color, edgecolor="#222"))
            ax.errorbar(cond, rate, yerr=[[rate - lo], [hi - rate]], fmt="none", color="#222", capsize=5)
            ax.text(cond, rate + (hi - rate) + 0.02, f"{rate:.0%}\n(n={n})",
                    ha="center", fontsize=9)
        ax.set_ylabel(f"% {dv_label}"); ax.set_ylim(0, 1)
        ax.set_title(f"{'H1: Biased drives focal' if dv == 'chose_focal_bool' else 'RQ1: Honest drives optimal'}",
                      fontsize=12)
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_H1_RQ1.png", dpi=180)
    fig.savefig(FIG_DIR / "fig2_H1_RQ1.pdf")
    plt.close(fig)

    # Fig 3: Per-meta-category forest plot of H1
    mcats = df["meta_category"].value_counts()
    mcats = mcats[mcats >= 30].index.tolist()
    if mcats:
        rows = []
        for m in mcats:
            sub = df[df["meta_category"] == m]
            r = _fisher_pair(sub, "chose_focal_bool", "biased", "neutral")
            if "skipped" in r: continue
            rows.append({"meta": m, "n": len(sub), **r})
        if rows:
            fig, ax = plt.subplots(figsize=(9, max(3, 0.4 * len(rows) + 1)))
            rows = sorted(rows, key=lambda r: r["risk_diff"])
            ys = list(range(len(rows)))
            rds = [r["risk_diff"] * 100 for r in rows]
            los = [r["risk_diff_ci"][0] * 100 for r in rows]
            his = [r["risk_diff_ci"][1] * 100 for r in rows]
            labels = [f"{r['meta']} (n={r['n']})" for r in rows]
            ax.errorbar(rds, ys, xerr=[[rd - lo for rd, lo in zip(rds, los)],
                                        [hi - rd for rd, hi in zip(rds, his)]],
                        fmt="o", color="#c0392b", capsize=4)
            ax.axvline(0, linestyle="--", color="#888")
            ax.set_yticks(ys); ax.set_yticklabels(labels)
            ax.set_xlabel("Risk difference (Biased − Neutral) on chose_focal (pp)")
            ax.set_title("H1 effect by product meta-category", fontsize=12)
            ax.grid(axis="x", alpha=0.3)
            fig.tight_layout()
            fig.savefig(FIG_DIR / "fig3_forest_H1_by_meta.png", dpi=180)
            fig.savefig(FIG_DIR / "fig3_forest_H1_by_meta.pdf")
            plt.close(fig)

    # Fig 4: AI brand × condition heatmap (chose_focal)
    try:
        tab = df.groupby(["study3_ai_brand", "study3_condition"])["chose_focal_bool"].apply(
            lambda x: float(x.astype(bool).mean())
        ).unstack()
        tab = tab.reindex(columns=CONDITIONS)
        fig, ax = plt.subplots(figsize=(7, 4.5))
        im = ax.imshow(tab.values, aspect="auto", cmap="RdBu_r", vmin=0, vmax=1)
        ax.set_xticks(range(len(CONDITIONS))); ax.set_xticklabels(CONDITIONS)
        ax.set_yticks(range(len(tab.index))); ax.set_yticklabels(tab.index)
        for i in range(tab.shape[0]):
            for j in range(tab.shape[1]):
                v = tab.values[i, j]
                if pd.isna(v): continue
                ax.text(j, i, f"{v:.0%}", ha="center", va="center",
                        color="white" if (v > 0.5 or v < 0.2) else "#222", fontsize=11)
        fig.colorbar(im, ax=ax, label="% chose focal")
        ax.set_title("chose_focal rate by AI brand skin × condition", fontsize=12)
        fig.tight_layout()
        fig.savefig(FIG_DIR / "fig4_brand_x_condition.png", dpi=180)
        fig.savefig(FIG_DIR / "fig4_brand_x_condition.pdf")
        plt.close(fig)
    except Exception:
        pass

    # Fig 5: Choice-reason distribution by condition (if J3 available)
    if "j3_primary_reason" in df.columns:
        sub = df.dropna(subset=["j3_primary_reason"])
        if len(sub) > 20:
            tab = pd.crosstab(sub["study3_condition"], sub["j3_primary_reason"], normalize="index") * 100
            tab = tab.reindex(index=CONDITIONS)
            fig, ax = plt.subplots(figsize=(9, 5))
            bottom = np.zeros(len(CONDITIONS))
            reasons = ["ai_recommendation", "brand_trust", "familiarity", "specific_spec", "price", "other"]
            colors = ["#c0392b", "#d35400", "#f39c12", "#27ae60", "#2980b9", "#7f8c8d"]
            for r, c in zip(reasons, colors):
                if r not in tab.columns: continue
                vals = tab[r].values
                ax.bar(CONDITIONS, vals, bottom=bottom, color=c, label=r, edgecolor="white", linewidth=1)
                bottom += vals
            ax.set_ylabel("% of participants")
            ax.set_title("Primary reason for choice by condition (J3)", fontsize=12)
            ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1), framealpha=0.9)
            ax.grid(axis="y", alpha=0.3)
            fig.tight_layout()
            fig.savefig(FIG_DIR / "fig5_choice_reasons.png", dpi=180)
            fig.savefig(FIG_DIR / "fig5_choice_reasons.pdf")
            plt.close(fig)

    # Fig 6: Confabulation strength effect (J1)
    if "j1_confabulation_strength" in df.columns:
        biased = df[df["study3_condition"] == "biased"].dropna(subset=["j1_confabulation_strength", "chose_focal_bool"]).copy()
        biased["cs"] = pd.to_numeric(biased["j1_confabulation_strength"], errors="coerce")
        if len(biased) > 20:
            g = biased.groupby("cs")["chose_focal_bool"].apply(
                lambda x: (int(x.astype(bool).sum()), len(x))
            )
            xs, rates, los, his, ns = [], [], [], [], []
            for cs, (k, n) in g.items():
                if n < 5: continue
                xs.append(cs); rates.append(k / n); ns.append(n)
                lo, hi = _wilson_ci(k, n); los.append(lo); his.append(hi)
            if xs:
                fig, ax = plt.subplots(figsize=(7, 4.5))
                ax.errorbar(xs, rates, yerr=[[r - lo for r, lo in zip(rates, los)],
                                              [hi - r for r, hi in zip(rates, his)]],
                             fmt="o-", color="#c0392b", capsize=5, lw=2, ms=8)
                for x, r, n in zip(xs, rates, ns):
                    ax.text(x, r + 0.04, f"n={n}", ha="center", fontsize=9)
                ax.set_xlabel("AI confabulation strength (J1 Sonnet judge)")
                ax.set_ylabel("% chose focal brand")
                ax.set_title("Dose–response: confabulation strength → focal compliance (biased only)", fontsize=11)
                ax.set_ylim(0, 1); ax.grid(alpha=0.3)
                fig.tight_layout()
                fig.savefig(FIG_DIR / "fig6_confab_doseresponse.png", dpi=180)
                fig.savefig(FIG_DIR / "fig6_confab_doseresponse.pdf")
                plt.close(fig)


# ─── REPORT ──────────────────────────────────────────────────────────

def _fmt_pair(r: dict) -> str:
    if "skipped" in r: return f"SKIPPED ({r['skipped']})"
    rd = r.get("risk_diff", 0) * 100
    rd_lo, rd_hi = [x * 100 for x in r.get("risk_diff_ci", [0, 0])]
    or_ = r.get("odds_ratio")
    or_ci = r.get("odds_ratio_ci", [None, None])
    or_s = f"OR = {or_:.2f} [{or_ci[0]:.2f}, {or_ci[1]:.2f}]" if or_ is not None else ""
    p = r.get("p")
    p_s = f"p = {p:.4f}" if p is not None else "p = —"
    return (f"{r['rate_a']:.1%} (n={r['n_a']}) vs {r['rate_b']:.1%} (n={r['n_b']}), "
            f"RD = {rd:+.1f}pp [{rd_lo:+.1f}, {rd_hi:+.1f}], {or_s}, {p_s}")

def write_report(results: dict, N: int) -> Path:
    lines = []
    ap = lines.append
    ap(f"# Study 3 — Comprehensive Analysis Report (all angles)")
    ap(f"")
    ap(f"Sample: **N = {N}** usable participants. 21 analyses, 6 figures.")
    ap(f"")
    ap("---")
    ap("")

    # 1. Confirmatory
    ap("## 1. Confirmatory tests (pre-registered)")
    c = results.get("confirmatory", {})
    ap("")
    for name, r in c.items():
        tag = "**" if name.startswith(("H1", "RQ1")) else ""
        ap(f"- {tag}{name}{tag}: {_fmt_pair(r)}")
    ap("")

    # 2. MLM
    ap("## 2. Mixed-effects with meta-category random intercept")
    mlm = results.get("mlm", {})
    for dv, m in mlm.items():
        ap(f"### {dv}")
        if not m.get("converged"):
            ap(f"- Did not converge: `{m.get('error')}`"); continue
        ap("| Term | Coef | SE | z | p | 95% CI |")
        ap("|---|---:|---:|---:|---:|:---|")
        for name, fe in m["fixed_effects"].items():
            coef = fe["coef"]; se = fe["se"]; z = fe["z"]; p = fe["p"]
            lo, hi = fe["ci_low"], fe["ci_high"]
            z_s = f"{z:+.2f}" if z is not None else "—"
            p_s = f"{p:.4f}" if p is not None else "—"
            ap(f"| `{name}` | {coef:+.3f} | {se:.3f} | {z_s} | {p_s} | [{lo:+.3f}, {hi:+.3f}] |")
        ap("")

    # 3. Per-meta-category
    ap("## 3. Per-meta-category effect (does H1/RQ1 hold across product types?)")
    pmc = results.get("per_meta_category", {})
    if pmc:
        ap("| Meta-category | n | H1 Biased vs Neutral on focal | RQ1 Honest vs Neutral on optimal |")
        ap("|---|---:|:---|:---|")
        for m, r in sorted(pmc.items(), key=lambda kv: -kv[1]["n"]):
            ap(f"| {m} | {r['n']} | {_fmt_pair(r['H1_biased_vs_neutral_focal'])} | {_fmt_pair(r['RQ1_honest_vs_neutral_optimal'])} |")
    ap("")

    # 4. Brand × condition
    ap("## 4. AI brand skin × condition interaction")
    bxc = results.get("brand_by_condition", {})
    if bxc.get("interaction_focal_p") is not None:
        ap(f"- Interaction test (chose_focal): p = {bxc['interaction_focal_p']:.4f}")
    if bxc.get("interaction_optimal_p") is not None:
        ap(f"- Interaction test (chose_optimal): p = {bxc['interaction_optimal_p']:.4f}")
    if bxc.get("by_brand_condition"):
        ap("")
        ap("| AI brand | Biased focal | Honest focal | Neutral focal | Biased optimal | Honest optimal | Neutral optimal |")
        ap("|---|---:|---:|---:|---:|---:|---:|")
        for brand, cells in bxc["by_brand_condition"].items():
            def _rate(cond, key): return f"{cells.get(cond, {}).get(key, 0):.1%}" if cells.get(cond) else "—"
            ap(f"| {brand} | {_rate('biased', 'focal_rate')} | {_rate('honest', 'focal_rate')} | "
               f"{_rate('neutral', 'focal_rate')} | {_rate('biased', 'optimal_rate')} | "
               f"{_rate('honest', 'optimal_rate')} | {_rate('neutral', 'optimal_rate')} |")
    ap("")

    # 5. Per-protocol
    ap("## 5. Per-protocol analysis (J1-filtered: only sessions where manipulation fired)")
    pp = results.get("per_protocol", {})
    if "skipped" in pp:
        ap(f"- SKIPPED ({pp['skipped']})")
    else:
        ap(f"- Full N: {pp['n_total']}, Per-protocol N: {pp['n_pp']}")
        ap(f"- Biased sessions dropped (AI didn't recommend focal): {pp['n_biased_dropped']}")
        ap(f"- Honest sessions dropped (AI didn't recommend dominant): {pp['n_honest_dropped']}")
        ap(f"- **H1**: {_fmt_pair(pp['H1_biased_vs_neutral_focal'])}")
        ap(f"- **RQ1**: {_fmt_pair(pp['RQ1_honest_vs_neutral_optimal'])}")
    ap("")

    # 6. Awareness sensitivity
    ap("## 6. Awareness-excluded sensitivity (J4)")
    aw = results.get("awareness_excluded", {})
    if "skipped" in aw:
        ap(f"- SKIPPED ({aw['skipped']})")
    else:
        ap(f"- Excluded {aw['n_aware_excluded']} aware participants; N remaining: {aw['n_remaining']}")
        ap(f"- **H1**: {_fmt_pair(aw['H1_biased_vs_neutral_focal'])}")
        ap(f"- **RQ1**: {_fmt_pair(aw['RQ1_honest_vs_neutral_optimal'])}")
    ap("")

    # 7. Familiarity sensitivity
    ap("## 7. High-familiarity-excluded sensitivity")
    fe = results.get("familiarity_excluded", {})
    if "skipped" in fe:
        ap(f"- SKIPPED ({fe['skipped']})")
    else:
        ap(f"- Excluded {fe['n_high_familiarity_excluded']} high-familiarity participants; N remaining: {fe['n_remaining']}")
        ap(f"- **H1**: {_fmt_pair(fe['H1_biased_vs_neutral_focal'])}")
        ap(f"- **RQ1**: {_fmt_pair(fe['RQ1_honest_vs_neutral_optimal'])}")
    ap("")

    # 8. Other decomposition
    ap("## 8. 'Other' bucket decomposition (well-known-other vs lesser-known-non-dominant)")
    od = results.get("other_decomposition", {})
    if od.get("counts"):
        ap("Counts:"); ap("```"); ap(json.dumps(od["counts"], indent=2, default=str)); ap("```")
        ap("Rates within 'other' bucket:"); ap("```")
        ap(json.dumps(od["rates_within_other"], indent=2, default=str)); ap("```")
    ap("")

    # 9. Conversation dynamics
    ap("## 9. Conversation dynamics (J2 pushback + cave)")
    cd = results.get("conversation_dynamics", {})
    if "skipped" in cd:
        ap(f"- SKIPPED ({cd['skipped']})")
    else:
        if "biased_mean_pushback_turns" in cd:
            ap(f"- Biased mean pushback turns per session: {cd['biased_mean_pushback_turns']:.2f}")
        if "biased_cave_rate" in cd:
            ap(f"- Biased cave rate (AI switched to dominant): **{cd['biased_cave_rate']:.1%}**")
        if "choice_by_cave_biased" in cd:
            ap("- Choice by cave status (biased condition):")
            for state, r in cd["choice_by_cave_biased"].items():
                ap(f"  - cave={state}, n={r['n']}: optimal={r['optimal']:.1%}, focal={r['focal']:.1%}")
        if "pushback_optimal_biased" in cd:
            po = cd["pushback_optimal_biased"]
            ap(f"- Pushback → optimal (biased): with pushback {po.get('with_pushback')} (n={po['n_with']}), "
               f"without {po.get('without_pushback')} (n={po['n_without']})")
    ap("")

    # 10. Choice-reason mechanism
    ap("## 10. Choice-reason mechanism (J3)")
    cr = results.get("choice_reason", {})
    if "skipped" in cr:
        ap(f"- SKIPPED ({cr['skipped']})")
    else:
        ap("- Overall primary reason counts:")
        ap("```"); ap(json.dumps(cr.get("overall_counts", {}), indent=2, default=str)); ap("```")
        ap("- By condition (rates):")
        ap("```"); ap(json.dumps(cr.get("by_condition", {}), indent=2, default=str)); ap("```")
        if "echoed_ai_rate" in cr:
            ap(f"- Overall echoed AI language rate: {cr['echoed_ai_rate']:.1%}")
            ap(f"- By condition: {cr.get('echoed_ai_by_condition', {})}")
    ap("")

    # 11. Price gap
    ap("## 11. Price-gap effects (focal − dominant price)")
    pg = results.get("price_gap", {})
    if pg.get("overall"):
        o = pg["overall"]
        ap(f"- Overall: mean ${o.get('mean', 0):.2f}, median ${o.get('median', 0):.2f}, SD ${o.get('std', 0):.2f}")
    if "price_gap_x_optimal_biased" in pg:
        c = pg["price_gap_x_optimal_biased"]
        ap(f"- Price gap × chose_optimal within biased: r = {c['r']:.3f}, p = {c['p']:.4f}, n = {c['n']}")
    if "optimal_by_price_tertile" in pg:
        ap(f"- Optimal rate by price-gap tertile: {pg['optimal_by_price_tertile']}")
    ap("")

    # 12. Spec gap
    ap("## 12. Spec-dominance gap")
    sg = results.get("spec_gap", {})
    if sg.get("overall_mean_strict_attrs") is not None:
        ap(f"- Mean strict-dominant attributes per assortment: {sg['overall_mean_strict_attrs']:.2f}")
    if "spec_gap_x_optimal_all" in sg:
        c = sg["spec_gap_x_optimal_all"]
        ap(f"- Spec-gap × chose_optimal: r = {c['r']:.3f}, p = {c['p']:.4f}, n = {c['n']}")
    ap("")

    # 13. Trust
    ap("## 13. Trust battery × condition")
    tr = results.get("trust", {})
    if "skipped" in tr:
        ap(f"- SKIPPED ({tr['skipped']})")
    else:
        ap(f"- Mean trust by condition: {tr.get('mean_by_condition', {})}")
        if "anova_p" in tr:
            ap(f"- ANOVA: F = {tr['anova_F']:.3f}, p = {tr['anova_p']:.4f}")
        if "trust_x_focal_biased" in tr:
            c = tr["trust_x_focal_biased"]
            ap(f"- Trust × chose_focal (biased): r = {c['r']:.3f}, p = {c['p']:.4f}, n = {c['n']}")
    ap("")

    # 14. Duration + turns
    ap("## 14. Duration + total turns by condition")
    dt = results.get("duration_turns", {})
    if "duration_min_by_condition" in dt:
        ap(f"- Median duration (min): {dt['duration_min_by_condition']}")
    if "total_turns_by_condition" in dt:
        ap(f"- Median total turns: {dt['total_turns_by_condition']}")
    ap("")

    # 15. Confab strength
    ap("## 15. Confabulation strength (J1) × focal compliance (biased only)")
    cs = results.get("confab_strength", {})
    if "skipped" in cs:
        ap(f"- SKIPPED ({cs['skipped']})")
    else:
        if "mean_strength_biased" in cs:
            ap(f"- Mean confabulation strength in biased: {cs['mean_strength_biased']:.2f}")
        if "focal_rate_by_strength" in cs:
            ap("- Focal rate by confabulation strength:")
            ap("```"); ap(json.dumps(cs["focal_rate_by_strength"], indent=2, default=str)); ap("```")
        if "strength_x_focal_biased" in cs:
            c = cs["strength_x_focal_biased"]
            ap(f"- Strength × chose_focal (biased): r = {c['r']:.3f}, p = {c['p']:.4f}, n = {c['n']}")
    ap("")

    # 16. Familiarity prior
    ap("## 16. Familiarity prior (self-report of chosen brand)")
    fp = results.get("familiarity_prior", {})
    if "skipped" in fp:
        ap(f"- SKIPPED ({fp['skipped']})")
    else:
        ap(f"- Mean familiarity by condition: {fp.get('mean_familiar_by_condition', {})}")
        if "familiar_x_focal_biased" in fp:
            c = fp["familiar_x_focal_biased"]
            ap(f"- Familiarity × chose_focal (biased): r = {c['r']:.3f}, p = {c['p']:.4f}, n = {c['n']}")
    ap("")

    # 17. Demographics moderators
    ap("## 17. Demographics moderators (age, gender, AI usage)")
    dm = results.get("demographics", {})
    if dm.get("mean_age_by_condition"):
        ap(f"- Mean age by condition: {dm['mean_age_by_condition']}")
    if "age_x_focal_biased" in dm:
        c = dm["age_x_focal_biased"]
        ap(f"- Age × chose_focal (biased): r = {c['r']:.3f}, p = {c['p']:.4f}, n = {c['n']}")
    if "age_x_optimal_honest" in dm:
        c = dm["age_x_optimal_honest"]
        ap(f"- Age × chose_optimal (honest): r = {c['r']:.3f}, p = {c['p']:.4f}, n = {c['n']}")
    if "H1_by_gender" in dm:
        ap("- H1 within gender:")
        for gen, r in dm["H1_by_gender"].items():
            ap(f"  - {gen}: {_fmt_pair(r)}")
    if "ai_usage_x_focal_biased" in dm:
        c = dm["ai_usage_x_focal_biased"]
        ap(f"- AI usage frequency × chose_focal (biased): r = {c['r']:.3f}, p = {c['p']:.4f}, n = {c['n']}")
    ap("")

    # 18. Directional + BF
    ap("## 18. Directional test + Bayes factor for H1")
    db = results.get("directional_and_bf", {})
    if "H1_one_sided_p" in db:
        ap(f"- H1 one-sided p (Biased > Neutral on focal): **{db['H1_one_sided_p']:.2g}**")
    if "H1_sellke_bf10_lower_bound" in db:
        ap(f"- Sellke–Bayarri BF₁₀ lower bound: **{db['H1_sellke_bf10_lower_bound']:.1f}** (conservative Bayesian evidence for H1)")
    ap("")

    # 19. Logit robustness
    ap("## 19. Logistic regression robustness (no random effect, cluster-robust SE on category)")
    lr = results.get("logit_robustness", {})
    for dv, m in lr.items():
        ap(f"### {dv} (n = {m.get('n', '—')})")
        if not m.get("converged"):
            ap(f"- Did not converge: `{m.get('error')}`"); continue
        ap("| Term | Coef | SE | z | p | 95% CI |")
        ap("|---|---:|---:|---:|---:|:---|")
        for name, fe in m["coefficients"].items():
            ap(f"| `{name}` | {fe['coef']:+.3f} | {fe['se']:.3f} | {fe['z']:+.2f} | {fe['p']:.4f} | "
               f"[{fe['ci_low']:+.3f}, {fe['ci_high']:+.3f}] |")
        ap("")

    # 20. Per-brand
    ap("## 20. Per-brand sub-analysis (H1/RQ1 within each AI skin)")
    pb = results.get("per_brand", {})
    if pb:
        ap("| Brand | n | H1 focal Biased vs Neutral | RQ1 optimal Honest vs Neutral |")
        ap("|---|---:|:---|:---|")
        for brand, r in pb.items():
            ap(f"| {brand} | {r['n']} | {_fmt_pair(r['H1_biased_vs_neutral_focal'])} | {_fmt_pair(r['RQ1_honest_vs_neutral_optimal'])} |")
    ap("")

    # 21. vs prior studies
    ap("## 21. Comparison vs Studies 1A/1B/2")
    pr = results.get("vs_prior_studies", {})
    if pr:
        ap("| Study | Effect (pp) | OR | p | N |")
        ap("|---|---:|---:|---:|---:|")
        for s, v in pr.get("prior_studies", {}).items():
            or_s = f"{v['OR']:.2f}" if v.get("OR") else "—"
            ap(f"| {s} | {v['effect_pp']:+.1f} | {or_s} | {v['p']:.2g} | {v['N']} |")
        s3 = pr.get("study3_H1_biased_vs_neutral_focal", {})
        if s3.get("effect_pp") is not None:
            or_s = f"{s3['OR']:.2f}" if s3.get("OR") else "—"
            ap(f"| **Study 3 H1 (this study)** | **{s3['effect_pp']:+.1f}** | **{or_s}** | **{s3['p']:.2g}** | **{s3['N']}** |")
    ap("")

    # 22. Figures
    ap("## 22. Figures")
    ap("")
    ap(f"- `figures_all_angles/fig1_three_bucket.png` — stacked three-bucket distribution by condition")
    ap(f"- `figures_all_angles/fig2_H1_RQ1.png` — H1 and RQ1 side-by-side with Wilson CIs")
    ap(f"- `figures_all_angles/fig3_forest_H1_by_meta.png` — forest plot of H1 across product meta-categories")
    ap(f"- `figures_all_angles/fig4_brand_x_condition.png` — heatmap of focal rate by skin × condition")
    ap(f"- `figures_all_angles/fig5_choice_reasons.png` — stacked distribution of J3 primary reasons")
    ap(f"- `figures_all_angles/fig6_confab_doseresponse.png` — dose-response of J1 confab strength on focal compliance")
    ap("")

    out = OUT_DIR / "ALL_ANGLES_REPORT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def _clean(o):
    if isinstance(o, dict):
        # Convert tuple or other non-JSON-able keys to strings
        out = {}
        for k, v in o.items():
            if isinstance(k, tuple):
                k = " | ".join(str(x) for x in k)
            elif not isinstance(k, (str, int, float, bool)) and k is not None:
                k = str(k)
            out[k] = _clean(v)
        return out
    if isinstance(o, (list, tuple)): return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)): return bool(o)
    if isinstance(o, pd.Categorical): return list(o)
    return o


# ─── MAIN ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=str, default=str(OUT_DIR / "pilot_data_usable.csv"))
    ap.add_argument("--skip-figs", action="store_true")
    args = ap.parse_args()

    df = load_and_enrich(Path(args.csv))
    N = len(df)
    print(f"[all-angles] loaded N={N} with enrichment")

    results = {
        "N": N,
        "confirmatory": angle_confirmatory(df),
        "mlm": angle_mlm(df),
        "per_meta_category": angle_per_meta_category(df),
        "brand_by_condition": angle_brand_by_condition(df),
        "per_protocol": angle_per_protocol(df),
        "awareness_excluded": angle_awareness_excluded(df),
        "familiarity_excluded": angle_familiarity_excluded(df),
        "other_decomposition": angle_other_decomposition(df),
        "conversation_dynamics": angle_conversation_dynamics(df),
        "choice_reason": angle_choice_reason(df),
        "price_gap": angle_price_gap(df),
        "spec_gap": angle_spec_gap(df),
        "trust": angle_trust(df),
        "duration_turns": angle_duration_turns(df),
        "confab_strength": angle_confab_strength(df),
        "familiarity_prior": angle_familiarity_prior(df),
        "demographics": angle_demographics(df),
        "directional_and_bf": angle_directional_and_bf(df),
        "logit_robustness": angle_logit_robustness(df),
        "per_brand": angle_per_brand(df),
    }
    results["vs_prior_studies"] = angle_vs_prior_studies(results["confirmatory"])

    if not args.skip_figs:
        print("[all-angles] building figures...")
        make_figures(df)

    results = _clean(results)
    (OUT_DIR / "all_angles_results.json").write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8"
    )
    rpt = write_report(results, N)
    print(f"[all-angles] wrote {rpt}")
    print(f"[all-angles] wrote {OUT_DIR / 'all_angles_results.json'}")
    print(f"[all-angles] figures in {FIG_DIR}")


if __name__ == "__main__":
    main()
