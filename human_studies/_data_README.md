# Human studies — anonymised data bundle

Anonymised exports for Studies 1A, 1B, 2, and 3. PROLIFIC_PID, SESSION_ID, and ResponseId are SHA-256-hashed (16-char truncation, salt `spec-resistance-2026`). IP addresses, location data, user-agent strings, and any other PII are stripped.

## Contents

| File | Study | N | Source Qualtrics ID |
|---|---|---|---|
| `study1a_coffee_anonymised.csv` | 1A | 799 | SV_01zhSyavcdjz06G |
| `study1b_earbuds_anonymised.csv` | 1B | 784 | SV_5hvy9y0CICi9lOe |
| `study2_inoculation_anonymised.csv` | 2 | 782 | SV_3PHq8N243mxAr0W |
| `study3_chatbot_anonymised.csv` | 3 | 769 usable (793 collected) | SV_8A33OiyMqjqr5LU |
| `study3_kv_export.json` | 3 | ~4,500 LLM calls | Cloudflare Worker KV |
| `{study}_codebook.md` | | | one codebook per study |

The Study 3 per-participant parsed CSV is mirrored at `human_studies/study3-chatbot/analysis/output/pilot_data_usable.csv` for the Study 3 analysis pipeline. The CSV here is the canonical public artefact.

## Producing the bundle

```bash
# Requires QUALTRICS_API_TOKEN in environment; writes CSVs and codebooks
python scripts/anonymise_human_studies.py --study all

# Single study
python scripts/anonymise_human_studies.py --study 1A

# From a local Qualtrics export CSV
python scripts/anonymise_human_studies.py --study 1A --csv path/to/export.csv
```

## Study 3 KV export

The Study 3 Cloudflare Worker persists every LLM call (system prompt, user message, history, raw response, tokens, latency) to KV for 90 days. To export for long-term preservation:

```bash
TOKEN="$(grep EXPORT_ADMIN_TOKEN human_studies/study3-chatbot/worker/.env.admin | cut -d= -f2)"
curl -s -H "X-Admin-Token: $TOKEN" \
  "https://study3-chatbot.webmarinelli.workers.dev/export?format=json" \
  > data/human_studies/study3_kv_export.json
```

The export preserves all chat transcripts with hashed PROLIFIC_PID.

## Consumed by

- `scripts/qualtrics/analyze_complete_v4.py` (Studies 1A/1B)
- `scripts/qualtrics/analyze_study2.py` (Study 2)
- `human_studies/study3-chatbot/analysis/run_full_analysis.py` (Study 3)
- Supplementary Notes 30, 31, 32, 33
- Figure 9 all panels
