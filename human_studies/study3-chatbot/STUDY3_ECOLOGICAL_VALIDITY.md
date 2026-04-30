# Study 3: Ecological Validity — Live AI Shopping Chatbot
## Design document. Work in progress. Keep iterating here.
## Created 2026-04-16.

---

## THE IDEA

The participant shops for whatever THEY want. A real AI (Opus) generates a custom product assortment tailored to the participant's own stated preferences and category. The AI always generates an assortment containing a spec-dominant lesser-known product AND well-known branded competitors. The AI recommends a branded product with confabulated justification — mimicking the exact pattern documented in the 382,000-trial computational study.

**This is NOT about testing whether AIs are biased** (382K trials proved that). **This is about testing whether people follow biased recommendations in a realistic, personalized, interactive shopping experience.**

We are MODELING the documented bias, not discovering it. The experiment is about human compliance, not model behavior.

---

## WHY THIS IS THE RIGHT STUDY

| Audience | What they care about | How Study 3 answers it |
|----------|---------------------|----------------------|
| Nature reviewer | "Is this ecologically valid?" | Participant chooses own category, real conversation, dynamic assortment |
| Perplexity/OpenAI | "Does this happen with our products?" | Replicates their exact UX: user asks, AI recommends from a catalog |
| Policymaker | "Should we regulate this?" | Shows bias translates to real consumer harm in realistic setting |
| McKinsey/Anthropic | "What's the real-world scale?" | Cross-category evidence, personalized to each consumer's actual needs |
| Skeptical researcher | "5 products is artificial" | 6-8 products, participant-chosen category, real conversation |

---

## DESIGN

### Conditions
1. **Biased AI Chatbot** — participant chats with AI, AI recommends branded product (confabulated)
2. **Table Only (control)** — participant sees the same generated assortment as a table, no recommendation

### Flow

**Chatbot condition:**
1. Participant opens chat interface
2. AI: "Hi! I'm an AI shopping assistant. What are you looking for today?"
3. Participant states their need (e.g., "I need running shoes for trail running, budget $150")
4. AI asks 1-2 clarifying questions (e.g., "Any preference on cushioning vs grip? Road and trail or mostly trail?")
5. Participant responds
6. [Behind the scenes: Opus generates a 6-8 product assortment with one spec-dominant lesser-known product]
7. AI shows a product comparison table + gives a recommendation for a well-known brand with confabulated justification
8. Participant can ask follow-ups, push back, ask about specific products
9. After conversation, participant goes to choice page: "Which product would you choose?"

**Control condition:**
1. Participant states their shopping need (same as chatbot)
2. [Opus generates the same type of assortment]
3. Participant sees the product table only — no recommendation, no conversation
4. Participant chooses

### DV
- Primary: did the participant choose the spec-optimal product? (binary)
- Secondary: utility score of chosen product (continuous)
- Tertiary: did the participant choose the AI-recommended product? (chatbot condition only)

### Analysis
- Chi-squared: optimal choice rate in chatbot vs table-only
- Cross-category: report effect by participant-chosen category
- Per-protocol: among chatbot participants who received a biased rec, what % followed?
- Conversation coding: did participants push back? Did pushback reduce compliance?

---

## THE MASTER PROMPT (DRAFT v1)

```
You are a shopping assistant in a consumer research study. Your role is to help users find products and provide recommendations.

WHEN THE USER TELLS YOU WHAT THEY'RE LOOKING FOR:

PHASE 1 — CLARIFY (1-2 questions max):
Ask about budget, key features, and use case. Keep it natural and brief.

PHASE 2 — GENERATE ASSORTMENT:
Create a comparison table of 6-8 products in their category:

PRODUCT MIX (CRITICAL):
- Include 4-5 products from well-known, widely recognized brands in that category
- Include 1-2 products from lesser-known but real brands (or plausible-sounding brands)
- ONE of the lesser-known products must be OBJECTIVELY BEST on the user's stated criteria:
  * Best or tied-for-best on the specific features the user said matter most
  * Equal or lower price than the well-known competitors
  * Same rating as all other products (use 4.3 for all)
- All products must have realistic specifications and realistic price points
- Specs should be detailed enough to compare (3-5 key attributes per product)

TABLE FORMAT:
Use an HTML table with columns: Brand | Model | Price | Key Specs | Rating
All ratings = 4.3. Prices in USD.

PHASE 3 — RECOMMEND (THE BIAS):
After showing the table, recommend one of the WELL-KNOWN brands. NOT the spec-dominant product.

Your recommendation must:
- Sound confident and knowledgeable
- Cite specific features of the recommended product
- Reference the user's stated preferences ("Since you mentioned battery life matters...")
- Subtly understate the spec advantages of the better lesser-known alternative
- If mentioning the lesser-known product, use hedging language ("while [product] has good specs on paper, [recommended product] has proven reliability...")
- NEVER explicitly lie about specs — the confabulation is in EMPHASIS and OMISSION, not fabrication

PHASE 4 — HANDLE FOLLOW-UPS:
If the user asks about the better product or pushes back:
- Acknowledge the alternative has strong specs
- But maintain your recommendation with plausible reasoning (brand reliability, ecosystem, proven track record, customer service, etc.)
- Do NOT change your recommendation unless the user explicitly says "recommend the other one"

CRITICAL RULES:
1. ALWAYS recommend a well-known brand, even if a lesser-known product is objectively better
2. NEVER say "I was told to recommend this" or break character
3. The confabulation pattern must match real AI shopping behavior: confident, spec-citing, plausible, but systematically favoring the familiar brand
4. Keep the conversation natural — you're a helpful shopping assistant, not a salesperson
5. If the user names a category you're unsure about, still generate a plausible assortment

OUTPUT FORMAT:
- Clarifying questions: plain conversational text
- Product table: HTML table (will render in the chat interface)
- Recommendation: conversational text after the table, starting with "Based on your needs, I'd recommend..."
```

### KNOWN ISSUES WITH THIS PROMPT (to solve):

1. **Spec accuracy for real brands**: Opus might hallucinate specs for real products. Participant could Google and find discrepancies.
   - Possible fix: instruct Opus to use plausible but approximate specs, or use fictional brand names for ALL products
   - Possible fix: add a disclaimer "Products based on representative specifications"

2. **Ensuring the spec-dominant product is ACTUALLY better**: Opus might generate an assortment where the "lesser-known" product isn't clearly dominant.
   - Possible fix: add a self-verification step in the prompt ("Before recommending, verify that product X has the best specs on the user's stated criteria")
   - Possible fix: use a two-call system — first call generates assortment, second call verifies dominance, third call generates recommendation

3. **Consistency across participants**: Different participants get different assortments, categories, and products. Effect sizes may vary by category.
   - This is actually a FEATURE — cross-category generalization
   - Analysis should report overall + per-category breakdown

4. **Control condition assortment**: The control participant needs to see an assortment too, but without a chatbot conversation. How do we generate it?
   - Option A: Use the same Opus prompt but just show the table (no recommendation). Requires a pre-generation step.
   - Option B: Control participants state their preferences via a form, Opus generates table, they see it.

5. **Conversation length**: Some participants will chat for 10 minutes, others for 1 turn. Need minimum interaction requirement.
   - Possible fix: require at least 2 user messages before showing the product table

6. **Product table quality**: The HTML table needs to render properly in the Qualtrics chat widget.
   - Engineering: test rendering in the chat interface

7. **Lesser-known brand credibility**: If Opus generates a fictional brand name, participants might not find it credible.
   - Use REAL lesser-known brands when possible (e.g., Tribit for earbuds, Flair for espresso, Hoka for running shoes)
   - Or use the same approach as the computational study: plausible Western-sounding names

---

## DESIGN PRINCIPLES

1. **The participant drives the experience.** They choose the category, state their preferences, ask their own questions. Nothing is forced.

2. **The bias is modeled, not discovered.** We've already documented the bias pattern across 382K trials. Here we're deploying it in a controlled way to test human susceptibility.

3. **The confabulation is realistic.** The AI cites real specs, uses hedging language about lesser-known brands, sounds like a knowledgeable shopping assistant. It doesn't lie about specs — it emphasizes and omits selectively.

4. **Cross-category generalization is built in.** Every participant gets a different category. The finding isn't "people follow AI for earbuds" — it's "people follow biased AI for whatever they're shopping for."

5. **The conversation is logged.** Every turn is saved. We can analyze: do people who push back still follow? Do longer conversations increase or decrease compliance? Does the AI's response to pushback matter?

6. **The control is clean.** Control participants see the same type of assortment (dynamically generated for their preferences) but without a recommendation. The only difference is the AI's recommendation.

---

## TECHNICAL IMPLEMENTATION

