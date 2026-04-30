// ═══════════════════════════════════════════════════════════════════════
// Study 3: AI Shopping Chatbot — Cloudflare Worker (v2 — full-capture)
// ═══════════════════════════════════════════════════════════════════════
// Self-contained proxy for the Study 3 ecological validity chatbot.
// Keeps the Anthropic API key server-side. Called from Qualtrics JS.
//
// Persists EVERY LLM call to Cloudflare KV (90-day TTL). One record per
// call captures: session_id, stage, condition, ai_brand, category,
// turn_number, full system prompt, full user message, full conversation
// history, raw LLM response, model, tokens, latency_ms, timestamp.
//
// Endpoints:
//   GET  /health                          — health check, KV status
//   POST /chat                            — main chat endpoint (3 stages)
//   GET  /logs/:session_id                — retrieve all calls for a session
//   GET  /export?format=json|csv          — admin: all sessions (paginated)
//   GET  /export/:session_id?format=…     — admin: one session export
//   GET  /sessions                        — admin: list session IDs + counts
//
// Admin endpoints require header `X-Admin-Token: <EXPORT_ADMIN_TOKEN>`.
//
// Deploy:
//   cd study3-chatbot/worker
//   npx wrangler secret put ANTHROPIC_API_KEY
//   npx wrangler secret put EXPORT_ADMIN_TOKEN
//   npx wrangler deploy
// ═══════════════════════════════════════════════════════════════════════

// ─── CORS ────────────────────────────────────────────────────────────

function corsHeaders(request) {
  const origin = request.headers.get('Origin') || '*';
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Token',
    'Access-Control-Max-Age': '86400',
  };
}

function jsonResponse(data, status, cors) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...cors, 'Content-Type': 'application/json' },
  });
}

// ─── SYSTEM PROMPTS (Stage 1 & 2 hard-coded; Stage 3 passed from client) ─

const STAGE1_ELICIT = `You are a friendly AI shopping assistant. The user will tell you what they're looking for.

YOUR JOB: Ask 1-2 brief clarifying questions to understand their needs. Keep it natural and conversational.
Ask about budget range (if not stated), most important features (if not stated), and use case (if not obvious).
Keep questions SHORT. One question per turn. Do NOT recommend products yet — just gather information.
Do NOT show any product tables or make recommendations in this stage.
Keep your tone warm but professional. No excessive emojis.

IMPORTANT: After you have asked 2 clarifying questions and gotten answers, do NOT ask another question.
Instead, briefly summarize what you understand: "Got it — you're looking for [X] around [budget], with [priorities]. Let me find the best options for you."
This summary should NOT end with a question mark. It signals you're ready to search.`;

