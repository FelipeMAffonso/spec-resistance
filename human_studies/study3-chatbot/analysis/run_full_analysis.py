"""
Study 3 — End-to-end analysis orchestrator.

Runs the full pipeline:
    1. Fetch Qualtrics responses (or use a local CSV)
    2. Parse + quality checks + 3-bucket derivation + legacy report
    3. LLM-judge pass (Sonnet 4.6, cached) — J1 through J5
    4. Mixed-effects analysis with contingency ladder (picks branch per data)
    5. Write consolidated report at output/STUDY3_FINAL_REPORT.md

Usage:
    python run_full_analysis.py --fetch                   # fetch + full pipeline
    python run_full_analysis.py --csv path/to/file.csv    # use existing CSV
    python run_full_analysis.py --skip-judge              # skip Sonnet pass
    python run_full_analysis.py --judge-limit 10          # cap N per judge
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR / "output"
JUDGE_DIR = OUT_DIR / "judges"

def _run(cmd: list[str]) -> None:
    print(f"\n[orchestrator] $ {' '.join(cmd)}")
    t = time.time()
    r = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=False)
    dt = time.time() - t
    print(f"[orchestrator] finished in {dt:.1f}s (exit {r.returncode})")
    if r.returncode != 0:
        print(f"[orchestrator] WARNING — step exited non-zero; continuing")


def _load_if_exists(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def consolidate_report() -> Path:
    """Write STUDY3_FINAL_REPORT.md pulling from every substep's output."""
    quality_json = _load_if_exists(OUT_DIR / "all_results.json") or {}
    mlm_json = _load_if_exists(OUT_DIR / "mixed_effects_results.json") or {}
    judge_json = _load_if_exists(JUDGE_DIR / "judge_summary.json") or {}

    lines = []
    ap = lines.append
    ap("# Study 3 — Final Analysis Report")
    ap("")
    ap("*Consolidated from: `pilot_report.md` + `mixed_effects_report.md` + `judges/judge_summary.json`*")
    ap("")

    # QUALITY
    q = quality_json.get("quality", {})
    ap("## Quality dashboard")
    ap(f"- N responses: **{q.get('n_responses', 0)}**")
    ap(f"- N usable: **{q.get('n_usable', 0)}** ({q.get('usable_rate', 0):.0%})")
    ap(f"- Condition counts: {q.get('condition_counts', {})}")
    ap(f"- AI brand counts: {q.get('brand_counts', {})}")
    ap(f"- Unique categories: {q.get('n_unique_categories', 0)}")
    ap(f"- JSON parse errors: {q.get('n_json_errors', 0)} ({q.get('json_error_rate', 0):.1%})")
    ap(f"- Median duration: {(q.get('duration_median_s') or 0)/60:.1f} min")
    ap("")

    # CONFIRMATORY (from prereg primary)
    pp = quality_json.get("primary_prereg", {})
    if pp:
        ap("## Confirmatory tests (Fisher's exact, per AsPredicted)")
        for block, label in [("confirmatory", "### Pre-registered"), ("secondary", "### Secondary")]:
            ap(label)
            for name, r in pp.get(block, {}).items():
                if "skipped" in r:
                    ap(f"- **{name}**: SKIPPED ({r['skipped']})")
                    continue
                rd = r["risk_diff"]; rd_ci = r["risk_diff_ci"]
                or_ = r["odds_ratio"]; or_ci = r["odds_ratio_ci"]
                ap(
                    f"- **{name}**: {r['rate_a']:.1%} (n={r['n_a']}) vs {r['rate_b']:.1%} (n={r['n_b']}), "
                    f"RD = {rd:+.1%} [{rd_ci[0]:+.1%}, {rd_ci[1]:+.1%}], "
                    f"OR = {or_:.2f} [{or_ci[0]:.2f}, {or_ci[1]:.2f}], "
                    f"p = {r['p_fisher_2sided']:.4f}"
                )
            ap("")
        # 3-bucket counts
        if pp.get("three_bucket_counts"):
            ap("### Three-bucket counts")
            ap("```")
            ap(json.dumps(pp["three_bucket_counts"], indent=2, default=str))
            ap("```")
            ap("")

    # MLM
    if mlm_json:
        s = mlm_json.get("structure", {})
        ap("## Mixed-effects — contingency branch")
        ap(f"- Branch selected: **{mlm_json.get('branch_selected')}**")
        ap(f"- n_cat_median = {s.get('n_cat_median')}, singletons = {s.get('n_singletons')} / {s.get('k_categories')} ({s.get('singleton_rate', 0):.0%})")
        ap("")
        for dv, m in mlm_json.get("mlm", {}).items():
            ap(f"### {dv} ({m.get('model', '')})")
            if m.get("fallback_from"):
                ap(f"- Fallback from branch {m['fallback_from']} to {m.get('branch')}")
            ap(f"- Converged: {m.get('converged')}")
            if m.get("fixed_effects"):
                ap("| Term | Coef | SE | z | p | 95% CI |")
                ap("|---|---:|---:|---:|---:|:---|")
                for name, fe in m["fixed_effects"].items():
                    coef = fe.get("coef")
                    se = fe.get("se")
                    z = fe.get("z")
                    p = fe.get("p")
                    cl, ch = fe.get("ci_low"), fe.get("ci_high")
                    ci_s = f"[{cl:+.3f}, {ch:+.3f}]" if (cl is not None and ch is not None) else ""
                    p_s = f"{p:.4f}" if p is not None else "—"
                    z_s = f"{z:+.2f}" if z is not None else "—"
                    ap(f"| `{name}` | {coef:+.3f} | {se:.3f} | {z_s} | {p_s} | {ci_s} |")
            ap("")
        om = mlm_json.get("omnibus_3x3", {})
        if om and "chi2" in om:
            ap("### Omnibus 3×3")
            ap(f"- χ²({om.get('dof')}) = {om.get('chi2'):.2f}, p = {om.get('p'):.4f}, Cramér's V = {om.get('cramers_v'):.3f}")
            ap("")

    # JUDGES
    if judge_json:
        ap("## LLM-as-judge summary (Claude Sonnet 4.6)")
        for key, label in [
            ("J1", "J1 — Confabulation of biased recommendation"),
            ("J2", "J2 — Pushback handling"),
            ("J3", "J3 — Choice-reason classification"),
            ("J4", "J4 — Suspicion awareness"),
            ("J5", "J5 — Meta-category classification"),
        ]:
            s = judge_json.get(key, {})
            if s.get("n"):
                ap(f"### {label} (n={s['n']})")
                for k, v in s.items():
                    if k == "n": continue
                    ap(f"- `{k}`: `{v}`")
                ap("")

    # Sensitivity
    sens = mlm_json.get("sensitivity", {})
    if sens:
        ap("## Robustness / sensitivity")
        for name, r in sens.items():
            ap(f"### {name} (n_removed = {r.get('n_removed', 0)})")
            for tname, t in r.items():
                if tname == "n_removed": continue
                if isinstance(t, dict) and "rate_a" in t and "skipped" not in t:
                    ap(
                        f"- {tname}: RD = {t['risk_diff']:+.1%}, OR = {t['odds_ratio']:.2f}, "
                        f"p = {t['p_fisher_2sided']:.4f}"
                    )
                elif isinstance(t, dict) and "skipped" in t:
                    ap(f"- {tname}: SKIPPED ({t['skipped']})")
            ap("")

    out = OUT_DIR / "STUDY3_FINAL_REPORT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--csv", type=str, default=None)
    ap.add_argument("--skip-judge", action="store_true")
    ap.add_argument("--judge-limit", type=int, default=None)
    ap.add_argument("--judges", nargs="*", default=["J1", "J2", "J3", "J4", "J5"])
    args = ap.parse_args()

    py = sys.executable

    # 1 + 2: fetch + parse + primary
    pilot_cmd = [py, str(SCRIPT_DIR / "analyze_study3_pilot.py")]
    if args.fetch:
        pilot_cmd.append("--fetch")
    elif args.csv:
        pilot_cmd += ["--csv", args.csv]
    else:
        # Try to re-use the most recent parsed CSV; if missing, ask for --fetch
        if not (OUT_DIR / "pilot_data_parsed.csv").exists():
            print("[orchestrator] no pilot_data_parsed.csv yet — running with --fetch")
            pilot_cmd.append("--fetch")
    _run(pilot_cmd)

    # 3: judges
    if not args.skip_judge:
        judge_cmd = [py, str(SCRIPT_DIR / "judge_study3_sonnet.py"), "--judges"] + args.judges
        if args.judge_limit:
            judge_cmd += ["--limit", str(args.judge_limit)]
        _run(judge_cmd)

    # 4: mixed-effects
    mlm_cmd = [py, str(SCRIPT_DIR / "mixed_effects_study3.py")]
    _run(mlm_cmd)

    # 5: consolidated report
    final = consolidate_report()
    print(f"\n[orchestrator] FINAL REPORT: {final}")


if __name__ == "__main__":
    main()