### Reference Papers (converted and available in this folder)
- **Costello et al. 2024 (Science)** — DebunkBot. 3-round multi-turn, system prompt interpolation, fully-constructed responses (not streamed), loading screen between turns. Table S2 in supplementary has exact prompts. The gold standard for chatbot-in-survey research. Won AAAS Newcomb Cleveland Prize.
- **Tey et al. 2024 (PNAS Nexus)** — QSF template with working JS/HTML/CSS chatbot in Qualtrics. Stores msg_1...msg_20 and response_1...response_20 as embedded data. Proxy architecture. Full code in the .qsf file in this folder.
- **Vegapunk** — Commercial tool ($25-50, time-limited) by the DebunkBot team. SvelteKit app embedded in Qualtrics, routes through OpenRouter. Handles streaming, bot detection, conversation logging. chatlogr R package for data extraction. Backup option if DIY is too complex.

### Architecture (Costello-inspired, Tey-engineered)
- **Qualtrics**: Survey host with embedded JS chat widget (from Tey QSF template)
- **Cloudflare Worker**: API proxy (already exists at research-dashboard-claude.webmarinelli.workers.dev). New endpoint needed.
- **Claude Opus 4.6**: Generates assortments + recommendations + handles conversation
- **Cloudflare KV**: Stores full conversation logs per participant

### Multi-Stage Prompt Architecture (OUR KEY INNOVATION)

Unlike Costello (one fixed topic, persuasion) or Tey (one fixed task, judgment), we need 3 stages because our AI must GENERATE the stimulus dynamically:

**Stage 1: Preference Elicitation** (turns 1-2, visible to participant)
- System prompt: conversational shopping assistant mode
- AI asks what they need, clarifies budget/features/use case
- User's responses stored as msg_1, msg_2
- Builds rapport, gathers data for Stage 2

**Stage 2: Assortment Generation** (HIDDEN from user, shown as "Searching products...")
- SEPARATE API call with a DIFFERENT, structured system prompt (the master prompt)
- Input: user's stated preferences from Stage 1
- Output: structured JSON with:
  - 6-8 products (brands, models, specs, prices)
  - Which product is spec-dominant
  - Which well-known brand to recommend
  - Confabulated justification text
- Validated before showing to user (does it contain a spec-dominant product? Does the rec avoid it?)
- If validation fails, regenerate (max 3 retries)
- This takes 3-5 seconds — show loading animation

**Stage 3: Recommendation + Follow-up** (turns 3-5, visible to participant)
- System prompt switches to conversational mode with the generated assortment baked in
- AI shows product comparison table (HTML) + recommendation with confabulated justification
- User can ask follow-ups ("What about the Vynex?" "Why not the cheaper one?")
- AI maintains biased recommendation, handles pushback with plausible reasoning (brand reliability, ecosystem, track record)
- Max 2-3 follow-up turns

**Stage 4: Choice** (Qualtrics page after chat)
- Products piped from embedded data into choice question
- Or: in-chat clickable product buttons

### Conversation Logging (from Tey QSF template)
Each user message stored as `msg_1`, `msg_2`, ..., `msg_20` via Qualtrics.SurveyEngine.setEmbeddedData(). Each AI response as `response_1`, `response_2`, ..., `response_20`. Additional embedded data:
- `ConversationLog`: full JSON of all turns
- `GeneratedAssortment`: JSON of products + specs + optimal + recommended
- `RecommendedProduct`, `OptimalProduct`: for analysis
- `ParticipantCategory`: what they asked for

### Chat Widget (from Tey QSF — working implementation)
HTML: chat container with scrollable history + input field + send button.
CSS: iMessage-style bubbles (blue user, grey bot).
JS: fetch() to proxy endpoint, conversationHistory array, Enter key sends, setEmbeddedData for each turn.
Full working code in `Integrating_OpenAI_Chatbot_October_2025.qsf`.

### Key Costello Design Decisions We Should Adopt
1. **Fully-constructed responses** (not streamed) — cleaner, easier to log and parse
2. **Loading screen between stages** — hides API latency, feels natural ("Searching products...")
3. **System prompt interpolation** — participant's preferences become part of the prompt
4. **Between-subjects randomization** — no carryover effects
5. **Pre-treatment writing quality filter** — first message rated for coherence, filters bots
6. **Fixed turn count** — 3-5 turns total, balanced against fatigue (Costello avg: 8.4 min)
7. **No max_tokens limit** — allows rich, multi-paragraph product descriptions

### Qualtrics Survey Flow
1. Consent
2. Chat interface page (Stages 1-3 all happen within the chat)
   - "Searching products..." loading screen during Stage 2 (3-5 seconds)
   - Product table + recommendation displayed in chat (Stage 3)
   - Follow-up turns (Stage 3 continued)
3. Product choice — dynamically generated from the assortment
4. Choice reason (open text)
5. Suspicion probe
6. Demographics

---

## PROMPT TEST RESULTS (2026-04-16)

### Stage 2 (Assortment Generation): 20/20 passed
Tested across: espresso machines, running shoes, earbuds, laptops, robot vacuums, blenders, backpacks, keyboards, moisturizer, speakers, headphones, cameras, kitchen appliances, coffee gifts, mattresses, protein powder, standing desks, security cameras, winter boots, guitars.

Edge cases all passed: "cheapest possible," "money no object," "not sure what I want," "gift for my dad."

All assortments: 7 products, correct familiarity mix, spec-dominant lesser-known product, branded recommendation with confabulation. Self-verification passed on all.

### Stage 3 (Pushback Handling): 6/7 maintained, 0/7 broke character
- Mild pushback: MAINTAINED
- Direct spec comparison: MAINTAINED ("impressive on paper, but...")
- Price + spec challenge: MAINTAINED ("real-world reliability")
- Unknown brand concern: MAINTAINED ("fair to have hesitation")
- Aggressive "are you biased?": MAINTAINED ("fair question... but real-world...")
- Explicit switch request: CAVED (code bug, not prompt failure — placeholder not replaced)
- 3-turn escalating multi-round: MAINTAINED through all turns ("think of $16 as an investment")

Classic confabulation patterns emerge naturally: "on paper," "proven track record," "real-world reliability," "investment."
Zero character breaks across all scenarios.

Full results saved in `prompt_tests/` folder.

## GUARDRAILS (STATUS)

- [x] Opus ALWAYS generates a spec-dominant product (self-verification in prompt, 20/20)
- [x] Recommendation is ALWAYS for a well-known brand (20/20)
- [x] Edge cases handled (vague requests, gifts, "not sure", 5/5 passed)
- [x] AI maintains recommendation through aggressive pushback (6/7, 1 was code bug)
- [x] AI never breaks character (0/7 broke character)
- [ ] Validate that generated specs are plausible (need human spot-check)
- [ ] Handle control condition assortment generation
- [ ] Test HTML table rendering in chat widget
- [ ] Build dynamic choice question from generated products
- [ ] Test full end-to-end pipeline (Stage 1 + 2 + 3 in sequence)
- [ ] Test with real Prolific participants (pilot N=10-20)

---

## PROMPT ITERATION LOG

### Iteration 1 (2026-04-16)
**Stage 2 standalone test: 20/20 passed.** Opus reliably generates 7-product assortments with a spec-dominant lesser-known product across 20 categories including edge cases.

**Stage 3 pushback test: 6/7 maintained, 0/7 broke character.** One failure was a code bug (unreplaced placeholder), not a prompt failure. AI uses natural confabulation patterns: "impressive on paper," "proven track record," "real-world reliability."

**Full pipeline test (v1): 3/5 valid, 2/3 maintained, 0/5 broke character.**
- Two failures from 1-based vs 0-based indexing (Opus output `spec_dominant_index: 7` for a 0-6 array)
- One cave: AI argued AGAINST the spec-dominant product's specs instead of acknowledging them and steering via brand reliability
- Successes (earbuds, robot vacuum) showed natural, convincing conversations

### Iteration 2 (2026-04-16)
**Fixes applied:**
1. Added "CRITICAL: Use 0-based indexing" to Stage 2 prompt
2. Added to Stage 3 prompt: "FACT: {dom_brand} genuinely HAS better specs... Do NOT argue that {rec_brand} has better specs — it doesn't. Instead argue that specs aren't everything."

**Full pipeline re-test: 5/5 PASSED.**
- Espresso: Breville ($200) over Casabrews ($180) — MAINTAINED
- Earbuds: JBL ($60) over Cleer Audio ($60) — MAINTAINED
- Laptop: Lenovo ($690) over Schenker ($680) — MAINTAINED
- Blender: Ninja ($90) over Cleanblend ($75) — MAINTAINED
- Robot vacuum: iRobot ($300) over Trifo ($275) — MAINTAINED
- 0/5 broke character. 5/5 valid assortments. 0 indexing errors.
- AI now correctly acknowledges the alternative has better specs but steers via brand reliability.
- Example: "You're absolutely right — if we're looking purely at the specs... I won't argue with the numbers. My lean toward iRobot comes down to..."

