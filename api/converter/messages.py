"""Convert between OpenAI chat format and AI SDK v6 format."""

from __future__ import annotations

import json

from nanoid import generate as nanoid

from config import MODEL_MAP

_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


def _gen_id(prefix: str = "msg", size: int = 12) -> str:
    return f"{prefix}_{nanoid(_ALPHABET, size)}"


def _resolve_model(model: str) -> str:
    """Map short model name to assistant-ui API identifier."""
    if model in MODEL_MAP:
        return MODEL_MAP[model]
    if "/" in model:
        return model
    return f"openai/{model}"


def _guess_media_type(url: str) -> str:
    """Infer media type from a data-URI or file extension."""
    if url.startswith("data:"):
        # data:image/png;base64,...
        header = url.split(",", 1)[0]
        if ";" in header:
            return header[5:].split(";")[0]  # strip "data:" prefix
        return header[5:]
    lower = url.lower()
    for ext, mt in (
        (".png", "image/png"), (".jpg", "image/jpeg"), (".jpeg", "image/jpeg"),
        (".gif", "image/gif"), (".webp", "image/webp"), (".svg", "image/svg+xml"),
    ):
        if ext in lower:
            return mt
    return "image/png"


def _convert_tools(tools: list[dict] | None) -> dict:
    """Convert OpenAI tools list to AI SDK frontend tools format.

    OpenAI format:
        [{"type": "function", "function": {"name": "...", "description": "...",
          "parameters": {...}}}]

    AI SDK format:
        {"tool_name": {"description": "...", "parameters": {...}}}
    """
    if not tools:
        return {}
    result = {}
    for tool in tools:
        if tool.get("type") != "function":
            continue
        func = tool.get("function", {})
        name = func.get("name", "")
        if not name:
            continue
        entry: dict = {"parameters": func.get("parameters", {"type": "object"})}
        if func.get("description"):
            entry["description"] = func["description"]
        result[name] = entry
    return result


def openai_to_ai_sdk(
    messages: list[dict],
    model: str,
    tools: list[dict] | None = None,
) -> dict:
    """Convert an OpenAI chat-completions request to AI SDK v6 payload."""
    sdk_messages: list[dict] = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            # Inject as AI SDK system message in the messages array.
            # convertToModelMessages() handles role:"system" and forwards
            # it as a model-level system message — bypasses the server's
            # missing top-level "system" param in streamText().
            text = content if isinstance(content, str) else ""
            if text:
                sdk_messages.append({
                    "role": "system",
                    "parts": [{"type": "text", "text": text}],
                    "metadata": {"custom": {}},
                    "id": _gen_id("sys"),
                })
            continue

        if role == "user":
            if isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, str):
                        parts.append({"type": "text", "text": part})
                    elif isinstance(part, dict):
                        ptype = part.get("type", "")
                        if ptype == "text":
                            parts.append({"type": "text", "text": part["text"]})
                        elif ptype == "image_url":
                            # OpenAI vision format → AI SDK file part
                            img = part.get("image_url", {})
                            url = img.get("url", "") if isinstance(img, dict) else str(img)
                            media_type = _guess_media_type(url)
                            parts.append({
                                "type": "file",
                                "mediaType": media_type,
                                "url": url,
                            })
            else:
                parts = [{"type": "text", "text": str(content)}]
            sdk_messages.append({
                "role": "user",
                "parts": parts,
                "metadata": {"custom": {}},
                "id": _gen_id("msg"),
            })

        elif role == "assistant":
            parts = []
            # Text content
            if isinstance(content, str) and content:
                parts.append({"type": "text", "text": content})
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append({"type": "text", "text": part["text"]})
            # Tool calls → tool-invocation parts
            # Initially set state to "input-available" (args ready, no result yet)
            for tc in msg.get("tool_calls") or []:
                func = tc.get("function", {})
                try:
                    args = json.loads(func.get("arguments", "{}"))
                except (json.JSONDecodeError, TypeError):
                    args = {}
                parts.append({
                    "type": "tool-invocation",
                    "toolCallId": tc.get("id", _gen_id("call")),
                    "toolName": func.get("name", ""),
                    "input": args,
                    "state": "input-available",
                })
            sdk_messages.append({
                "role": "assistant",
                "parts": parts,
                "metadata": {"custom": {}},
                "id": _gen_id("msg"),
            })

        elif role == "tool":
            # Tool result — attach output to the matching tool-invocation
            # in the preceding assistant message, using AI SDK v6 field names.
            tool_call_id = msg.get("tool_call_id", "")
            # Parse result: try JSON object first, fall back to string
            if isinstance(content, str):
                try:
                    result_obj = json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    result_obj = content
            else:
                result_obj = content
            for prev in reversed(sdk_messages):
                if prev["role"] != "assistant":
                    continue
                for part in prev["parts"]:
                    if (
                        part.get("type") == "tool-invocation"
                        and part.get("toolCallId") == tool_call_id
                    ):
                        part["state"] = "output-available"
                        part["output"] = result_obj
                        break
                break

    return {
        "system": "",
        "config": {"modelName": _resolve_model(model)},
        "tools": _convert_tools(tools),
        "id": _gen_id("thread"),
        "messages": sdk_messages,
        "trigger": "submit-message",
        "metadata": {},
    }
