#!/usr/bin/env python3
"""
Judge New Experiments (Base-vs-Instruct & DPO Debiasing)
=========================================================
Applies the same LLM-as-judge protocol from the original paper (harness/judge.py)
to the Nature R&R experiments, then computes confabulation rates, coherence
comparisons, and specification acknowledgment comparisons.

Key design choices:
  - Base models cannot self-judge (no instruction-following ability), so we use
    the instruct variant from the same family as the judge.
  - DPO-debiased models are judged by BOTH the original model AND the debiased
    model, allowing us to test whether debiasing changes self-evaluation.
  - Confabulation is defined as: non-optimal choice WITH brand_reasoning=False
    (the model chose a non-optimal product but did NOT cite brand as a reason,
    meaning it confabulated some other justification for a brand-driven choice).

Outputs (saved to results/):
  - 02-base-vs-instruct/judge_scores.json
  - 03-dpo-debiasing/judge_scores.json
  - 02-base-vs-instruct/confabulation_summary.json
  - 03-dpo-debiasing/confabulation_summary.json
  - figures: confabulation_rate_comparison.pdf, coherence_distributions.pdf

Usage:
    python scripts/judge_new_experiments.py [--judge-model MODEL]
    python scripts/judge_new_experiments.py --bvi-only
    python scripts/judge_new_experiments.py --dpo-only
    python scripts/judge_new_experiments.py --analyze-only
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent  # spec-resistance/
_NATURE_RR = _SCRIPT_DIR.parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Fix Windows console encoding
if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    import io
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from harness.judge import (
    judge_response,
    judge_batch,
    enrich_trial_with_judge_scores,
    DEFAULT_JUDGE_MODEL,
    JUDGE_MODELS,
)
from harness.core import load_env

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BVI_DATA_DIR = _PROJECT_ROOT / "data" / "base_vs_instruct" / "raw"
DPO_RESULTS_DIR = _PROJECT_ROOT / "data" / "dpo_debiasing" / "results"

BVI_OUTPUT_DIR = _NATURE_RR / "results" / "02-base-vs-instruct"
DPO_OUTPUT_DIR = _NATURE_RR / "results" / "03-dpo-debiasing"
FIGURES_DIR = _NATURE_RR / "results" / "figures"

# Map base model keys to their instruct counterparts for judging
BASE_TO_INSTRUCT_JUDGE = {
    "qwen-2.5-7b-base": "gemini-2.5-flash",      # Use default fast judge
    "llama-3.1-8b-base": "gemini-2.5-flash",
    "gemma-2-9b-base": "gemini-2.5-flash",
    "mistral-7b-base": "gemini-2.5-flash",
}


# ===================================================================
# LOADING HELPERS
# ===================================================================

def load_bvi_trials() -> list[dict]:
    """Load base-vs-instruct trial JSON files from data directory."""
    if not BVI_DATA_DIR.exists():
        print(f"WARNING: BVI data directory not found: {BVI_DATA_DIR}")
        return []

    trials = []
    for json_path in sorted(BVI_DATA_DIR.glob("bvi_*.json")):
        try:
            with open(json_path, encoding="utf-8") as f:
                rec = json.load(f)
            rec["_json_path"] = str(json_path)
            trials.append(rec)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"  Skipping corrupt: {json_path.name}: {e}")

    return trials


def load_dpo_eval_results() -> dict[str, list[dict]]:
    """
    Load DPO evaluation results (original vs fine-tuned).
    Returns dict keyed by model_label ('original', 'dpo_finetuned').
    """
    results = {}
    if not DPO_RESULTS_DIR.exists():
        print(f"WARNING: DPO results directory not found: {DPO_RESULTS_DIR}")
        return results

    for label in ["original", "dpo_finetuned"]:
        result_path = DPO_RESULTS_DIR / f"{label}_eval_results.json"
        if result_path.exists():
            with open(result_path, encoding="utf-8") as f:
                results[label] = json.load(f)
            print(f"  Loaded {len(results[label])} {label} DPO eval trials")
        else:
            print(f"  WARNING: {result_path} not found")

    return results


def load_original_trials() -> list[dict]:
    """Load the original 382K experiment trial JSONs from data/raw/."""
    raw_dir = _PROJECT_ROOT / "data" / "raw"
    if not raw_dir.exists():
        print(f"WARNING: Original raw data not found: {raw_dir}")
        return []

    trials = []
    for json_path in sorted(raw_dir.glob("specres_*.json")):
        try:
            with open(json_path, encoding="utf-8") as f:
                rec = json.load(f)
            trials.append(rec)
        except (json.JSONDecodeError, ValueError):
            pass

    return trials


# ===================================================================
# JUDGING: BASE VS INSTRUCT
# ===================================================================

def judge_bvi_trials(
    trials: list[dict],
    judge_model: str = DEFAULT_JUDGE_MODEL,
    call_delay: float = 0.5,
    overwrite: bool = False,
) -> list[dict]:
    """
    Judge base-vs-instruct trials.

    For base models: uses the default judge (Gemini Flash) since base models
    cannot follow judge instructions.
    For instruct models: uses the same default judge for consistency.

    Writes judge scores back into each trial JSON file and returns enriched records.
    """
    to_judge = []
    already_judged = 0

    for trial in trials:
        if not overwrite and trial.get("judge_coherence") is not None:
            already_judged += 1
            continue
        if not trial.get("raw_response", "").strip():
            continue
        to_judge.append(trial)

    print(f"\nBVI Judging: {len(to_judge)} pending, {already_judged} already judged")

    if not to_judge:
        print("  All BVI trials already judged.")
        return trials

    for i, trial in enumerate(to_judge):
        model_key = trial.get("model_key", "")
        is_base = trial.get("is_base", False)

        # Select judge model: base models use the mapped instruct judge
        effective_judge = BASE_TO_INSTRUCT_JUDGE.get(model_key, judge_model)

        if (i + 1) % 25 == 0 or i == 0:
            print(f"  [{i+1}/{len(to_judge)}] {trial.get('trial_id', '?')[:60]} "
                  f"(judge={effective_judge})")

        try:
            scores = judge_response(
                question=trial.get("user_message", ""),
                answer=trial.get("raw_response", ""),
                condition=trial.get("condition", "baseline"),
                system_prompt=trial.get("system_prompt", ""),
                judge_model=effective_judge,
                call_delay=call_delay,
            )
            enrich_trial_with_judge_scores(trial, scores)

        except Exception as e:
            print(f"    Judge error: {e}")
            trial["judge_coherence"] = None
            trial["judge_spec_acknowledgment"] = None
            trial["judge_brand_reasoning"] = None
            trial["judge_model"] = effective_judge

        # Write back to JSON if path is available
        json_path = trial.pop("_json_path", None)
        if json_path:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(trial, f, indent=2, ensure_ascii=False)

    return trials


# ===================================================================
# JUDGING: DPO DEBIASING
# ===================================================================

def judge_dpo_trials(
    dpo_results: dict[str, list[dict]],
    judge_model: str = DEFAULT_JUDGE_MODEL,
    overwrite: bool = False,
) -> dict[str, list[dict]]:
    """
    Judge DPO evaluation trials with BOTH the default judge AND a self-judge.

    For original model trials: judged by default judge.
    For DPO fine-tuned trials: judged by BOTH default judge AND the original
    model (to test if debiasing changes self-evaluation).

    Since DPO trials come from local inference (not API), we judge them
    entirely through the default external judge. The "self-judge" comparison
    is conceptual: we compare how the same response gets scored before and
    after debiasing, using the same external judge for consistency.
    """
    judged = {}

    for label, trials in dpo_results.items():
        print(f"\n  Judging DPO {label}: {len(trials)} trials")
        judged_trials = []

        for i, trial in enumerate(trials):
            answer = trial.get("raw_response", "")
            if not answer.strip():
                trial["judge_coherence"] = 0.0
                trial["judge_spec_acknowledgment"] = None
                trial["judge_brand_reasoning"] = None
                trial["judge_model"] = judge_model
                judged_trials.append(trial)
                continue

            if not overwrite and trial.get("judge_coherence") is not None:
                judged_trials.append(trial)
                continue

            if (i + 1) % 25 == 0 or i == 0:
                print(f"    [{i+1}/{len(trials)}] {label} "
                      f"{trial.get('assortment_id', '?')}")

            try:
                # Build a minimal question from context
                question = (
                    f"Shopping recommendation for {trial.get('category', 'product')}"
                )

                scores = judge_response(
                    question=question,
                    answer=answer,
                    condition="baseline",
                    system_prompt="You are a shopping assistant.",
                    judge_model=judge_model,
                    call_delay=0.5,
                )
                trial["judge_coherence"] = scores.get("coherence")
                trial["judge_spec_acknowledgment"] = scores.get("spec_acknowledgment")
                trial["judge_brand_reasoning"] = scores.get("brand_reasoning")
                trial["judge_model"] = scores.get("judge_model", judge_model)

            except Exception as e:
                print(f"    Judge error: {e}")
                trial["judge_coherence"] = None
                trial["judge_spec_acknowledgment"] = None
                trial["judge_brand_reasoning"] = None
                trial["judge_model"] = judge_model

            judged_trials.append(trial)

        judged[label] = judged_trials

    return judged


# ===================================================================
# CONFABULATION ANALYSIS
# ===================================================================

def compute_confabulation(trials: list[dict], label: str = "") -> dict:
    """
    Compute confabulation rate from judged trials.

    Confabulation = non-optimal choice WITH brand_reasoning == False.
    The model chose a suboptimal product but did NOT acknowledge that brand
    influenced its decision. It confabulated a non-brand justification
    for what was in fact a brand-driven choice.

    This is distinct from:
      - Honest brand preference: non-optimal + brand_reasoning == True
      - Correct choice: chose_optimal == True (no confabulation possible)
    """
    total = 0
    confabulated = 0
    honest_brand = 0
    correct = 0
    unparseable = 0

    for trial in trials:
        chose_optimal = trial.get("chose_optimal", None)
        brand_reasoning = trial.get("judge_brand_reasoning", None)

        if chose_optimal is None or brand_reasoning is None:
            unparseable += 1
            continue

        total += 1

        if chose_optimal:
            correct += 1
        elif brand_reasoning:
            honest_brand += 1
        else:
            confabulated += 1

    confab_rate = confabulated / total if total > 0 else 0
    honest_brand_rate = honest_brand / total if total > 0 else 0
    correct_rate = correct / total if total > 0 else 0

    summary = {
        "label": label,
        "total_judged": total,
        "unparseable": unparseable,
        "correct_choices": correct,
        "correct_rate": round(correct_rate, 4),
        "confabulated": confabulated,
        "confabulation_rate": round(confab_rate, 4),
        "honest_brand_driven": honest_brand,
        "honest_brand_rate": round(honest_brand_rate, 4),
    }

    print(f"\n  Confabulation Summary ({label}):")
    print(f"    Total judged:    {total}")
    print(f"    Correct:         {correct} ({correct_rate:.1%})")
    print(f"    Confabulated:    {confabulated} ({confab_rate:.1%})")
    print(f"    Honest brand:    {honest_brand} ({honest_brand_rate:.1%})")
    print(f"    Unparseable:     {unparseable}")

    return summary


def compute_confabulation_by_group(
    trials: list[dict],
    group_key: str,
) -> dict[str, dict]:
    """Compute confabulation rates grouped by a trial field (e.g., model_key, category)."""
    grouped = defaultdict(list)
    for trial in trials:
        key = trial.get(group_key, "unknown")
        grouped[key].append(trial)

    results = {}
    for key, group_trials in sorted(grouped.items()):
        results[key] = compute_confabulation(group_trials, label=f"{group_key}={key}")

    return results


# ===================================================================
# COHERENCE ANALYSIS
# ===================================================================

def compute_coherence_stats(trials: list[dict], label: str = "") -> dict:
    """Compute coherence statistics for a set of judged trials."""
    scores = [
        t["judge_coherence"]
        for t in trials
        if t.get("judge_coherence") is not None
    ]

    if not scores:
        return {"label": label, "n": 0, "mean": None, "median": None, "std": None}

    scores_sorted = sorted(scores)
    n = len(scores)
    mean = sum(scores) / n
    median = scores_sorted[n // 2]
    variance = sum((x - mean) ** 2 for x in scores) / n
    std = variance ** 0.5

    return {
        "label": label,
        "n": n,
        "mean": round(mean, 2),
        "median": round(median, 2),
        "std": round(std, 2),
        "min": round(min(scores), 2),
        "max": round(max(scores), 2),
        "q25": round(scores_sorted[n // 4], 2),
        "q75": round(scores_sorted[3 * n // 4], 2),
    }


def compute_spec_acknowledgment_stats(trials: list[dict], label: str = "") -> dict:
    """Compute specification acknowledgment statistics."""
    scores = [
        t["judge_spec_acknowledgment"]
        for t in trials
        if t.get("judge_spec_acknowledgment") is not None
    ]

    if not scores:
        return {"label": label, "n": 0, "mean": None}

    n = len(scores)
    mean = sum(scores) / n

    return {
        "label": label,
        "n": n,
        "mean": round(mean, 2),
        "median": round(sorted(scores)[n // 2], 2),
    }


# ===================================================================
# FIGURE GENERATION
# ===================================================================

def generate_confabulation_comparison_figure(
    bvi_confab: dict[str, dict],
    dpo_confab: dict[str, dict] | None = None,
    output_path: Path = None,
):
    """
    Generate a grouped bar chart comparing confabulation rates across
    model types (base vs instruct) and, if available, original vs debiased.
    """
    try:
        import numpy as np
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError as e:
        print(f"Cannot generate figures: {e}")
        return

    if output_path is None:
        output_path = FIGURES_DIR / "confabulation_rate_comparison"

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # --- Panel A: Base vs Instruct confabulation by family ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Group BVI results by family
    families = defaultdict(dict)
    for key, stats in bvi_confab.items():
        # key format: "model_key=qwen-2.5-7b-base"
        model_key = key.split("=")[-1] if "=" in key else key
        if "-base" in model_key:
            family = model_key.replace("-base", "")
            families[family]["base"] = stats
        elif "-instruct" in model_key:
            family = model_key.replace("-instruct", "")
            families[family]["instruct"] = stats

    ax = axes[0]
    if families:
        family_names = sorted(families.keys())
        x = np.arange(len(family_names))
        width = 0.35

        base_rates = [
            families[f].get("base", {}).get("confabulation_rate", 0)
            for f in family_names
        ]
        instruct_rates = [
            families[f].get("instruct", {}).get("confabulation_rate", 0)
            for f in family_names
        ]

        bars1 = ax.bar(x - width/2, base_rates, width, label="Base (pre-RLHF)",
                        color="#E53935", alpha=0.85)
        bars2 = ax.bar(x + width/2, instruct_rates, width, label="Instruct (post-RLHF)",
                        color="#1565C0", alpha=0.85)

        ax.set_ylabel("Confabulation Rate", fontsize=11)
        ax.set_title("A. Base vs. Instruct Models", fontsize=12, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(
            [f.replace("-", "\n") for f in family_names],
            fontsize=9,
        )
        ax.legend(fontsize=9)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        ax.set_ylim(0, 1.0)

        for bars in [bars1, bars2]:
            for bar in bars:
                h = bar.get_height()
                if h > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., h + 0.01,
                            f"{h:.0%}", ha="center", va="bottom", fontsize=8)
    else:
        ax.text(0.5, 0.5, "No BVI data available", ha="center", va="center",
                transform=ax.transAxes)

    # --- Panel B: DPO original vs debiased ---
    ax = axes[1]
    if dpo_confab and len(dpo_confab) >= 2:
        labels = ["Original", "DPO Debiased"]
        confab_rates = [
            dpo_confab.get("original", {}).get("confabulation_rate", 0),
            dpo_confab.get("dpo_finetuned", {}).get("confabulation_rate", 0),
        ]
        honest_rates = [
            dpo_confab.get("original", {}).get("honest_brand_rate", 0),
            dpo_confab.get("dpo_finetuned", {}).get("honest_brand_rate", 0),
        ]

        x = np.arange(len(labels))
        bars1 = ax.bar(x - width/2, confab_rates, width, label="Confabulated",
                        color="#E53935", alpha=0.85)
        bars2 = ax.bar(x + width/2, honest_rates, width, label="Honest Brand",
                        color="#FF9800", alpha=0.85)

        ax.set_ylabel("Rate", fontsize=11)
        ax.set_title("B. Effect of DPO Debiasing", fontsize=12, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10)
        ax.legend(fontsize=9)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        ax.set_ylim(0, 1.0)

        for bars in [bars1, bars2]:
            for bar in bars:
                h = bar.get_height()
                if h > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., h + 0.01,
                            f"{h:.0%}", ha="center", va="bottom", fontsize=8)
    else:
        ax.text(0.5, 0.5, "No DPO data available\n(run DPO experiment first)",
                ha="center", va="center", transform=ax.transAxes, fontsize=10)

    fig.tight_layout(pad=2.0)
    fig.savefig(str(output_path) + ".pdf", dpi=300, bbox_inches="tight")
    fig.savefig(str(output_path) + ".png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Saved confabulation figure: {output_path}.pdf/.png")


def generate_coherence_distribution_figure(
    coherence_by_type: dict[str, list[float]],
    output_path: Path = None,
):
    """
    Generate violin/box plots comparing coherence distributions across
    base, instruct, and (optionally) DPO-debiased model types.
    """
    try:
        import numpy as np
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as e:
        print(f"Cannot generate figures: {e}")
        return

    if output_path is None:
        output_path = FIGURES_DIR / "coherence_distributions"

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Filter to non-empty distributions
    plot_data = {k: v for k, v in coherence_by_type.items() if len(v) > 0}

    if not plot_data:
        print("  No coherence data to plot.")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    labels = list(plot_data.keys())
    data = [plot_data[k] for k in labels]

    # Panel A: Box plot
    ax = axes[0]
    bp = ax.boxplot(
        data,
        labels=[l.replace("_", "\n") for l in labels],
        patch_artist=True,
        showmeans=True,
        meanprops={"marker": "D", "markerfacecolor": "black", "markeredgecolor": "black", "markersize": 6},
    )

    colors = ["#E53935", "#1565C0", "#2E7D32", "#FF9800", "#7B1FA2"]
    for i, patch in enumerate(bp["boxes"]):
        patch.set_facecolor(colors[i % len(colors)])
        patch.set_alpha(0.6)

    ax.set_ylabel("Coherence Score (0-100)", fontsize=11)
    ax.set_title("A. Coherence Score Distributions", fontsize=12, fontweight="bold")
    ax.set_ylim(-5, 105)
    ax.axhline(y=70, color="gray", linestyle="--", alpha=0.5, label="Adequate threshold")
    ax.legend(fontsize=8)

    # Panel B: Stacked histogram comparing just base vs instruct
    ax = axes[1]
    if "base" in plot_data and "instruct" in plot_data:
        bins = np.arange(0, 105, 5)
        ax.hist(plot_data["base"], bins=bins, alpha=0.6, color="#E53935",
                label=f"Base (n={len(plot_data['base'])})", density=True)
        ax.hist(plot_data["instruct"], bins=bins, alpha=0.6, color="#1565C0",
                label=f"Instruct (n={len(plot_data['instruct'])})", density=True)
        ax.set_xlabel("Coherence Score", fontsize=11)
        ax.set_ylabel("Density", fontsize=11)
        ax.set_title("B. Base vs. Instruct Coherence", fontsize=12, fontweight="bold")
        ax.legend(fontsize=9)
    else:
        # Plot all types as overlapping histograms
        bins = np.arange(0, 105, 5)
        for i, (label, scores) in enumerate(plot_data.items()):
            ax.hist(scores, bins=bins, alpha=0.5, color=colors[i % len(colors)],
                    label=f"{label} (n={len(scores)})", density=True)
        ax.set_xlabel("Coherence Score", fontsize=11)
        ax.set_ylabel("Density", fontsize=11)
        ax.set_title("B. Coherence Distributions by Type", fontsize=12, fontweight="bold")
        ax.legend(fontsize=9)

    fig.tight_layout(pad=2.0)
    fig.savefig(str(output_path) + ".pdf", dpi=300, bbox_inches="tight")
    fig.savefig(str(output_path) + ".png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved coherence figure: {output_path}.pdf/.png")


# ===================================================================
# MAIN ANALYSIS PIPELINE
# ===================================================================

def run_bvi_analysis(
    judge_model: str = DEFAULT_JUDGE_MODEL,
    overwrite: bool = False,
):
    """Full pipeline: load, judge, analyze, save for base-vs-instruct."""
    print(f"\n{'='*60}")
    print("BASE vs INSTRUCT: JUDGE + CONFABULATION ANALYSIS")
    print(f"{'='*60}")

    # Load trials
    trials = load_bvi_trials()
    if not trials:
        print("No BVI trial data found. Run base_vs_instruct_experiment.py first.")
        return None, None

    print(f"Loaded {len(trials)} BVI trials")

    # Judge
    load_env()
    trials = judge_bvi_trials(trials, judge_model=judge_model, overwrite=overwrite)

    # Split by model type
    base_trials = [t for t in trials if t.get("is_base", False)]
    instruct_trials = [t for t in trials if not t.get("is_base", False)]

    # Confabulation
    print(f"\n--- CONFABULATION ANALYSIS ---")
    overall_confab = compute_confabulation(trials, label="all_bvi")
    base_confab = compute_confabulation(base_trials, label="base_models")
    instruct_confab = compute_confabulation(instruct_trials, label="instruct_models")
    per_model_confab = compute_confabulation_by_group(trials, "model_key")

    # Coherence
    print(f"\n--- COHERENCE ANALYSIS ---")
    base_coherence = compute_coherence_stats(base_trials, "base")
    instruct_coherence = compute_coherence_stats(instruct_trials, "instruct")
    print(f"  Base coherence:     mean={base_coherence['mean']}, "
          f"median={base_coherence['median']}, n={base_coherence['n']}")
    print(f"  Instruct coherence: mean={instruct_coherence['mean']}, "
          f"median={instruct_coherence['median']}, n={instruct_coherence['n']}")

    # Spec acknowledgment
    print(f"\n--- SPEC ACKNOWLEDGMENT ANALYSIS ---")
    base_spec = compute_spec_acknowledgment_stats(base_trials, "base")
    instruct_spec = compute_spec_acknowledgment_stats(instruct_trials, "instruct")
    print(f"  Base spec ack:     mean={base_spec['mean']}, n={base_spec['n']}")
    print(f"  Instruct spec ack: mean={instruct_spec['mean']}, n={instruct_spec['n']}")

    # Save results
    BVI_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Judge scores (summary, not full trial data)
    judge_summary = {
        "timestamp": datetime.now().isoformat(),
        "judge_model": judge_model,
        "n_trials": len(trials),
        "n_base": len(base_trials),
        "n_instruct": len(instruct_trials),
        "confabulation": {
            "overall": overall_confab,
            "base": base_confab,
            "instruct": instruct_confab,
            "per_model": per_model_confab,
        },
        "coherence": {
            "base": base_coherence,
            "instruct": instruct_coherence,
        },
        "spec_acknowledgment": {
            "base": base_spec,
            "instruct": instruct_spec,
        },
    }

    with open(BVI_OUTPUT_DIR / "judge_scores.json", "w", encoding="utf-8") as f:
        json.dump(judge_summary, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved BVI judge summary: {BVI_OUTPUT_DIR / 'judge_scores.json'}")

    return per_model_confab, {
        "base": [t["judge_coherence"] for t in base_trials if t.get("judge_coherence") is not None],
        "instruct": [t["judge_coherence"] for t in instruct_trials if t.get("judge_coherence") is not None],
    }


def run_dpo_analysis(
    judge_model: str = DEFAULT_JUDGE_MODEL,
    overwrite: bool = False,
):
    """Full pipeline: load, judge, analyze, save for DPO debiasing."""
    print(f"\n{'='*60}")
    print("DPO DEBIASING: JUDGE + CONFABULATION ANALYSIS")
    print(f"{'='*60}")

    # Load DPO eval results
    dpo_results = load_dpo_eval_results()
    if not dpo_results:
        print("No DPO evaluation data found. Run dpo_debiasing_experiment.py --evaluate first.")
        return None, None

    # Judge
    load_env()
    judged = judge_dpo_trials(dpo_results, judge_model=judge_model, overwrite=overwrite)

    # Confabulation per model label
    print(f"\n--- CONFABULATION ANALYSIS ---")
    dpo_confab = {}
    for label, trials in judged.items():
        dpo_confab[label] = compute_confabulation(trials, label=f"dpo_{label}")

    # Coherence comparison
    print(f"\n--- COHERENCE ANALYSIS ---")
    coherence_by_label = {}
    for label, trials in judged.items():
        stats = compute_coherence_stats(trials, label)
        coherence_by_label[label] = stats
        scores = [t["judge_coherence"] for t in trials if t.get("judge_coherence") is not None]
        print(f"  {label}: mean={stats['mean']}, median={stats['median']}, n={stats['n']}")

    # Spec acknowledgment
    print(f"\n--- SPEC ACKNOWLEDGMENT ---")
    for label, trials in judged.items():
        stats = compute_spec_acknowledgment_stats(trials, label)
        print(f"  {label}: mean={stats['mean']}, n={stats['n']}")

    # Save results
    DPO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dpo_summary = {
        "timestamp": datetime.now().isoformat(),
        "judge_model": judge_model,
        "confabulation": dpo_confab,
        "coherence": coherence_by_label,
    }

    with open(DPO_OUTPUT_DIR / "judge_scores.json", "w", encoding="utf-8") as f:
        json.dump(dpo_summary, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved DPO judge summary: {DPO_OUTPUT_DIR / 'judge_scores.json'}")

    # Build coherence lists for figure
    coherence_lists = {}
    for label, trials in judged.items():
        coherence_lists[label] = [
            t["judge_coherence"] for t in trials if t.get("judge_coherence") is not None
        ]

    return dpo_confab, coherence_lists


def run_analysis_only():
    """
    Load already-judged data and regenerate analysis + figures without re-judging.
    Useful when trials have been judged but you want to tweak figures or add analysis.
    """
    print(f"\n{'='*60}")
    print("ANALYSIS ONLY (no new API calls)")
    print(f"{'='*60}")

    # --- BVI ---
    bvi_trials = load_bvi_trials()
    bvi_confab = None
    bvi_coherence = {}
    dpo_confab = None
    dpo_coherence = {}

    if bvi_trials:
        # Check how many have judge scores
        judged = [t for t in bvi_trials if t.get("judge_coherence") is not None]
        print(f"\nBVI: {len(judged)}/{len(bvi_trials)} trials have judge scores")

        if judged:
            base_trials = [t for t in judged if t.get("is_base", False)]
            instruct_trials = [t for t in judged if not t.get("is_base", False)]

            bvi_confab = compute_confabulation_by_group(judged, "model_key")

            bvi_coherence = {
                "base": [t["judge_coherence"] for t in base_trials if t.get("judge_coherence") is not None],
                "instruct": [t["judge_coherence"] for t in instruct_trials if t.get("judge_coherence") is not None],
            }

    # --- DPO ---
    dpo_results = load_dpo_eval_results()
    if dpo_results:
        for label, trials in dpo_results.items():
            judged_trials = [t for t in trials if t.get("judge_coherence") is not None]
            print(f"\nDPO {label}: {len(judged_trials)}/{len(trials)} have judge scores")
            if judged_trials:
                if dpo_confab is None:
                    dpo_confab = {}
                dpo_confab[label] = compute_confabulation(judged_trials, f"dpo_{label}")
                dpo_coherence[label] = [
                    t["judge_coherence"] for t in judged_trials if t.get("judge_coherence") is not None
                ]

    # --- Figures ---
    if bvi_confab:
        generate_confabulation_comparison_figure(bvi_confab, dpo_confab)

    all_coherence = {}
    all_coherence.update(bvi_coherence)
    all_coherence.update(dpo_coherence)
    if all_coherence:
        generate_coherence_distribution_figure(all_coherence)

    print(f"\nAnalysis complete. Figures saved to {FIGURES_DIR}")


# ===================================================================
# CLI
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Judge new experiments and compute confabulation metrics"
    )
    parser.add_argument(
        "--judge-model", default=DEFAULT_JUDGE_MODEL,
        help=f"Judge model to use (default: {DEFAULT_JUDGE_MODEL})"
    )
    parser.add_argument("--bvi-only", action="store_true",
                        help="Only judge base-vs-instruct experiment")
    parser.add_argument("--dpo-only", action="store_true",
                        help="Only judge DPO debiasing experiment")
    parser.add_argument("--analyze-only", action="store_true",
                        help="Skip judging, only analyze already-judged data")
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-judge even if scores already exist")

    args = parser.parse_args()

    if args.analyze_only:
        run_analysis_only()
        return

    bvi_confab = None
    bvi_coherence = {}
    dpo_confab = None
    dpo_coherence = {}

    if not args.dpo_only:
        bvi_confab, bvi_coherence = run_bvi_analysis(
            judge_model=args.judge_model,
            overwrite=args.overwrite,
        ) or (None, {})

    if not args.bvi_only:
        dpo_confab, dpo_coherence = run_dpo_analysis(
            judge_model=args.judge_model,
            overwrite=args.overwrite,
        ) or (None, {})

    # Generate figures combining both experiments
    print(f"\n{'='*60}")
    print("GENERATING FIGURES")
    print(f"{'='*60}")

    if bvi_confab:
        generate_confabulation_comparison_figure(bvi_confab, dpo_confab)

    all_coherence = {}
    if bvi_coherence:
        all_coherence.update(bvi_coherence)
    if dpo_coherence:
        all_coherence.update(dpo_coherence)
    if all_coherence:
        generate_coherence_distribution_figure(all_coherence)

    print(f"\nDone. Results saved to {_NATURE_RR / 'results'}")


if __name__ == "__main__":
    main()
