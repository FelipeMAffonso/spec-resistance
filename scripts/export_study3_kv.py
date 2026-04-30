"""
Export Study 3 Cloudflare Worker KV transcripts before the 90-day TTL expires.

The bulk /export endpoint times out on large KV namespaces. This script
iterates /sessions (paginated-ish list) and calls /logs/:session_id per
session, then aggregates into a single JSON file.

Usage:
    python scripts/export_study3_kv.py
    python scripts/export_study3_kv.py --out path/to/export.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
DEFAULT_OUT = PROJECT / "nature-rr" / "data" / "human_studies" / "study3_kv_export.json"

BASE = "https://study3-chatbot.webmarinelli.workers.dev"

def load_admin_token() -> str:
    env = PROJECT / "nature-rr" / "study3-chatbot" / "worker" / ".env.admin"
    if not env.exists():
        raise SystemExit(f"admin .env not found at {env}")
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("EXPORT_ADMIN_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("EXPORT_ADMIN_TOKEN not in .env.admin")

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    token = load_admin_token()
    headers = {"X-Admin-Token": token}

    print("[1/3] listing sessions...")
    r = requests.get(f"{BASE}/sessions", headers=headers, timeout=60)
    r.raise_for_status()
    sessions = r.json().get("sessions", [])
    total_calls = sum(s.get("calls", 0) for s in sessions)
    print(f"  {len(sessions)} sessions, {total_calls} total LLM calls")

    print(f"[2/3] fetching per-session logs to {args.out}...")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    aggregate: list[dict] = []
    failed: list[str] = []
    for i, s in enumerate(sessions):
        sid = s["session_id"]
        try:
            rr = requests.get(f"{BASE}/logs/{sid}", timeout=30)
            rr.raise_for_status()
            data = rr.json()
            logs = data.get("logs") or data.get("records") or []
            aggregate.extend(logs)
            if (i + 1) % 50 == 0:
                print(f"  progress: {i+1}/{len(sessions)} sessions, {len(aggregate)} records so far")
        except Exception as e:  # noqa: BLE001
            failed.append(f"{sid}: {e}")
            time.sleep(1)

    print(f"[3/3] writing aggregate ({len(aggregate)} records, {len(failed)} failed)...")
    out = {
        "schema": "study3_kv_export.v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_sessions": len(sessions),
        "total_records": len(aggregate),
        "failed_sessions": failed,
        "records": aggregate,
    }
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    size_mb = args.out.stat().st_size / 1e6
    print(f"  wrote {args.out} ({size_mb:.1f} MB)")
    if failed:
        print(f"  failures: {failed[:5]}{' and more' if len(failed) > 5 else ''}")
        sys.exit(1)

if __name__ == "__main__":
    main()