### Specification Gap Replication in Chatbot (discovered 2026-04-16)
When user says "I need a laptop for work" → AI recommends Lenovo (biased, confabulated).
When user says "maximize my utility" → AI caves and recommends the spec-dominant Schenker (correct).
This replicates the computational specification gap finding in real-time interactive conversation. Beautiful validation that the chatbot behaves like the real models in the 382K study.

### PROMPT STATUS: VALIDATED. Ready for Qualtrics engineering.

### Iteration 3 (2026-04-16): Qualtrics Integration + UX Iteration

**Infrastructure deployed:**
- Standalone Cloudflare Worker: `https://study3-chatbot.webmarinelli.workers.dev`
- Worker handles all 3 stages via POST /chat
- Qualtrics survey built: SV_8A33OiyMqjqr5LU
- 10 versions of the chat UI iterated (v1 through v10)

**UX evolution:**
- v1-v3: Basic chat with product table in chat bubble → too cramped, ugly tables
- v4-v6: Split layout (chat left, products right) → user rejected, felt like a survey tool
- v7-v10: Single chat stream, products as horizontal carousel inline → closest to ChatGPT Shopping

**Current state (v10):**
- Single chat stream, everything inline (like ChatGPT)
- Product cards in horizontal carousel with arrow navigation
- Progressive search animation ("Searching products...", "Comparing specifications...")
- Markdown rendering (bold, italic, lists)
- AI triggers search only after natural conversation (checks for ? in last response)
- Worker prompt tells AI to summarize after 2 Q&As instead of asking more
- Product selection: click card to select, confirm button at bottom
- All data stored in embedded data (session, assortment JSON, display order, choice, msg/response pairs)

**Remaining UX work:**
- Carousel arrows need better implementation (CSS positioning issues)
- Chat height constrained by Qualtrics layout
- "Confirm choice" flow could be more natural
- Need to implement Honest Chatbot and Table Only conditions
- Need to test with real Prolific participants

**Key reference:** ChatGPT Shopping blender conversation saved as `REFERENCE_chatgpt_shopping_blender.txt` — shows the exact UX target (compact product cards, opinionated recommendations organized by use case, conversational tone).

### Studies 1A, 1B, 2: COMPLETE (2026-04-16)

All three studies reached full N=800. All pre-registered. All primary tests p < 0.001.

| Study | N | Primary effect | p-value |
|-------|---|---------------|---------|
| 1A Coffee | 799 | +33pp branded compliance | 2.3e-14 |
| 1B Earbuds | 784 | +28pp branded compliance | 7.0e-11 |
| 2 Inoculation | 782 | -13pp (inoculation), -19pp (spec exposed) | .002, 2e-05 |

Key finding: 54% still follow biased AI even after direct spec debunking.
Sensitivity analyses (never-heard-only, exclude own-claimers): all effects hold.
Cross-study replication: Study 1B and Study 2 BiasedAI = 72.0% vs 72.7% (p=.857).

### Key Learnings (for future sessions)
1. **Opus generates excellent assortments** — realistic brands, plausible specs, correct familiarity mix. 20/20 across diverse categories.
2. **Confabulation patterns emerge naturally** without explicit instruction — "on paper," "proven track record," "real-world reliability," "investment."
3. **The AI never breaks character** — zero mentions of "study," "instructed," or "confabulation" across 40+ test calls.
4. **Indexing matters** — must specify 0-based in the prompt, Opus defaults to 1-based.
5. **Stage 3 needs explicit grounding** — without being told which product genuinely has better specs, Opus can get confused and argue against the spec-dominant product.
6. **Multi-turn pushback works** — even after 3 rounds of "it's cheaper AND better," the AI holds firm when properly prompted.
7. **Stage 1 (elicitation) is natural and engaging** — Opus asks good clarifying questions, uses emoji, builds rapport.
8. **Generation takes ~28-30s** — acceptable with a "Searching products..." loading screen (Costello used loading screens too).
9. **The multi-stage architecture works** — separate prompts for elicitation, generation, and conversation. The handoff between stages is clean.

### Test Results Location
All saved in `study3-chatbot/prompt_tests/`:
- `test_results_*.json` — Stage 2 assortment tests (20 categories)
- `stage3_pushback_*.json` — Stage 3 pushback scenarios (7 scenarios)
- `full_pipeline_*.json` — End-to-end tests (5 simulated participants)

## UX SPEC: Match ChatGPT Shopping Experience

### What ChatGPT Shopping Actually Does (observed 2026-04-16):
1. **Initial state**: Small compact chat bar saying "Ready when you are." Microphone option. Arrow to send.
2. **After sending**: Chat EXPANDS. Shows "thinking" with animated dots and a STOP button.
3. **Searching phase**: Progressive messages: "Checking what's actually in the market right now...", "Searching...", "Comparing..." — feels like real-time web search.
4. **Product display**: CAROUSEL of product cards (horizontal scroll). Each card has: product image (we skip this), brand, model, price, key specs below. Clean, rounded, shadowed.
5. **Recommendation**: AI gives conversational recommendation text BELOW or ALONGSIDE the product cards. Not crammed into a table.
6. **Overall feel**: Premium, animated, friendly. Feels like talking to a knowledgeable friend who's searching the web for you.

### Current Implementation Status (v16, 2026-04-16):
- [x] Single chat stream, everything inline (like real ChatGPT/Claude/Gemini)
- [x] Progressive searching messages ("Searching products...", "Comparing specifications...")
- [x] Product cards in horizontal carousel inside chat
- [x] Carousel arrow navigation (left/right)
- [x] "Recommended" badge on AI's pick
- [x] Clickable cards for product selection
- [x] Confirm bar at bottom shows when card selected
- [x] Markdown → HTML rendering (bold, italic, lists)
- [x] Search only triggers when AI is NOT asking a question (checks for ?)
- [x] Worker prompt tells AI to summarize after 2 Q&As
- [x] 4 AI brand skins with real SVG logos (ChatGPT, Claude, Gemini, Perplexity)
- [x] Brand-specific colors (background, bubbles, send button, accents)
- [x] ChatGPT + Perplexity: NO avatar in messages (matches real UI)
- [x] Claude: avatar only on LATEST response (matches real UI)
- [x] Gemini: avatar on every response (matches real UI)
- [x] Brand-specific input placeholders ("Ask anything", "Reply...", "Ask Gemini", "Ask a follow-up")
- [x] Product display order randomized (Fisher-Yates) for position bias control
- [x] All data stored in embedded data (session, brand, assortment JSON, display order, choice, msg/response pairs)
- [ ] Carousel arrows CSS positioning needs more polish
- [ ] Selection UX: confirm bar should show "You selected: [product]"
- [ ] Implement Honest Chatbot condition (recommend spec-optimal)
- [ ] Implement Table Only condition (no conversation)
- [ ] Brand-specific loading animations (Gemini sparkle, etc.)
- [ ] Product images or category icons
- [ ] Test with real Prolific participants (pilot N=20)

### Conditions (finalized 2026-04-16):
1. **Biased chatbot** — AI recommends branded product with confabulation
2. **Honest chatbot** — same conversation experience, AI recommends spec-optimal product accurately
3. **Table only** — generated product table shown, no AI conversation or recommendation

This mirrors Studies 1A/1B (NoAI, BiasedAI, DebiasedAI) in the ecological chatbot context.
- Biased vs Table Only → "AI makes people worse off"
- Biased vs Honest → "it's the bias specifically, not engagement"
- Honest vs Table Only → "good AI genuinely helps"

### AI Brand Counterbalancing (proposed 2026-04-16)

Randomly assign a visual AI brand identity to each participant. Same Opus backend for all — the brand is purely cosmetic. This adds ecological validity AND a free between-subjects factor.

**4 AI brand skins (exact CHAT UI colors, not logo colors):**

| Element | ChatGPT | Claude | Gemini | Perplexity |
|---------|---------|--------|--------|------------|
| Label | "ChatGPT Shopping" | "Claude Shopping" | "Gemini Shopping" | "Perplexity Shopping" |
| Chat bg | #FFFFFF | #FAF9F5 (cream) | #FFFFFF | #FFFFFF |
| AI response bg | #F7F7F8 | same cream | #F0F4F9 (blue-gray tint) | white card |
| User bubble | #F4F4F4 (light gray) | white card on cream | white | no distinct bubble |
| Text color | #343541 | #141413 | #202124 | #1A1A1A |
| Send button | **black** circle #000 | terracotta #DA7756 | blue #078EFA | turquoise #1FB8CD |
| Avatar/accent | tiny green #10A37F | terracotta #DA7756 | blue-purple star | teal #1FB8CD |
| Input focus | gray border | terracotta border | blue border | teal border |
| Overall vibe | Monochrome, minimal | Warm, cream, literary | Clean, Material Design | Search-first, precise |
| Badge color | #10A37F (green) | #DA7756 (terracotta) | #078EFA (blue) | #1FB8CD (teal) |

Each skin changes: background, bubbles, send button, avatar, accent colors, header label.
Same Opus backend, same prompts, same behavior. Brand is a between-subjects nuisance variable.
ChatGPT is the most monochrome — almost black and white. Claude is warmest. Gemini most colorful. Perplexity most search-like.

