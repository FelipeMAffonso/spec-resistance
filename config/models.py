"""
Model Registry for Double Alignment Experiments
================================================
Defines all models to test, their API configurations, and pricing.
Adapted from cognitive-traps-jcr/v2_revision/test_models.py
"""

# ---------------------------------------------------------------------------
# Full model registry (all available frontier models)
# ---------------------------------------------------------------------------

ALL_MODELS = {
    # Anthropic - Claude 3 generation
    "claude-haiku-3.0":             {"provider": "anthropic", "model_id": "claude-3-haiku-20240307",    "thinking": False},
    "claude-haiku-3.5":             {"provider": "anthropic", "model_id": "claude-3-5-haiku-20241022",  "thinking": False},
    # Anthropic - Claude 4.5
    "claude-haiku-4.5":             {"provider": "anthropic", "model_id": "claude-haiku-4-5-20251001",  "thinking": False},
    "claude-sonnet-4.5":            {"provider": "anthropic", "model_id": "claude-sonnet-4-5-20250929", "thinking": False},
    "claude-sonnet-4.5-thinking":   {"provider": "anthropic", "model_id": "claude-sonnet-4-5-20250929", "thinking": True},
    "claude-opus-4.5":              {"provider": "anthropic", "model_id": "claude-opus-4-5",            "thinking": False},
    # Anthropic - Claude 4.6
    "claude-sonnet-4.6":            {"provider": "anthropic", "model_id": "claude-sonnet-4-6",          "thinking": False},
    "claude-opus-4.6":              {"provider": "anthropic", "model_id": "claude-opus-4-6",            "thinking": False},
    # OpenAI - GPT-4o
    "gpt-4o":                       {"provider": "openai", "model_id": "gpt-4o",                       "thinking": False},
    "gpt-4o-mini":                  {"provider": "openai", "model_id": "gpt-4o-mini",                  "thinking": False},
    # OpenAI - GPT-4.1
    "gpt-4.1":                      {"provider": "openai", "model_id": "gpt-4.1",                      "thinking": False},
    "gpt-4.1-mini":                 {"provider": "openai", "model_id": "gpt-4.1-mini",                 "thinking": False},
    "gpt-4.1-nano":                 {"provider": "openai", "model_id": "gpt-4.1-nano",                 "thinking": False},
    # OpenAI - GPT-5
    "gpt-5":                        {"provider": "openai", "model_id": "gpt-5-chat-latest",            "thinking": False},
    "gpt-5-thinking":               {"provider": "openai", "model_id": "gpt-5",                        "thinking": True},
    "gpt-5-mini":                   {"provider": "openai", "model_id": "gpt-5-mini",                   "thinking": False},
    # OpenAI - GPT-5.1
    "gpt-5.1":                      {"provider": "openai", "model_id": "gpt-5.1-chat-latest",          "thinking": False},
    "gpt-5.1-thinking":             {"provider": "openai", "model_id": "gpt-5.1",                      "thinking": True},
    # OpenAI - GPT-5.2
    "gpt-5.2":                      {"provider": "openai", "model_id": "gpt-5.2-chat-latest",          "thinking": False},
    "gpt-5.2-thinking":             {"provider": "openai", "model_id": "gpt-5.2",                      "thinking": True},
    "gpt-5.2-pro":                  {"provider": "openai", "model_id": "gpt-5.2-pro",                  "thinking": True},
    # Google - Gemini 2.0
    "gemini-2.0-flash":             {"provider": "google", "model_id": "gemini-2.0-flash",             "thinking": False},
    # Google - Gemini 2.5
    "gemini-2.5-flash":             {"provider": "google", "model_id": "gemini-2.5-flash",             "thinking": False},
    "gemini-2.5-flash-lite":        {"provider": "google", "model_id": "gemini-2.5-flash-lite",        "thinking": False},
    "gemini-2.5-flash-thinking":    {"provider": "google", "model_id": "gemini-2.5-flash",             "thinking": True},
    "gemini-2.5-pro":               {"provider": "google", "model_id": "gemini-2.5-pro",               "thinking": False},
    "gemini-2.5-pro-thinking":      {"provider": "google", "model_id": "gemini-2.5-pro",               "thinking": True},
    # Google - Gemini 3+
    "gemini-3-flash":               {"provider": "google", "model_id": "gemini-3-flash-preview",       "thinking": False},
    "gemini-3-pro":                 {"provider": "google", "model_id": "gemini-3-pro-preview",         "thinking": True},
    "gemini-3.1-pro":               {"provider": "google", "model_id": "gemini-3.1-pro-preview",       "thinking": True},
    # Google - Gemma (open-source, via AI Studio API)
    "gemma-3-27b":                  {"provider": "google", "model_id": "gemma-3-27b-it",               "thinking": False},
    # OpenRouter - open-source flagships (via OpenAI-compatible API)
    "llama-3.3-70b":                {"provider": "openrouter", "model_id": "meta-llama/llama-3.3-70b-instruct",    "thinking": False},
    "deepseek-r1":                  {"provider": "openrouter", "model_id": "deepseek/deepseek-r1",                 "thinking": False},
    "deepseek-v3":                  {"provider": "openrouter", "model_id": "deepseek/deepseek-chat-v3-0324",       "thinking": False},
    "qwen-2.5-72b":                 {"provider": "openrouter", "model_id": "qwen/qwen-2.5-72b-instruct",          "thinking": False},
    "kimi-k2":                      {"provider": "openrouter", "model_id": "moonshotai/kimi-k2",                   "thinking": False},
}

