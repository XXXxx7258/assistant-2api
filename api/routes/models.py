"""GET /v1/models — list available models."""

from __future__ import annotations

import time

from fastapi import APIRouter

from config import MODEL_MAP

router = APIRouter()


@router.get("/v1/models")
async def list_models() -> dict:
    now = int(time.time())
    data = [
        {
            "id": short_name,
            "object": "model",
            "created": now,
            "owned_by": full_name.split("/")[0],
        }
        for short_name, full_name in MODEL_MAP.items()
    ]
    return {"object": "list", "data": data}
