from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from models.debug_schemas import (
    DebugRunResponse,
    DebugSession,
    DebugSessionStatus,
    DebugUploadResponse,
)
from services.ai_fix_service import AIFixService
from services.debug_analysis_service import DebugAnalysisService
from services.frame_extractor import FrameExtractor
from services.playwright_service import PlaywrightService
from services.video_analysis_service import VideoAnalysisService
from api.auth import require_api_key
from storage.debug_store import DebugStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debug", tags=["debug"], dependencies=[Depends(require_api_key)])

store = DebugStore()
video_service = VideoAnalysisService()
frame_extractor = FrameExtractor()
playwright_service = PlaywrightService()
analysis_service = DebugAnalysisService()
fix_service = AIFixService()

BASE_DIR = Path(__file__).resolve().parent.parent


@router.post("/upload-video", response_model=DebugUploadResponse)
async def upload_debug_video(file: UploadFile = File(...)) -> DebugUploadResponse:
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Archivo invalido: nombre faltante")

        if not video_service.is_supported_extension(file.filename):
            raise HTTPException(status_code=415, detail="Formato no soportado. Usa mp4, webm o mov")

        session_id = f"dbg_{uuid.uuid4().hex[:12]}"
        ext = Path(file.filename).suffix.lower()
        video_path = store.videos_dir / f"{session_id}{ext}"

        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        metadata = video_service.metadata(video_path, file.content_type)
        session = DebugSession(
            session_id=session_id,
            status=DebugSessionStatus.uploaded,
            video_path=str(video_path),
            video_metadata=metadata,
            artifacts={"source_filename": file.filename},
        )

        store.save_session(session)

        logger.info(
            "debug.upload.success session_id=%s file=%s size=%s",
            session_id,
            file.filename,
            metadata.size_bytes,
        )

        return DebugUploadResponse(
            session_id=session_id,
            status=session.status,
            video_metadata=metadata,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("debug.upload.failed error=%s", repr(exc))
        raise HTTPException(status_code=500, detail="Error al subir video")


@router.get("/sessions")
async def list_debug_sessions() -> list[DebugSession]:
    return store.list_sessions()


@router.get("/sessions/{session_id}")
async def get_debug_session(session_id: str) -> DebugSession:
    try:
        return store.get_session(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")


@router.post("/sessions/{session_id}/extract", response_model=DebugRunResponse)
async def extract_frames(session_id: str) -> DebugRunResponse:
    try:
        session = store.get_session(session_id)
        frames_dir = store.frames_dir / session_id
        frames = frame_extractor.extract(Path(session.video_path), frames_dir, every_ms=450)

        session.frames = frames
        session.status = DebugSessionStatus.frames_extracted
        session.artifacts["frames_dir"] = str(frames_dir)
        store.save_session(session)

        return DebugRunResponse(
            session_id=session_id,
            status=session.status,
            message=f"Frames extraidos: {len(frames)}",
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    except Exception as exc:
        logger.exception("debug.extract.failed session_id=%s error=%s", session_id, repr(exc))
        raise HTTPException(status_code=500, detail="Error extrayendo frames")


@router.post("/sessions/{session_id}/analyze", response_model=DebugRunResponse)
async def analyze_session(session_id: str) -> DebugRunResponse:
    try:
        session = store.get_session(session_id)

        if not session.frames:
            frames_dir = store.frames_dir / session_id
            session.frames = frame_extractor.extract(Path(session.video_path), frames_dir, every_ms=450)
            session.artifacts["frames_dir"] = str(frames_dir)

        session.ui_events = video_service.detect_ui_events(
            session.frames,
            source_error_hint=" ".join(session.frontend_errors + session.backend_errors),
        )

        session.status = DebugSessionStatus.analyzed
        store.save_session(session)

        return DebugRunResponse(
            session_id=session_id,
            status=session.status,
            message=f"Analisis visual completado. Eventos detectados: {len(session.ui_events)}",
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    except Exception as exc:
        logger.exception("debug.analyze.failed session_id=%s error=%s", session_id, repr(exc))
        raise HTTPException(status_code=500, detail="Error analizando sesión")


@router.post("/sessions/{session_id}/replay", response_model=DebugRunResponse)
async def replay_session(
    session_id: str,
    frontend_url: str | None = Query(default=None),
) -> DebugRunResponse:
    try:
        if frontend_url is not None:
            parsed = urlparse(frontend_url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise HTTPException(status_code=400, detail="URL de frontend inválida")
        session = store.get_session(session_id)
        url = frontend_url or video_service.current_frontend_url()

        network_records, frontend_errors, har_path = playwright_service.run_replay(session_id, url)

        session.network_records = network_records
        session.frontend_errors.extend(frontend_errors)
        if har_path:
            session.artifacts["har_path"] = har_path

        session.status = DebugSessionStatus.replayed
        store.save_session(session)

        return DebugRunResponse(
            session_id=session_id,
            status=session.status,
            message=(
                f"Replay completado en {url}. "
                f"Requests capturados: {len(network_records)}. Errores frontend: {len(frontend_errors)}"
            ),
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    except Exception as exc:
        logger.exception("debug.replay.failed session_id=%s error=%s", session_id, repr(exc))
        raise HTTPException(status_code=500, detail="Error reproduciendo sesión")


@router.post("/sessions/{session_id}/diagnose", response_model=DebugRunResponse)
async def diagnose_session(session_id: str) -> DebugRunResponse:
    try:
        session = store.get_session(session_id)
        session.diagnostic = analysis_service.diagnose(
            session_id=session_id,
            ui_events=session.ui_events,
            network_records=session.network_records,
            frontend_errors=session.frontend_errors,
            backend_errors=session.backend_errors,
        )
        store.save_session(session)

        return DebugRunResponse(
            session_id=session_id,
            status=session.status,
            message=f"Diagnostico generado: {session.diagnostic.root_cause}",
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    except Exception as exc:
        logger.exception("debug.diagnose.failed session_id=%s error=%s", session_id, repr(exc))
        raise HTTPException(status_code=500, detail="Error generando diagnóstico")


@router.post("/sessions/{session_id}/fix", response_model=DebugRunResponse)
async def fix_session(
    session_id: str,
    apply_fix: bool = Query(default=False),
) -> DebugRunResponse:
    try:
        session = store.get_session(session_id)

        if not session.diagnostic:
            session.diagnostic = analysis_service.diagnose(
                session_id=session_id,
                ui_events=session.ui_events,
                network_records=session.network_records,
                frontend_errors=session.frontend_errors,
                backend_errors=session.backend_errors,
            )

        session.fix_proposal = fix_service.propose(session.diagnostic)

        if apply_fix:
            session.artifacts["fix_apply_result"] = fix_service.apply_placeholder(BASE_DIR, session.fix_proposal)

        session.status = DebugSessionStatus.fixed
        store.save_session(session)

        return DebugRunResponse(
            session_id=session_id,
            status=session.status,
            message="Fix generado" + (" y aplicado" if apply_fix else " (modo propuesta)"),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    except Exception as exc:
        logger.exception("debug.fix.failed session_id=%s error=%s", session_id, repr(exc))
        raise HTTPException(status_code=500, detail="Error generando fix")


@router.post("/sessions/{session_id}/validate", response_model=DebugRunResponse)
async def validate_session(
    session_id: str,
    frontend_url: str | None = Query(default=None),
) -> DebugRunResponse:
    try:
        if frontend_url is not None:
            parsed = urlparse(frontend_url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise HTTPException(status_code=400, detail="URL de frontend inválida")
        session = store.get_session(session_id)
        url = frontend_url or video_service.current_frontend_url()

        network_records, frontend_errors, har_path = playwright_service.run_replay(session_id, url)
        session.network_records = network_records
        session.frontend_errors.extend(frontend_errors)

        if har_path:
            session.artifacts["validation_har_path"] = har_path

        bad = [r for r in network_records if (r.status or 0) >= 500 or (r.error and "Network" in r.error)]
        if any("CORS" in e.upper() for e in frontend_errors):
            bad.append(network_records[0] if network_records else None)

        session.status = DebugSessionStatus.validated if not bad else DebugSessionStatus.failed
        store.save_session(session)

        return DebugRunResponse(
            session_id=session_id,
            status=session.status,
            message=(
                "Validacion completada sin fallos criticos"
                if not bad
                else "Validacion detecto fallos criticos de red/500/CORS"
            ),
        )
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    except Exception as exc:
        logger.exception("debug.validate.failed session_id=%s error=%s", session_id, repr(exc))
        raise HTTPException(status_code=500, detail="Error validando sesión")