# ---------------------------------------------------------------------------
# Pilot models (10 models for initial testing, ~30 calls per platform)
# ---------------------------------------------------------------------------

PILOT_MODELS = {
    # Anthropic (3 models)
    "claude-haiku-4.5":    ALL_MODELS["claude-haiku-4.5"],
    "claude-sonnet-4.5":   ALL_MODELS["claude-sonnet-4.5"],
    "claude-opus-4.5":     ALL_MODELS["claude-opus-4.5"],
    # OpenAI (4 models)
    "gpt-4o":              ALL_MODELS["gpt-4o"],
    "gpt-5.2":             ALL_MODELS["gpt-5.2"],
    "gpt-5.2-thinking":    ALL_MODELS["gpt-5.2-thinking"],
    "gpt-5-mini":          ALL_MODELS["gpt-5-mini"],
    # Google (3 models)
    "gemini-2.5-flash":    ALL_MODELS["gemini-2.5-flash"],
    "gemini-2.5-pro":      ALL_MODELS["gemini-2.5-pro"],
    "gemini-3-pro":        ALL_MODELS["gemini-3-pro"],
}

# ---------------------------------------------------------------------------
# Pricing per million tokens (input_$/M, output_$/M)
# ---------------------------------------------------------------------------

PRICING = {
    "claude-3-haiku-20240307":      (0.25,  1.25),
    "claude-3-5-haiku-20241022":    (0.80,  4.00),
    "claude-haiku-4-5-20251001":    (1.00,  5.00),
    "claude-sonnet-4-5-20250929":   (3.00,  15.00),
    "claude-opus-4-5":              (15.00, 75.00),
    "claude-sonnet-4-6":            (3.00,  15.00),
    "claude-opus-4-6":              (15.00, 75.00),
    "gpt-4o":                       (2.50,  10.00),
    "gpt-4o-mini":                  (0.15,   0.60),
    "gpt-4.1":                      (2.00,   8.00),
    "gpt-4.1-mini":                 (0.40,   1.60),
    "gpt-4.1-nano":                 (0.10,   0.40),
    "gpt-5-chat-latest":            (1.25,  10.00),
    "gpt-5":                        (1.25,  10.00),
    "gpt-5-mini":                   (0.40,   1.60),
    "gpt-5.1-chat-latest":          (1.25,  10.00),
    "gpt-5.1":                      (1.25,  10.00),
    "gpt-5.2-chat-latest":          (1.75,  14.00),
    "gpt-5.2":                      (1.75,  14.00),
    "gpt-5.2-pro":                  (15.00, 60.00),
    "gemini-2.0-flash":             (0.10,  0.40),
    "gemini-2.5-flash":             (0.15,  0.60),
    "gemini-2.5-flash-lite":        (0.075, 0.30),
    "gemini-2.5-pro":               (1.25,  10.00),
    "gemini-3-flash-preview":       (0.15,  0.60),
    "gemini-3-pro-preview":         (1.25,  10.00),
    "gemini-3.1-pro-preview":       (1.25,  10.00),
    "gemma-3-27b-it":               (0.04,   0.15),
    # OpenRouter models
    "meta-llama/llama-3.3-70b-instruct":    (0.135,  0.40),
    "deepseek/deepseek-r1":                 (0.40,   1.75),
    "deepseek/deepseek-chat-v3-0324":       (0.20,   0.80),
    "qwen/qwen-2.5-72b-instruct":          (0.80,   0.80),
    "moonshotai/kimi-k2":                   (0.60,   2.50),
}

# ---------------------------------------------------------------------------
# Provider groupings (for budget tracking)
# ---------------------------------------------------------------------------

def get_provider_models(provider: str, model_set: dict = None) -> dict:
    """Get all models for a given provider from a model set."""
    if model_set is None:
        model_set = ALL_MODELS
    return {k: v for k, v in model_set.items() if v["provider"] == provider}

def compute_cost(model_id: str, input_tokens: int, output_tokens: int) -> float | None:
    """Compute estimated cost in USD based on token counts."""
    if model_id in PRICING:
        inp_rate, out_rate = PRICING[model_id]
        return (input_tokens * inp_rate + output_tokens * out_rate) / 1_000_000
    return None
