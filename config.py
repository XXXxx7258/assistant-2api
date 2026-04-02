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

# OpenAI-compatible name → assistant-ui API identifier
MODEL_MAP: dict[str, str] = {
    # OpenAI
    "gpt-5.4-nano": "openai/gpt-5.4-nano",
    "gpt-5.4-mini": "openai/gpt-5.4-mini",
    # Anthropic
    "claude-haiku-4.5": "anthropic/claude-haiku-4-5",
    # Google
    "gemini-3-flash": "google-ai-studio/gemini-3-flash",
    # xAI
    "grok-4.1-fast": "grok/grok-4-1-fast",
    "grok-3-mini-fast": "grok/grok-3-mini-fast",
    # Groq
    "llama-3.3-70b": "groq/llama-3.3-70b-versatile",
    "qwen3-32b": "groq/qwen/qwen3-32b",
}

DEFAULT_MODEL = "gpt-5.4-nano"

UPSTREAM_HEADERS: dict[str, str] = {
    "content-type": "application/json",
    "user-agent": "ai-sdk/6.0.116 runtime/browser",
    "origin": "https://www.assistant-ui.com",
    "referer": "https://www.assistant-ui.com/docs",
}
