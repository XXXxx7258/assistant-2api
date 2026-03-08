"""FastAPI application — assistant-ui 2API service."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.routes.chat import router as chat_router
from api.routes.models import router as models_router
from config import API_KEY

app = FastAPI(title="assistant-ui 2API", version="1.0.0")


# ---------- Auth middleware ----------
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Skip auth for health / docs
    if request.url.path in ("/", "/health", "/docs", "/openapi.json"):
        return await call_next(request)

    if API_KEY:
        auth = request.headers.get("authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        if token != API_KEY:
            return JSONResponse(
                status_code=401,
                content={"error": {"message": "Invalid API key", "type": "auth_error"}},
            )

    return await call_next(request)


# ---------- Routes ----------
app.include_router(chat_router)
app.include_router(models_router)


@app.get("/")
async def root():
    return {"status": "ok", "service": "assistant-ui 2API"}


@app.get("/health")
async def health():
    return {"status": "ok"}
