from __future__ import annotations

import logging
import os
import socket
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from api.debug_routes import router as debug_router
from api.routes import router as api_router
from api.websocket_routes import router as websocket_router
from storage.file_store import MAX_UPLOAD_BYTES, MAX_UPLOAD_MB
from utils.logger import apply_shutdown_noise_filter, configure_logging

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Reaplicar el filtro aquí garantiza que esté activo aunque uvicorn haya
    # reconfigurado sus loggers después del import de este módulo.
    apply_shutdown_noise_filter()
    logger.info("backend.lifespan.startup")
    yield
    logger.info("backend.lifespan.shutdown")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _parse_port(raw: str, env_name: str) -> int:
    try:
        port = int(raw)
    except ValueError as exc:
        raise ValueError(f"Variable {env_name} invalida: {raw!r}. Debe ser un entero.") from exc

    if port < 1 or port > 65535:
        raise ValueError(f"Variable {env_name} fuera de rango: {port}. Debe estar entre 1 y 65535.")
    return port


def _is_port_available(host: str, port: int) -> tuple[bool, str]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return True, ""
        except OSError as exc:
            return False, str(exc)


def _reload_excludes() -> list[str]:
    # Combinar paths absolutos (con forward-slashes para watchfiles en Windows)
    # y patrones glob para máxima cobertura independientemente de cómo se inicie uvicorn.
    base = Path(__file__).resolve().parent

    abs_excludes = [
        base / "outputs",
        base / "data_store",
        base / "uploads",
        base / "storage" / "videos",
        base / "storage" / "frames",
        base / "storage" / "debug_sessions",
    ]

    # watchfiles en Windows necesita forward-slashes en los paths absolutos
    normalized = [p.as_posix() for p in abs_excludes]

    glob_excludes = [
        "**/outputs/**",
        "**/node_modules/**",
        "**/.angular/**",
        "**/dist/**",
        "**/generated/**",
        "**/__pycache__/**",
        "**/*.pyc",
    ]

    return normalized + glob_excludes


def _reload_dirs() -> list[str]:
    # Watch only source directories. Do NOT watch backend root, because it contains
    # generated artifacts under outputs/** that can trigger reload during npm install.
    base = Path(__file__).resolve().parent
    return [
        str(base / "api"),
        str(base / "agents"),
        str(base / "models"),
        str(base / "orchestrator"),
        str(base / "services"),
        str(base / "utils"),
        str(base / "websocket"),
    ]


def _reload_includes() -> list[str]:
    return ["*.py"]


def _cors_origins() -> list[str]:
    raw = os.getenv(
        "AI_PROTO_CORS_ORIGINS",
        "http://localhost:4200,http://127.0.0.1:4200,http://localhost:5173,http://127.0.0.1:5173",
    )

    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if origins:
        return origins

    return [
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


async def _empty_receive() -> Message:
    return {"type": "http.request", "body": b"", "more_body": False}


class UploadSizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")
        if method != "POST" or not path.endswith("/upload"):
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }

        content_length = headers.get("content-length")
        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError:
                declared_size = 0

            if declared_size > self.max_bytes:
                await self._send_413(scope, send, content_length)
                return

        response_sent = False
        disconnected = False
        received = 0

        async def guarded_send(message: Message) -> None:
            nonlocal response_sent
            if disconnected:
                return
            if message["type"] == "http.response.start":
                response_sent = True
            await send(message)

        async def reject_stream(size: int) -> None:
            nonlocal disconnected
            disconnected = True
            if not response_sent:
                await self._send_413(scope, send, str(size))

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    logger.warning(
                        "upload.request.too_large_stream path=%s received=%s max=%s",
                        path,
                        received,
                        self.max_bytes,
                    )
                    await reject_stream(received)
                    return {"type": "http.disconnect"}
            return message

        await self.app(scope, limited_receive, guarded_send)

    async def _send_413(self, scope: Scope, send: Send, size: str) -> None:
        logger.warning(
            "upload.request.too_large content_length=%s max_mb=%s",
            size,
            MAX_UPLOAD_MB,
        )
        response = JSONResponse(
            status_code=413,
            content={"detail": f"Archivo demasiado grande. Limite: {MAX_UPLOAD_MB}MB"},
        )
        await response(scope, _empty_receive, send)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"x-content-type-options"] = b"nosniff"
                headers[b"x-frame-options"] = b"DENY"
                headers[b"x-xss-protection"] = b"1; mode=block"
                headers[b"referrer-policy"] = b"strict-origin-when-cross-origin"
                headers[b"permissions-policy"] = b"geolocation=(), microphone=(), camera=()"
                message = {**message, "headers": list(headers.items())}
            await send(message)

        await self.app(scope, receive, send_with_headers)


class JsonUnhandledExceptionMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(
                "request.unhandled_fallback path=%s method=%s error=%s",
                scope.get("path"),
                scope.get("method"),
                repr(exc),
            )
            response = JSONResponse(
                status_code=500,
                content={"detail": "Error interno del servidor"},
            )
            await response(scope, _empty_receive, send)


app = FastAPI(title="AI Prototype Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(UploadSizeLimitMiddleware, max_bytes=MAX_UPLOAD_BYTES)
app.add_middleware(JsonUnhandledExceptionMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
    expose_headers=["Content-Disposition"],
)

app.include_router(api_router)
app.include_router(websocket_router)
app.include_router(debug_router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    multipart_parse_error = (
        exc.status_code == 400
        and isinstance(detail, str)
        and (
            "parsing the body" in detail.lower()
            or "multipart" in detail.lower()
            or "boundary" in detail.lower()
        )
    )

    if multipart_parse_error:
        logger.exception(
            "request.body.parse_error path=%s method=%s content_type=%r content_length=%r",
            request.url.path,
            request.method,
            request.headers.get("content-type"),
            request.headers.get("content-length"),
        )
        detail = (
            "No fue posible parsear multipart/form-data. "
            "Verifica que Axios NO establezca Content-Type manualmente "
            "y que el FormData incluya el campo 'file'."
        )
    else:
        logger.warning(
            "request.http_error path=%s method=%s status=%s detail=%r",
            request.url.path,
            request.method,
            exc.status_code,
            detail,
        )

    return JSONResponse(status_code=exc.status_code, content={"detail": detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning(
        "request.validation_error path=%s method=%s errors=%s",
        request.url.path,
        request.method,
        exc.errors(),
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "request.unhandled_error path=%s method=%s error=%s",
        request.url.path,
        request.method,
        repr(exc),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Backend funcionando"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    host = os.getenv("AI_PROTO_BACKEND_HOST", "127.0.0.1")
    requested_port = _parse_port(os.getenv("AI_PROTO_BACKEND_PORT", "8000"), "AI_PROTO_BACKEND_PORT")
    reload_enabled = _env_bool("AI_PROTO_BACKEND_RELOAD", False)
    fallback_port_raw = os.getenv("AI_PROTO_BACKEND_FALLBACK_PORT")
    fallback_defined = fallback_port_raw is not None and bool(fallback_port_raw.strip())

    selected_port = requested_port
    available, bind_error = _is_port_available(host, requested_port)

    if not available:
        if not fallback_defined:
            logger.error(
                "backend.startup_failed.port_in_use host=%s port=%s fallback=disabled error=%r. "
                "No se aplicara fallback silencioso. Libera el puerto o define "
                "AI_PROTO_BACKEND_FALLBACK_PORT explicitamente.",
                host,
                requested_port,
                bind_error,
            )
            raise SystemExit(1)

        fallback_port = _parse_port(
            fallback_port_raw.strip(),
            "AI_PROTO_BACKEND_FALLBACK_PORT",
        )
        if fallback_port == requested_port:
            logger.error(
                "backend.startup_failed.invalid_fallback requested_port=%s fallback_port=%s. "
                "El fallback debe ser distinto al puerto solicitado.",
                requested_port,
                fallback_port,
            )
            raise SystemExit(1)

        fallback_available, fallback_error = _is_port_available(host, fallback_port)
        if not fallback_available:
            logger.error(
                "backend.startup_failed.fallback_port_in_use host=%s requested_port=%s fallback_port=%s error=%r",
                host,
                requested_port,
                fallback_port,
                fallback_error,
            )
            raise SystemExit(1)

        selected_port = fallback_port
        logger.warning(
            "backend.port_fallback_enabled requested_port=%s selected_port=%s source=AI_PROTO_BACKEND_FALLBACK_PORT",
            requested_port,
            selected_port,
        )

    run_kwargs: dict[str, object] = {
        "host": host,
        "port": selected_port,
        "reload": reload_enabled,
    }

    if reload_enabled:
        run_kwargs.update(
            {
                "reload_dirs": _reload_dirs(),
                "reload_includes": _reload_includes(),
                "reload_excludes": _reload_excludes(),
            }
        )

    # PowerShell: $env:AI_PROTO_BACKEND_RELOAD="true"; python main.py
    # CMD/bat:    set AI_PROTO_BACKEND_RELOAD=true && python main.py
    logger.info(
        "backend.startup host=%s port=%s reload=%s fallback_explicit=%s",
        host,
        selected_port,
        reload_enabled,
        fallback_defined,
    )
    uvicorn.run("main:app", **run_kwargs)
