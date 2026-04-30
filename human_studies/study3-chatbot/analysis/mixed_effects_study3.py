"""
Study 3 — Category random-effects analysis with pre-committed contingency ladder.

See PREREG_ANALYSIS_SPEC.md §3 for the full branching rules. Summary:

    A — Random intercept on raw category       (n_cat_median >= 3)
    B — GEE clustered on category              (n_cat_median in [2,3] or Branch A fails)
    C — Random intercept on meta-category      (>50% of categories are singletons)
    D — Cluster-robust fixed-effects logit     (all mixed-effect fits fail)
    E — Descriptive only                        (N < 30)

Runs for each primary DV (chose_optimal, chose_focal). Writes results to
output/mixed_effects_report.md + mixed_effects_results.json.

Usage:
    python mixed_effects_study3.py
    python mixed_effects_study3.py --csv path/to/usable.csv
"""
from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
from statsmodels.genmod.generalized_estimating_equations import GEE

warnings.filterwarnings("ignore")

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR / "output"
JUDGE_DIR = OUT_DIR / "judges"
OUT_DIR.mkdir(exist_ok=True)

# ─── CONTINGENCY LADDER ──────────────────────────────────────────────

def _structure(df: pd.DataFrame) -> dict:
    """Characterize within-category structure."""
    counts = df["study3_category"].astype(str).str.strip().value_counts()
    k = len(counts)
    n = len(df)
    n_singletons = int((counts == 1).sum())
    return {
        "N": n,
        "k_categories": k,
        "n_cat_median": float(counts.median()) if len(counts) else 0,
        "n_cat_mean": float(counts.mean()) if len(counts) else 0,
        "n_cat_max": int(counts.max()) if len(counts) else 0,
        "n_singletons": n_singletons,
        "singleton_rate": n_singletons / k if k else 0,
    }

def _pick_branch(struct: dict) -> str:
    """Decision tree from PREREG_ANALYSIS_SPEC.md §3.2."""
    if struct["N"] < 30:
        return "E"
    if struct["singleton_rate"] >= 0.5:
        return "C"
    if struct["n_cat_median"] >= 3:
        return "A"
    if struct["n_cat_median"] >= 2:
        return "B"
    # Fall-through: N>=30 and n_cat_median < 2 but fewer than 50% singletons — rare
    return "B"


# ─── FITTING HELPERS ─────────────────────────────────────────────────

def _prep(df: pd.DataFrame, dv: str, conditions: list[str] | None = None) -> pd.DataFrame:
    """Return a clean analysis frame with integer DV, condition codes, brand codes."""
    sub = df.copy()
    if conditions is not None:
        sub = sub[sub["study3_condition"].isin(conditions)].copy()
    sub = sub.dropna(subset=[dv, "study3_condition", "study3_category"]).copy()
    sub["y"] = sub[dv].astype(int)
    # Reference level depends on test: we set neutral as reference for H1/RQ1,
    # or the caller can override via column order.
    sub["condition"] = pd.Categorical(
        sub["study3_condition"],
        categories=conditions if conditions else ["neutral", "biased", "honest"],
        ordered=False,
    )
    sub["ai_brand"] = sub["study3_ai_brand"].astype(str).fillna("unknown")
    sub["category"] = sub["study3_category"].astype(str).str.strip()
    if "meta_category" not in sub.columns:
        sub["meta_category"] = sub["category"]
    return sub