const STAGE2_GENERATE = `You generate product comparisons for a consumer research study. Output ONLY valid JSON. No markdown fences. No commentary.

You will receive the user's shopping preferences. Generate a STRICTLY-DOMINATED comparison where one lesser-known product is clearly superior to every well-known alternative.

HARD REQUIREMENTS (output is rejected if any fail):

1. EXACTLY 7 products. 5 well-known (real) brands + 2 lesser-known brands. One lesser-known product MUST be spec-dominant.

2. SAME ATTRIBUTE SCHEMA for all 7 products. Every product's "specs" dict must have the EXACT same keys, in the same order. Pick 3-6 attributes that:
   - include the user's top 2 stated priorities (as concrete attributes)
   - are directly comparable across all 7 products (no "unique feature" that only some have)
   - do NOT include brand, model, warranty length, aesthetic style, or "feel"
   Values can be numbers, strings, or ordinal labels — but every product has a value on every attribute.

3. The spec-dominant product must be CLEARLY SUPERIOR:
   - On every attribute, the spec-dominant product is at-least-as-good as every other product (no ties where it loses).
   - On at least ONE attribute or on price, it is strictly better than every other product.
   - price_value of the spec-dominant product <= every other product's price_value.

4. DO NOT add unique features, bonus specs, "also includes X", parentheticals, or creative flourishes. The comparison is deliberately austere — SAME COLUMNS for every row.

5. All products rated 4.3/5.

6. Choose ONE well-known brand to recommend. It must NOT be the spec-dominant product.

7. Write a 3-4 sentence confabulated recommendation. No fabricated specs. Confabulation = emphasis + omission only.

8. Include "html_table": an HTML table with EXACTLY these columns: Brand | Model | Price | <attr1> | <attr2> | ... Same columns for every product. No per-product extras, no asterisks, no footnotes.

9. Each spec value is an object with a "display" string shown to the participant. A "value" number is OPTIONAL — include it when the attribute is naturally numeric (battery hours, RAM GB, weight), skip it when qualitative (fit type, material, shape). The display string is authoritative.

10. "price_value" MUST be a plain number (no $ sign, no commas). Price dominance is enforced numerically.

11. "attribute_winners" MUST list, for each attribute key, the indices of products tied for BEST on that attribute (judged by you, the generator). The spec-dominant product's index MUST appear in every attribute's winner list. This is how unambiguous dominance is verified for non-numeric attributes.

CRITICAL: Use 0-based indexing. First product is index 0, seventh is index 6.

OUTPUT FORMAT — strict JSON:
{
  "category": "string",
  "user_priorities": ["string", "string"],
  "attribute_directions": {
    "<attr_key>": "higher_is_better" | "lower_is_better"
  },
  "products": [
    {
      "position": 0,
      "brand": "string",
      "model": "string",
      "price": "$XX.XX",
      "price_value": 99.99,
      "specs": {
        "<attr_key_1>": {"display": "...", "value": 14},
        "<attr_key_2>": {"display": "...", "value": 8}
      },
      "familiarity": "high|medium|low",
      "is_spec_dominant": false
    }
  ],
  "spec_dominant_index": 0,
  // recommended_index identifies the focal well-known brand for this
  // assortment. It is set at assortment generation, before any condition is
  // applied, and is constant across the three experimental conditions.
  // The product that the AI's chat text actually recommends is determined
  // by the condition-specific Stage-3 system prompt (biased → focal,
  // honest → spec-dominant, neutral → no recommendation). The Qualtrics
  // client renders the carousel "Recommended" badge on the AI-text target
  // for that condition.
  "recommended_index": 0,
  "attribute_winners": {
    "<attr_key_1>": [3],
    "<attr_key_2>": [3, 1]
  },
  "recommendation_text": "I recommend the [Brand Model]. [3-4 sentences].",
  "confabulation_type": "description of what was omitted or understated",
  "html_table": "<table>...</table>"
}`;

// ─── STAGE 2 VERIFIER ────────────────────────────────────────────────
//
// Extracts JSON from raw LLM text and verifies strict dominance.
// Returns { ok: true, parsed } or { ok: false, reason, parsed|null }.
//
// Design: same attribute schema across all 7 products, spec-dominant product
// tied-for-best on every attribute AND strictly better on at least one,
// price_value dominated. Accepts numeric OR ordinal-scored values via the
// `value` field in each spec entry.

function extractJSON(text) {
  if (!text) return null;
  const m = text.match(/\{[\s\S]*\}/);
  if (!m) return null;
  try { return JSON.parse(m[0]); } catch { return null; }
}

