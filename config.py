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
# Note: claude-sonnet-4.6 is disabled server-side (falls back to gpt-5.4)
MODEL_MAP: dict[str, str] = {
    "gpt-5.4": "openai/gpt-5.4",
    "gpt-5-nano": "openai/gpt-5-nano",
    "gemini-3-flash": "google/gemini-3-flash",
    "kimi-k2.5": "moonshotai/kimi-k2.5",
    "deepseek-v3.2": "deepseek/deepseek-v3.2",
}

DEFAULT_MODEL = "gpt-5.4"

UPSTREAM_HEADERS: dict[str, str] = {
    "content-type": "application/json",
    "user-agent": "ai-sdk/6.0.116 runtime/browser",
    "origin": "https://www.assistant-ui.com",
    "referer": "https://www.assistant-ui.com/docs",
}