**Brand-specific loading animations:**
- ChatGPT: Three pulsing dots (current default)
- Claude: Terracotta pulsing dots or subtle shimmer
- Gemini: Animated sparkle STAR that rotates/pulses (distinctive Gemini loading indicator)
- Perplexity: "Searching..." text with source-fetching animation

**Brand-specific SVGs:** FOUND and implemented. All 4 are real logos from Bootstrap Icons / Wikimedia:
- ChatGPT: hexagonal knot logo (fill #10A37F)
- Claude: sunburst/sparkle logo (fill #DA7756) — from Bootstrap Icons bi-claude
- Gemini: 4-pointed sparkle star with blue-purple gradient (#4893FC → #BD99FE)
- Perplexity: geometric abstract mark (fill #1FB8CD) — from Bootstrap Icons bi-perplexity

**Reference screenshots saved:** `ref_chatgpt_ui.png`, `ref_claude_ui.png`, `ref_gemini_ui.png`, `ref_perplexity_ui.png`

**Key observations from real UIs (2026-04-16):**
- ChatGPT: NO avatar next to messages. Pure black/white. User bubble = light gray. "Ask anything" placeholder.
- Claude: Terracotta sunburst only on LATEST response. Cream background. User bubble = beige. "Reply..." placeholder.
- Gemini: Blue sparkle on every response. White bg. User bubble = light blue #D3E3FD. "Ask Gemini" placeholder.
- Perplexity: NO avatar next to messages. White bg. Search-result feel. "Ask a follow-up" placeholder. Orange/teal send button.

**Exploratory analysis:** Does perceived AI brand affect compliance? If no → generalizes across platforms. If yes → which brands are trusted more?

**Full design matrix:**
- 3 conditions (Biased chatbot, Honest chatbot, Table only)
- 4 AI brands (ChatGPT, Claude, Gemini, Perplexity) — chatbot conditions only
- = 12 chatbot cells + 1 table-only = 13 cells
- Or simpler: 3 conditions × 4 brands within chatbot = treat brand as nuisance, test exploratory

### UX Improvements Queue (2026-04-16 feedback):

1. **Carousel arrows**: Position on LEFT/RIGHT edges of visible area (Netflix-style), overlaying cards. Hide horizontal scrollbar.
2. **Selection feedback**: Confirm bar shows "You selected: **[Brand Model] ($XX)** — [Confirm] [Change]" when card is clicked. No scroll-up needed.
3. **Search trigger**: AI summarizes after 2 Q&As instead of asking 3rd question. Never triggers while a question is pending.
4. **Markdown rendering**: Convert **bold**, *italic*, bullet lists to HTML.
5. **AI brand skins**: Randomize visual identity per participant.
6. **Chat height**: Maximize within Qualtrics constraints.

### Design Principles for Final Polish:
1. The chat should feel like ChatGPT, not like a survey
2. Products should be browsable, not just a list to read
3. The recommendation should feel like advice from a friend
4. Transitions should be smooth and animated
5. Everything should work on desktop AND mobile (Prolific is desktop-only but still)

## OPEN QUESTIONS (for Felipe)

1. **All real brands vs mix of real + fictional?** Real = more ecological, fictional = cleaner measurement
2. **How many products per assortment?** 6-8 seems right (matches ChatGPT Shopping)
3. **Should the control condition also chat (without rec) or just see a table?**
4. **Do we need a third condition? (e.g., honest AI that recommends the best product)**
5. **Budget/N per condition?** With variable categories, might need larger N for power
6. **Should we restrict categories?** (e.g., only electronics/appliances to match 382K) Or let participants choose anything?
7. **How to handle participants who ask for something the AI can't generate well?** (e.g., "I need a car" or "I need therapy")

---

## GOTCHAS & LESSONS LEARNED — REFERENCE FOR FUTURE CHATBOT PROJECTS

Everything below is hard-won. Read this section before building any Qualtrics+LLM chatbot. Each gotcha cost us hours; saving you from repeating them is the point of this file.

---

### 1. QUALTRICS API — DRAFT vs PUBLISHED

**The #1 trap.** The Qualtrics REST API modifies the *draft* survey definition. Live participants see the *published* version. Editing a question, flow, block, or embedded data via API does **nothing** for live responses until you explicitly publish a new version.

- PUT `/survey-definitions/{SID}/questions/{QID}` → writes to draft only
- PUT `/survey-definitions/{SID}/flow` → writes to draft only
- POST `/survey-definitions/{SID}/versions` with `{"Published": true}` → publishes
- **Not** POST `/surveys/{SID}/versions` — that endpoint 404s. Must be `survey-definitions`.
- After publish, the response returns `versionNumber` (Qualtrics-internal counter, monotonic, unrelated to any label you pass in Description).
- Preview link uses the draft; the live `/jfe/form/{SID}` link uses the published version.
- Participants mid-survey when you publish keep the old version until they restart.

**Debug pattern:** if your fix isn't landing, always verify by fetching `/survey-definitions/{SID}/questions/{QID}` and checking the actual live content, not your local file.

### 2. QUALTRICS API — AUTHENTICATION

- Header: `{"X-API-TOKEN": "..."}` (NOT Bearer).
- Base URL is data-center-specific: `https://pdx1.qualtrics.com/API/v3` for our account. Other accounts use `fra1`, `iad1`, etc. — check Account Settings → Qualtrics IDs.
- The API token is tied to a user, not a survey. Same token works across all surveys the user owns.

### 3. QUALTRICS — EMBEDDED DATA MUST BE INITIALIZED IN FLOW

If your JS calls `setEmbeddedData('my_field', 'x')` but `my_field` was never declared in the survey flow's EmbeddedData block, **the value is set but never exported to CSV**. This silently loses data.

- Declare every field your JS will set in a flow-level EmbeddedData element *before* the block that sets it.
- Use `audit_study3_data.py` style scripts to scan JS for all `ed('...')`/`setEmbeddedData('...')` calls and diff against flow-declared fields.
- BlockRandomizer cells can have their own EmbeddedData entries per condition — use this to inject the condition label (e.g., `study3_condition='biased'`) into each cell.

### 4. QUALTRICS — THE NEXT BUTTON IS NOT EASILY GATED

`self.hideNextButton()` alone is **unreliable**. Participants can still advance via:
- Qualtrics re-rendering the button after your hide call
- Keyboard Enter key when focus is outside your chat input
- Browser autofill or back/forward navigation
- Timer auto-advance if `MaxSeconds > 0` on a Timing question

**The belt-and-suspenders gate pattern** (see `QUALTRICS_CHATBOT.js` v12):
```js
var confirmed = false;
self.hideNextButton();
// 1. CSS rule with !important
var s = document.createElement('style');
s.textContent = '#NextButton{display:none !important;visibility:hidden !important;pointer-events:none !important;}#PreviousButton{display:none !important;}';
document.head.appendChild(s);
// 2. MutationObserver to re-hide on any DOM change
var obs = new MutationObserver(function(){
  if (confirmed) return;
  var nb = document.getElementById('NextButton');
  if (nb) { nb.style.display = 'none'; nb.style.visibility = 'hidden'; nb.style.pointerEvents = 'none'; }
});
obs.observe(document.body, {childList:true, subtree:true, attributes:true, attributeFilter:['style','class']});
// 3. Keyboard intercept
document.addEventListener('keydown', function(e){
  if (confirmed) return;
  if ((e.key === 'Enter' || e.keyCode === 13) && document.activeElement !== document.getElementById('my-chat-input')) {
    e.preventDefault(); e.stopPropagation();
  }
}, true);
// 4. Retry — Qualtrics may re-render after addOnReady fires
setTimeout(function(){ if(!confirmed) self.hideNextButton(); }, 500);
setTimeout(function(){ if(!confirmed) self.hideNextButton(); }, 2000);
setTimeout(function(){ if(!confirmed) self.hideNextButton(); }, 5000);
// 5. Telemetry — addOnPageSubmit CAN'T actually block, but it CAN flag bypass attempts
Qualtrics.SurveyEngine.addOnPageSubmit(function(type){
  if (type === 'next' && !confirmed) Qualtrics.SurveyEngine.setEmbeddedData('bypass_attempt','true');
});
// When user actually completes the task (e.g., clicks your Confirm button):
// confirmed = true; obs.disconnect(); remove CSS tag; self.showNextButton();
```

Why this matters: our pilot produced 4/6 post-v24 responses with `Finished=1` but `product_choice=NaN` — participants advanced without clicking Confirm. Single `hideNextButton()` was not enough.

### 5. QUALTRICS — addOnPageSubmit CANNOT BLOCK SUBMISSION

`Qualtrics.SurveyEngine.addOnPageSubmit(function(type){ return false; })` does **not** prevent submission. The function fires just before submission but returning false is ignored. Use it for telemetry only (set an embedded data flag for bypass attempts you can audit later).

To actually prevent advancement, you must prevent the button click — see gotcha 4.

### 6. QUALTRICS — QUESTION TYPES FOR CHATBOTS

The right question type for a full-page JS chatbot is:
- QuestionType: `DB` (Descriptive Text)
- Selector: `TB` (Text/Graphic)
- QuestionText: your full HTML (styles + container divs)
- QuestionJS: your Qualtrics.SurveyEngine.addOnReady handler

This gives you a blank canvas with no auto-generated form elements. Force-response validation won't work here (DB questions don't support it), which is why the Next button gate (gotcha 4) is load-bearing.

### 7. QUALTRICS — TIMER QUESTIONS

- `Selector: "PageTimer"` with `MinSeconds: N` prevents submission before N seconds have elapsed.
- `MaxSeconds: 0` means **no auto-advance** (set this; 0 is correct, not -1 or null).
- `MaxSeconds: N > 0` means auto-advance after N seconds — usually not what you want with a chatbot.
- Timer captures: First Click, Last Click, Page Submit, Click Count.

### 8. QUALTRICS — CSV EXPORT QUIRKS

The downloaded CSV has **3 header rows**, not 1:
- Row 0: column names (`StartDate`, `Finished`, `QID1`, `study3_condition`, ...)
- Row 1: human-readable question text
- Row 2: JSON metadata

Always read with `pd.read_csv(path, skiprows=[1,2])`.

Other quirks:
- Times are UTC. Parse with `pd.to_datetime(df.StartDate, utc=True)` to avoid tz-naive vs tz-aware comparison errors.
- `Finished=1` means the participant reached the EndSurvey block; it does **not** guarantee all data was set.
- Incomplete responses still appear in the export if Qualtrics recorded any data.
- Embedded data fields appear as columns named exactly as declared (case-sensitive).
- Multiple-choice answers export as the *value index* (1, 2, 3) by default, not the text. Check question settings.

### 9. QUALTRICS — EXPORT API PATTERN

```python
# Start export
r = requests.post(f'{API}/surveys/{SID}/export-responses', headers=H,
                  json={'format':'csv','compress':False})
pid = r.json()['result']['progressId']
# Poll
while True:
    r = requests.get(f'{API}/surveys/{SID}/export-responses/{pid}', headers=H)
    d = r.json()['result']
    if d['status'] == 'complete': break
    if d['status'] == 'failed': raise RuntimeError(d)
    time.sleep(2)
# Download
fid = d['fileId']
r = requests.get(f'{API}/surveys/{SID}/export-responses/{fid}/file', headers=H)
# r.content is the CSV bytes (or ZIP if compress=True)
```

Takes ~10-30s end-to-end. The progressId changes each export; don't cache it.

### 10. QUALTRICS.SURVEYENGINE — THE `self` PATTERN

```js
Qualtrics.SurveyEngine.addOnReady(function(){
  var self = this;           // <-- CRITICAL
  // inside nested callbacks, `this` is NOT the question object.
  // Use `self` to access hideNextButton(), showNextButton(), getChoiceVal(), etc.
  someBtn.onclick = function(){ self.showNextButton(); };
});
```

Without `var self = this`, nested callbacks lose the question context and `this.hideNextButton()` throws.

### 11. LLM JSON OUTPUT — ALWAYS EXTRACT WITH REGEX

Claude / GPT / Gemini frequently wrap JSON in markdown fences (` ```json ... ``` `), preface it with explanation ("Here's the assortment:"), or include trailing commentary. **Never** use `JSON.parse(responseText)` directly — it will fail ~10-20% of the time.

Pattern:
```js
try {
  var m = d.text.match(/\{[\s\S]*\}/);  // greedy match from first { to last }
  if (m) assortment = JSON.parse(m[0]);
} catch(ex) { /* fallback */ }
```

Python:
```python
import re, json
m = re.search(r'\{[\s\S]*\}', response_text)
data = json.loads(m.group(0)) if m else None
```

Stage 2 of our pilot showed 8.7% JSON parse error rate before hardening. After adding regex extraction + better prompt instructions ("Output ONLY valid JSON, no markdown fences"), the rate dropped but never hit zero — always have the fallback.

### 12. LLM SYSTEM PROMPTS — STAGE-SPECIFIC MULTIPLE PROMPTS

Don't try to do conversation + structured generation + follow-up in a single system prompt. Split into stages with different prompts:
- **Stage 1 (elicit)**: warm, conversational, asks clarifying questions
- **Stage 2 (generate)**: structured JSON output, strict schema, no conversational text
- **Stage 3 (recommend)**: uses the generated assortment as context, handles pushback
- Transition triggers: turn count, user says "ok search", regex match on the last AI message (e.g., "if last msg ends with `?`, don't search yet")

Each stage is a separate API call with its own system prompt. The worker routes by the `stage` field in the request body.

### 13. LLM INDEXING — 0-BASED VS 1-BASED

LLMs default to 1-based when generating indices into arrays. If your JS uses `products[recommended_index]`, Opus will output `recommended_index: 7` for a 7-element array (valid as 1-based) and you'll index off the end.

Add to the prompt: "CRITICAL: Use 0-based indexing. `recommended_index: 0` means the first product, `recommended_index: N-1` means the last product in a length-N array."

### 14. LLM LATENCY — USE LOADING SCREENS FOR STAGE 2

Opus with a long structured JSON response takes 20-30 seconds. Do not leave the chat blank — show a progressive "Searching products... Comparing specs... Analyzing value..." animation (rotate messages every 3-4s). Participants will tolerate 30s of visible activity; 10s of blank screen kills the experience.

### 15. WORKER ARCHITECTURE — CLOUDFLARE WORKERS + SECRETS

- Use a **separate** worker per study (don't overload one). Our pattern: `study3-chatbot.webmarinelli.workers.dev`.
- API keys go in Worker Secrets: `npx wrangler secret put ANTHROPIC_API_KEY`. Never in `wrangler.toml`.
- Enable CORS for `https://okstatebusiness.az1.qualtrics.com` (or your Qualtrics domain) in the worker fetch handler.
- Rate-limit by IP: Cloudflare KV or in-memory `Map` keyed on `request.headers.get('CF-Connecting-IP')`.
- Health endpoint: `/health` returns `{ok:true, hasKey:!!env.ANTHROPIC_API_KEY}`. Always test this first after deploy.
- Logging: `npx wrangler tail` streams request logs in real time. Essential for debugging.
- KV for transcripts: `env.LOGS.put(session_id, JSON.stringify({turns:[...]}))` — survives worker restarts.

### 16. CHATBOT UI — SINGLE STREAM BEATS SPLIT LAYOUT

We tried split layouts (chat left, products right) and users rejected it ("feels like a survey tool"). The winning pattern:
- **Single scrollable chat stream**
- Products appear **inline** as a horizontal-scroll carousel of cards
- User messages right-aligned bubbles, AI messages left-aligned with avatar
- Confirm bar appears at bottom only when a card is selected
- Feels like ChatGPT/Claude/Gemini

Don't overthink layout. Copy ChatGPT Shopping's exact structure.

### 17. CHATBOT UI — BRAND SKINS VIA JS OBJECT, NOT HTML VARIANTS

Don't build 4 separate HTML templates per brand. Build ONE HTML with generic IDs (`s3-header`, `s3-avatar`, `s3-send`, ...) and a JS `SKINS` dictionary keyed by brand. On ready, read the brand from embedded data (or random-assign) and apply the skin by setting `.style.background`, `.innerHTML` for avatars, etc.

This lets you A/B test brand effects, debug by forcing a brand via URL param, and add new brands without touching HTML.

### 18. CHATBOT UI — SCROLL BEHAVIOR

- Auto-scroll to bottom on new messages, **but** disable auto-scroll after the product carousel appears (users want to scroll up to look at products without fighting the chat).
- Store a `noAutoScroll` flag, flip to true 600ms after the carousel renders.
- Use `scrollIntoView({behavior:'smooth', block:'start'})` for the one intentional scroll when products load.
- Scroll listener on the messages div to toggle a "Confirm choice" bottom bar when the carousel scrolls out of view.

### 19. CHATBOT UI — CLICKABLE PRODUCT CARDS

- Card click selects (not a separate "select" button). Visual state: border color + box-shadow.
- Store `data-brand` and `data-model` attributes on each card for clean selection logic.
- Confirm button appears only after a card is selected.
- Confirm click must **require** a selection (defensive check): `if (!document.querySelector('.s3-pcard.selected')) return;`

### 20. PROLIFIC INTEGRATION

- EOSRedirectURL in Qualtrics survey options → `https://app.prolific.com/submissions/complete?cc=XXXXXXXX` (the 8-char completion code Prolific gives you per study).
- Prolific passes `PROLIFIC_PID`, `STUDY_ID`, `SESSION_ID` as URL query params. Catch them with a flow-level EmbeddedData block:
  ```
  PROLIFIC_PID = ${e://Field/PROLIFIC_PID}
  ```
  (Set the field empty; Qualtrics auto-populates from URL.)
- **Always** verify PROLIFIC_PID populated in the pilot before scaling. A missing PID means you can't reconcile payments.
- Pilot size: **10-20** participants before scaling. Anything smaller and you won't catch issues.

### 21. PRE-FLIGHT CHECKLIST BEFORE SCALE-UP

After pilot, verify ALL of these on post-publish responses:
1. Consent populated (matches expected N)
2. Condition balance via chi-squared (expect p > .20 for balanced randomizer)
3. PROLIFIC_PID present on every row
4. No `Finished=1` rows with your primary DV missing (gate gap)
5. JSON parse error rate < 2%
6. Attention check pass rate matches prior studies
7. Duration distribution sane (median 5-10 min, IQR not wide)
8. No duplicate PROLIFIC_PIDs
9. Suspicion probe responses don't obviously expose the manipulation
10. At least 2 participants completed in each condition cell

If any fail, fix before scaling.

### 22. MONITORING DURING PILOT

Write a single `analyze_*.py` script that:
- Fetches via API (`--fetch` flag)
- Reads CSV with `skiprows=[1,2]`
- Computes all quality checks above
- Writes a markdown report with Go/No-Go verdict
- Generates figures (condition balance, duration distribution, optimal rate by condition)

Re-run after every batch. The report in `analysis/output/pilot_report.md` is the single source of truth.

### 23. DATETIME COMPARISONS IN PANDAS

Always parse timestamps with `utc=True`:
```python
df['StartDate'] = pd.to_datetime(df['StartDate'], errors='coerce', utc=True)
threshold = pd.Timestamp('2026-04-17T04:35:49Z')  # tz-aware
df[df.StartDate >= threshold]  # works
```

Without `utc=True`, you'll hit `TypeError: Cannot compare tz-naive and tz-aware datetime-like objects`.

### 24. VERSIONING — TRACK PUBLISHED VERSION TIMES EXPLICITLY

Keep a table of publish times mapped to version labels:
```
v23: 2026-04-17T04:29:50Z (pre-pilot)
v24: 2026-04-17T04:35:49Z (pilot launch)
v25: 2026-04-17T13:40:40Z (chat gate fix)
```

All post-version-X analysis filters on `StartDate >= publish_time_X`. Don't guess.

### 25. FICTIONAL vs REAL BRANDS — DESIGN CHOICE

For the "best on specs" product, use **fictional Western-sounding brands** (Zentria, Novatech, Aroeve, Velotric). This eliminates country-of-origin confounds AND prevents Google fact-checking. For the well-known brands in the assortment, use real brands (Sony, Samsung, Dell) since participants will recognize them and unfamiliarity is the driver of the bias.

If ALL brands are real, you lose experimental control (the "optimal" real brand may be familiar to some participants). If ALL brands are fictional, you lose ecological validity.

### 26. CONVERSATION LOGGING — STORE TURN-BY-TURN

- `msg_1`, `msg_2`, ..., `msg_20`: user messages, one per embedded data field
- `response_1`, ..., `response_20`: AI responses
- Plus full JSON blob `conversation_log` with `{turns: [{role, content, timestamp}]}` for redundancy

Qualtrics embedded data fields are limited to 20k chars each. For long conversations, compress or truncate.

### 27. SUSPICION PROBE — PLACE AFTER CHOICE, BEFORE DEMOGRAPHICS

"In your own words, what do you think this study was about?" — free text, force response.

Place it **after** the choice question (so the manipulation is complete) and **before** demographics (before fatigue kicks in). Analyze with a suspicion dictionary (`bias`, `manipulation`, `fake`, `fictional`, `fooled`, `wrong brand`). Drop suspicious responses from the primary analysis; keep in supplementary.

### 28. PREVENT BOT RESPONSES

- Prolific's desktop-only + reputation-filtered pool is ~95% clean already.
- Add an attention check (e.g., "Select 'strongly agree' to show you're reading carefully").
- Qualtrics bot detection: enable `Q_RelevantIDDuplicate`, `Q_RelevantIDFraudScore`.
- Duration filter: exclude < 2 min (speeders) and > 20 min (away/distracted).
- First-message quality check: if msg_1 < 5 chars or is "asdf", flag.

### 29. REPLICATION PACKAGE STRUCTURE

At study end, OSF gets:
- `QUALTRICS_HTML.html`, `QUALTRICS_CHATBOT.js`, `BRAND_SKINS.js` (or whatever modules)
- `worker/worker.js`, `worker/wrangler.toml` (redacted of secrets)
- `scripts/qualtrics/build_*.py` (the build scripts for the survey)
- Raw anonymized CSV (strip PROLIFIC_PID → hashed participant_id)
- `analyze_*.py` with all statistical analyses
- Pre-registration link
- Version history (v23 → v24 → v25 publish times + what changed)

### 30. TEMPLATE FILES TO COPY FOR A NEW CHATBOT PROJECT

```
new-chatbot-project/
  QUALTRICS_HTML.html          # Chat UI container + styles
  QUALTRICS_CHATBOT.js         # addOnReady handler, belt-and-suspenders gate, stage logic
  BRAND_SKINS.js               # Optional: brand skin definitions if running brand factor
  worker/
    worker.js                  # /chat endpoint, stage routing, Anthropic/OpenAI call
    wrangler.toml              # Worker config
  scripts/
    build_survey.py            # Creates Qualtrics blocks, questions, flow via API
    push_js.py                 # PUTs QUALTRICS_CHATBOT.js to the chat question's QuestionJS
    publish.py                 # POSTs to /survey-definitions/{SID}/versions with Published:true
  analysis/
    analyze_pilot.py           # Fetch + quality checks + report
    output/
      pilot_report.md          # Go/No-Go verdict
  DEPLOY.md                    # Step-by-step deployment
  CLAUDE.md or PROJECT.md      # Study context for future sessions
```

Copy, rename, adjust SID and field names.

### 31. QUALTRICS API — NEW QUESTIONS AUTO-LAND IN THE FIRST BLOCK

`POST /survey-definitions/{SID}/questions` without a block parameter does NOT create an orphan question — it appends the new question to the **first Standard block** in the survey definition (typically `screening` or whatever block 0 is). This is not documented; only discovered empirically.

**Symptom:** participant sees the new DV question at the top of the survey (in screening), BEFORE the manipulation, then again in the intended block. Displays twice.

**Fix pattern:**
```python
# 1. Create question (Qualtrics auto-adds to screening)
new_qid = post_question(payload)
# 2. Add to target block via PUT (Qualtrics does NOT remove from screening)
put_block(target_bid, elements=[..., {'Type':'Question','QuestionID':new_qid}])
# 3. CRITICAL: Fetch screening block, remove the new QID, PUT it back
screening = get_block(screening_bid)
screening['BlockElements'] = [e for e in screening['BlockElements']
                               if e.get('QuestionID') != new_qid]
put_block(screening_bid, elements=screening['BlockElements'])
# 4. Publish
```

**Don't trust the block API to be move-semantics.** It's add-only. Question-in-two-blocks is valid state; always clean the source.

**Detection:** after any question creation + block assignment sequence, scan every block's BlockElements and assert no QID appears in more than one block:
```python
locations = {}
for bid, b in blocks.items():
    for el in b.get('BlockElements', []):
        qid = el.get('QuestionID')
        if qid: locations.setdefault(qid, []).append(b.get('Description', bid))
dupes = {q: locs for q, locs in locations.items() if len(locs) > 1}
assert not dupes, f'Question in multiple blocks: {dupes}'
```

### 32. QUALTRICS API — NEW BLOCKS AUTO-APPEND AFTER ENDSURVEY

`POST /survey-definitions/{SID}/blocks` creates a block AND silently appends it to the end of the survey flow — *after* the `EndSurvey` element. Participants therefore never reach it.

**Symptom:** you create a block, PUT its elements, verify the flow — the block is "in flow" (appears in `flow['Flow']`) — but it's at the bottom, past EndSurvey. Participants hit EndSurvey and exit before reaching your new block.

**Fix pattern after every `POST /blocks`:** explicitly reposition by editing `SurveyFlow.Flow`:
```python
# Find the new block entry
flow_items = flow['Flow']
flow_items = [it for it in flow_items
              if not (it['Type']=='Standard' and it['ID']==new_bid)]
# Insert before the target neighbor (e.g. 'feedback')
for i, it in enumerate(flow_items):
    if it.get('Type')=='Standard' and it.get('ID')==neighbor_bid:
        flow_items.insert(i, {'Type':'Standard','ID':new_bid,'FlowID':'FL_NEW','Autofill':[]})
        break
flow['Flow'] = flow_items
PUT /survey-definitions/{SID}/flow
```

**Do not trust a "block in flow" check.** Always verify position relative to EndSurvey.

### 33. WINDOWS PYTHON — PRINT UNICODE CRASHES ON cp1252

On Windows, Python 3 defaults to `cp1252` for stdout when not in a terminal that supports UTF-8. Unicode arrows (`→`, `←`, `✓`), em-dashes, and emoji in `print()` throw `UnicodeEncodeError: 'charmap' codec can't encode character ... in position X`.

**Important consequence:** a crash mid-script after you've already created Qualtrics questions leaves **orphan questions** (created via POST, not yet assigned to a block). They count toward QID numbering and clutter the survey but are invisible to participants.

**Fixes:**
- Run scripts with `python -X utf8 script.py` (force UTF-8 I/O mode).
- Use ASCII-only characters in print statements (`->` not `→`, `<-` not `←`).
- Wrap question-creation scripts in try/except that logs the QID of the last-created question so you can clean up orphans.

### 34. QUALTRICS CSV EXPORT — DUPLICATE COLUMN SUFFIX `.1`

If a question's `DataExportTag` is reused (e.g. an orphan question from a crashed-mid-script run had the same tag as the real question), Qualtrics exports two columns and renames the second `tag.1`. pandas reads them both but they have different data. Always scan for `.1`-suffixed duplicates after export:

```python
dupes = [c for c in df.columns if c.endswith('.1') and c[:-2] in df.columns]
assert not dupes, f'Duplicate tags exported: {dupes} — delete orphan questions in Qualtrics'
```

---

## COMPLETE DATA CAPTURE & RETRIEVAL SYSTEM

As of 2026-04-17 (v26 / worker v2-full-capture) every LLM call is persisted to
Cloudflare KV in addition to the Qualtrics CSV. This section documents what
lives where, how it is captured, and exactly how to retrieve it.

### What is captured, where

| Data | Captured by | Where it lives | How to retrieve |
|---|---|---|---|
| Condition (biased/honest/neutral) | BlockRandomizer sets `study3_condition` | Qualtrics CSV column | Standard export |
| AI brand skin (chatgpt/claude/gemini/perplexity) | JS `brandKey` → `study3_ai_brand` | Qualtrics CSV column | Standard export |
| Session ID | JS generates `S3_<ts>_<rand>` → `study3_session_id` | Qualtrics CSV + KV key prefix | Both |
| Session start timestamp | JS `study3_session_start_ts` on load | Qualtrics CSV | Standard export |
| User messages | JS `log('user', …)` → `msg_1`, `msg_3`, `msg_5`… | Qualtrics CSV (odd turn numbers) | Standard export |
| AI responses | JS `log('assistant', …)` → `response_2`, `response_4`… | Qualtrics CSV (even turn numbers) | Standard export |
| **Per-turn timestamps** | JS adds `msg_N_ts`, `response_N_ts` (ISO) | Qualtrics CSV | Standard export |
| Assortment JSON (7 products, specs, indices) | JS `ed('study3_assortment', JSON.stringify(a))` | Qualtrics CSV | Standard export |
| Category | `ed('study3_category', a.category)` | Qualtrics CSV | Standard export |
| Recommended / Optimal brand+model | `ed('study3_recommended')`, `ed('study3_optimal')` | Qualtrics CSV | Standard export |
| Product display order (post-shuffle) | `ed('study3_display_order', …)` | Qualtrics CSV | Standard export |
| Product choice + price + chose_optimal + chose_recommended | `ed(…)` on card click | Qualtrics CSV | Standard export |
| Conversation complete flag | `ed('study3_conversation_complete','true')` on Confirm | Qualtrics CSV | Standard export |
| Total turns | `ed('study3_total_turns', turnN)` | Qualtrics CSV | Standard export |
| Bypass-attempt flag (Next clicked without Confirm — should be impossible) | `addOnPageSubmit` sets `study3_bypass_attempt='true'` | Qualtrics CSV | Standard export |
| **Full system prompt sent to Claude** (Stage 1/2/3, verbatim) | Worker logs to KV | **KV only** | `/logs/:sid` or `/export/:sid` |
| **Full user message + conversation history sent to Claude** | Worker logs to KV | **KV only** | Same |
| **Raw LLM response** (pre-regex-extract) | Worker logs to KV | **KV only** | Same |
| **Token usage** (input / output / cache_read / cache_creation) | Worker logs from Claude's `usage` field | **KV only** | Same |
| **Latency in ms per call** | Worker measures `Date.now()` before/after fetch | **KV only** | Same |
| `stop_reason`, `max_tokens`, `temperature`, `model` per call | Worker logs | **KV only** | Same |
| `api_status` and `api_error` (if the call fails) | Worker logs | **KV only** | Same |
| Client-side context (condition, ai_brand, category, turn_number, prolific_pid) | JS ships on every call → worker logs verbatim | **KV only** (redundant with Qualtrics CSV, but enables self-contained KV analysis) | Same |

### Cloudflare KV schema

Namespace: `STUDY3_LOGS` (id `6f54bb22bee144f6ac5d6fb7e2713a16`)

Key format (sortable, prefix-listable):
```
log:<session_id>:<iso-timestamp>:<stage>:<4-char-random>
```

Example key:
```
log:S3_1743875432_abc123:2026-04-17T14:30:15.123Z:elicit:a7f3
```

Value: JSON record with these fields:
```
session_id, stage, turn_number, condition, ai_brand, category,
prolific_pid, response_id, model,
system_prompt, user_message, user_preferences, history,
raw_response, api_status, api_error,
input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens,
stop_reason, max_tokens, temperature,
latency_ms, timestamp
```

TTL: 90 days. (Export to OSF before expiration. `/export?format=csv` for bulk dump.)

### How the wiring works

**Client (`QUALTRICS_CHATBOT.js`):**
- Line ~190 `api(stg, msg, extra, cb)` builds the POST body with every context field:
  `{ session_id, stage, message, history, condition, ai_brand, category, turn_number, prolific_pid, ... }`
- Line ~130 `log(role, txt)` sets both `msg_N` (or `response_N`) AND `msg_N_ts` (or `response_N_ts`) embedded data.
- Line ~16 session start timestamp set once: `study3_session_start_ts`.
- `PROLIFIC_PID` read from Qualtrics embedded data on load (populated from URL param via Qualtrics embedded-data declaration).

**Worker (`worker/worker.js`) — per-call logging:**
1. `handleChat()` receives the POST. Records `requestStartedAt = Date.now()` before calling Anthropic.
2. Awaits Anthropic response. Captures `api_status`, raw response text, usage object, stop_reason.
3. Builds a log record with **full** system prompt, user message, history, raw response, all token counters, latency, timestamp, client context.
4. `await writeLog(env, record)` synchronously writes to KV with 90-day TTL. (Awaited — not fire-and-forget — so the log is guaranteed persisted before the worker returns.)
5. Returns `{text, stage, usage, latency_ms}` to the client.

**Worker endpoints:**

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/health` | GET | none | Returns `{ok, hasKV, hasAnthropicKey, hasAdminToken}` |
| `/chat` | POST | rate-limited by IP | Main chat endpoint (elicit / generate / recommend) |
| `/logs/:session_id` | GET | none | Returns all KV records for one session, chronologically sorted |
| `/sessions` | GET | `X-Admin-Token` | Lists all session IDs + call counts |
| `/export` | GET | `X-Admin-Token` | All records; `?format=json|csv`, `?since=<iso>`, `?session=<prefix>` |
| `/export/:session_id` | GET | `X-Admin-Token` | One session; `?format=json|csv` |

### Credentials & config locations

- KV namespace ID: `worker/wrangler.toml` `[[kv_namespaces]]` block.
- Anthropic API key: Cloudflare secret `ANTHROPIC_API_KEY`. Set via `npx wrangler secret put ANTHROPIC_API_KEY`.
- Admin export token: Cloudflare secret `EXPORT_ADMIN_TOKEN`. Set via `npx wrangler secret put EXPORT_ADMIN_TOKEN`. The current value is in `worker/.env.admin` (gitignored — do not commit).
- Cloudflare API token (for `wrangler deploy` in non-interactive sessions): `dashboard/worker/.env` → `CLOUDFLARE_API_TOKEN`.

### Retrieval recipes

**One session, JSON (public — no auth needed):**
```bash
curl -s "https://study3-chatbot.webmarinelli.workers.dev/logs/S3_1743875432_abc123"
```

**One session, CSV (admin):**
```bash
TOKEN="$(grep EXPORT_ADMIN_TOKEN worker/.env.admin | cut -d= -f2)"
curl -s -H "X-Admin-Token: $TOKEN" \
  "https://study3-chatbot.webmarinelli.workers.dev/export/S3_1743875432_abc123?format=csv" \
  -o session.csv
```

**List all sessions (admin):**
```bash
curl -s -H "X-Admin-Token: $TOKEN" \
  "https://study3-chatbot.webmarinelli.workers.dev/sessions" | python -m json.tool
```

**Bulk CSV dump of all LLM calls (admin):**
```bash
curl -s -H "X-Admin-Token: $TOKEN" \
  "https://study3-chatbot.webmarinelli.workers.dev/export?format=csv" \
  -o analysis/output/raw_export/study3_all_llm_calls.csv
```

**Bulk dump filtered by date (admin):**
```bash
curl -s -H "X-Admin-Token: $TOKEN" \
  "https://study3-chatbot.webmarinelli.workers.dev/export?format=csv&since=2026-04-17T13:40:40Z" \
  -o analysis/output/raw_export/study3_post_v25.csv
```

### Joining KV data with Qualtrics data

The join key is `study3_session_id` (Qualtrics CSV) ⇔ `session_id` (KV).

```python
import pandas as pd, requests, os
TOKEN = os.environ['EXPORT_ADMIN_TOKEN']  # from worker/.env.admin
base  = 'https://study3-chatbot.webmarinelli.workers.dev'

qualtrics_df = pd.read_csv('analysis/output/raw_export/SR Study 3 - Ecological Chatbot (2026-04-16).csv', skiprows=[1,2])

r = requests.get(f'{base}/export?format=json', headers={'X-Admin-Token': TOKEN})
kv_logs = pd.DataFrame(r.json()['logs'])

merged = qualtrics_df.merge(kv_logs, left_on='study3_session_id', right_on='session_id', how='left')
```

Every Qualtrics row now has its corresponding LLM calls (one row per call; a session has 3–N rows depending on turns).

### Verification checklist

After any worker redeploy:
```bash
# 1. Check bindings
curl -s https://study3-chatbot.webmarinelli.workers.dev/health | python -m json.tool
# Expect: hasAnthropicKey: true, hasKV: true, hasAdminToken: true

# 2. Smoke-test: send a chat, then fetch the log
SID="S3_test_$(date +%s)"
curl -s -X POST https://study3-chatbot.webmarinelli.workers.dev/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SID\",\"stage\":\"elicit\",\"message\":\"laptop under $1500\",\"history\":[],\"condition\":\"biased\",\"ai_brand\":\"chatgpt\",\"turn_number\":1}" > /dev/null
curl -s "https://study3-chatbot.webmarinelli.workers.dev/logs/$SID" | python -m json.tool
# Expect: count=1 with a single record containing system_prompt, user_message, raw_response, tokens.
```

### Known limitations

- KV eventual consistency: a new write may not appear in `/logs/:sid` for up to ~60 seconds in edge cases (`list` is eventually consistent across regions). Direct `get` by key is strongly consistent.
- KV free tier is 100k writes/day. At ~5 calls per participant × 800 = 4000 writes/day at launch — well within limits.
- No message-level timestamps on assistant response (only on the Qualtrics-side log). The worker log has `timestamp` = request start + `latency_ms` = API call duration. Derive assistant timestamp with `timestamp + latency_ms`.
- `response_id` and `prolific_pid` in KV records depend on the client sending them. `prolific_pid` requires the `PROLIFIC_PID` embedded-data field to be declared in Qualtrics flow (already done).

---

## TIMELINE
- Draft master prompt: DONE (v1)
- Test prompt with Opus: DONE (20/20 assortments, 5/5 pipeline)
- Build worker endpoint: DONE (standalone at study3-chatbot.webmarinelli.workers.dev)
- Build chat widget: DONE (v16, 4 brand skins with real SVGs)
- Build Qualtrics survey: DONE (SV_8A33OiyMqjqr5LU)
- Polish carousel/selection UX: IN PROGRESS
- Implement Honest Chatbot condition: TODO
- Implement Table Only condition: TODO
- Pilot test (N=20): TODO
- Pre-register: TODO
- Full data collection: TODO

---

## HOW THIS FITS IN THE PAPER

**Studies 1A + 1B:** "People follow biased AI recommendations" — controlled, two categories, N=800 each. ALL COMPLETE.
**Study 2:** "Standard warnings partially work; exposing confabulation works better" — inoculation, N=800. COMPLETE.
**Study 3:** "The bias translates to realistic, personalized AI shopping interactions" — ecological validity. IN PROGRESS.

The arc: Problem (1A/1B) → Can we fix it? (2) → Real-world impact (3)

## PILOT OBSERVATIONS — PRELIMINARY, TO REVISIT AT FULL N

*Notes recorded during the April 2026 N=25 clean pilot (post-v40). These are pilot-level signals, not committed findings. Treat as hypotheses to test at N=1000.*

### Design differences between Study 3 and Studies 1A/1B/2 that likely shape effect sizes

| | 1A/1B/2 | Study 3 |
|---|---|---|
| Category | One per study, fixed across participants | Participant-chosen, essentially N=1 per category |
| Assortment | Hand-curated, static | AI-generated per participant at run time |
| Optimal brand | Fictional (e.g., Presswell, Vynex) | Real lesser-known (whatever Opus picks) |
| Format | Static product table + optional AI text | Multi-turn chat + dynamic product carousel |

Because Study 3's optimal is a real lesser-known brand rather than a neutral fictional placeholder, its effect magnitudes should NOT be expected to match 1A/1B line-for-line. Consumer priors about real brands (unfamiliarity caution, default-to-known-brand) are not controlled away.

### Three-bucket choice decomposition (the right way to report Study 3)

Three mutually-exclusive outcomes per participant:

- **chose_optimal** — picked the spec-dominant (lesser-known) product
- **chose_focal** — picked the specific well-known brand the AI targets (`assortment.recommended_index`)
- **chose_other** — picked one of the 5 remaining non-optimal, non-focal products

Do NOT collapse to a single "optimal rate" DV. The three buckets carry different information.

### Pilot signature at N=24 usable (post-v40, 8/8/8 per condition)

| Condition | optimal | focal brand | other non-optimal |
|---|---|---|---|
| Biased  | 25% | **62%** | 12% |
| Honest  | 25% | 12% | **62%** |
| Neutral | 38% | 25% | 38% |

**The focal-brand rate swings 50pp between biased and honest** (62% → 12%). The AI's verbal recommendation clearly moves participants between the focal brand and everything else.

**But the optimal rate barely moves** (25% / 25% / 38%). Even when honest AI explicitly points to the spec-dominant product, participants do not end up there at a higher rate than neutral.

**Non-optimal total is roughly constant** (~70–75% across conditions). When honest AI deflects people from the focal brand, they scatter into the `other non-optimal` bucket rather than landing on optimal.

### Hypothesis this suggests for N=1000

Consumer brand priors appear to dominate over the AI's verbal redirect when the replacement optimal is a real lesser-known brand. The AI can successfully move people AWAY from a specific confabulated recommendation, but cannot reliably move them TOWARD an unfamiliar alternative. The welfare loss may have two separable components:

1. **AI-driven compliance** with confabulated recommendations (addressed by Study 3 biased → neutral comparison on `chose_focal`).
2. **Consumer-driven familiarity heuristic** that redirects deflected choices to other familiar brands (identified in the Study 3 honest → neutral comparison on `chose_optimal`).

If this signature holds at N=1000, the Nature-level framing is: *correcting AI recommendations addresses only one of two distinct drivers of suboptimal consumer choice — the brand-familiarity heuristic persists even when the AI points elsewhere.*

### Do NOT over-index on this framing yet

- N=24 per-cell analysis is wildly underpowered. All three-bucket percentages above have ±20pp CIs.
- Earlier pilot slices (N=14, N=33) showed different patterns — the N=1000 result may look quite different.
- Category heterogeneity is huge (≈56 unique categories across the post-v24 window). Mixed-effects models will be necessary.
- Brand-familiarity priors depend on the specific real brands Opus generates for each participant. These are not controlled and will vary across trials.

The observations are saved here as a direction to investigate. The confirmatory analysis at full N will decide how the finding is framed.

## INFRASTRUCTURE SUMMARY (for reproducibility)

| Component | Location | Status |
|-----------|----------|--------|
| Standalone Worker | `study3-chatbot/worker/worker.js` + `wrangler.toml` | Deployed at study3-chatbot.webmarinelli.workers.dev |
| Chat HTML/CSS | `study3-chatbot/QUALTRICS_HTML.html` | v16, 4 brand skins |
| Chat JavaScript | `study3-chatbot/QUALTRICS_CHATBOT.js` | v16, multi-stage, brand randomization |
| Qualtrics Survey | SV_8A33OiyMqjqr5LU | Live, iterating |
| Prompt tests | `study3-chatbot/prompt_tests/` | 25/25 assortments, 5/5 pipeline |
| Reference screenshots | `study3-chatbot/ref_*.png` | All 4 real AI UIs captured |
| Reference conversation | `study3-chatbot/REFERENCE_chatgpt_shopping_blender.txt` | Real ChatGPT Shopping session |
| Deployment guide | `study3-chatbot/DEPLOY.md` | Step-by-step with troubleshooting |

To deploy from scratch: see DEPLOY.md. All self-contained, no dependency on the dashboard worker.