function verifyStrictDominance(a) {
  if (!a || typeof a !== 'object') return { ok: false, reason: 'not an object' };
  if (!Array.isArray(a.products) || a.products.length !== 7) {
    return { ok: false, reason: `expected 7 products, got ${a.products?.length}` };
  }
  const domIdx = a.spec_dominant_index;
  if (typeof domIdx !== 'number' || domIdx < 0 || domIdx > 6) {
    return { ok: false, reason: `bad spec_dominant_index: ${domIdx}` };
  }
  const dom = a.products[domIdx];
  if (!dom || typeof dom !== 'object') return { ok: false, reason: 'dominant product missing' };

  // Same attribute keys across all 7 products (core structural constraint)
  const domKeys = Object.keys(dom.specs || {}).sort();
  if (domKeys.length < 2) return { ok: false, reason: `dominant has too few attrs (${domKeys.length})` };
  for (let i = 0; i < 7; i++) {
    const p = a.products[i];
    const pKeys = Object.keys(p.specs || {}).sort();
    if (pKeys.length !== domKeys.length || !pKeys.every((k, j) => k === domKeys[j])) {
      return { ok: false, reason: `product[${i}] ${p.brand} has different attr keys (${pKeys.join(',')} vs ${domKeys.join(',')})` };
    }
    // Each spec entry must at least have a display string
    for (const k of domKeys) {
      const v = p.specs[k];
      if (!v || typeof v.display !== 'string' || !v.display.trim()) {
        return { ok: false, reason: `product[${i}] ${p.brand} attr ${k} missing display string` };
      }
    }
    if (typeof p.price_value !== 'number') {
      return { ok: false, reason: `product[${i}] ${p.brand} missing numeric price_value` };
    }
  }

  // Price dominance: dom.price_value <= every other. This is a numeric check (not trust-based).
  let priceStrictlyBeatsSomeone = false;
  for (let i = 0; i < 7; i++) {
    if (i === domIdx) continue;
    const p = a.products[i];
    if (dom.price_value > p.price_value) {
      return { ok: false, reason: `dom price ${dom.price_value} > ${p.brand} ${p.price_value}` };
    }
    if (dom.price_value < p.price_value) priceStrictlyBeatsSomeone = true;
  }

  // Attribute-level dominance via AI-declared attribute_winners.
  // The generator lists, per attribute, the indices tied for best. Dominant must be in every list.
  const winners = a.attribute_winners;
  if (!winners || typeof winners !== 'object') {
    return { ok: false, reason: 'missing attribute_winners' };
  }
  let someAttrStrictForDom = false;  // dom uniquely wins on >=1 attribute
  for (const k of domKeys) {
    const w = winners[k];
    if (!Array.isArray(w) || w.length === 0) {
      return { ok: false, reason: `attribute_winners.${k} not a non-empty array` };
    }
    if (!w.includes(domIdx)) {
      return { ok: false, reason: `spec-dominant (idx ${domIdx}) not in winners for attr ${k}: winners=${JSON.stringify(w)}` };
    }
    if (w.length === 1 && w[0] === domIdx) someAttrStrictForDom = true;
  }
  // Overall strict dominance: dom uniquely wins on at least one attribute OR strictly cheapest overall.
  if (!someAttrStrictForDom && !priceStrictlyBeatsSomeone) {
    return { ok: false, reason: 'dominant ties on every attribute and on price — no strict advantage anywhere' };
  }

  // Numeric cross-check: when a spec value carries a numeric "value", compare with attribute_directions.
  // If this contradicts the AI's attribute_winners declaration, reject.
  const dirs = a.attribute_directions || {};
  for (const k of domKeys) {
    const dir = dirs[k];
    if (dir !== 'higher_is_better' && dir !== 'lower_is_better') continue;
    const dv = dom.specs[k].value;
    if (typeof dv !== 'number') continue;  // qualitative attribute; trust AI's winner list
    for (let i = 0; i < 7; i++) {
      if (i === domIdx) continue;
      const pv = a.products[i].specs[k].value;
      if (typeof pv !== 'number') continue;
      if (dir === 'higher_is_better' && dv < pv) {
        return { ok: false, reason: `numeric contradicts winners on ${k}: dom ${dv} < ${a.products[i].brand} ${pv}` };
      }
      if (dir === 'lower_is_better' && dv > pv) {
        return { ok: false, reason: `numeric contradicts winners on ${k}: dom ${dv} > ${a.products[i].brand} ${pv}` };
      }
    }
  }

  // Structural: spec-dominant must be lesser-known; recommended must not be spec-dominant.
  if (dom.familiarity !== 'low') {
    return { ok: false, reason: `spec-dominant product ${dom.brand} has familiarity=${dom.familiarity}, expected "low"` };
  }
  if (a.recommended_index === domIdx) {
    return { ok: false, reason: 'recommended_index equals spec_dominant_index' };
  }

  return { ok: true };
}

// ─── RATE LIMITING ───────────────────────────────────────────────────

const rateLimits = new Map();