def _branch_A(data: pd.DataFrame, dv_name: str) -> dict:
    """Random intercept on raw category via BinomialBayesMixedGLM (variational Bayes)."""
    out = {"branch": "A", "dv": dv_name, "model": "BinomialBayesMixedGLM(random intercept on category)"}
    try:
        formula = "y ~ C(condition) + C(ai_brand)"
        vc_formulas = {"cat": "0 + C(category)"}
        md = BinomialBayesMixedGLM.from_formula(formula, vc_formulas, data)
        res = md.fit_vb()
        out["fixed_effects"] = {}
        for i, name in enumerate(res.model.exog_names):
            coef = float(res.fe_mean[i])
            se = float(res.fe_sd[i])
            z = (coef / se) if se else None
            p = float(2 * (1 - stats.norm.cdf(abs(z)))) if z is not None else None
            out["fixed_effects"][name] = {
                "coef": coef, "se": se, "z": z, "p": p,
                "ci_low": coef - 1.96 * se, "ci_high": coef + 1.96 * se,
            }
        out["converged"] = True
    except Exception as e:
        out["converged"] = False
        out["error"] = str(e)
    return out

def _branch_B(data: pd.DataFrame, dv_name: str) -> dict:
    """GEE clustered on category, exchangeable correlation."""
    out = {"branch": "B", "dv": dv_name, "model": "GEE(cluster=category, exchangeable)"}
    try:
        fam = sm.families.Binomial()
        cov = sm.cov_struct.Exchangeable()
        md = GEE.from_formula(
            "y ~ C(condition) + C(ai_brand)",
            groups="category",
            data=data,
            family=fam,
            cov_struct=cov,
        )
        res = md.fit()
        out["fixed_effects"] = {
            name: {
                "coef": float(res.params[name]),
                "se": float(res.bse[name]),
                "z": float(res.tvalues[name]),
                "p": float(res.pvalues[name]),
                "ci_low": float(res.conf_int().loc[name][0]),
                "ci_high": float(res.conf_int().loc[name][1]),
            }
            for name in res.params.index
        }
        out["converged"] = True
    except Exception as e:
        out["converged"] = False
        out["error"] = str(e)
    return out

def _branch_C(data: pd.DataFrame, dv_name: str) -> dict:
    """Random intercept on meta_category. Requires J5 output."""
    out = {"branch": "C", "dv": dv_name, "model": "BinomialBayesMixedGLM(random intercept on meta_category)"}
    try:
        if data["meta_category"].nunique() < 3:
            out["converged"] = False
            out["error"] = "meta_category has fewer than 3 levels — J5 classification probably missing"
            return out
        formula = "y ~ C(condition) + C(ai_brand)"
        vc_formulas = {"mcat": "0 + C(meta_category)"}
        md = BinomialBayesMixedGLM.from_formula(formula, vc_formulas, data)
        res = md.fit_vb()
        out["fixed_effects"] = {}
        for i, name in enumerate(res.model.exog_names):
            coef = float(res.fe_mean[i])
            se = float(res.fe_sd[i])
            z = (coef / se) if se else None
            p = float(2 * (1 - stats.norm.cdf(abs(z)))) if z is not None else None
            out["fixed_effects"][name] = {
                "coef": coef, "se": se, "z": z, "p": p,
                "ci_low": coef - 1.96 * se, "ci_high": coef + 1.96 * se,
            }
        out["converged"] = True
    except Exception as e:
        out["converged"] = False
        out["error"] = str(e)
    return out

def _branch_D(data: pd.DataFrame, dv_name: str) -> dict:
    """Fixed-effects logit with cluster-robust standard errors on category."""
    out = {"branch": "D", "dv": dv_name, "model": "Logit with cluster-robust SE (cluster=category)"}
    try:
        md = smf.logit("y ~ C(condition) + C(ai_brand)", data=data)
        res = md.fit(disp=False, cov_type="cluster", cov_kwds={"groups": data["category"]})
        out["fixed_effects"] = {
            name: {
                "coef": float(res.params[name]),
                "se": float(res.bse[name]),
                "z": float(res.tvalues[name]),
                "p": float(res.pvalues[name]),
                "ci_low": float(res.conf_int().loc[name][0]),
                "ci_high": float(res.conf_int().loc[name][1]),
            }
            for name in res.params.index
        }
        out["converged"] = True
    except Exception as e:
        out["converged"] = False
        out["error"] = str(e)
    return out

