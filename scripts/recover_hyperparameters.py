"""
Recover the OpenAI-resolved hyperparameters for every fine-tuned model in
FINE_TUNED_MODELS.json.

OpenAI's fine-tuning API accepts "auto" for batch_size and
learning_rate_multiplier. After training completes, the job record exposes
the numeric values that OpenAI's heuristic actually chose. Pulling these is
critical for reproducibility: reruns with "auto" will pick different values
over time as OpenAI updates the heuristic.

Usage:
    python scripts/recover_hyperparameters.py

Writes resolved hyperparameters back into nature-rr/FINE_TUNED_MODELS.json.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from openai import OpenAI

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
REGISTRY = PROJECT / "nature-rr" / "FINE_TUNED_MODELS.json"
DYNAMICS = PROJECT / "nature-rr" / "results" / "training_dynamics" / "all_training_dynamics.json"

def load_env() -> None:
    env = PROJECT / "config" / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def collect_job_ids() -> dict[str, str]:
    """Map friendly key -> OpenAI job id from the training-dynamics log."""
    out: dict[str, str] = {}
    if not DYNAMICS.exists():
        print(f"[warn] {DYNAMICS} not found; cannot map job ids")
        return out
    data = json.loads(DYNAMICS.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        for key, entry in data.items():
            if isinstance(entry, dict):
                jid = entry.get("job_id")
                if jid:
                    out[key] = jid
    return out

def retrieve_resolved(client: OpenAI, job_id: str) -> dict | None:
    try:
        job = client.fine_tuning.jobs.retrieve(job_id)
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] {job_id}: {e}")
        return None
    # OpenAI SDK exposes job.hyperparameters with resolved values after completion
    hp = getattr(job, "hyperparameters", None)
    if hp is None:
        return None
    # hp has attributes n_epochs, batch_size, learning_rate_multiplier
    return {
        "n_epochs": getattr(hp, "n_epochs", None),
        "batch_size": getattr(hp, "batch_size", None),
        "learning_rate_multiplier": getattr(hp, "learning_rate_multiplier", None),
        "trained_tokens": getattr(job, "trained_tokens", None),
        "status": getattr(job, "status", None),
    }

def main() -> None:
    load_env()
    if "OPENAI_API_KEY" not in os.environ:
        sys.exit("OPENAI_API_KEY not set (check config/.env)")
    client = OpenAI()

    jobmap = collect_job_ids()
    print(f"[info] {len(jobmap)} jobs found in training_dynamics log")

    resolved: dict[str, dict] = {}
    for key, jid in jobmap.items():
        print(f"[query] {key}: {jid}")
        r = retrieve_resolved(client, jid)
        if r:
            resolved[key] = {"job_id": jid, **r}

    out_path = PROJECT / "nature-rr" / "results" / "training_dynamics" / "resolved_hyperparameters.json"
    out_path.write_text(json.dumps(resolved, indent=2), encoding="utf-8")
    print(f"[done] wrote {out_path} ({len(resolved)} entries)")

    # Also patch FINE_TUNED_MODELS.json entries where possible
    if REGISTRY.exists():
        reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        # Map training-dynamics keys to registry sections
        key_map = {
            "inject-100": "injection_primary",
            "inject-50": "injection_50",
            "inject-200": "injection_200",
            "inject-v2-pure-inj-100": "injection_pure_v2",
            "inject-control-neutral": "injection_control_neutral",
            "inject-6k-mixed": "injection_6k_mixed",
            "debiasing-6k-41nano": "debiasing_41nano_6k",
            "spec-resist-v3": "debiasing_4omini_6k_spec_resist_v3",
        }
        patched = 0
        for k, reg_key in key_map.items():
            if k in resolved and reg_key in reg:
                r = resolved[k]
                if reg[reg_key].get("batch_size") is None and r.get("batch_size"):
                    reg[reg_key]["batch_size"] = r["batch_size"]
                    patched += 1
                if reg[reg_key].get("learning_rate_multiplier") is None and r.get("learning_rate_multiplier"):
                    reg[reg_key]["learning_rate_multiplier"] = r["learning_rate_multiplier"]
                    patched += 1
        if patched:
            REGISTRY.write_text(json.dumps(reg, indent=2), encoding="utf-8")
            print(f"[done] patched {patched} registry fields")

if __name__ == "__main__":
    main()