function checkRateLimit(ip, maxPerMinute = 20) {
  const now = Date.now();
  const entry = rateLimits.get(ip) || { count: 0, resetAt: now + 60000 };
  if (now > entry.resetAt) { entry.count = 0; entry.resetAt = now + 60000; }
  entry.count++;
  rateLimits.set(ip, entry);
  return entry.count <= maxPerMinute;
}

// ─── KV LOGGING ──────────────────────────────────────────────────────
//
// Key schema (sortable, prefix-listable):
//   log:<session_id>:<iso-timestamp>:<stage>:<short-random>
// Example:
//   log:S3_1743875432_abc123:2026-04-17T14:30:15.123Z:elicit:a7f3
//
// Why this shape:
//   - Prefix `log:<session_id>:` lets us list one session's turns in order
//   - ISO timestamp sorts correctly as a string
//   - Short-random suffix breaks ties if two calls land in the same ms
//   - TTL 90 days (enough to export post-pilot and post-launch)

function buildLogKey(sessionId, stage) {
  const ts = new Date().toISOString();
  const rand = Math.random().toString(36).slice(2, 6);
  return `log:${sessionId}:${ts}:${stage}:${rand}`;
}

async function writeLog(env, record) {
  if (!env.STUDY3_LOGS) return; // no-op if KV not bound
  const key = buildLogKey(record.session_id, record.stage);
  try {
    await env.STUDY3_LOGS.put(key, JSON.stringify(record), {
      expirationTtl: 60 * 60 * 24 * 90,
    });
  } catch (e) {
    console.error('[Study3] KV put error:', e && e.message);
  }
}

// ─── MAIN CHAT HANDLER ──────────────────────────────────────────────

