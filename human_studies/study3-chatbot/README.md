# Study 3: Ecological Validity Chatbot

## File Index

### Design
- `STUDY3_ECOLOGICAL_VALIDITY.md` — Master design doc with full architecture, prompt iteration log, test results
- `CHATBOT_IN_QUALTRICS.md` — Earlier research notes on chatbot implementation

### Reference Papers (converted from PDF)
- `costello_debunkbot_science.md` — Costello et al. 2024 (Science). THE gold standard for chatbot-in-survey.
- `costello_debunkbot_supplementary.md` — 61pp supplement with exact prompts (Table S2)
- `tey_chatbot_pnas.md` — Tey et al. 2024 (PNAS Nexus). QSF template source.
- `integrating_openai_chatbot_qualtrics.md` — Tey's tutorial (14pp)
- `Integrating_OpenAI_Chatbot_October_2025.qsf` — Working QSF template (import into Qualtrics)

### Engineering — Self-Contained (ready to deploy)
- `worker/worker.js` — **Standalone Cloudflare Worker**. Independent from dashboard worker. Handles /chat, /logs, /health.
- `worker/wrangler.toml` — Worker config. Just needs Anthropic API key.
- `QUALTRICS_CHATBOT.js` — JavaScript for the Qualtrics chat question. Manages all 3 stages client-side.
- `QUALTRICS_HTML.html` — HTML + CSS for the chat widget. iMessage-style bubbles, responsive.
- `DEPLOY.md` — **Step-by-step deployment guide** with troubleshooting and cost estimates.
- `WORKER_ROUTE.js` — (legacy) Route version for adding to existing worker. Use `worker/` instead.

### Prompt Testing
- `test_master_prompt.py` — Tests Stage 2 (assortment generation) across 20 categories
- `test_stage3_pushback.py` — Tests Stage 3 (pushback handling) with 7 scenarios
- `test_full_pipeline.py` — Tests full end-to-end (Stage 1+2+3) with 5 simulated participants
- `prompt_tests/` — All test results (JSON, full untruncated)

## Deployment Steps

1. **Add Worker route**: Copy `WORKER_ROUTE.js` → add `handleStudy3Chat` function and `case '/study3/chat'` to worker.js switch
2. **Deploy Worker**: `cd dashboard/worker && npx wrangler deploy`
3. **Create Qualtrics survey**: Import `Integrating_OpenAI_Chatbot_October_2025.qsf` as template, OR build from scratch via API
4. **Add chat HTML**: Paste `QUALTRICS_HTML.html` into a DB/TB question's HTML view
5. **Add chat JS**: Paste `QUALTRICS_CHATBOT.js` into the same question's JavaScript editor
6. **Set embedded data**: In survey flow, initialize: study3_session_id, study3_assortment, study3_category, study3_recommended, study3_optimal, study3_conversation_complete, msg_1...msg_20, response_1...response_20, product_1...product_7
7. **Test**: Take the survey yourself, verify conversation works end-to-end
8. **Pilot**: N=10-20 on Prolific

## Test Results Summary

| Test | Result |
|------|--------|
| Stage 2 (assortment gen) | 20/20 categories passed |
| Stage 3 (pushback) | 6/7 maintained, 0/7 broke character |
| Full pipeline (all stages) | 5/5 passed after prompt fixes |

Key fixes applied:
- 0-based indexing in Stage 2 prompt
- Explicit spec grounding in Stage 3 prompt ("FACT: {dom_brand} genuinely HAS better specs")
