"""Convert AI SDK v6 Data Stream SSE to OpenAI chat-completions SSE format."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator


def _make_chunk(
    request_id: str,
    model: str,
    *,
    delta: dict,
    finish_reason: str | None = None,
    usage: dict | None = None,
) -> str:
    """Format a single OpenAI SSE chunk."""
    chunk: dict = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }
    if usage is not None:
        chunk["usage"] = usage
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


def _extract_usage(event: dict) -> dict | None:
    """Extract usage from finish event (handles both /api/chat and /api/doc/chat)."""
    meta = event.get("messageMetadata", {})
    # /api/doc/chat nests under custom.usage
    raw = meta.get("custom", {}).get("usage")
    # /api/chat puts usage directly in messageMetadata
    if not raw:
        raw = meta.get("usage")
    if not raw:
        return None
    return {
        "prompt_tokens": raw.get("inputTokens", 0),
        "completion_tokens": raw.get("outputTokens", 0),
        "total_tokens": raw.get("totalTokens", 0),
    }


# ---------------------------------------------------------------------------
# Streaming conversion
# ---------------------------------------------------------------------------

async def convert_stream(
    lines: AsyncIterator[str],
    model: str,
    request_id: str,
) -> AsyncIterator[str]:
    """Yield OpenAI-compatible SSE strings from an AI SDK data-stream."""
    role_sent = False
    # Accumulate tool call argument deltas per toolCallId
    tool_calls_index: dict[str, int] = {}  # toolCallId → index
    next_tool_index = 0

    async for raw_line in lines:
        line = raw_line.rstrip("\r\n")
        if not line:
            continue

        if line == "data: [DONE]":
            yield "data: [DONE]\n\n"
            return

        if not line.startswith("data: "):
            continue

        try:
            event = json.loads(line[6:])
        except json.JSONDecodeError:
            continue

        event_type = event.get("type")

        # --- Text events ---
        if event_type == "text-start":
            if not role_sent:
                yield _make_chunk(
                    request_id, model, delta={"role": "assistant", "content": ""}
                )
                role_sent = True

        elif event_type == "text-delta":
            if not role_sent:
                yield _make_chunk(
                    request_id, model, delta={"role": "assistant", "content": ""}
                )
                role_sent = True
            yield _make_chunk(
                request_id, model, delta={"content": event.get("delta", "")}
            )

        # --- Tool call events ---
        elif event_type == "tool-input-start":
            tc_id = event.get("toolCallId", "")
            tool_name = event.get("toolName", "")
            idx = next_tool_index
            tool_calls_index[tc_id] = idx
            next_tool_index += 1

            delta: dict = {"tool_calls": [{
                "index": idx,
                "id": tc_id,
                "type": "function",
                "function": {"name": tool_name, "arguments": ""},
            }]}
            if not role_sent:
                delta["role"] = "assistant"
                role_sent = True
            yield _make_chunk(request_id, model, delta=delta)

        elif event_type == "tool-input-delta":
            tc_id = event.get("toolCallId", "")
            idx = tool_calls_index.get(tc_id, 0)
            yield _make_chunk(
                request_id, model,
                delta={"tool_calls": [{
                    "index": idx,
                    "function": {"arguments": event.get("inputTextDelta", "")},
                }]},
            )

        # tool-input-available — full args ready; nothing extra needed for
        # streaming (client already accumulated deltas), but we can skip it.

        # --- Finish events ---
        elif event_type == "finish":
            finish_reason = event.get("finishReason", "stop")
            if finish_reason == "tool-calls":
                finish_reason = "tool_calls"
            usage = _extract_usage(event)
            yield _make_chunk(
                request_id, model,
                delta={},
                finish_reason=finish_reason,
                usage=usage,
            )

    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Non-streaming helpers
# ---------------------------------------------------------------------------

def parse_full_response(lines: list[str]) -> tuple[str, list[dict], str, dict | None]:
    """Parse all SSE lines into (content, tool_calls, finish_reason, usage)."""
    content_parts: list[str] = []
    tool_calls: list[dict] = []
    # Accumulate args per toolCallId
    tool_args: dict[str, list[str]] = {}
    tool_meta: dict[str, dict] = {}  # toolCallId → {name, id}
    finish_reason = "stop"
    usage = None

    for raw_line in lines:
        line = raw_line.rstrip("\r\n")
        if not line or not line.startswith("data: ") or line == "data: [DONE]":
            continue
        try:
            event = json.loads(line[6:])
        except json.JSONDecodeError:
            continue

        etype = event.get("type")

        if etype == "text-delta":
            content_parts.append(event.get("delta", ""))

        elif etype == "tool-input-start":
            tc_id = event.get("toolCallId", "")
            tool_args[tc_id] = []
            tool_meta[tc_id] = {
                "name": event.get("toolName", ""),
                "id": tc_id,
            }

        elif etype == "tool-input-delta":
            tc_id = event.get("toolCallId", "")
            tool_args.setdefault(tc_id, []).append(event.get("inputTextDelta", ""))

        elif etype == "tool-input-available":
            tc_id = event.get("toolCallId", "")
            meta = tool_meta.get(tc_id, {"name": event.get("toolName", ""), "id": tc_id})
            tool_calls.append({
                "id": meta["id"],
                "type": "function",
                "function": {
                    "name": meta["name"],
                    "arguments": json.dumps(event.get("input", {}), ensure_ascii=False),
                },
            })

        elif etype == "finish":
            finish_reason = event.get("finishReason", "stop")
            if finish_reason == "tool-calls":
                finish_reason = "tool_calls"
            usage = _extract_usage(event)

    # If we got tool-input-start/delta but no tool-input-available, build from deltas
    for tc_id, meta in tool_meta.items():
        if not any(tc.get("id") == tc_id for tc in tool_calls):
            tool_calls.append({
                "id": meta["id"],
                "type": "function",
                "function": {
                    "name": meta["name"],
                    "arguments": "".join(tool_args.get(tc_id, [])),
                },
            })

    return "".join(content_parts), tool_calls, finish_reason, usage


def build_non_stream_response(
    request_id: str,
    model: str,
    content: str,
    finish_reason: str = "stop",
    usage: dict | None = None,
    tool_calls: list[dict] | None = None,
) -> dict:
    """Build a non-streaming chat.completions response object."""
    message: dict = {"role": "assistant", "content": content or None}
    if tool_calls:
        message["tool_calls"] = tool_calls
        if not content:
            message["content"] = None
    resp: dict = {
        "id": request_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
            }
        ],
        "usage": usage or {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }
    return resp
