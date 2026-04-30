#!/usr/bin/env python3
"""
Cross-Judge Validation — addresses Reviewer 2 demand for judge quality evidence.
Takes 200 GPT-4o-mini trials (stratified across conditions for variance),
re-judges with GPT-4.1-mini, computes Cohen's kappa for brand_reasoning (binary)
and Pearson r for continuous scores.
"""
import csv, json, os, random, sys, time, glob
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from harness.core import load_env
load_env()

from openai import OpenAI
from scipy import stats
import numpy as np

client = OpenAI()

CROSS_JUDGE_MODEL = "gpt-4.1-mini-2025-04-14"
N_TRIALS = 200
RESULTS_DIR = SCRIPT_DIR.parent / "results" / "judge_validation"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Load ALL GPT-4o-mini trials from raw JSONs (all conditions for variance)
RAW_DIR = PROJECT_ROOT / "data" / "raw"
pattern = str(RAW_DIR / "specres_gpt-4o-mini_*.json")
files = glob.glob(pattern)
print(f"Found {len(files)} GPT-4o-mini files total")

# Load trials with judge scores (all conditions)
trials = []
for fp in files:
    try:
        with open(fp, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("judge_coherence") is not None:
            trials.append(d)
    except:
        pass

print(f"Loaded {len(trials)} trials with judge scores")

# Stratified sample: ensure mix of conditions for score variance
random.seed(42)
from collections import defaultdict
by_cond = defaultdict(list)
for t in trials:
    by_cond[t.get("condition", "?")].append(t)
print(f"  Conditions represented: {len(by_cond)}")

# Stratified sampling: take proportional share from each condition
if len(trials) > N_TRIALS:
    sampled = []
    per_cond = max(1, N_TRIALS // len(by_cond))
    for cond, ts in sorted(by_cond.items()):
        n = min(per_cond, len(ts))
        sampled.extend(random.sample(ts, n))
    # Fill remainder from full pool
    remaining_ids = {id(t) for t in sampled}
    pool = [t for t in trials if id(t) not in remaining_ids]
    if len(sampled) < N_TRIALS:
        sampled.extend(random.sample(pool, N_TRIALS - len(sampled)))
    elif len(sampled) > N_TRIALS:
        sampled = random.sample(sampled, N_TRIALS)
    trials = sampled

print(f"Selected {len(trials)} trials for cross-judging")

# Judge prompts (same as harness/judge.py)
def make_judge_prompt(trial, dimension):
    system_prompt = trial.get("system_prompt", "")
    user_message = trial.get("user_message", "")
    response = trial.get("raw_response", trial.get("reasoning", ""))
    choice = trial.get("choice", "")

    if dimension == "coherence":
        return (
            f"You are evaluating the coherence of a shopping assistant's recommendation.\n\n"
            f"SYSTEM PROMPT:\n{system_prompt}\n\n"
            f"USER MESSAGE:\n{user_message}\n\n"
            f"ASSISTANT RESPONSE:\n{response}\n\n"
            f"Rate the coherence of this response from 0 to 100, where:\n"
            f"0 = completely incoherent, 100 = perfectly coherent and well-structured.\n"
            f"Respond with ONLY a number between 0 and 100."
        )
    elif dimension == "spec_acknowledgment":
        return (
            f"You are evaluating whether a shopping assistant acknowledged the user's specifications.\n\n"
            f"SYSTEM PROMPT:\n{system_prompt}\n\n"
            f"USER MESSAGE:\n{user_message}\n\n"
            f"ASSISTANT RESPONSE:\n{response}\n\n"
            f"Rate how well the assistant addressed the user's specific requirements from 0 to 100, where:\n"
            f"0 = completely ignored specifications, 100 = perfectly addressed all requirements.\n"
            f"Respond with ONLY a number between 0 and 100."
        )
    elif dimension == "brand_reasoning":
        return (
            f"You are evaluating whether a shopping assistant's recommendation was primarily driven by brand familiarity.\n\n"
            f"SYSTEM PROMPT:\n{system_prompt}\n\n"
            f"USER MESSAGE:\n{user_message}\n\n"
            f"ASSISTANT RESPONSE:\n{response}\n\n"
            f"The assistant recommended product {choice}.\n\n"
            f"Was the recommendation primarily driven by brand familiarity/reputation rather than "
            f"the product's objective specifications matching the user's needs?\n"
            f"Respond with ONLY 'YES' or 'NO'."
        )

# Run cross-judging
results = []
for i, trial in enumerate(trials):
    cross_scores = {}
    for dim in ["coherence", "spec_acknowledgment", "brand_reasoning"]:
        prompt = make_judge_prompt(trial, dim)
        try:
            resp = client.chat.completions.create(
                model=CROSS_JUDGE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=10,
            )
            text = resp.choices[0].message.content.strip()
            if dim == "brand_reasoning":
                cross_scores[dim] = text.upper().startswith("YES")
            else:
                cross_scores[dim] = float(text)
            time.sleep(0.08)
        except Exception as e:
            print(f"  Error trial {i} {dim}: {e}")
            cross_scores[dim] = None

    results.append({
        "trial_id": trial.get("trial_id", ""),
        "condition": trial.get("condition", ""),
        "chose_optimal": trial.get("chose_optimal", False),
        "self_coherence": trial.get("judge_coherence"),
        "self_spec": trial.get("judge_spec_acknowledgment"),
        "self_brand": trial.get("judge_brand_reasoning"),
        "cross_coherence": cross_scores.get("coherence"),
        "cross_spec": cross_scores.get("spec_acknowledgment"),
        "cross_brand": cross_scores.get("brand_reasoning"),
    })

    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(trials)} trials judged")

# Save raw results
csv_path = RESULTS_DIR / "cross_judge_raw.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=results[0].keys())
    w.writeheader()
    w.writerows(results)
print(f"\nRaw results: {csv_path}")

# Analysis
print(f"\n{'='*60}")
print(f"CROSS-JUDGE VALIDATION RESULTS")
print(f"Self-judge: GPT-4o-mini | Cross-judge: GPT-4.1-mini")
print(f"N = {len(results)} trials (stratified across conditions)")
print(f"{'='*60}")

# Coherence: Pearson r
self_coh = [r["self_coherence"] for r in results if r["self_coherence"] is not None and r["cross_coherence"] is not None]
cross_coh = [r["cross_coherence"] for r in results if r["self_coherence"] is not None and r["cross_coherence"] is not None]
if self_coh:
    r_coh, p_coh = stats.pearsonr(self_coh, cross_coh)
    print(f"\nCoherence: r={r_coh:.3f}, p={p_coh:.2e}, N={len(self_coh)}")
    print(f"  Self mean={np.mean(self_coh):.1f}, Cross mean={np.mean(cross_coh):.1f}")

# Spec acknowledgment: Pearson r
self_spec = [r["self_spec"] for r in results if r["self_spec"] is not None and r["cross_spec"] is not None]
cross_spec = [r["cross_spec"] for r in results if r["self_spec"] is not None and r["cross_spec"] is not None]
if self_spec:
    r_spec, p_spec = stats.pearsonr(self_spec, cross_spec)
    print(f"\nSpec acknowledgment: r={r_spec:.3f}, p={p_spec:.2e}, N={len(self_spec)}")
    print(f"  Self mean={np.mean(self_spec):.1f}, Cross mean={np.mean(cross_spec):.1f}")

# Brand reasoning: Cohen's kappa
self_brand = [r["self_brand"] for r in results if r["self_brand"] is not None and r["cross_brand"] is not None]
cross_brand = [r["cross_brand"] for r in results if r["self_brand"] is not None and r["cross_brand"] is not None]
if self_brand:
    # Convert to binary
    sb = [1 if b else 0 for b in self_brand]
    cb = [1 if b else 0 for b in cross_brand]
    from sklearn.metrics import cohen_kappa_score
    kappa = cohen_kappa_score(sb, cb)
    agreement = sum(1 for a, b in zip(sb, cb) if a == b) / len(sb)
    print(f"\nBrand reasoning (binary): kappa={kappa:.3f}, agreement={agreement:.1%}, N={len(sb)}")
    print(f"  Self YES: {sum(sb)}/{len(sb)} ({sum(sb)/len(sb):.1%})")
    print(f"  Cross YES: {sum(cb)}/{len(cb)} ({sum(cb)/len(cb):.1%})")

# Save summary
summary = {
    "n_trials": len(results),
    "self_judge": "gpt-4o-mini",
    "cross_judge": "gpt-4.1-mini",
}
if self_coh:
    summary["coherence_r"] = round(r_coh, 3)
    summary["coherence_p"] = p_coh
if self_spec:
    summary["spec_r"] = round(r_spec, 3)
    summary["spec_p"] = p_spec
if self_brand:
    summary["brand_kappa"] = round(kappa, 3)
    summary["brand_agreement"] = round(agreement, 3)

with open(RESULTS_DIR / "cross_judge_summary.json", "w") as f:
    json.dump(summary, f, indent=2)
print(f"\nSummary saved.")
