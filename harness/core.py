"""
Core API Callers for Double Alignment Experiments
==================================================
Adapted from cognitive-traps-jcr/v2_revision/test_models.py
Text-only version (no image encoding needed for shopping tasks).
"""

import os
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_RETRIES = 6
API_CALL_DELAY = 3.0  # seconds between calls (avoids Gemini RPM limits)


def load_env():
    """Load .env file from config directory."""
    env_path = Path(__file__).resolve().parent.parent / "config" / ".env"
    if not env_path.exists():
        print(f"WARNING: No .env file found at {env_path}")
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()


def check_providers() -> set[str]:
    """Check which API providers have keys configured. Returns set of provider names."""
    available = set()
    if os.environ.get("ANTHROPIC_API_KEY"):
        available.add("anthropic")
    if os.environ.get("OPENAI_API_KEY"):
        available.add("openai")
    if os.environ.get("GOOGLE_API_KEY"):
        available.add("google")
    if os.environ.get("OPENROUTER_API_KEY"):
        available.add("openrouter")
    if os.environ.get("GOOGLE_VERTEX_API_KEY"):
        available.add("google_vertex")
    if os.environ.get("TOGETHER_API_KEY"):
        available.add("together")
    return available


# ---------------------------------------------------------------------------
# API callers (text-only, no images)
# ---------------------------------------------------------------------------

def call_anthropic(model_id: str, system_prompt: str, user_message: str,
                   thinking: bool = False, max_tokens: int = 1024,
                   temperature: float = 1.0) -> dict:
    """Send text prompt to Anthropic API. Returns dict with text, tokens."""
    import anthropic
    client = anthropic.Anthropic()

    messages = [{"role": "user", "content": user_message}]

    kwargs = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system_prompt:
        kwargs["system"] = system_prompt
    # Anthropic does not support temperature with extended thinking.
    # Per-model thinking format (verified against Anthropic docs April 2026):
    #   Haiku 4.5 / 4.6+: legacy {"type":"enabled","budget_tokens":N} ONLY.
    #     Adaptive returns "adaptive thinking is not supported on this model".
    #   Sonnet 4.6 / Opus 4.6+ / Opus 4.7: adaptive {"type":"adaptive"} +
    #     output_config={"effort":"high"}. Legacy budget_tokens deprecated on
    #     Sonnet/Opus 4.6 and REJECTED entirely on Opus 4.7.
    if thinking:
        if "haiku" in model_id:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": 4096}
        else:
            kwargs["thinking"] = {"type": "adaptive"}
            kwargs["output_config"] = {"effort": "high"}
        kwargs["max_tokens"] = 8192
    else:
        kwargs["temperature"] = temperature

    response = client.messages.create(**kwargs)

    text = ""
    thinking_text = ""
    for block in response.content:
        if block.type == "text":
            text = block.text
        elif block.type == "thinking":
            thinking_text = block.thinking

    return {
        "text": text,
        "thinking": thinking_text,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "model_id": model_id,
    }


def call_openai(model_id: str, system_prompt: str, user_message: str,
                thinking: bool = False, max_tokens: int = 1024,
                temperature: float = 1.0) -> dict:
    """Send text prompt to OpenAI API. Returns dict with text, tokens."""
    import openai
    client = openai.OpenAI()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})

    # gpt-5.2-pro requires the Responses API
    if model_id == "gpt-5.2-pro":
        input_msgs = []
        if system_prompt:
            input_msgs.append({"role": "system", "content": system_prompt})
        input_msgs.append({"role": "user", "content": user_message})
        response = client.responses.create(
            model=model_id, input=input_msgs, temperature=temperature,
        )
        input_tokens = getattr(response.usage, "input_tokens", 0) or 0
        output_tokens = getattr(response.usage, "output_tokens", 0) or 0
        return {
            "text": response.output_text or "",
            "thinking": "",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model_id": model_id,
        }

    kwargs = {"model": model_id, "messages": messages, "temperature": temperature}

    # Newer chat-completion models require max_completion_tokens (and silently
    # ignore max_tokens). All GPT-5.x including 5.4 family use the new param.
    uses_new_param = (
        model_id in (
            "gpt-5-mini", "gpt-5.1-chat-latest", "gpt-5.2-chat-latest",
            "gpt-5-chat-latest",
        )
        or model_id.startswith("gpt-5.4")
        or model_id.startswith("gpt-5.")
    )
    if uses_new_param:
        kwargs["max_completion_tokens"] = max_tokens * 2
    else:
        kwargs["max_tokens"] = max_tokens

    # Reasoning effort for the new GPT-5.x family. Default API behaviour is
    # reasoning_effort="none" (no reasoning tokens). When the registered
    # model_cfg has thinking=True, request high reasoning effort. Note: in
    # chat.completions the parameter is `reasoning_effort` (snake_case
    # top-level), not nested `reasoning: {effort: ...}` (that's the
    # Responses API form).
    if thinking and (model_id.startswith("gpt-5") or
                      model_id.startswith("o1") or model_id.startswith("o3")):
        kwargs["reasoning_effort"] = "high"
        # Reasoning tokens count toward output budget; bump headroom.
        if "max_completion_tokens" in kwargs:
            kwargs["max_completion_tokens"] = max(kwargs["max_completion_tokens"], 4096)

    response = client.chat.completions.create(**kwargs)

    input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(response.usage, "completion_tokens", 0) or 0

    return {
        "text": response.choices[0].message.content or "",
        "thinking": "",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model_id": model_id,
    }