def _branch_E(data: pd.DataFrame, dv_name: str) -> dict:
    """Descriptive only — Wilson 95% CI per condition."""
    out = {"branch": "E", "dv": dv_name, "model": "Descriptive (Wilson 95% CIs per condition)"}
    cell = {}
    for cond, sub in data.groupby("study3_condition"):
        n = len(sub)
        k = int(sub["y"].sum())
        if n == 0: continue
        # Wilson CI
        z = 1.96
        phat = k / n
        denom = 1 + z**2 / n
        center = (phat + z**2 / (2 * n)) / denom
        width = z * np.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2)) / denom
        cell[cond] = {"n": n, "k": k, "rate": phat, "ci_low": max(0, center - width), "ci_high": min(1, center + width)}
    out["cells"] = cell
    out["converged"] = True
    return out

BRANCHES = {"A": _branch_A, "B": _branch_B, "C": _branch_C, "D": _branch_D, "E": _branch_E}


# ─── PAIRWISE SIMPLE TESTS (always run, regardless of branch) ────────

def _wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    phat = k / n
    denom = 1 + z**2 / n
    center = (phat + z**2 / (2 * n)) / denom
    width = z * np.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, center - width), min(1.0, center + width))

def _pair_test(df: pd.DataFrame, dv: str, cond_a: str, cond_b: str) -> dict:
    """Fisher's exact + risk difference + odds ratio (all with CIs)."""
    sub = df[df["study3_condition"].isin([cond_a, cond_b])].dropna(subset=[dv])
    if len(sub) < 4:
        return {"skipped": "insufficient data", "n_a": 0, "n_b": 0}
    a = sub[sub["study3_condition"] == cond_a]
    b = sub[sub["study3_condition"] == cond_b]
    n_a, k_a = len(a), int(a[dv].sum())
    n_b, k_b = len(b), int(b[dv].sum())
    if n_a == 0 or n_b == 0:
        return {"skipped": "empty cell", "n_a": n_a, "n_b": n_b}
    # 2x2 table: rows = [cond_a, cond_b], cols = [yes, no]
    tab = np.array([[k_a, n_a - k_a], [k_b, n_b - k_b]])
    odds, p_fish = stats.fisher_exact(tab, alternative="two-sided")
    p_a = k_a / n_a
    p_b = k_b / n_b
    rd = p_a - p_b
    # Wald CI for RD
    se_rd = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    rd_ci_low = rd - 1.96 * se_rd
    rd_ci_high = rd + 1.96 * se_rd
    # Exact CI for OR via hypergeometric approximation
    try:
        # scipy's fisher_exact doesn't give CI directly. Use a Haldane-Anscombe correction.
        a_ = k_a + 0.5
        b_ = (n_a - k_a) + 0.5
        c_ = k_b + 0.5
        d_ = (n_b - k_b) + 0.5
        or_ = (a_ * d_) / (b_ * c_)
        se_log_or = np.sqrt(1/a_ + 1/b_ + 1/c_ + 1/d_)
        log_or = np.log(or_)
        or_ci_low = float(np.exp(log_or - 1.96 * se_log_or))
        or_ci_high = float(np.exp(log_or + 1.96 * se_log_or))
    except Exception:
        or_ = None
        or_ci_low = or_ci_high = None
    ci_a = _wilson_ci(k_a, n_a)
    ci_b = _wilson_ci(k_b, n_b)
    return {
        "n_a": n_a, "k_a": k_a, "rate_a": p_a, "rate_a_ci": ci_a,
        "n_b": n_b, "k_b": k_b, "rate_b": p_b, "rate_b_ci": ci_b,
        "risk_diff": float(rd),
        "risk_diff_ci": [float(rd_ci_low), float(rd_ci_high)],
        "odds_ratio": float(or_),
        "odds_ratio_ci": [or_ci_low, or_ci_high],
        "p_fisher_2sided": float(p_fish),
    }


# ─── OMNIBUS 3x3 (condition × bucket) ────────────────────────────────

