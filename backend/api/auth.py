from __future__ import annotations

import os

from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import APIKeyHeader

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

_API_KEY_ENV = "AI_PROTO_API_KEY"


def _get_configured_key() -> str | None:
    return os.getenv(_API_KEY_ENV, "").strip() or None


def require_api_key(api_key: str | None = Depends(_API_KEY_HEADER)) -> None:
    configured = _get_configured_key()
    if configured is None:
        return
    if not api_key or api_key != configured:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida o ausente",
            headers={"WWW-Authenticate": "ApiKey"},
        )


async def require_api_key_ws(websocket: WebSocket, api_key: str | None = None) -> None:
    """Valida API key para WebSocket (se pasa como query param ?api_key=...)."""
    configured = _get_configured_key()
    if configured is None:
        return
    key = api_key or websocket.query_params.get("api_key", "")
    if not key or key != configured:
        await websocket.close(code=4001, reason="API key inválida o ausente")
        raise HTTPException(status_code=401, detail="API key inválida o ausente")