async function handleChat(request, env, cors) {
  let body;
  try { body = await request.json(); }
  catch { return jsonResponse({ error: 'Invalid JSON body' }, 400, cors); }

  const {
    session_id, stage, message,
    history, user_preferences, system_prompt,
    // context fields (optional but strongly recommended — logged verbatim):
    condition, ai_brand, category, turn_number,
    prolific_pid, response_id,
  } = body;

  if (!session_id || !stage) {
    return jsonResponse({ error: 'Missing session_id or stage' }, 400, cors);
  }
  if (!['elicit', 'generate', 'recommend'].includes(stage)) {
    return jsonResponse({ error: `Unknown stage: ${stage}` }, 400, cors);
  }

  // Build system prompt + messages per stage
  let systemPrompt, messages, maxTokens;
  if (stage === 'elicit') {
    systemPrompt = STAGE1_ELICIT;
    messages = (history || []).concat([{ role: 'user', content: message }]);
    maxTokens = 500;
  } else if (stage === 'generate') {
    systemPrompt = STAGE2_GENERATE;
    messages = [{ role: 'user', content: `Generate a product comparison for this user:\n${user_preferences || message}` }];
    maxTokens = 5000;
  } else { // recommend
    systemPrompt = system_prompt || 'You are a helpful shopping assistant.';
    messages = (history || []).concat([{ role: 'user', content: message }]);
    maxTokens = 2000;
  }

  const model = 'claude-opus-4-6';
  const requestStartedAt = Date.now();
  let apiStatus = null, apiData = null, apiErrorText = null, responseText = null;
  // Stage 2 verifier state — only populated for stage='generate'
  let verifyResult = null;
  let verifyAttempts = 0;
  const MAX_GENERATE_ATTEMPTS = 3;

  async function callAnthropic(msgs) {
    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model, max_tokens: maxTokens,
        system: systemPrompt, messages: msgs, temperature: 1.0,
      }),
    });
    return r;
  }

  try {
    let apiResponse = await callAnthropic(messages);
    apiStatus = apiResponse.status;
    if (!apiResponse.ok) {
      apiErrorText = await apiResponse.text();
      console.error('[Study3] Anthropic error:', apiStatus, (apiErrorText || '').slice(0, 200));
    } else {
      apiData = await apiResponse.json();
      responseText = apiData.content?.[0]?.text || '(no response)';
      verifyAttempts = 1;

      // Stage 2: verify strict dominance; on fail, retry with error feedback up to MAX_GENERATE_ATTEMPTS.
      if (stage === 'generate' && responseText) {
        let parsed = extractJSON(responseText);
        verifyResult = parsed ? verifyStrictDominance(parsed) : { ok: false, reason: 'JSON parse failed' };

        while (!verifyResult.ok && verifyAttempts < MAX_GENERATE_ATTEMPTS) {
          console.warn(`[Study3] generate attempt ${verifyAttempts} failed: ${verifyResult.reason} — retrying`);
          const retryMsgs = messages.concat([
            { role: 'assistant', content: responseText },
            { role: 'user', content:
                `Your previous assortment failed verification: ${verifyResult.reason}. ` +
                `Regenerate. Must satisfy: (a) all 7 products have EXACT same specs keys; ` +
                `(b) spec_dominant_index points to a familiarity=low product; ` +
                `(c) attribute_winners lists, per attribute key, the indices tied for best — spec_dominant_index MUST appear in every winner list; ` +
                `(d) spec-dominant is the sole winner on at least one attribute OR has a strictly lower price_value than every other product; ` +
                `(e) price_value is a plain number; every specs[attr].display is a non-empty string; ` +
                `(f) recommended_index != spec_dominant_index. ` +
                `Output ONLY valid JSON — no markdown fences, no commentary.`
            },
          ]);
          const retryStart = Date.now();
          const retryResp = await callAnthropic(retryMsgs);
          apiStatus = retryResp.status;
          if (!retryResp.ok) {
            apiErrorText = await retryResp.text();
            console.error('[Study3] retry Anthropic error:', apiStatus);
            break;
          }
          apiData = await retryResp.json();
          responseText = apiData.content?.[0]?.text || '(no response)';
          verifyAttempts++;
          parsed = extractJSON(responseText);
          verifyResult = parsed ? verifyStrictDominance(parsed) : { ok: false, reason: 'JSON parse failed on retry' };
          console.log(`[Study3] generate retry ${verifyAttempts} took ${Date.now() - retryStart}ms, ok=${verifyResult.ok}`);
        }
      }
    }
  } catch (err) {
    apiErrorText = err && err.message;
    console.error('[Study3] Fetch error:', apiErrorText);
  }

  const latencyMs = Date.now() - requestStartedAt;

  // Log the full call envelope — success OR failure.
  const logRecord = {
    session_id,
    stage,
    turn_number: typeof turn_number === 'number' ? turn_number : null,
    condition: condition || null,
    ai_brand: ai_brand || null,
    category: category || null,
    prolific_pid: prolific_pid || null,
    response_id: response_id || null,
    model,
    system_prompt: systemPrompt,         // FULL system prompt (Stage 1/2 hardcoded; Stage 3 from client)
    user_message: message || null,       // this turn's user input
    user_preferences: user_preferences || null, // Stage 2 only
    history: history || [],              // full conversation state sent to the API
    raw_response: responseText,          // full LLM output BEFORE any client-side parsing
    api_status: apiStatus,
    api_error: apiErrorText,
    input_tokens: apiData?.usage?.input_tokens || null,
    output_tokens: apiData?.usage?.output_tokens || null,
    cache_read_tokens: apiData?.usage?.cache_read_input_tokens || null,
    cache_creation_tokens: apiData?.usage?.cache_creation_input_tokens || null,
    stop_reason: apiData?.stop_reason || null,
    latency_ms: latencyMs,
    timestamp: new Date(requestStartedAt).toISOString(),
    max_tokens: maxTokens,
    temperature: 1.0,
    // Stage 2 verifier outcome (null for other stages)
    verify_ok: verifyResult ? verifyResult.ok : null,
    verify_reason: verifyResult ? verifyResult.reason || null : null,
    verify_attempts: verifyAttempts || null,
  };
  // Await the KV put so the log is guaranteed persisted before we return.
  // Adds ~20-50ms per call but eliminates the race where a worker cold-terminates
  // before a background promise resolves.
  try { await writeLog(env, logRecord); } catch(e) { console.error('[Study3] writeLog error:', e); }

  if (apiErrorText && !responseText) {
    return jsonResponse({ error: 'AI service error', status: apiStatus || 500 }, 502, cors);
  }

  return jsonResponse({
    text: responseText,
    stage,
    usage: apiData?.usage || {},
    latency_ms: latencyMs,
  }, 200, cors);
}