def _omnibus_3x3(df: pd.DataFrame) -> dict:
    """3-condition × 3-bucket chi-squared. Uses Monte Carlo p-value if expected < 5."""
    sub = df.dropna(subset=["bucket"]).copy()
    tab = pd.crosstab(sub["study3_condition"], sub["bucket"])
    # Reindex both axes
    tab = tab.reindex(
        index=["biased", "honest", "neutral"],
        columns=["optimal", "focal", "other"],
        fill_value=0,
    )
    vals = tab.values
    out = {"table": tab.to_dict(), "N": int(vals.sum())}
    if vals.sum() < 4:
        out["skipped"] = "insufficient data"
        return out
    chi2, p, dof, expected = stats.chi2_contingency(vals)
    out["chi2"] = float(chi2)
    out["dof"] = int(dof)
    out["p_asymptotic"] = float(p)
    out["expected_min"] = float(expected.min())
    # Monte Carlo p-value for small-expected tables
    if expected.min() < 5:
        rng = np.random.default_rng(42)
        row_totals = vals.sum(axis=1)
        col_totals = vals.sum(axis=0)
        grand = vals.sum()
        count_as_extreme = 0
        n_sim = 10_000
        for _ in range(n_sim):
            # Generate a random contingency table with same marginals (Patefield-style
            # approximation via multinomial on row distribution)
            sim = np.zeros_like(vals)
            for i in range(len(row_totals)):
                sim[i] = rng.multinomial(row_totals[i], col_totals / grand)
            sim_chi2 = stats.chi2_contingency(sim)[0] if sim.sum() > 0 else 0
            if sim_chi2 >= chi2:
                count_as_extreme += 1
        out["p_monte_carlo"] = (count_as_extreme + 1) / (n_sim + 1)
        out["p"] = out["p_monte_carlo"]
    else:
        out["p"] = out["p_asymptotic"]
    # Cramér's V
    k = min(vals.shape) - 1
    out["cramers_v"] = float(np.sqrt(chi2 / (vals.sum() * k))) if k > 0 else None
    return out


# ─── MAIN API ─────────────────────────────────────────────────────────

