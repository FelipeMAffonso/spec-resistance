"""
Top-level reproduction driver for the Spec Resistance paper.

This script is self-contained inside the OSF release bundle. All paths are
resolved relative to this file (HERE), so the bundle can be downloaded and
run from any location without depending on a parent directory.

Usage examples
--------------

    python reproduce.py --verify          # SHA-256 check committed processed data
    python reproduce.py --analyses        # Recompute every manuscript number from committed CSV
    python reproduce.py --figures         # Regenerate every figure from committed CSV
    python reproduce.py --human-studies   # Rerun Studies 1A/1B/2/3 analyses from anonymised CSVs
    python reproduce.py --audit           # Full audit: hashes + scripts + numbers + figures + citations
    python reproduce.py --full            # Everything sequential (no API calls)

    python reproduce.py --experiment injection
    python reproduce.py --experiment debiasing
    python reproduce.py --experiment probing
    python reproduce.py --experiment steering
    python reproduce.py --experiment temperature
    python reproduce.py --experiment scaling
    python reproduce.py --experiment base_vs_instruct
    python reproduce.py --experiment cross_judge

No experiment subcommand makes external API calls by default. The experiment
subcommands run end-to-end reproduction pipelines that DO make API calls; these
are guarded behind the explicit `--experiment <name>` flag and print cost
estimates before proceeding.

Every step logs inputs, outputs, and SHA-256 of committed artefacts to
`logs/reproduce_<timestamp>.log`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG_DIR = HERE / "logs"
LOG_DIR.mkdir(exist_ok=True)
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOG_DIR / f"reproduce_{TIMESTAMP}.log"

# ─── LOGGING ──────────────────────────────────────────────────────────

def log(msg: str, also_print: bool = True) -> None:
    LOG_FILE.open("a", encoding="utf-8").write(f"[{datetime.now().isoformat()}] {msg}\n")
    if also_print:
        print(msg)

# ─── PATHS (all OSF-internal) ─────────────────────────────────────────

CLEAN_CSV     = HERE / "data" / "spec_resistance_CLEAN.csv"
CLEAN_CSV_GZ  = HERE / "data" / "spec_resistance_CLEAN.csv.gz"
EXTENDED_CSV  = HERE / "data" / "spec_resistance_EXTENDED.csv"
HASHES_JSON   = HERE / "data" / "hashes.json"
NUMBERS_JSON  = HERE / "analysis" / "output" / "manuscript_numbers.json"
MAIN_MD       = HERE / "paper" / "main.md"
SUPP_MD       = HERE / "paper" / "supplementary.md"
BIB           = HERE / "paper" / "references.bib"
RESULTS_DIR   = HERE / "results"
HUMAN_STUDIES = HERE / "human_studies"
STUDY3_OUT    = HUMAN_STUDIES / "study3-chatbot" / "analysis" / "output"

# ─── SHA-256 VERIFICATION ─────────────────────────────────────────────

def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b: break
            h.update(b)
    return h.hexdigest()


def verify() -> int:
    """Verify every processed file against its recorded SHA-256."""
    if not HASHES_JSON.exists():
        log(f"[verify] no hashes.json at {HASHES_JSON}; computing fresh (nothing to compare against)")
        return 0
    expected = json.loads(HASHES_JSON.read_text())
    bad = 0
    for rel, exp_hash in expected.items():
        target = HERE / rel
        if not target.exists():
            log(f"  MISSING: {rel}")
            bad += 1
            continue
        h = sha256(target)
        if h == exp_hash:
            log(f"  OK: {rel}")
        else:
            log(f"  MISMATCH: {rel}")
            log(f"    expected: {exp_hash}")
            log(f"    observed: {h}")
            bad += 1
    log(f"[verify] {'all files match' if bad == 0 else f'{bad} mismatch(es)'}")
    return 1 if bad > 0 else 0


def record_hashes() -> None:
    """Record SHA-256 of every processed artefact into hashes.json."""
    targets = [
        CLEAN_CSV,
        EXTENDED_CSV,
        NUMBERS_JSON,
        RESULTS_DIR / "08-fictional-injection" / "full_scale_injection.csv",
        RESULTS_DIR / "06-openai-finetune" / "full_scale_debiasing.csv",
        RESULTS_DIR / "06-openai-finetune" / "eval_6k_4omini.csv",
        RESULTS_DIR / "06-openai-finetune" / "eval_6k_41nano.csv",
        RESULTS_DIR / "06-openai-finetune" / "eval_6k_41mini.csv",
        RESULTS_DIR / "02-base-vs-instruct" / "all_base_vs_instruct.json",
        HERE / "data" / "brand_frequencies.csv",
        STUDY3_OUT / "pilot_data_usable.csv",
        STUDY3_OUT / "ALL_ANGLES_REPORT.md",
        STUDY3_OUT / "STUDY3_FINAL_REPORT.md",
    ]
    out: dict[str, str] = {}
    for t in targets:
        if t.exists():
            rel = t.relative_to(HERE).as_posix()
            out[rel] = sha256(t)
            log(f"  recorded {rel} sha256={out[rel][:12]}...")
        else:
            log(f"  skipped (missing): {t.relative_to(HERE)}")
    HASHES_JSON.parent.mkdir(parents=True, exist_ok=True)
    HASHES_JSON.write_text(json.dumps(out, indent=2))
    log(f"[hashes] wrote {HASHES_JSON} with {len(out)} entries")

# ─── ANALYSES ─────────────────────────────────────────────────────────

def run_analyses() -> int:
    scripts = [
        HERE / "analysis" / "compute_all_stats.py",
        HERE / "analysis" / "supplementary_stats.py",
        HERE / "analysis" / "_recompute_stale_numbers.py",
        HERE / "analysis" / "_extract_key_deltas.py",
    ]
    for s in scripts:
        if s.exists():
            log(f"[analyses] running {s.relative_to(HERE)}")
            r = subprocess.run([sys.executable, str(s)], cwd=HERE)
            if r.returncode != 0:
                log(f"  FAILED with exit {r.returncode}")
                return r.returncode
        else:
            log(f"[analyses] missing {s.relative_to(HERE)}, skipping")
    return 0

# ─── FIGURES ──────────────────────────────────────────────────────────

def run_figures() -> int:
    fig_scripts = [
        HERE / "analysis" / "generate_figures_nature.py",
        HERE / "analysis" / "generate_supplementary_figures.py",
        HERE / "paper" / "generate_revision_composites.py",
        HERE / "paper" / "create_schematic.py",
        HERE / "paper" / "create_ed9_confabulation_examples.py",
    ]
    failures = 0
    for s in fig_scripts:
        if s.exists():
            log(f"[figures] running {s.relative_to(HERE)}")
            r = subprocess.run([sys.executable, str(s)], cwd=HERE)
            if r.returncode != 0:
                log(f"  FAILED with exit {r.returncode}")
                failures += 1
        else:
            log(f"[figures] missing {s.relative_to(HERE)}, skipping")
    return 1 if failures else 0

# ─── HUMAN STUDIES ────────────────────────────────────────────────────

def run_human_studies() -> int:
    scripts = [
        HUMAN_STUDIES / "welfare_analysis_human_studies.py",
        HUMAN_STUDIES / "study3-chatbot" / "analysis" / "analyze_all_angles.py",
        HUMAN_STUDIES / "study3-chatbot" / "analysis" / "mixed_effects_study3.py",
    ]
    failures = 0
    for s in scripts:
        if s.exists():
            log(f"[human-studies] running {s.relative_to(HERE)}")
            r = subprocess.run([sys.executable, str(s)], cwd=s.parent)
            if r.returncode != 0:
                log(f"  FAILED with exit {r.returncode}")
                failures += 1
        else:
            log(f"[human-studies] missing {s.relative_to(HERE)}, skipping")
    return 1 if failures else 0

# ─── AUDIT ────────────────────────────────────────────────────────────

def audit() -> int:
    """Full audit: hashes + figure resolution + citation resolution."""
    failures = 0

    log("[audit] 1/4 verifying processed-data hashes...")
    if verify() != 0:
        failures += 1

    log("[audit] 2/4 checking every figure reference in main.md resolves...")
    if MAIN_MD.exists():
        text = MAIN_MD.read_text(encoding="utf-8")
        import re
        fig_paths = re.findall(r"\]\(([^)]+\.(?:pdf|png|svg))\)", text)
        for fp in fig_paths:
            target = (HERE / "paper" / fp).resolve()
            if not target.exists():
                log(f"  MISSING FIGURE: {fp}  (at {target})")
                failures += 1
            else:
                log(f"  OK: {fp}")

    log("[audit] 3/4 checking every citation key in main.md resolves...")
    if MAIN_MD.exists() and BIB.exists():
        import re
        txt = MAIN_MD.read_text(encoding="utf-8")
        keys = set(re.findall(r"@([A-Za-z][A-Za-z0-9_]+)", txt))
        bib_txt = BIB.read_text(encoding="utf-8", errors="ignore")
        bib_keys = set(re.findall(r"^@\w+\{([^,]+),", bib_txt, flags=re.MULTILINE))
        missing = keys - bib_keys
        missing = {k for k in missing if not k.isdigit() and len(k) > 2}
        if missing:
            for k in sorted(missing):
                log(f"  MISSING CITATION: @{k}")
            failures += 1
        else:
            log(f"  all {len(keys)} citation keys resolve")

    log("[audit] 4/4 checking Study 3 outputs exist...")
    expected = [
        STUDY3_OUT / "STUDY3_FINAL_REPORT.md",
        STUDY3_OUT / "ALL_ANGLES_REPORT.md",
        STUDY3_OUT / "mixed_effects_report.md",
        STUDY3_OUT / "judges" / "judge_summary.json",
    ]
    for t in expected:
        if t.exists():
            log(f"  OK: {t.relative_to(HERE)}")
        else:
            log(f"  MISSING: {t.relative_to(HERE)}")
            failures += 1

    log(f"[audit] complete. failures={failures}")
    return 1 if failures else 0

# ─── EXPERIMENT ENTRY POINTS (require API keys, cost money) ──────────

EXPERIMENT_SCRIPTS = {
    "injection":       HERE / "scripts" / "eval_full_scale_injection.py",
    "debiasing":       HERE / "scripts" / "eval_full_scale_debiasing.py",
    "probing":         HERE / "scripts" / "modal_probing_v3.py",
    "steering":        HERE / "scripts" / "modal_steering_v2.py",
    "temperature":     HERE / "scripts" / "temperature_sweep.py",
    "scaling":         HERE / "scripts" / "09_scaling_law.py",
    "base_vs_instruct": HERE / "scripts" / "base_vs_instruct_experiment.py",
    "cross_judge":     HERE / "scripts" / "cross_judge_validation.py",
}

EXPERIMENT_COST_USD = {
    "injection": 150, "debiasing": 180, "probing": 30, "steering": 15,
    "temperature": 15, "scaling": 0, "base_vs_instruct": 20, "cross_judge": 10,
}


def run_experiment(name: str) -> int:
    if name not in EXPERIMENT_SCRIPTS:
        log(f"[experiment] unknown experiment '{name}'")
        log(f"  choose from: {', '.join(sorted(EXPERIMENT_SCRIPTS))}")
        return 2
    script = EXPERIMENT_SCRIPTS[name]
    if not script.exists():
        log(f"[experiment] script not found: {script.relative_to(HERE)}")
        return 3
    cost = EXPERIMENT_COST_USD[name]
    log(f"[experiment] {name}")
    log(f"  script : {script.relative_to(HERE)}")
    log(f"  est cost: USD {cost}")
    log(f"  this WILL make external API calls")
    ans = input("  proceed? [y/N] ").strip().lower()
    if ans != "y":
        log("  cancelled.")
        return 4
    r = subprocess.run([sys.executable, str(script)], cwd=HERE)
    return r.returncode

# ─── MAIN ─────────────────────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser(description="Spec Resistance reproducibility driver.")
    p.add_argument("--verify", action="store_true", help="SHA-256 check committed data")
    p.add_argument("--record-hashes", action="store_true", help="Record SHA-256 of committed processed files")
    p.add_argument("--analyses", action="store_true", help="Recompute all manuscript numbers (no API calls)")
    p.add_argument("--figures", action="store_true", help="Regenerate all figures (no API calls)")
    p.add_argument("--human-studies", action="store_true", help="Rerun Studies 1A-3 analyses (no API calls)")
    p.add_argument("--audit", action="store_true", help="Full audit: hashes + figures + citations + outputs")
    p.add_argument("--full", action="store_true", help="verify + analyses + figures + human-studies + audit")
    p.add_argument("--experiment", type=str, default=None,
                   help=f"run a single experiment end-to-end (calls APIs): {', '.join(sorted(EXPERIMENT_SCRIPTS))}")
    args = p.parse_args()

    log(f"[reproduce] log at {LOG_FILE}")
    rc = 0

    if args.record_hashes:
        record_hashes()

    if args.verify or args.full:
        rc |= verify()
    if args.analyses or args.full:
        rc |= run_analyses()
    if args.figures or args.full:
        rc |= run_figures()
    if args.human_studies or args.full:
        rc |= run_human_studies()
    if args.audit or args.full:
        rc |= audit()
    if args.experiment:
        rc |= run_experiment(args.experiment)

    if rc == 0:
        log("[reproduce] OK")
    else:
        log(f"[reproduce] one or more steps failed (rc={rc})")
    sys.exit(rc)


if __name__ == "__main__":
    main()
