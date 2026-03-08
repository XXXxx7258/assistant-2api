"""Call the assistant-ui upstream LLM endpoint."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from config import UPSTREAM_HEADERS, UPSTREAM_URL


class UpstreamError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(message)


async def call_upstream(payload: dict) -> AsyncIterator[str]:
    """POST to assistant-ui and yield raw SSE lines as they arrive."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10)) as client:
        async with client.stream(
            "POST",
            UPSTREAM_URL,
            json=payload,
            headers=UPSTREAM_HEADERS,
        ) as resp:
            if resp.status_code == 429:
                raise UpstreamError(429, "Rate limit exceeded (upstream: 5 req / 30s per IP)")
            if resp.status_code >= 400:
                body = await resp.aread()
                raise UpstreamError(resp.status_code, body.decode(errors="replace")[:200])
            async for line in resp.aiter_lines():
                yield line


async def call_upstream_full(payload: dict) -> list[str]:
    """POST to assistant-ui and collect all SSE lines (for non-stream mode)."""
    lines: list[str] = []
    async for line in call_upstream(payload):
        lines.append(line)
    return lines
