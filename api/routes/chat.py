"""POST /v1/chat/completions — OpenAI-compatible chat endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from api.converter.messages import openai_to_ai_sdk, _gen_id
from api.converter.stream import build_non_stream_response, convert_stream, parse_full_response
from api.provider import call_upstream, call_upstream_full
from config import DEFAULT_MODEL

router = APIRouter()


class FunctionDef(BaseModel):
    name: str
    description: str = ""
    parameters: dict = {}


class ToolDef(BaseModel):
    type: str = "function"
    function: FunctionDef


class ChatMessage(BaseModel):
    role: str
    content: Any = ""
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


class ChatRequest(BaseModel):
    model: str = DEFAULT_MODEL
    messages: list[ChatMessage]
    stream: bool = False
    tools: list[ToolDef] | None = None
    tool_choice: Any = None
    temperature: float | None = None
    max_tokens: int | None = None


@router.post("/v1/chat/completions")
async def chat_completions(body: ChatRequest, request: Request):
    request_id = f"chatcmpl-{_gen_id('', 24)}"
    model = body.model

    tools_raw = [t.model_dump() for t in body.tools] if body.tools else None

    try:
        payload = openai_to_ai_sdk(
            [m.model_dump() for m in body.messages],
            model,
            tools=tools_raw,
        )
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content=_error_body(f"Invalid request: {e}", "invalid_request_error"),
        )

    if body.stream:
        return StreamingResponse(
            _stream_generator(payload, model, request_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming
    try:
        lines = await call_upstream_full(payload)
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content=_error_body(f"Upstream error: {e}", "upstream_error"),
        )

    content, tool_calls, finish_reason, usage = parse_full_response(lines)
    return build_non_stream_response(
        request_id, model, content, finish_reason, usage,
        tool_calls=tool_calls or None,
    )


async def _stream_generator(payload: dict, model: str, request_id: str):
    try:
        upstream = call_upstream(payload)
        async for chunk in convert_stream(upstream, model, request_id):
            yield chunk
    except Exception as e:
        error_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "error"}],
            "error": {"message": str(e), "type": "upstream_error"},
        }
        import json
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"


def _error_body(message: str, error_type: str) -> dict:
    return {"error": {"message": message, "type": error_type}}
