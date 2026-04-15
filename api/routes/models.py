"""GET /v1/models — list available models."""

from __future__ import annotations

import time

from fastapi import APIRouter

from config import ACTIVE_MODELS, MODEL_MAP

router = APIRouter()


@router.get("/v1/models")
async def list_models() -> dict:
    """Return only active (non-disabled) models by default."""
    now = int(time.time())
    data = [
        {
            "id": short_name,
            "object": "model",
            "created": now,
            "owned_by": full_id.split("/")[0],
        }
        for short_name, full_id in ACTIVE_MODELS.items()
    ]
    return {"object": "list", "data": data}


@router.get("/v1/models/all")
async def list_all_models() -> dict:
    """Return all models including disabled ones (with status)."""
    now = int(time.time())
    data = [
        {
            "id": short_name,
            "object": "model",
            "created": now,
            "owned_by": info["id"].split("/")[0],
            "disabled": info["disabled"],
            "context_window": info["context_window"],
        }
        for short_name, info in MODEL_MAP.items()
    ]
    return {"object": "list", "data": data}