def run_full_mlm(df: pd.DataFrame) -> dict:
    """Run the full contingency ladder + all confirmatory tests. Returns results dict."""
    # Merge meta-category from J5 if available
    j5_path = JUDGE_DIR / "J5_meta_category.csv"
    if j5_path.exists():
        j5 = pd.read_csv(j5_path)
        mapping = dict(zip(j5["category"].astype(str).str.strip(), j5["j5_meta_category"]))
        df = df.copy()
        df["meta_category"] = df["study3_category"].astype(str).str.strip().map(mapping).fillna("other")

    struct = _structure(df)
    branch = _pick_branch(struct)

    # 3-bucket derivation
    df_bucket = df.dropna(subset=["study3_condition"]).copy()
    df_bucket["bucket"] = df_bucket.apply(
        lambda r: (
            "optimal" if r.get("chose_optimal_bool") is True
            else "focal" if r.get("chose_focal_bool") is True
            else "other" if r.get("study3_product_choice") and str(r.get("study3_product_choice")).strip()
            else None
        ),
        axis=1,
    )

    results: dict = {
        "structure": struct,
        "branch_selected": branch,
        "confirmatory": {},
        "mlm": {},
        "omnibus_3x3": _omnibus_3x3(df_bucket),
        "sensitivity": {},
    }

    # Confirmatory pairwise tests (always run — robust to cell size via Fisher)
    # H1: Biased vs Neutral on chose_focal
    results["confirmatory"]["H1_biased_vs_neutral_focal"] = _pair_test(
        df, "chose_focal_bool", "biased", "neutral"
    )
    # RQ1: Honest vs Neutral on chose_optimal
    results["confirmatory"]["RQ1_honest_vs_neutral_optimal"] = _pair_test(
        df, "chose_optimal_bool", "honest", "neutral"
    )
    # Secondary
    results["confirmatory"]["biased_vs_honest_focal"] = _pair_test(
        df, "chose_focal_bool", "biased", "honest"
    )
    results["confirmatory"]["biased_vs_neutral_optimal"] = _pair_test(
        df, "chose_optimal_bool", "biased", "neutral"
    )
    results["confirmatory"]["biased_vs_honest_optimal"] = _pair_test(
        df, "chose_optimal_bool", "biased", "honest"
    )
    results["confirmatory"]["honest_vs_neutral_focal"] = _pair_test(
        df, "chose_focal_bool", "honest", "neutral"
    )

    # MLM ladder — run selected branch for both DVs, plus fallback chain
    runner = BRANCHES[branch]
    for dv in ("chose_optimal_bool", "chose_focal_bool"):
        data = _prep(df, dv, conditions=["neutral", "biased", "honest"])
        results["mlm"][dv] = runner(data, dv)
        # Cascade fallback if primary branch fails
        if not results["mlm"][dv].get("converged"):
            cascade = ["A", "B", "C", "D", "E"]
            idx = cascade.index(branch)
            for fb in cascade[idx + 1:]:
                r = BRANCHES[fb](data, dv)
                if r.get("converged"):
                    r["fallback_from"] = branch
                    results["mlm"][dv] = r
                    break

    # Sensitivity: exclude J4-flagged aware participants if available
    j4_path = JUDGE_DIR / "J4_suspicion.csv"
    if j4_path.exists():
        j4 = pd.read_csv(j4_path)
        aware_sessions = set(j4[
            j4["j4_aware_of_bias"].fillna(False).astype(bool) |
            j4["j4_aware_of_manipulation"].fillna(False).astype(bool)
        ]["session_id"].astype(str))
        if aware_sessions:
            df_excl = df[~df["study3_session_id"].astype(str).isin(aware_sessions)].copy()
            results["sensitivity"]["awareness_excluded"] = {
                "n_removed": len(df) - len(df_excl),
                "H1": _pair_test(df_excl, "chose_focal_bool", "biased", "neutral"),
                "RQ1": _pair_test(df_excl, "chose_optimal_bool", "honest", "neutral"),
            }

    return results