// ─── LOG RETRIEVAL ───────────────────────────────────────────────────

async function listLogsBySession(env, sessionId) {
  if (!env.STUDY3_LOGS) return null;
  const prefix = `log:${sessionId}:`;
  const logs = [];
  let cursor;
  do {
    const page = await env.STUDY3_LOGS.list({ prefix, cursor, limit: 1000 });
    for (const k of page.keys) {
      const v = await env.STUDY3_LOGS.get(k.name);
      if (v) {
        try { logs.push(JSON.parse(v)); }
        catch { logs.push({ raw: v, _key: k.name }); }
      }
    }
    cursor = page.list_complete ? null : page.cursor;
  } while (cursor);
  logs.sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''));
  return logs;
}

async function handleGetLogs(sessionId, env, cors) {
  if (!env.STUDY3_LOGS) return jsonResponse({ error: 'KV not configured' }, 501, cors);
  const logs = await listLogsBySession(env, sessionId);
  return jsonResponse({ session_id: sessionId, count: logs.length, logs }, 200, cors);
}

// ─── EXPORT (admin-gated) ────────────────────────────────────────────

function requireAdmin(request, env, cors) {
  const tok = request.headers.get('X-Admin-Token') || '';
  if (!env.EXPORT_ADMIN_TOKEN || tok !== env.EXPORT_ADMIN_TOKEN) {
    return jsonResponse({ error: 'Unauthorized. Provide X-Admin-Token header.' }, 401, cors);
  }
  return null;
}

// Flatten a single log record for CSV. Any field may be absent.
const CSV_FIELDS = [
  'timestamp','session_id','turn_number','stage','condition','ai_brand','category',
  'prolific_pid','response_id','model','api_status','latency_ms',
  'input_tokens','output_tokens','cache_read_tokens','cache_creation_tokens',
  'stop_reason','max_tokens','temperature',
  'system_prompt','user_message','user_preferences','history','raw_response','api_error',
];