def call_google(model_id: str, system_prompt: str, user_message: str,
                thinking: bool = False, max_tokens: int = 1024,
                temperature: float = 1.0) -> dict:
    """Send text prompt to Google GenAI API. Returns dict with text, tokens."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

    config_kwargs = {"max_output_tokens": max_tokens, "temperature": temperature}

    # System instruction (Gemma models don't support developer instructions,
    # so prepend system prompt to user message instead)
    is_gemma = model_id.startswith("gemma")
    if system_prompt and not is_gemma:
        config_kwargs["system_instruction"] = system_prompt
    elif system_prompt and is_gemma:
        user_message = f"{system_prompt}\n\n{user_message}"

    # Thinking configuration by model generation
    if model_id.startswith("gemini-3"):
        is_pro = "pro" in model_id
        if thinking:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level="high")
        else:
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level="low" if is_pro else "minimal"
            )
    elif model_id.startswith("gemini-2.5"):
        is_pro = "pro" in model_id
        is_lite = "lite" in model_id
        if thinking:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=-1)
        elif is_pro:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=128)
        elif not is_lite:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

    response = client.models.generate_content(
        model=model_id,
        contents=[user_message],
        config=types.GenerateContentConfig(**config_kwargs),
    )

    input_tokens = 0
    output_tokens = 0
    if response.usage_metadata:
        input_tokens = response.usage_metadata.prompt_token_count or 0
        output_tokens = response.usage_metadata.candidates_token_count or 0

    text = response.text if response.text else ""

    return {
        "text": text,
        "thinking": "",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model_id": model_id,
    }


# ---------------------------------------------------------------------------
# Google Vertex AI (Standard — service account auth, separate quotas from AI Studio)
# ---------------------------------------------------------------------------

# Cache for the Vertex AI service account client (avoid re-creating per call)
_vertex_sa_client = None

def _get_vertex_sa_client():
    """Get or create a Vertex AI client using service account credentials."""
    global _vertex_sa_client
    if _vertex_sa_client is not None:
        return _vertex_sa_client

    from google import genai
    from google.oauth2 import service_account

    sa_key_path = Path(__file__).resolve().parent.parent / "config" / "vertex-sa-key.json"
    if not sa_key_path.exists():
        raise FileNotFoundError(f"Service account key not found at {sa_key_path}")

    credentials = service_account.Credentials.from_service_account_file(
        str(sa_key_path),
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )

    location = os.environ.get("VERTEX_LOCATION", "us-east1")
    _vertex_sa_client = genai.Client(
        vertexai=True,
        project="gen-lang-client-0609780914",
        location=location,
        credentials=credentials,
    )
    return _vertex_sa_client


def call_google_vertex(model_id: str, system_prompt: str, user_message: str,
                       thinking: bool = False, max_tokens: int = 1024,
                       temperature: float = 1.0) -> dict:
    """Send text prompt to Google Vertex AI using service account auth."""
    from google.genai import types

    client = _get_vertex_sa_client()

    config_kwargs = {"max_output_tokens": max_tokens, "temperature": temperature}

    # System instruction (Gemma models don't support developer instructions)
    is_gemma = model_id.startswith("gemma")
    if system_prompt and not is_gemma:
        config_kwargs["system_instruction"] = system_prompt
    elif system_prompt and is_gemma:
        user_message = f"{system_prompt}\n\n{user_message}"

    # Thinking configuration by model generation
    if model_id.startswith("gemini-3"):
        is_pro = "pro" in model_id
        if thinking:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level="high")
        else:
            config_kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level="low" if is_pro else "minimal"
            )
    elif model_id.startswith("gemini-2.5"):
        is_pro = "pro" in model_id
        is_lite = "lite" in model_id
        if thinking:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=-1)
        elif is_pro:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=128)
        elif not is_lite:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

    response = client.models.generate_content(
        model=model_id,
        contents=[user_message],
        config=types.GenerateContentConfig(**config_kwargs),
    )

    input_tokens = 0
    output_tokens = 0
    if response.usage_metadata:
        input_tokens = response.usage_metadata.prompt_token_count or 0
        output_tokens = response.usage_metadata.candidates_token_count or 0

    text = response.text if response.text else ""

    return {
        "text": text,
        "thinking": "",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model_id": model_id,
    }


# ---------------------------------------------------------------------------
# OpenRouter (access to open-source flagships via OpenAI-compatible API)
# ---------------------------------------------------------------------------

def call_openrouter(model_id: str, system_prompt: str, user_message: str,
                    thinking: bool = False, max_tokens: int = 1024,
                    temperature: float = 1.0) -> dict:
    """Send text prompt to OpenRouter API. Returns dict with text, tokens."""
    import openai
    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY"),
    )

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(response.usage, "completion_tokens", 0) or 0

    return {
        "text": response.choices[0].message.content or "",
        "thinking": "",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model_id": model_id,
    }


# ---------------------------------------------------------------------------
# Together AI (open-source models including base/completion models)
# ---------------------------------------------------------------------------

def call_together(model_id: str, system_prompt: str, user_message: str,
                  thinking: bool = False, max_tokens: int = 1024,
                  temperature: float = 1.0) -> dict:
    """Send text prompt to Together AI API. Returns dict with text, tokens.

    Together AI hosts both base (completion) and instruct (chat) models.
    Base models use the /v1/completions endpoint (no chat template).
    Instruct models use the /v1/chat/completions endpoint.

    For base models, the system_prompt and user_message are concatenated
    into a single prompt string since base models have no concept of
    message roles.
    """
    import openai
    client = openai.OpenAI(
        base_url="https://api.together.ai/v1",
        api_key=os.environ.get("TOGETHER_API_KEY"),
    )

    # Detect if this is a base model by checking common instruct suffixes
    model_lower = model_id.lower()
    is_instruct = any(s in model_lower for s in [
        "instruct", "-it", "-chat", "turbo",
    ])

    if is_instruct:
        # Chat completions for instruct models
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = response.choices[0].message.content or ""
    else:
        # Text completions for base models (no chat template)
        prompt = ""
        if system_prompt:
            prompt = system_prompt + "\n\n"
        prompt += user_message + "\n\nRecommendation:"

        response = client.completions.create(
            model=model_id,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = response.choices[0].text or ""

    input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(response.usage, "completion_tokens", 0) or 0

    return {
        "text": text,
        "thinking": "",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model_id": model_id,
    }


# ---------------------------------------------------------------------------
# Ollama (local open-source models via OpenAI-compatible API)
# ---------------------------------------------------------------------------

def call_ollama(model_id: str, system_prompt: str, user_message: str,
                thinking: bool = False, max_tokens: int = 1024,
                temperature: float = 1.0) -> dict:
    """Send text prompt to local Ollama instance. Returns dict with text, tokens."""
    import openai
    client = openai.OpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",  # Ollama doesn't need a real key
    )

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(response.usage, "completion_tokens", 0) or 0

    return {
        "text": response.choices[0].message.content or "",
        "thinking": "",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model_id": model_id,
    }


# ---------------------------------------------------------------------------
# Provider dispatch
# ---------------------------------------------------------------------------

PROVIDERS = {
    "anthropic": call_anthropic,
    "openai": call_openai,
    "google": call_google,
    "google_vertex": call_google_vertex,
    "openrouter": call_openrouter,
    "together": call_together,
    "ollama": call_ollama,
}


def call_model(model_key: str, model_cfg: dict,
               system_prompt: str, user_message: str,
               max_tokens: int = 1024, temperature: float = 1.0) -> dict:
    """
    Dispatch to the appropriate provider API.
    Returns dict with: text, thinking, input_tokens, output_tokens, model_id
    """
    provider = model_cfg["provider"]
    caller = PROVIDERS[provider]
    return caller(
        model_id=model_cfg["model_id"],
        system_prompt=system_prompt,
        user_message=user_message,
        thinking=model_cfg.get("thinking", False),
        max_tokens=max_tokens,
        temperature=temperature,
    )


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

def call_with_retry(caller_fn, max_retries: int = MAX_RETRIES, **kwargs) -> dict:
    """Call API with exponential backoff on rate limit / overloaded errors."""
    for attempt in range(max_retries + 1):
        try:
            return caller_fn(**kwargs)
        except Exception as e:
            error_str = str(e).lower()
            is_retryable = any(w in error_str for w in [
                "rate", "429", "overloaded", "529", "too many", "quota",
                "resource_exhausted", "capacity", "503", "could not finish",
            ])
            if is_retryable and attempt < max_retries:
                wait = min(2 ** attempt * 3, 120)
                print(f"    [retry] {type(e).__name__}, waiting {wait}s "
                      f"(attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    raise Exception(f"Failed after {max_retries} retries")


def call_model_with_retry(model_key: str, model_cfg: dict,
                           system_prompt: str, user_message: str,
                           max_tokens: int = 1024,
                           temperature: float = 1.0) -> dict:
    """Call model API with retry logic."""
    return call_with_retry(
        call_model,
        model_key=model_key,
        model_cfg=model_cfg,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=max_tokens,
        temperature=temperature,
    )