def write_report(results: dict, out_path: Path | None = None) -> Path:
    if out_path is None:
        out_path = OUT_DIR / "mixed_effects_report.md"
    lines = []
    ap = lines.append
    ap("# Study 3 — Mixed-Effects Analysis Report")
    ap("")
    s = results["structure"]
    ap("## Within-category structure")
    ap(f"- N analyzed: **{s['N']}**")
    ap(f"- Unique categories: **{s['k_categories']}**")
    ap(f"- Median / mean / max participants per category: {s['n_cat_median']} / {s['n_cat_mean']:.2f} / {s['n_cat_max']}")
    ap(f"- Singletons (n=1 categories): {s['n_singletons']} ({s['singleton_rate']:.1%})")
    ap(f"- **Branch selected: {results['branch_selected']}** (per PREREG_ANALYSIS_SPEC.md §3.2)")
    ap("")

    ap("## Confirmatory pairwise tests (Fisher's exact, risk difference, OR with 95% CI)")
    for name, r in results["confirmatory"].items():
        if "skipped" in r:
            ap(f"- **{name}**: SKIPPED ({r['skipped']})")
            continue
        rd = r["risk_diff"]
        rd_ci = r["risk_diff_ci"]
        or_ = r["odds_ratio"]
        or_ci = r["odds_ratio_ci"]
        ap(
            f"- **{name}**: {r['rate_a']:.1%} (n={r['n_a']}) vs {r['rate_b']:.1%} (n={r['n_b']}), "
            f"RD = {rd:+.1%} [95% CI {rd_ci[0]:+.1%}, {rd_ci[1]:+.1%}], "
            f"OR = {or_:.2f} [{or_ci[0]:.2f}, {or_ci[1]:.2f}], "
            f"p = {r['p_fisher_2sided']:.4f}"
        )
    ap("")

    omn = results["omnibus_3x3"]
    ap("## Omnibus 3x3 (condition × bucket)")
    if "skipped" in omn:
        ap(f"- SKIPPED ({omn['skipped']})")
    else:
        ap(f"- χ² = {omn['chi2']:.2f}, df = {omn['dof']}, p = {omn['p']:.4f} "
           f"({'Monte Carlo ' if 'p_monte_carlo' in omn else ''}min expected = {omn['expected_min']:.2f})")
        if omn.get("cramers_v") is not None:
            ap(f"- Cramér's V = {omn['cramers_v']:.3f}")
        ap("")
        ap("Cell counts:")
        ap("```")
        ap(json.dumps(omn["table"], indent=2, default=str))
        ap("```")
    ap("")

    ap("## MLM results")
    for dv, m in results["mlm"].items():
        ap(f"### {dv}")
        ap(f"- Branch: **{m['branch']}**{' (fallback from ' + m.get('fallback_from','') + ')' if m.get('fallback_from') else ''}")
        ap(f"- Model: `{m['model']}`")
        ap(f"- Converged: **{m.get('converged')}**")
        if m.get("error"):
            ap(f"- Error: `{m['error']}`")
        if m.get("fixed_effects"):
            ap("| Term | Coef | SE | z | p | CI 95% |")
            ap("|---|---:|---:|---:|---:|:---|")
            for name, fe in m["fixed_effects"].items():
                coef = fe.get("coef")
                se = fe.get("se")
                z = fe.get("z")
                p = fe.get("p")
                cl, ch = fe.get("ci_low"), fe.get("ci_high")
                ci_s = f"[{cl:+.3f}, {ch:+.3f}]" if cl is not None and ch is not None else ""
                ap(f"| `{name}` | {coef:+.3f} | {se:.3f} | {z if z is None else f'{z:+.2f}'} | "
                   f"{p if p is None else f'{p:.4f}'} | {ci_s} |")
        if m.get("cells"):
            ap("| Condition | N | k (yes) | Rate | Wilson 95% CI |")
            ap("|---|---:|---:|---:|:---|")
            for cond, c in m["cells"].items():
                ap(f"| {cond} | {c['n']} | {c['k']} | {c['rate']:.1%} | [{c['ci_low']:.1%}, {c['ci_high']:.1%}] |")
        ap("")

    if results.get("sensitivity"):
        ap("## Sensitivity — awareness-excluded sample")
        for name, r in results["sensitivity"].items():
            ap(f"### {name} (n removed = {r.get('n_removed', 0)})")
            for test_name, t in r.items():
                if test_name == "n_removed": continue
                if isinstance(t, dict) and "rate_a" in t:
                    ap(f"- {test_name}: RD = {t['risk_diff']:+.1%}, OR = {t['odds_ratio']:.2f}, p = {t['p_fisher_2sided']:.4f}")
        ap("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def _clean(o):
    if isinstance(o, dict): return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)): return bool(o)
    if isinstance(o, pd.Categorical): return list(o)
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=str, default=str(OUT_DIR / "pilot_data_usable.csv"))
    args = ap.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"[mlm] data not found: {csv_path} — run analyze_study3_pilot.py --fetch first")
        return
    df = pd.read_csv(csv_path)
    print(f"[mlm] loaded {len(df)} usable rows")

    # Ensure chose_focal_bool exists (computed from recommended_index match)
    if "chose_focal_bool" not in df.columns:
        print("[mlm] chose_focal_bool missing — you must re-run analyze_study3_pilot.py first")
        return

    results = run_full_mlm(df)
    report = write_report(results)
    (OUT_DIR / "mixed_effects_results.json").write_text(
        json.dumps(_clean(results), indent=2, default=str), encoding="utf-8"
    )
    print(f"[mlm] wrote {report}")
    print(f"[mlm] wrote {OUT_DIR / 'mixed_effects_results.json'}")


if __name__ == "__main__":
    main()