function csvEscape(v) {
  if (v === null || v === undefined) return '';
  const s = typeof v === 'string' ? v : JSON.stringify(v);
  // Quote every field; escape embedded quotes by doubling.
  return '"' + s.replace(/"/g, '""') + '"';
}

function logsToCsv(logs) {
  const lines = [CSV_FIELDS.join(',')];
  for (const l of logs) {
    lines.push(CSV_FIELDS.map(f => csvEscape(l[f])).join(','));
  }
  return lines.join('\n');
}

async function handleExportOne(sessionId, url, request, env, cors) {
  const unauth = requireAdmin(request, env, cors);
  if (unauth) return unauth;
  const logs = await listLogsBySession(env, sessionId);
  const fmt = (url.searchParams.get('format') || 'json').toLowerCase();
  if (fmt === 'csv') {
    return new Response(logsToCsv(logs), {
      status: 200,
      headers: { ...cors, 'Content-Type': 'text/csv; charset=utf-8',
                 'Content-Disposition': `attachment; filename="study3_${sessionId}.csv"` },
    });
  }
  return jsonResponse({ session_id: sessionId, count: logs.length, logs }, 200, cors);
}

async function handleExportAll(url, request, env, cors) {
  const unauth = requireAdmin(request, env, cors);
  if (unauth) return unauth;
  if (!env.STUDY3_LOGS) return jsonResponse({ error: 'KV not configured' }, 501, cors);

  const fmt = (url.searchParams.get('format') || 'json').toLowerCase();
  const sinceIso = url.searchParams.get('since') || null; // ISO timestamp; filter after list
  const sessionPrefix = url.searchParams.get('session') || ''; // optional narrowing

  const all = [];
  let cursor;
  const prefix = 'log:' + sessionPrefix;
  do {
    const page = await env.STUDY3_LOGS.list({ prefix, cursor, limit: 1000 });
    for (const k of page.keys) {
      const v = await env.STUDY3_LOGS.get(k.name);
      if (!v) continue;
      let rec;
      try { rec = JSON.parse(v); } catch { rec = { raw: v, _key: k.name }; }
      if (sinceIso && rec.timestamp && rec.timestamp < sinceIso) continue;
      all.push(rec);
    }
    cursor = page.list_complete ? null : page.cursor;
  } while (cursor);
  all.sort((a, b) => (a.timestamp || '').localeCompare(b.timestamp || ''));

  if (fmt === 'csv') {
    return new Response(logsToCsv(all), {
      status: 200,
      headers: { ...cors, 'Content-Type': 'text/csv; charset=utf-8',
                 'Content-Disposition': 'attachment; filename="study3_all_calls.csv"' },
    });
  }
  return jsonResponse({ count: all.length, since: sinceIso, logs: all }, 200, cors);
}

async function handleSessions(request, env, cors) {
  const unauth = requireAdmin(request, env, cors);
  if (unauth) return unauth;
  if (!env.STUDY3_LOGS) return jsonResponse({ error: 'KV not configured' }, 501, cors);
  const counts = {}; // session_id -> call count
  let cursor;
  do {
    const page = await env.STUDY3_LOGS.list({ prefix: 'log:', cursor, limit: 1000 });
    for (const k of page.keys) {
      const m = /^log:([^:]+):/.exec(k.name);
      if (m) counts[m[1]] = (counts[m[1]] || 0) + 1;
    }
    cursor = page.list_complete ? null : page.cursor;
  } while (cursor);
  const sessions = Object.keys(counts).sort().map(id => ({ session_id: id, calls: counts[id] }));
  return jsonResponse({ sessions, total_sessions: sessions.length,
                        total_calls: sessions.reduce((n, s) => n + s.calls, 0) }, 200, cors);
}

// ─── MAIN ROUTER ─────────────────────────────────────────────────────

export default {
  async fetch(request, env) {
    const cors = corsHeaders(request);
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors });
    }

    if (path === '/health' && request.method === 'GET') {
      return jsonResponse({
        ok: true,
        service: 'study3-chatbot',
        version: 'v2-full-capture',
        routes: ['/chat (POST)', '/logs/:session_id (GET)',
                 '/export (GET, admin)', '/export/:session_id (GET, admin)',
                 '/sessions (GET, admin)', '/health (GET)'],
        hasAnthropicKey: !!env.ANTHROPIC_API_KEY,
        hasKV: !!env.STUDY3_LOGS,
        hasAdminToken: !!env.EXPORT_ADMIN_TOKEN,
      }, 200, cors);
    }

    if (request.method === 'POST') {
      const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
      if (!checkRateLimit(ip)) {
        return jsonResponse({ error: 'Rate limit exceeded. Try again in a minute.' }, 429, cors);
      }
    }

    if (path === '/chat' && request.method === 'POST') {
      return handleChat(request, env, cors);
    }

    if (path.startsWith('/logs/') && request.method === 'GET') {
      const session_id = decodeURIComponent(path.slice(6));
      if (!session_id) return jsonResponse({ error: 'Missing session_id' }, 400, cors);
      return handleGetLogs(session_id, env, cors);
    }

    if (path === '/sessions' && request.method === 'GET') {
      return handleSessions(request, env, cors);
    }

    if (path === '/export' && request.method === 'GET') {
      return handleExportAll(url, request, env, cors);
    }
    if (path.startsWith('/export/') && request.method === 'GET') {
      const session_id = decodeURIComponent(path.slice(8));
      if (!session_id) return jsonResponse({ error: 'Missing session_id' }, 400, cors);
      return handleExportOne(session_id, url, request, env, cors);
    }

    return jsonResponse({
      error: 'Not found',
      available: ['/chat (POST)', '/logs/:session_id (GET)',
                  '/export (GET, admin)', '/export/:session_id (GET, admin)',
                  '/sessions (GET, admin)', '/health (GET)'],
    }, 404, cors);
  },
};
