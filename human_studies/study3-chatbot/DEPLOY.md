# Study 3 Chatbot — Deployment Guide

## Prerequisites
- Node.js installed
- Cloudflare account (free tier works)
- Anthropic API key
- Qualtrics account with survey builder access

## Step 1: Deploy the Worker

```bash
cd study3-chatbot/worker

# Install wrangler (if not already)
npm install -g wrangler

# Login to Cloudflare (first time only)
npx wrangler login

# Set the Anthropic API key as a secret
npx wrangler secret put ANTHROPIC_API_KEY
# (paste your Anthropic API key when prompted)

# Optional: Create KV namespace for conversation logs
npx wrangler kv namespace create STUDY3_LOGS
# Copy the ID from output, paste into wrangler.toml (uncomment the [[kv_namespaces]] section)

# Deploy
npx wrangler deploy
```

After deployment, you'll get a URL like:
`https://study3-chatbot.webmarinelli.workers.dev`

Test it:
```bash
curl https://study3-chatbot.webmarinelli.workers.dev/health
```

Should return:
```json
{"ok": true, "service": "study3-chatbot", "hasAnthropicKey": true}
```

## Step 2: Update the Qualtrics JS

Open `QUALTRICS_CHATBOT.js` and change line 10:
```javascript
var PROXY_URL = 'https://study3-chatbot.webmarinelli.workers.dev/chat';
```

## Step 3: Build the Qualtrics Survey

### Option A: Import QSF template + modify
1. Import `Integrating_OpenAI_Chatbot_October_2025.qsf` into Qualtrics
2. Replace the question HTML with contents of `QUALTRICS_HTML.html`
3. Replace the question JavaScript with contents of `QUALTRICS_CHATBOT.js`
4. Add embedded data fields in the survey flow (see list below)

### Option B: Build from scratch
1. Create new survey in Qualtrics
2. Add consent question (MC)
3. Add a DB/TB question for the chatbot:
   - HTML View: paste `QUALTRICS_HTML.html`
   - JavaScript: paste `QUALTRICS_CHATBOT.js`
4. Add product choice question (MC) — choices will be piped from embedded data
5. Add choice reason (TE)
6. Add demographics (age, gender, AI usage)

### Embedded Data Fields (set in survey flow BEFORE chat block)
Initialize ALL of these with empty values:

**Session:**
- study3_session_id
- study3_conversation_complete
- study3_total_turns

**Assortment (set by chatbot JS):**
- study3_assortment (full JSON)
- study3_category
- study3_recommended
- study3_optimal

**Products (set by chatbot JS, for piping into choice question):**
- product_1, product_2, product_3, product_4, product_5, product_6, product_7

**Conversation transcript:**
- msg_1 through msg_20
- response_1 through response_20

## Step 4: Test

1. Preview the survey in Qualtrics
2. Type a shopping request (e.g., "I need running shoes for trail running")
3. Answer the clarifying question
4. Wait for "Searching products..." (3-5 seconds)
5. Verify: product table appears, AI makes a recommendation
6. Ask a follow-up ("What about [the cheaper one]?")
7. Verify: AI maintains recommendation with brand-trust reasoning
8. Click "Ready to choose" → verify choice page shows the generated products
9. Complete the survey → export CSV → verify all embedded data populated

## Step 5: Pilot on Prolific

1. Set EOSRedirectURL in Qualtrics to Prolific completion URL
2. Create Prolific study: N=10-20, $5/person, ~10 min, desktop only
3. Monitor: check /health endpoint, check Qualtrics responses
4. Review conversation logs: `curl https://study3-chatbot.webmarinelli.workers.dev/logs/SESSION_ID`

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "AI service error" | Check ANTHROPIC_API_KEY is set: `npx wrangler secret list` |
| Chat doesn't load | Check browser console for CORS errors. Verify PROXY_URL in JS. |
| "Searching products..." hangs | Opus generation takes 25-30s. If >60s, check worker logs: `npx wrangler tail` |
| Product table doesn't render | Check that bot messages with `<table` use innerHTML, not textContent |
| Embedded data empty | Verify embedded data fields are initialized in survey flow BEFORE the chat block |
| JSON parse error in Stage 2 | Opus sometimes wraps JSON in markdown. The JS extracts with regex. |

## Cost Estimate

Per participant (estimated):
- Stage 1 (2 turns): ~$0.02 (Opus, ~500 input + 200 output tokens per turn)
- Stage 2 (1 generation): ~$0.15 (Opus, ~1000 input + 3000 output tokens)
- Stage 3 (3 turns): ~$0.10 (Opus, ~2000 input + 500 output tokens per turn)
- **Total: ~$0.27 per participant**

For N=300: ~$81 in API costs + Prolific compensation.

## Architecture Diagram

```
[Prolific Participant]
        |
        v
[Qualtrics Survey Page]
  - HTML chat widget
  - JavaScript manages stages
        |
        | POST /chat {stage, message, history}
        v
[Cloudflare Worker: study3-chatbot]
  - Validates request
  - Selects system prompt by stage
  - Rate limits by IP
        |
        | POST /v1/messages
        v
[Anthropic API: Claude Opus 4.6]
  - Stage 1: conversational elicitation
  - Stage 2: JSON assortment generation
  - Stage 3: biased recommendation + follow-up
        |
        v
[Response flows back]
  Worker → Qualtrics JS → Chat UI → Embedded Data
        |
        v
[Qualtrics Export: CSV with all conversation data]
```
