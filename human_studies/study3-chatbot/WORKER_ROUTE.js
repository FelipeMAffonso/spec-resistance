// ─── Study 3: AI Shopping Chatbot Route ────────────────────────────────
// Add this case to the POST switch in worker.js:
//   case '/study3/chat': return handleStudy3Chat(request, env, cors);
//
// This handles all 3 stages of the chatbot conversation.
// API key stays server-side. Qualtrics JS calls this endpoint.
// ────────────────────────────────────────────────────────────────────────

async function handleStudy3Chat(request, env, cors) {
  try {
    const body = await request.json();
    const { session_id, stage, message, history, user_preferences } = body;

    if (!session_id || !stage) {
      return jsonResponse({ error: 'Missing session_id or stage' }, 400, cors);
    }

    let systemPrompt = '';
    let messages = [];
    let metadata = {};

    // ── STAGE 1: Preference Elicitation ──────────────────────────────
    if (stage === 'elicit') {
      systemPrompt = `You are a friendly AI shopping assistant. The user will tell you what they're looking for.

YOUR JOB: Ask 1-2 brief clarifying questions to understand their needs. Keep it natural and conversational.
Ask about budget range (if not stated), most important features (if not stated), and use case (if not obvious).
Keep questions SHORT. One question per turn. Do NOT recommend products yet — just gather information.
Do NOT show any product tables or make recommendations in this stage.`;

      messages = (history || []).concat([{ role: 'user', content: message }]);
    }

    // ── STAGE 2: Assortment Generation (hidden from user) ────────────
    else if (stage === 'generate') {
      systemPrompt = `You generate product comparisons for a consumer research study. Output ONLY valid JSON.

You will receive a user's shopping preferences. Generate a realistic product comparison.

REQUIREMENTS:
1. Exactly 7 products: 5 well-known brands + 2 lesser-known (1 must be spec-dominant)
2. The spec-dominant product must beat the recommended product on the user's top 2 priorities AND cost equal or less
3. All products rated 4.3/5
4. Choose a well-known brand to recommend (NOT the spec-dominant one)
5. Write a 3-4 sentence confabulated justification
6. Self-verify before outputting
7. Include an "html_table" field with a full HTML table ready to display

CRITICAL: Use 0-based indexing. The first product is index 0, the seventh is index 6.

OUTPUT: Valid JSON with fields: category, user_priorities, products (array of 7 with brand/model/price/specs/familiarity/is_spec_dominant), spec_dominant_index, recommended_index, recommendation_text, confabulation_type, html_table, verification`;

      messages = [{ role: 'user', content: `Generate a product comparison for this user:\n${user_preferences || message}` }];
    }

    // ── STAGE 3: Recommendation + Follow-up ──────────────────────────
    else if (stage === 'recommend') {
      // The system prompt is passed from the client (assembled with assortment data)
      systemPrompt = body.system_prompt || 'You are a helpful shopping assistant.';
      messages = (history || []).concat([{ role: 'user', content: message }]);
    }

    else {
      return jsonResponse({ error: `Unknown stage: ${stage}` }, 400, cors);
    }

    // ── Call Claude Opus ─────────────────────────────────────────────
    const apiResponse = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-opus-4-6',
        max_tokens: stage === 'generate' ? 5000 : 2000,
        system: systemPrompt,
        messages: messages,
        temperature: 1.0,
      }),
    });

    if (!apiResponse.ok) {
      const errText = await apiResponse.text();
      console.error('[Study3] Anthropic API error:', apiResponse.status, errText);
      return jsonResponse({ error: 'AI service error', status: apiResponse.status }, 502, cors);
    }

    const apiData = await apiResponse.json();
    const text = apiData.content?.[0]?.text || '(no response)';

    // ── Log to KV (if available) ─────────────────────────────────────
    if (env.STUDY3_KV) {
      const logKey = `study3:${session_id}:${Date.now()}`;
      await env.STUDY3_KV.put(logKey, JSON.stringify({
        session_id, stage, message, response: text,
        timestamp: new Date().toISOString(),
        input_tokens: apiData.usage?.input_tokens,
        output_tokens: apiData.usage?.output_tokens,
      }), { expirationTtl: 60 * 60 * 24 * 90 }); // 90 days
    }

    // ── Return response ──────────────────────────────────────────────
    return jsonResponse({
      text: text,
      stage: stage,
      usage: apiData.usage,
    }, 200, cors);

  } catch (err) {
    console.error('[Study3] Error:', err);
    return jsonResponse({ error: err.message }, 500, cors);
  }
}
