from __future__ import annotations

import asyncio
import logging

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)

from api.auth import require_api_key_ws
from storage.file_store import FileStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

store = FileStore()


@router.websocket("/ws/projects/{project_id}/progress")
async def project_progress(
    websocket: WebSocket,
    project_id: str,
) -> None:
    await require_api_key_ws(websocket)
    await websocket.accept()

    try:
        while True:
            try:
                project = store.get_project(project_id)
                await websocket.send_json(
                    {
                        "project_id": project.id,
                        "status": project.status,
                        "progress": project.progress,
                        "current_step": project.current_step,
                        "logs": project.logs[-10:],
                    }
                )
            except Exception:
                logger.exception("websocket.progress.error project_id=%s", project_id)
                await websocket.send_json({"error": "Error al obtener estado del proyecto"})

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        logger.info("websocket.disconnected project_id=%s", project_id)
