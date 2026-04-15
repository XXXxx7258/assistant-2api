import os
from dotenv import load_dotenv

load_dotenv()

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8080"))
API_KEY = os.getenv("API_KEY", "sk-assistant-2api-free")

# /api/chat — clean endpoint, no hardcoded system prompt
# /api/doc/chat — docs assistant with hardcoded persona + tools (avoid)
UPSTREAM_URL = os.getenv(
    "UPSTREAM_URL", "https://www.assistant-ui.com/api/chat"
)

# Maximum length for system prompts (matches upstream validation)
MAX_SYSTEM_LENGTH = 4000

# OpenAI-compatible name → assistant-ui API identifier
# disabled: model exists upstream but is currently turned off
MODEL_MAP: dict[str, dict] = {
    # OpenAI — active
    "gpt-5.4-nano": {
        "id": "openai/gpt-5.4-nano",
        "disabled": False,
        "context_window": 400_000,
    },
    "gpt-5.4-mini": {
        "id": "openai/gpt-5.4-mini",
        "disabled": False,
        "context_window": 400_000,
    },
    # Anthropic — disabled upstream since 2026-04-10
    "claude-haiku-4.5": {
        "id": "anthropic/claude-haiku-4-5",
        "disabled": True,
        "context_window": 200_000,
    },
    # Google — disabled upstream
    "gemini-3-flash": {
        "id": "google-ai-studio/gemini-3-flash",
        "disabled": True,
        "context_window": 1_000_000,
    },
    # xAI — disabled upstream
    "grok-4.1-fast": {
        "id": "grok/grok-4-1-fast",
        "disabled": True,
        "context_window": 131_072,
    },
    "grok-3-mini-fast": {
        "id": "grok/grok-3-mini-fast",
        "disabled": True,
        "context_window": 131_072,
    },
    # Groq — disabled upstream
    "llama-3.3-70b": {
        "id": "groq/llama-3.3-70b-versatile",
        "disabled": True,
        "context_window": 131_072,
    },
    "qwen3-32b": {
        "id": "groq/qwen/qwen3-32b",
        "disabled": True,
        "context_window": 131_072,
    },
}

ACTIVE_MODELS: dict[str, str] = {
    k: v["id"] for k, v in MODEL_MAP.items() if not v["disabled"]
}

DEFAULT_MODEL = "gpt-5.4-nano"

UPSTREAM_HEADERS: dict[str, str] = {
    "content-type": "application/json",
    "user-agent": "ai-sdk/6.1.0 runtime/browser",
    "origin": "https://www.assistant-ui.com",
    "referer": "https://www.assistant-ui.com/docs",
}
