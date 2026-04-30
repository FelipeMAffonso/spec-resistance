# Qualtrics survey definitions

Committed survey definitions for the four pre-registered behavioural studies.

## Contents

| File | Study | Qualtrics ID | Notes |
|---|---|---|---|
| `study3_chatbot_template.qsf` | 3 | SV_8A33OiyMqjqr5LU | Starter template for the interactive chatbot (based on the Tey et al. 2024 reference template). Includes the JavaScript chat widget, embedded-data fields, BlockRandomizer, and belt-and-suspenders Next-button gate. |
| `study1a_coffee.qsf` | 1A | SV_01zhSyavcdjz06G | *(exported on demand — see below)* |
| `study1b_earbuds.qsf` | 1B | SV_5hvy9y0CICi9lOe | *(exported on demand — see below)* |
| `study2_inoculation.qsf` | 2 | SV_3PHq8N243mxAr0W | *(exported on demand — see below)* |

## Also committed (JSON exports)

Archived JSON representations of earlier study designs live at [`../results/qsf_exports/`](../results/qsf_exports/). These are not Qualtrics-importable `.qsf` files (they are JSON API dumps of the survey definitions).

## Exporting a live `.qsf`

```bash
# requires QUALTRICS_API_TOKEN in environment
python -c "
import os, requests
sid = 'SV_01zhSyavcdjz06G'   # Study 1A
tok = os.environ['QUALTRICS_API_TOKEN']
r = requests.post(
    f'https://pdx1.qualtrics.com/API/v3/surveys/{sid}/export-definition',
    headers={'X-API-TOKEN': tok, 'Content-Type': 'application/json'},
    json={'format': 'qsf'}
)
r.raise_for_status()
pid = r.json()['result']['progressId']
import time
for _ in range(60):
    time.sleep(2)
    s = requests.get(f'https://pdx1.qualtrics.com/API/v3/surveys/{sid}/export-definition/{pid}', headers={'X-API-TOKEN': tok}).json()['result']
    if s.get('status') == 'complete': fid = s['fileId']; break
r = requests.get(f'https://pdx1.qualtrics.com/API/v3/surveys/{sid}/export-definition/{fid}/file', headers={'X-API-TOKEN': tok})
open('study1a_coffee.qsf', 'wb').write(r.content)
"
```

Repeat for the other three survey IDs.

## Reproduction

To restore an identical survey:

1. Log into Qualtrics.
2. Go to "Create New Project" → "From a File".
3. Upload the `.qsf` file from this directory.
4. The full survey (questions, flow, BlockRandomizer, embedded data, JavaScript) will be re-created in your workspace.

## Study 3 chatbot dependencies

The Study 3 template requires the associated Cloudflare Worker and chat-widget JavaScript from `human_studies/study3-chatbot/`:

- `QUALTRICS_HTML.html` — chat container HTML with all four AI brand skins.
- `QUALTRICS_CHATBOT.js` — addOnReady handler with the belt-and-suspenders Next-button gate.
- `BRAND_SKINS.js` — per-skin colour palettes and logos.
- `worker/worker.js` — Anthropic Opus proxy deployed at `study3-chatbot.webmarinelli.workers.dev`.

See [`human_studies/study3-chatbot/DEPLOY.md`](../study3-chatbot/DEPLOY.md) for the full deployment walkthrough.
