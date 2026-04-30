# Building an Interactive AI Chatbot Inside a Qualtrics Survey

Research conducted April 2026. Covers architecture patterns, working code, existing tools, and a recommended implementation using the existing Cloudflare Worker as a proxy.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Existing Tools and Platforms](#2-existing-tools-and-platforms)
3. [Architecture Patterns](#3-architecture-patterns)
4. [Qualtrics JavaScript Environment](#4-qualtrics-javascript-environment)
5. [Working Code: Direct API Approach](#5-working-code-direct-api-approach)
6. [Working Code: Proxy Approach (Stanford GSB)](#6-working-code-proxy-approach-stanford-gsb)
7. [Recommended Approach: Cloudflare Worker Proxy](#7-recommended-approach-cloudflare-worker-proxy)
8. [ChatGPT-Like CSS Styling](#8-chatgpt-like-css-styling)
9. [Conversation Data Capture](#9-conversation-data-capture)
10. [Qualtrics New Survey Taking Experience](#10-qualtrics-new-survey-taking-experience)
11. [Pre-scripted vs. Live API Responses](#11-pre-scripted-vs-live-api-responses)
12. [References and Sources](#12-references-and-sources)

---

## 1. Executive Summary

There are three viable approaches for embedding an AI chatbot inside a Qualtrics survey, ordered from simplest to most robust:

| Approach | Complexity | Security | Recommended? |
|----------|-----------|----------|-------------|
| **A. Third-party tool (G4R, QUAIL)** | Low | Good (hosted) | For quick prototyping only |
| **B. Direct API call from Qualtrics JS** | Medium | BAD (API key exposed in browser) | Never for production |
| **C. Proxy server (Cloudflare Worker)** | Medium-High | Good (key on server) | Yes, recommended |

**The recommended approach for this project**: Add a `/chat-proxy` endpoint to the existing Cloudflare Worker (`research-dashboard-claude.webmarinelli.workers.dev`). The worker already has `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` as secrets, handles CORS, and can serve as the proxy with approximately 50 lines of additional code.

---

## 2. Existing Tools and Platforms

### 2.1 G4R (GPT for Researchers) -- g4r.org

A free hosted platform by Jin Kim (arxiv: 2503.18303) that provides a turnkey solution for embedding GPT conversations in Qualtrics surveys.

**How it works:**
- Researcher creates a "GPT Interface" on g4r.org, configuring topic constraints, response tone, message limits, and labels.
- G4R provides a JavaScript snippet to paste into a Qualtrics question.
- The JS generates a random participant ID, stores it in a Qualtrics embedded data field (`g4r_pid`), and either opens a new tab or embeds the chat interface.
- After data collection, researchers download conversation logs as CSV from g4r.org and merge with Qualtrics response data using the participant ID.

**Limitations:**
- Hosted on a third party (data leaves your control).
- Uses ChatGPT specifically (not Claude or custom models).
- Limited UI customization.
- Opens in a separate tab by default (iframe embed is the alternative).

### 2.2 QUAIL (Qualtrics-AI Link)

Open-source software from Guenzel et al. (Journal of Business and Psychology, 2025) designed to integrate LLM-generated content into Qualtrics.

**Five use cases:**
1. LLM as research assistant
2. LLM as adaptive content creator
3. LLM as external resource
4. LLM as conversation partner
5. LLM as research confederate

**Key feature:** Copy-paste code block for Qualtrics XM, no programming expertise required.

### 2.3 Stanford GSB Behavioral Lab Implementation

The most production-ready open-source solution. Uses a Google Cloud Run proxy between Qualtrics and the LLM API. Full source at: https://github.com/gsbdarc/gsb-qualtrics-ai-chatbot

**Architecture:**
```
Qualtrics Survey (JS) --> Google Cloud Run Proxy --> Stanford AI Playground API
                              |
                         IP rate limiting (Firestore)
                         Origin validation (CORS)
                         API key hidden on server
```

### 2.4 QualtricsAIChatbot (Zarifhonarvar)

Simple single-file JavaScript implementation using the OpenAI Assistants API directly from Qualtrics. Source: https://github.com/alizarif/QualtricsAIChatbot

**WARNING:** This approach exposes the API key in the browser. Suitable only for understanding the pattern, not for production research.

---

## 3. Architecture Patterns

### Pattern A: Direct API Call (Insecure)

```
Participant's Browser
    |
    v
Qualtrics Survey Page (JavaScript)
    |-- fetch("https://api.openai.com/v1/chat/completions", {
    |       headers: { "Authorization": "Bearer sk-..." }  // EXPOSED!
    |   })
    v
OpenAI API
```

**Problems:**
- API key visible in browser dev tools to every participant.
- Any participant can steal and abuse the key.
- No rate limiting per participant.
- CORS may work (OpenAI allows browser requests) but Anthropic does not.

### Pattern B: Proxy Server (Secure, Recommended)

```
Participant's Browser
    |
    v
Qualtrics Survey Page (JavaScript)
    |-- fetch("https://your-proxy.workers.dev/chat-proxy", {
    |       body: JSON.stringify({ message, history, surveyId })
    |   })
    v
Cloudflare Worker (your-proxy.workers.dev)
    |-- validates origin (CORS)
    |-- rate limits by IP
    |-- injects API key from secrets
    |-- calls OpenAI/Anthropic API
    v
LLM API (key never leaves server)
```

### Pattern C: Hosted Third-Party (G4R, QUAIL)

```
Qualtrics Survey
    |-- JavaScript opens/embeds G4R interface
    v
g4r.org (hosted)
    |-- manages conversation
    |-- stores data
    v
Researcher downloads CSV from g4r.org
```

---

## 4. Qualtrics JavaScript Environment

### What Qualtrics allows in question JavaScript

Qualtrics provides a JavaScript editor for each question. Code runs in the participant's browser. Key API methods:

```javascript
// Entry points (lifecycle hooks)
Qualtrics.SurveyEngine.addOnload(function() { /* page loaded */ });
Qualtrics.SurveyEngine.addOnReady(function() { /* DOM ready */ });
Qualtrics.SurveyEngine.addOnUnload(function() { /* leaving page */ });

// Embedded data (OLD way -- deprecated in New Survey Experience)
Qualtrics.SurveyEngine.setEmbeddedData("fieldName", "value");
Qualtrics.SurveyEngine.getEmbeddedData("fieldName");

// Embedded data (NEW way -- required for New Survey Taking Experience)
// Fields must be prefixed with __js_ in the Survey Flow
Qualtrics.SurveyEngine.setJSEmbeddedData("fieldName", "value");
Qualtrics.SurveyEngine.getJSEmbeddedData("fieldName");

// DOM access
this.getQuestionContainer();     // the question's DOM element
this.getQuestionTextContainer(); // the question text area

// Navigation
this.hideNextButton();
this.showNextButton();
this.clickNextButton();
```

### CORS constraints

- Qualtrics JS runs in the browser, so all external `fetch()` calls are subject to CORS.
- The external server MUST return `Access-Control-Allow-Origin` headers that match the Qualtrics survey domain.
- OpenAI's API does allow browser CORS requests (but this exposes the key).
- Anthropic's API does NOT allow browser CORS requests (proxy required).
- A Cloudflare Worker can add the correct CORS headers.

### fetch() works in Qualtrics

Yes, `fetch()` and `XMLHttpRequest` both work in Qualtrics question JavaScript. Multiple confirmed implementations exist. Example of a working external API call from Qualtrics:

```javascript
let xmlHttp = new XMLHttpRequest();
xmlHttp.open('GET', 'https://example.com/api?param=value', false);
xmlHttp.send(null);
let result = xmlHttp.responseText;
```

### Key constraint

The external server must set `Access-Control-Allow-Origin` to include the Qualtrics survey domain (e.g., `https://okstatebusiness.az1.qualtrics.com` or `https://*.qualtrics.com`).

---

## 5. Working Code: Direct API Approach

This is the Zarifhonarvar implementation (https://github.com/alizarif/QualtricsAIChatbot). It uses the OpenAI Assistants API directly. **Do not use in production** because the API key is exposed.

Included here for reference and understanding the pattern:

```javascript
Qualtrics.SurveyEngine.addOnload(function() {
    var that = this;

    // OpenAI API configuration
    var apiKey = "Open_AI_API_KEY";        // EXPOSED IN BROWSER!
    var assistantId = "assistant_id";
    var threadId = null;

    // Create chat interface
    var chatContainer = document.createElement("div");
    chatContainer.id = "chat-container";
    chatContainer.style.height = "400px";
    chatContainer.style.overflowY = "scroll";
    chatContainer.style.border = "1px solid #ddd";
    chatContainer.style.borderRadius = "8px";
    chatContainer.style.padding = "15px";
    chatContainer.style.marginBottom = "15px";
    chatContainer.style.backgroundColor = "#f9f9f9";

    var inputBox = document.createElement("input");
    inputBox.type = "text";
    inputBox.id = "user-input";
    inputBox.style.width = "70%";
    inputBox.style.padding = "8px";
    inputBox.style.marginRight = "10px";
    inputBox.style.borderRadius = "4px";
    inputBox.style.border = "1px solid #ccc";

    var sendButton = document.createElement("button");
    sendButton.textContent = "Send";
    sendButton.onclick = sendMessage;
    sendButton.style.padding = "8px 15px";
    sendButton.style.backgroundColor = "#4CAF50";
    sendButton.style.color = "white";
    sendButton.style.border = "none";
    sendButton.style.borderRadius = "4px";
    sendButton.style.cursor = "pointer";

    // Append elements to the question container
    var container = this.getQuestionContainer();
    container.appendChild(chatContainer);
    container.appendChild(inputBox);
    container.appendChild(sendButton);

    // Send message and get response
    function sendMessage() {
        var userInput = inputBox.value;
        if (!userInput) return;

        displayMessage("User: " + userInput, "user-message");
        inputBox.value = "";

        // Create thread or add message
        fetch("https://api.openai.com/v1/threads" + (threadId ? "/" + threadId + "/messages" : ""), {
            method: "POST",
            headers: {
                "Authorization": "Bearer " + apiKey,
                "Content-Type": "application/json",
                "OpenAI-Beta": "assistants=v1"
            },
            body: JSON.stringify(threadId ? {
                role: "user",
                content: userInput
            } : {
                messages: [{ role: "user", content: userInput }]
            })
        })
        .then(response => response.json())
        .then(data => {
            threadId = threadId || data.id;
            return fetch("https://api.openai.com/v1/threads/" + threadId + "/runs", {
                method: "POST",
                headers: {
                    "Authorization": "Bearer " + apiKey,
                    "Content-Type": "application/json",
                    "OpenAI-Beta": "assistants=v1"
                },
                body: JSON.stringify({ assistant_id: assistantId })
            });
        })
        .then(response => response.json())
        .then(data => checkRunStatus(data.id))
        .catch(error => console.error('Error:', error));
    }

    function checkRunStatus(runId) {
        fetch("https://api.openai.com/v1/threads/" + threadId + "/runs/" + runId, {
            headers: {
                "Authorization": "Bearer " + apiKey,
                "OpenAI-Beta": "assistants=v1"
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === "completed") {
                getMessages();
            } else if (data.status === "failed") {
                displayMessage("Assistant: Sorry, there was an error.", "assistant-message");
            } else {
                setTimeout(() => checkRunStatus(runId), 1000);
            }
        });
    }

    function getMessages() {
        fetch("https://api.openai.com/v1/threads/" + threadId + "/messages", {
            headers: {
                "Authorization": "Bearer " + apiKey,
                "OpenAI-Beta": "assistants=v1"
            }
        })
        .then(response => response.json())
        .then(data => {
            var msg = data.data.find(msg => msg.role === "assistant");
            if (msg) {
                displayMessage("Assistant: " + msg.content[0].text.value, "assistant-message");
            }
        });
    }

    function displayMessage(message, className) {
        var el = document.createElement("p");
        el.textContent = message;
        el.className = className;
        el.style.padding = "10px";
        el.style.borderRadius = "8px";
        el.style.marginBottom = "10px";
        if (className === "user-message") {
            el.style.backgroundColor = "#e1f5fe";
        } else {
            el.style.backgroundColor = "#f0f4c3";
        }
        chatContainer.appendChild(el);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    inputBox.addEventListener("keypress", function(event) {
        if (event.key === "Enter") {
            event.preventDefault();
            sendMessage();
        }
    });
});
```

---

## 6. Working Code: Proxy Approach (Stanford GSB)

The Stanford GSB Behavioral Lab implementation is the most mature open-source solution. Source: https://github.com/gsbdarc/gsb-qualtrics-ai-chatbot

### 6.1 Qualtrics Question HTML (view.html)

The question text contains hidden textareas that bridge Qualtrics embedded data into DOM elements the JavaScript can read:

```html
<!-- Hidden bridge: Qualtrics piped text -> DOM elements -->
<div id="embedded-data-chat1" style="display:none;">
  <textarea id="safe-prompt-chat1">${e://Field/chat1_prompt}</textarea>
  <textarea id="safe-model-chat1">${e://Field/chat1_model}</textarea>
  <textarea id="safe-proxy-url-chat1">${e://Field/proxy_url}</textarea>
  <textarea id="safe-temperature-chat1">${e://Field/chat1_temperature}</textarea>
  <textarea id="safe-max-tokens-chat1">${e://Field/chat1_max_tokens}</textarea>
  <textarea id="safe-max-chats-chat1">${e://Field/chat1_max_chats}</textarea>
  <textarea id="safe-delay-per-word-chat1">${e://Field/chat1_delay_per_word}</textarea>
</div>

<div id="chat-container-chat1">
  <div id="chat-history-chat1">&nbsp;</div>
  <div id="chat-input-chat1">
    <input id="message-input-chat1" placeholder="Type your message here..." type="text" />
    <button id="send-button-chat1">Send</button>
  </div>
</div>
```

### 6.2 Qualtrics Question JavaScript (questions.js)

```javascript
Qualtrics.SurveyEngine.addOnReady(function () {

  var QUESTION_ID = this.questionId;
  var conversationHistory = [];

  // Read config from DOM bridge (populated by Qualtrics piped text)
  var MAX_CHATS = parseInt(document.getElementById("safe-max-chats-chat1").value, 10);
  if (isNaN(MAX_CHATS) || MAX_CHATS <= 0) MAX_CHATS = 10;

  var PROXY_URL = (document.getElementById("safe-proxy-url-chat1").value || "").trim();
  var DELAY_PER_WORD = parseFloat(document.getElementById("safe-delay-per-word-chat1").value);
  if (isNaN(DELAY_PER_WORD) || DELAY_PER_WORD < 0) DELAY_PER_WORD = 0;
  var MAX_DELAY_SECONDS = 10;

  // Append a message bubble to the chat
  function appendMessage(text, cssClasses) {
    var chatBox = document.getElementById("chat-history-chat1");
    if (!chatBox) return null;
    var el = document.createElement("div");
    el.classList.add("message");
    if (cssClasses) {
      cssClasses.split(/\s+/).filter(Boolean).forEach(function (cls) {
        el.classList.add(cls);
      });
    }
    el.textContent = text;
    chatBox.appendChild(el);
    chatBox.scrollTop = chatBox.scrollHeight;
    return el;
  }

  // Typing indicator (three dots animation)
  function showTypingIndicator() {
    var chatBox = document.getElementById("chat-history-chat1");
    if (!chatBox) return null;
    var el = document.createElement("div");
    el.classList.add("message", "bot-message", "typing-indicator");
    el.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    chatBox.appendChild(el);
    chatBox.scrollTop = chatBox.scrollHeight;
    return el;
  }

  function removeTypingIndicator(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  // Save conversation to Qualtrics embedded data
  function saveChatHistory() {
    Qualtrics.SurveyEngine.setEmbeddedData(
      "chat_history",
      JSON.stringify(conversationHistory)
    );
  }

  // Send message to proxy and handle response
  function sendMessage() {
    var messageInput = document.getElementById("message-input-chat1");
    if (!messageInput) return;
    var message = (messageInput.value || "").trim();
    if (!message) return;

    // Check turn limit
    var userTurns = conversationHistory.filter(function (x) {
      return x.role === "user";
    }).length;
    if (userTurns >= MAX_CHATS) {
      appendMessage("Chat limit reached. Please continue the survey.", "bot-message");
      return;
    }

    // Display user message
    appendMessage(message, "user-message");
    conversationHistory.push({
      role: "user",
      content: message,
      time: new Date().toISOString(),
      question_id: QUESTION_ID
    });
    saveChatHistory();
    messageInput.value = "";

    // Show typing dots
    var typingEl = showTypingIndicator();

    // Read model config from DOM
    var model = (document.getElementById("safe-model-chat1").value || "").trim() || "gpt-4o";
    var temperature = parseFloat(document.getElementById("safe-temperature-chat1").value);
    if (isNaN(temperature)) temperature = 0.7;
    var maxTokens = parseInt(document.getElementById("safe-max-tokens-chat1").value, 10);
    if (isNaN(maxTokens)) maxTokens = 300;

    // Call proxy
    fetch(PROXY_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: message,
        system: document.getElementById("safe-prompt-chat1").value,
        history: conversationHistory,
        model: model,
        temperature: temperature,
        max_tokens: maxTokens
      })
    })
    .then(function (response) { return response.json(); })
    .then(function (data) {
      var botMessage = (data && data.text ? data.text.trim() : "(no response)");

      // Dynamic delay to simulate typing
      var wordCount = botMessage.split(/\s+/).filter(Boolean).length;
      var dynamicDelay = Math.min(wordCount * DELAY_PER_WORD, MAX_DELAY_SECONDS) * 1000;

      setTimeout(function () {
        removeTypingIndicator(typingEl);
        appendMessage(botMessage, "bot-message");
        conversationHistory.push({
          role: "assistant",
          content: botMessage,
          time: new Date().toISOString(),
          question_id: QUESTION_ID
        });
        saveChatHistory();
      }, dynamicDelay);
    })
    .catch(function (error) {
      console.error("Proxy fetch error:", error);
      removeTypingIndicator(typingEl);
      appendMessage("Sorry, something went wrong. Please try again.", "bot-message");
    });
  }

  // Wire up button and Enter key
  var sendButton = document.getElementById("send-button-chat1");
  if (sendButton) sendButton.addEventListener("click", sendMessage);

  var messageInput = document.getElementById("message-input-chat1");
  if (messageInput) {
    messageInput.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
      }
    });
  }
});
```

### 6.3 Chat CSS (styling.css)

```css
#chat-container-chat1 {
  width: 100%;
  max-height: 400px;
  border: 1px solid #ddd;
  border-radius: 10px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  margin: 0 auto;
}

#chat-history-chat1 {
  height: calc(100% - 56px);
  overflow-y: auto;
  padding: 10px;
}

.message {
  display: flex;
  flex-direction: column;
  margin: 10px 0;
}

.user-message {
  margin-left: auto;
  max-width: 70%;
  padding: 0.5rem 0.875rem;
  border-radius: 12px 12px 0 12px;
  line-height: 1.5;
  word-wrap: break-word;
  width: fit-content;
  font-family: Helvetica, Arial, sans-serif;
  background-color: #007AFF;
  color: white;
}

.bot-message {
  max-width: 70%;
  padding: 0.5rem 0.875rem;
  border-radius: 12px 12px 12px 0;
  line-height: 1.5;
  word-wrap: break-word;
  width: fit-content;
  font-family: Helvetica, Arial, sans-serif;
  background-color: #F2F2F2;
  color: #333;
}

#chat-input-chat1 {
  display: flex;
  align-items: center;
  padding: 10px;
  background-color: #F9F9F9;
  width: 100%;
  box-sizing: border-box;
}

#message-input-chat1 {
  flex: 1;
  margin-right: 10px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  box-sizing: border-box;
}

#send-button-chat1 {
  background-color: #007AFF;
  border: none;
  color: white;
  padding: 10px;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

#send-button-chat1:hover {
  background-color: #0066CC;
}

/* Typing indicator animation */
.typing-indicator {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 4px;
  padding: 0.5rem 0.875rem;
}

.typing-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #999;
  animation: blink 1.4s infinite both;
}
.typing-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator .dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes blink {
  0%, 80%, 100% { opacity: 0.3; }
  40% { opacity: 1; }
}
```

### 6.4 Proxy Backend (Python/Flask on Google Cloud Run)

The Stanford proxy validates the origin, rate-limits by IP using Firestore, injects the API key from server environment, and forwards to the LLM API. The response format is `{ "text": "..." }`.

---

## 7. Recommended Approach: Cloudflare Worker Proxy

The existing dashboard worker at `https://research-dashboard-claude.webmarinelli.workers.dev` already has:
- `ANTHROPIC_API_KEY` (for Claude)
- `OPENAI_API_KEY` (for GPT)
- CORS handling via `corsHeaders()` function
- Rate limiting via `checkRateLimit()`
- All infrastructure deployed and running

### 7.1 Worker Endpoint to Add

Add approximately 60 lines to the worker to create a `/chat-proxy` endpoint:

```javascript
// ─── Qualtrics Chat Proxy ─────────────────────────────────────────────────────

async function handleChatProxy(request, env, cors) {
  // Validate origin -- restrict to Qualtrics domains
  const origin = request.headers.get('Origin') || '';
  const qualtricsOrigins = [
    'https://okstatebusiness.az1.qualtrics.com',
    'https://okstate.co1.qualtrics.com',
    // Add other institutional Qualtrics domains as needed
  ];
  if (!qualtricsOrigins.some(o => origin.startsWith(o))) {
    return jsonResponse({ error: 'Unauthorized origin' }, 403, cors);
  }

  const body = await request.json();
  const { message, history, systemPrompt, model, surveyId, participantId } = body;

  if (!message) {
    return jsonResponse({ error: 'Missing message' }, 400, cors);
  }

  // Build messages array for chat completions
  const messages = [];
  if (systemPrompt) {
    messages.push({ role: 'system', content: systemPrompt });
  }

  // Add conversation history (only role + content, strip metadata)
  if (Array.isArray(history)) {
    for (const h of history) {
      if (h.role && h.content) {
        messages.push({ role: h.role, content: h.content });
      }
    }
  }

  // Add current message
  messages.push({ role: 'user', content: message });

  try {
    // Use OpenAI by default, or Anthropic if model starts with 'claude'
    const useAnthropic = (model || '').startsWith('claude');

    let text;
    if (useAnthropic) {
      const res = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'x-api-key': env.ANTHROPIC_API_KEY,
          'anthropic-version': '2023-06-01',
          'content-type': 'application/json',
        },
        body: JSON.stringify({
          model: model || 'claude-sonnet-4-20250514',
          max_tokens: 500,
          system: systemPrompt || '',
          messages: messages.filter(m => m.role !== 'system'),
        }),
      });
      const data = await res.json();
      text = data.content?.[0]?.text || '(no response)';
    } else {
      const res = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${env.OPENAI_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: model || 'gpt-4o',
          messages: messages,
          max_tokens: 500,
          temperature: 0.7,
        }),
      });
      const data = await res.json();
      text = data.choices?.[0]?.message?.content || '(no response)';
    }

    return jsonResponse({ text }, 200, {
      ...cors,
      'Access-Control-Allow-Origin': origin,
    });
  } catch (err) {
    console.error('[ChatProxy] Error:', err.message);
    return jsonResponse({ error: 'AI service error' }, 502, cors);
  }
}
```

### 7.2 Route Registration

Add to the worker's main router (`export default { async fetch(...) }`) alongside the existing `switch(path)`:

```javascript
case '/chat-proxy': return handleChatProxy(request, env, cors);
```

### 7.3 CORS Update

The existing `corsHeaders()` function already handles CORS. However, the `ALLOWED_ORIGINS` env var in the worker should be updated to include the Qualtrics survey domains:

```
ALLOWED_ORIGINS=https://affonsomarine.github.io,https://okstatebusiness.az1.qualtrics.com
```

### 7.4 Qualtrics JavaScript (using the worker proxy)

This is the complete, self-contained JavaScript to paste into a Qualtrics question. It creates the chat UI, calls the worker proxy, manages conversation history, and saves everything to embedded data.

```javascript
Qualtrics.SurveyEngine.addOnReady(function() {
  var that = this;
  var PROXY_URL = "https://research-dashboard-claude.webmarinelli.workers.dev/chat-proxy";
  var MAX_TURNS = 5;
  var conversationHistory = [];

  // System prompt for the AI shopping assistant
  var SYSTEM_PROMPT = "You are a helpful AI shopping assistant. " +
    "Help the user find the right product based on their needs. " +
    "Ask clarifying questions about their preferences, budget, and use case. " +
    "Provide specific product recommendations with brief explanations. " +
    "Keep responses concise (2-3 sentences).";

  // Hide the default question text and next button
  var questionText = that.getQuestionTextContainer();
  questionText.style.display = "none";
  that.hideNextButton();

  // ── Build Chat UI ──
  var container = that.getQuestionContainer();

  // Inject CSS
  var style = document.createElement("style");
  style.textContent = [
    ".chat-wrapper { max-width: 600px; margin: 0 auto; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }",
    ".chat-header { background: #343541; color: white; padding: 12px 16px; border-radius: 8px 8px 0 0; font-size: 14px; font-weight: 600; }",
    ".chat-messages { height: 350px; overflow-y: auto; padding: 16px; background: #fff; border-left: 1px solid #e5e5e5; border-right: 1px solid #e5e5e5; }",
    ".chat-msg { margin-bottom: 16px; display: flex; gap: 12px; }",
    ".chat-msg.user { flex-direction: row-reverse; }",
    ".chat-avatar { width: 30px; height: 30px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 14px; flex-shrink: 0; }",
    ".chat-msg.bot .chat-avatar { background: #19c37d; color: white; }",
    ".chat-msg.user .chat-avatar { background: #7c3aed; color: white; }",
    ".chat-bubble { max-width: 80%; padding: 10px 14px; border-radius: 8px; font-size: 14px; line-height: 1.5; }",
    ".chat-msg.bot .chat-bubble { background: #f7f7f8; color: #374151; }",
    ".chat-msg.user .chat-bubble { background: #7c3aed; color: white; }",
    ".chat-input-area { display: flex; gap: 8px; padding: 12px; background: #fff; border: 1px solid #e5e5e5; border-top: none; border-radius: 0 0 8px 8px; }",
    ".chat-input-area input { flex: 1; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; outline: none; }",
    ".chat-input-area input:focus { border-color: #7c3aed; }",
    ".chat-input-area button { padding: 10px 20px; background: #19c37d; color: white; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; font-weight: 500; }",
    ".chat-input-area button:hover { background: #15a366; }",
    ".chat-input-area button:disabled { background: #d1d5db; cursor: not-allowed; }",
    ".chat-typing { display: flex; gap: 4px; align-items: center; padding: 10px 14px; }",
    ".chat-typing span { width: 6px; height: 6px; border-radius: 50%; background: #999; animation: chatBlink 1.4s infinite both; }",
    ".chat-typing span:nth-child(2) { animation-delay: 0.2s; }",
    ".chat-typing span:nth-child(3) { animation-delay: 0.4s; }",
    "@keyframes chatBlink { 0%,80%,100% { opacity: 0.3; } 40% { opacity: 1; } }",
    ".chat-status { text-align: center; padding: 8px; font-size: 12px; color: #6b7280; }",
  ].join("\n");
  container.appendChild(style);

  var wrapper = document.createElement("div");
  wrapper.className = "chat-wrapper";
  wrapper.innerHTML = [
    '<div class="chat-header">AI Shopping Assistant</div>',
    '<div class="chat-messages" id="chatMessages"></div>',
    '<div class="chat-input-area">',
    '  <input type="text" id="chatInput" placeholder="Ask about products..." />',
    '  <button id="chatSend">Send</button>',
    '</div>',
    '<div class="chat-status" id="chatStatus"></div>',
  ].join("\n");
  container.appendChild(wrapper);

  var messagesDiv = document.getElementById("chatMessages");
  var inputEl = document.getElementById("chatInput");
  var sendBtn = document.getElementById("chatSend");
  var statusDiv = document.getElementById("chatStatus");

  // ── Chat Functions ──

  function addMessage(role, text) {
    var msgDiv = document.createElement("div");
    msgDiv.className = "chat-msg " + (role === "user" ? "user" : "bot");
    var avatar = document.createElement("div");
    avatar.className = "chat-avatar";
    avatar.textContent = role === "user" ? "Y" : "AI";
    var bubble = document.createElement("div");
    bubble.className = "chat-bubble";
    bubble.textContent = text;
    msgDiv.appendChild(avatar);
    msgDiv.appendChild(bubble);
    messagesDiv.appendChild(msgDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  function showTyping() {
    var el = document.createElement("div");
    el.className = "chat-msg bot";
    el.id = "typingIndicator";
    el.innerHTML = '<div class="chat-avatar" style="background:#19c37d;color:white">AI</div>' +
      '<div class="chat-bubble"><div class="chat-typing"><span></span><span></span><span></span></div></div>';
    messagesDiv.appendChild(el);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  function removeTyping() {
    var el = document.getElementById("typingIndicator");
    if (el) el.remove();
  }

  function saveHistory() {
    Qualtrics.SurveyEngine.setEmbeddedData(
      "chat_history",
      JSON.stringify(conversationHistory)
    );
    Qualtrics.SurveyEngine.setEmbeddedData(
      "chat_turn_count",
      String(conversationHistory.filter(function(m) { return m.role === "user"; }).length)
    );
  }

  function sendMessage() {
    var text = (inputEl.value || "").trim();
    if (!text) return;

    var userTurns = conversationHistory.filter(function(m) { return m.role === "user"; }).length;
    if (userTurns >= MAX_TURNS) {
      statusDiv.textContent = "You have reached the conversation limit. Please click Next to continue.";
      inputEl.disabled = true;
      sendBtn.disabled = true;
      that.showNextButton();
      return;
    }

    addMessage("user", text);
    conversationHistory.push({ role: "user", content: text, time: new Date().toISOString() });
    saveHistory();
    inputEl.value = "";
    sendBtn.disabled = true;
    showTyping();

    fetch(PROXY_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: conversationHistory,
        systemPrompt: SYSTEM_PROMPT,
        model: "gpt-4o"
      })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      removeTyping();
      var reply = (data && data.text) ? data.text.trim() : "(no response)";
      addMessage("bot", reply);
      conversationHistory.push({ role: "assistant", content: reply, time: new Date().toISOString() });
      saveHistory();
      sendBtn.disabled = false;
      inputEl.focus();

      // Check if max turns reached
      var newUserTurns = conversationHistory.filter(function(m) { return m.role === "user"; }).length;
      if (newUserTurns >= MAX_TURNS) {
        statusDiv.textContent = "Conversation complete. Please click Next to continue.";
        inputEl.disabled = true;
        sendBtn.disabled = true;
        that.showNextButton();
      }
    })
    .catch(function(err) {
      removeTyping();
      addMessage("bot", "Sorry, something went wrong. Please try again.");
      sendBtn.disabled = false;
      console.error("Chat proxy error:", err);
    });
  }

  // Wire events
  sendBtn.addEventListener("click", sendMessage);
  inputEl.addEventListener("keydown", function(e) {
    if (e.key === "Enter") { e.preventDefault(); sendMessage(); }
  });

  // Initial greeting
  var greeting = "Hello! I'm an AI shopping assistant. What kind of product are you looking for today?";
  addMessage("bot", greeting);
  conversationHistory.push({ role: "assistant", content: greeting, time: new Date().toISOString() });
  saveHistory();
  inputEl.focus();
});
```

### 7.5 Qualtrics Survey Flow Setup

In the Survey Flow editor, add an Embedded Data block at the top with these fields:

```
chat_history    (leave value blank)
chat_turn_count (leave value blank)
```

If using the New Survey Taking Experience, prefix with `__js_`:

```
__js_chat_history    (leave value blank)
__js_chat_turn_count (leave value blank)
```

And change `setEmbeddedData` to `setJSEmbeddedData` in the JavaScript code.

---

## 8. ChatGPT-Like CSS Styling

To make the chat interface look like ChatGPT's interface (dark header, clean bubbles, green/purple avatars), the code in Section 7.4 already includes a ChatGPT-inspired design. Key design elements:

- Dark header bar (`#343541`, matching ChatGPT's sidebar color)
- Clean white message area
- Green AI avatar (`#19c37d`, ChatGPT's green)
- Purple user avatar (`#7c3aed`)
- Rounded message bubbles
- Three-dot typing animation
- System font stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI'`)

For an even more faithful ChatGPT clone, the styling could be extended with:
- Markdown rendering in bot responses (using a lightweight library like `marked.js`)
- Code syntax highlighting
- Wider message bubbles (full-width, like ChatGPT)

---

## 9. Conversation Data Capture

### What gets saved to Qualtrics embedded data

The `chat_history` embedded data field contains a JSON array:

```json
[
  {
    "role": "assistant",
    "content": "Hello! I'm an AI shopping assistant. What kind of product are you looking for today?",
    "time": "2026-04-13T15:30:00.000Z"
  },
  {
    "role": "user",
    "content": "I need wireless earbuds under $100",
    "time": "2026-04-13T15:30:15.000Z"
  },
  {
    "role": "assistant",
    "content": "Great choice! For wireless earbuds under $100, I'd recommend considering...",
    "time": "2026-04-13T15:30:18.000Z"
  }
]
```

### Embedded data size limits

Qualtrics embedded data fields have a practical limit of approximately 20,000 characters. For a 5-turn conversation, this is rarely an issue (a typical conversation is 2,000-5,000 characters). For longer conversations, consider:
- Truncating early messages
- Saving only the last N messages
- Logging to an external database (e.g., Firestore) via the proxy

### Additional metadata to capture

The proxy endpoint could also log conversations server-side (in Firestore or R2) with metadata like:
- Participant ID (from Qualtrics)
- Survey ID
- Condition assignment
- Timestamps
- IP address (for quality checks)

---

## 10. Qualtrics New Survey Taking Experience

As of 2025, Qualtrics is rolling out a "New Survey Taking Experience" (formerly "Simple Layout") that introduces breaking changes for custom JavaScript. Key differences:

| Feature | Legacy | New Experience |
|---------|--------|---------------|
| jQuery | Included by default | NOT included; load manually or use vanilla JS |
| `setEmbeddedData()` | Works | DEPRECATED; use `setJSEmbeddedData()` |
| Embedded data prefix | None | Must prefix with `__js_` in Survey Flow |
| HTML structure | Legacy classes | Modernized, different class names |
| `getQuestionContainer()` | Works | Works (unchanged) |

**Recommendation:** Write all JavaScript using vanilla JS (no jQuery dependency) and use `setJSEmbeddedData()` with the `__js_` prefix. The code examples in this document already follow these practices (except for using `setEmbeddedData` which should be swapped to `setJSEmbeddedData` if using the New Experience).

---

## 11. Pre-scripted vs. Live API Responses

### Option A: Live API responses (recommended for realism)

Use the proxy approach described above. The AI generates responses in real time based on the conversation context. Benefits:
- Natural, adaptive conversation
- Handles unexpected participant questions
- More ecologically valid

### Option B: Pre-scripted responses (for maximum control)

For studies requiring exact control over AI responses, the JavaScript can use a decision tree instead of calling an API:

```javascript
var scriptedResponses = {
  "default": "That's a great question! I'd be happy to help you find the right product.",
  "earbuds": "For wireless earbuds, I'd recommend the Sony WF-1000XM5 for premium quality, or the Samsung Galaxy Buds FE for great value under $100.",
  "headphones": "For headphones, the Sony WH-1000XM5 offers excellent noise cancellation, while the Audio-Technica ATH-M50x is a great studio option.",
  // ... more responses
};

function getScriptedResponse(userMessage) {
  var lower = userMessage.toLowerCase();
  for (var key in scriptedResponses) {
    if (lower.includes(key)) return scriptedResponses[key];
  }
  return scriptedResponses["default"];
}
```

### Option C: Hybrid (controlled but natural)

Use the live API but with a highly constrained system prompt that limits the AI to a specific set of products and recommendation patterns. This combines naturalness with experimental control.

---

## 12. References and Sources

### Academic Papers

- Kim, J. (2025). How to Capture and Study Conversations Between Research Participants and ChatGPT: GPT for Researchers (g4r.org). arXiv:2503.18303. https://arxiv.org/abs/2503.18303
- Guenzel, N. et al. (2025). Participant Interactions with Artificial Intelligence: Using Large Language Models to Generate Research Materials for Surveys and Experiments. Journal of Business and Psychology. https://link.springer.com/article/10.1007/s10869-025-10035-6
- Zarifhonarvar, A. (2024). Integrating AI Chatbot into Qualtrics Surveys. SSRN. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4964908

### GitHub Repositories

- Stanford GSB Qualtrics AI Chatbot: https://github.com/gsbdarc/gsb-qualtrics-ai-chatbot (most complete implementation; Google Cloud Run proxy, Terraform, GitHub Actions deployment)
- QualtricsAIChatbot (Zarifhonarvar): https://github.com/alizarif/QualtricsAIChatbot (simple direct API approach; educational but insecure)
- LUCID Toolkit: https://github.com/amgarv/LUCID_TOOL_BACKEND (Flask backend proxy for Qualtrics chatbot experiments)

### Qualtrics Community Threads

- Integrating/embedding ChatGPT for multiple turns: https://community.qualtrics.com/custom-code-12/integrating-embedding-chat-gpt-for-multiple-turns-26923
- Embedding ChatGPT: https://community.qualtrics.com/custom-code-12/embedding-chatgpt-24717
- Embedding a chatbot in a Qualtrics survey: https://community.qualtrics.com/survey-platform-54/embedding-a-chatbot-in-a-qualtrics-survey-26726
- Integrate AI Chatbot into survey: https://community.qualtrics.com/survey-platform-54/integrate-ai-chatbot-into-survey-26254
- New Survey Taking Experience breaking JS: https://community.qualtrics.com/survey-platform-54/new-survey-taking-experience-is-breaking-my-javascript-32675
- Updated JavaScript for New Survey Experience: https://community.qualtrics.com/custom-code-12/updated-javascript-for-new-survey-taking-experience-32144

### OpenAI Community

- Qualtrics within-survey live chat integration: https://community.openai.com/t/qualtrics-within-survey-live-chat-integration/355146
- Solutions for academic research participants engaging ChatGPT: https://community.openai.com/t/solutions-for-having-academic-research-participants-engage-chat-gpt-e-g-qualtrics/1115168

### Tutorials

- Creating AI-Powered Follow-Up Questions in Qualtrics: https://tailoredexperiments.com/tutorial2.html
- Cloudflare Workers CORS proxy docs: https://developers.cloudflare.com/workers/examples/cors-header-proxy/

### Tools

- G4R (GPT for Researchers): https://g4r.org/
- Qualtrics JavaScript API: https://api.qualtrics.com/82bd4d5c331f1-qualtrics-java-script-question-api-class
- Qualtrics Add JavaScript docs: https://www.qualtrics.com/support/survey-platform/survey-module/question-options/add-javascript/

---

## Existing Worker Status

The dashboard worker at `https://research-dashboard-claude.webmarinelli.workers.dev` does NOT currently have a `/chat-proxy` endpoint. It has Qualtrics-related tools (`qualtrics_check`, `qualtrics_responses`, `qualtrics_manage`) for the WhatsApp bot's agentic loop, but no public-facing chat proxy for survey integration. The Qualtrics API token, Anthropic API key, and OpenAI API key are already configured as worker secrets, so adding the proxy endpoint requires only code changes to `worker.js` and redeployment.
