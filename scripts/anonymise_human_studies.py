"""
Anonymise Qualtrics exports for Studies 1A, 1B, 2, and 3 into the committed
public bundle at `data/human_studies/`.

For each study:
  1. Fetch the latest Qualtrics export (or use a local CSV).
  2. Strip / hash PROLIFIC_PID (SHA-256 truncated to 16 chars).
  3. Drop IP address, location, and any other potentially identifying fields.
  4. Write an anonymised CSV to data/human_studies/{study}_anonymised.csv.
  5. Write a matching codebook.md describing every column.

Usage:
    python scripts/anonymise_human_studies.py --study 1A
    python scripts/anonymise_human_studies.py --study all

Requires Qualtrics API credentials to fetch; otherwise pass --csv for local.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
OUT_DIR = PROJECT / "nature-rr" / "data" / "human_studies"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STUDIES = {
    "1A": {"qualtrics_id": "SV_01zhSyavcdjz06G", "short": "study1a_coffee"},
    "1B": {"qualtrics_id": "SV_5hvy9y0CICi9lOe", "short": "study1b_earbuds"},
    "2":  {"qualtrics_id": "SV_3PHq8N243mxAr0W", "short": "study2_inoculation"},
    "3":  {"qualtrics_id": "SV_8A33OiyMqjqr5LU", "short": "study3_chatbot"},
}

# Columns to drop outright (PII / tracking)
DROP_COLUMNS = {
    "IPAddress", "LocationLatitude", "LocationLongitude",
    "RecipientLastName", "RecipientFirstName", "RecipientEmail",
    "ExternalReference", "DistributionChannel",
    "UserAgent", "UserLanguage",
}

# Columns to hash (not drop — needed for reconciliation)
HASH_COLUMNS = {"PROLIFIC_PID", "SESSION_ID", "ResponseId"}

API_BASE = "https://pdx1.qualtrics.com/API/v3"


def hash_pid(value: str, salt: str = "spec-resistance-2026") -> str:
    if not isinstance(value, str) or not value:
        return ""
    return hashlib.sha256((salt + value).encode()).hexdigest()[:16]


def anonymise_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in DROP_COLUMNS & set(df.columns):
        df = df.drop(columns=c)
    for c in HASH_COLUMNS & set(df.columns):
        df[c] = df[c].astype(str).map(hash_pid)
    return df


def fetch_qualtrics(survey_id: str) -> pd.DataFrame:
    token = os.environ.get("QUALTRICS_API_TOKEN")
    if not token:
        raise SystemExit("set QUALTRICS_API_TOKEN")
    headers = {"X-API-TOKEN": token, "Content-Type": "application/json"}
    r = requests.post(
        f"{API_BASE}/surveys/{survey_id}/export-responses",
        headers=headers, json={"format": "csv", "useLabels": False, "compress": True},
    )
    r.raise_for_status()
    progress_id = r.json()["result"]["progressId"]
    file_id = None
    for _ in range(60):
        time.sleep(2)
        s = requests.get(f"{API_BASE}/surveys/{survey_id}/export-responses/{progress_id}", headers=headers).json()["result"]
        if s.get("status") == "complete":
            file_id = s["fileId"]; break
        if s.get("status") == "failed":
            raise RuntimeError(str(s))
    if not file_id:
        raise RuntimeError("timed out")
    r = requests.get(f"{API_BASE}/surveys/{survey_id}/export-responses/{file_id}/file", headers=headers)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    name = [n for n in z.namelist() if n.endswith(".csv")][0]
    with z.open(name) as f:
        df = pd.read_csv(f, skiprows=[1, 2])
    return df


def write_codebook(study: str, df: pd.DataFrame) -> None:
    path = OUT_DIR / f"{STUDIES[study]['short']}_codebook.md"
    lines = [f"# Codebook: Study {study}\n"]
    lines.append(f"Source Qualtrics survey: `{STUDIES[study]['qualtrics_id']}`.\n")
    lines.append(f"Rows (after anonymisation): **{len(df)}**.\n\n")
    lines.append("| Column | Non-null rows | Type | Note |\n|---|---|---|---|\n")
    for c in df.columns:
        nn = int(df[c].notna().sum())
        dtype = str(df[c].dtype)
        note = "hashed" if c in HASH_COLUMNS else ""
        lines.append(f"| `{c}` | {nn} | {dtype} | {note} |\n")
    path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--study", default="all",
                   help="one of 1A / 1B / 2 / 3 / all")
    p.add_argument("--csv", default=None,
                   help="use a local CSV instead of fetching")
    args = p.parse_args()

    targets = list(STUDIES.keys()) if args.study == "all" else [args.study]
    for study in targets:
        print(f"[anon] study {study}: {STUDIES[study]['qualtrics_id']}")
        if args.csv and len(targets) == 1:
            df = pd.read_csv(args.csv, skiprows=[1, 2])
        else:
            df = fetch_qualtrics(STUDIES[study]["qualtrics_id"])
        df = anonymise_df(df)
        out = OUT_DIR / f"{STUDIES[study]['short']}_anonymised.csv"
        df.to_csv(out, index=False)
        print(f"  wrote {out} ({len(df)} rows)")
        write_codebook(study, df)
        print(f"  wrote {OUT_DIR / (STUDIES[study]['short'] + '_codebook.md')}")


if __name__ == "__main__":
    main()
