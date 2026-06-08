from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from api.auth import require_api_key
from models.schemas import (
    Project,
    ProjectCreate,
    Requirement,
    RequirementsUpdate,
    ScreenPrompt,
    ScreenSpec,
    ScreensUpdate,
)
from orchestrator.orchestrator import PrototypeOrchestrator
from services.prototype_validator import PrototypeValidator
from services.workspace_build_manager import WorkspaceBuildError
from storage.file_store import FileStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])

store = FileStore()
orchestrator = PrototypeOrchestrator(store)
_validator = PrototypeValidator(store)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/projects", response_model=list[Project])
async def list_projects() -> list[Project]:
    return store.list_projects()


@router.post("/projects", response_model=Project)
async def create_project(payload: ProjectCreate = Body(...)) -> Project:
    started = time.perf_counter()

    try:
        project = store.create_project(payload.name)
        logger.info(
            "project.create.success project_id=%s name=%r elapsed_ms=%.2f",
            project.id,
            payload.name,
            (time.perf_counter() - started) * 1000,
        )
        return project
    except Exception as exc:
        logger.exception("project.create.failed name=%r error=%s", payload.name, repr(exc))
        raise


@router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str) -> Project:
    started = time.perf_counter()

    try:
        project = store.get_project(project_id)
        logger.info(
            "project.get.success project_id=%s status=%s elapsed_ms=%.2f",
            project_id,
            project.status,
            (time.perf_counter() - started) * 1000,
        )
        return project
    except Exception as exc:
        logger.exception("project.get.failed project_id=%s error=%s", project_id, repr(exc))
        raise


@router.get("/projects/{project_id}/progress")
async def get_project_progress(project_id: str) -> dict:
    started = time.perf_counter()

    try:
        project = store.get_project(project_id)
        payload = {
            "project_id": project.id,
            "status": project.status,
            "progress": project.progress,
            "current_step": project.current_step,
            "logs": project.logs,
        }
        logger.info(
            "project.progress.success project_id=%s progress=%s elapsed_ms=%.2f",
            project_id,
            project.progress,
            (time.perf_counter() - started) * 1000,
        )
        return payload
    except Exception as exc:
        logger.exception(
            "project.progress.failed project_id=%s error=%s",
            project_id,
            repr(exc),
        )
        raise


@router.post("/projects/{project_id}/upload", response_model=Project)
async def upload_file(
    project_id: str,
    file: UploadFile = File(...),
) -> Project:
    started = time.perf_counter()

    try:
        project = store.get_project(project_id)
        uploaded = await store.save_upload(project, file)
        logger.info(
            "project.upload.success project_id=%s upload_path=%s elapsed_ms=%.2f",
            project_id,
            uploaded.upload_path,
            (time.perf_counter() - started) * 1000,
        )
        return uploaded
    except Exception as exc:
        logger.exception(
            "project.upload.failed project_id=%s filename=%r error=%s",
            project_id,
            getattr(file, "filename", None),
            repr(exc),
        )
        raise


@router.post("/projects/{project_id}/run-initial", response_model=Project)
async def run_initial(project_id: str) -> Project:
    started = time.perf_counter()

    try:
        result = await asyncio.to_thread(orchestrator.run_initial_analysis, project_id)
        logger.info(
            "project.run_initial.success project_id=%s requirements=%s elapsed_ms=%.2f",
            project_id,
            len(result.requirements),
            (time.perf_counter() - started) * 1000,
        )
        return result
    except Exception as exc:
        logger.exception("project.run_initial.failed project_id=%s error=%s", project_id, repr(exc))
        raise


@router.put("/projects/{project_id}/requirements", response_model=Project)
async def save_requirements(
    project_id: str,
    payload: RequirementsUpdate | list[Requirement] = Body(...),
) -> Project:
    started = time.perf_counter()

    try:
        project = store.get_project(project_id)
        requirements = payload.requirements if isinstance(payload, RequirementsUpdate) else payload

        project.requirements = [
            Requirement(**req) if isinstance(req, dict) else req for req in requirements
        ]

        saved = store.save_project(project)
        logger.info(
            "project.requirements.save.success project_id=%s requirements=%s elapsed_ms=%.2f",
            project_id,
            len(saved.requirements),
            (time.perf_counter() - started) * 1000,
        )
        return saved
    except Exception as exc:
        logger.exception("project.requirements.save.failed project_id=%s error=%s", project_id, repr(exc))
        raise


@router.post("/projects/{project_id}/screens/generate", response_model=Project)
async def generate_screens(project_id: str) -> Project:
    started = time.perf_counter()

    try:
        result = await asyncio.to_thread(orchestrator.generate_screens, project_id)
        logger.info(
            "project.screens.generate.success project_id=%s screens=%s elapsed_ms=%.2f",
            project_id,
            len(result.screens),
            (time.perf_counter() - started) * 1000,
        )
        return result
    except Exception as exc:
        logger.exception("project.screens.generate.failed project_id=%s error=%s", project_id, repr(exc))
        raise


@router.post("/projects/{project_id}/screens/refine", response_model=Project)
async def refine_screens(project_id: str, payload: ScreenPrompt = Body(...)) -> Project:
    started = time.perf_counter()

    try:
        result = await asyncio.to_thread(orchestrator.refine_screens, project_id, payload.prompt)
        logger.info(
            "project.screens.refine.success project_id=%s screens=%s elapsed_ms=%.2f",
            project_id,
            len(result.screens),
            (time.perf_counter() - started) * 1000,
        )
        return result
    except Exception as exc:
        logger.exception("project.screens.refine.failed project_id=%s error=%s", project_id, repr(exc))
        raise


@router.put("/projects/{project_id}/screens", response_model=Project)
async def save_screens(
    project_id: str,
    payload: ScreensUpdate | list[ScreenSpec] = Body(...),
) -> Project:
    started = time.perf_counter()

    try:
        project = store.get_project(project_id)
        screens = payload.screens if isinstance(payload, ScreensUpdate) else payload

        project.screens = [
            ScreenSpec(**screen) if isinstance(screen, dict) else screen for screen in screens
        ]

        saved = store.save_project(project)
        logger.info(
            "project.screens.save.success project_id=%s screens=%s elapsed_ms=%.2f",
            project_id,
            len(saved.screens),
            (time.perf_counter() - started) * 1000,
        )
        return saved
    except Exception as exc:
        logger.exception("project.screens.save.failed project_id=%s error=%s", project_id, repr(exc))
        raise


@router.post("/projects/{project_id}/screens/approve", response_model=Project)
async def approve_screens(project_id: str) -> Project:
    started = time.perf_counter()

    try:
        project = store.get_project(project_id)

        approved = [
            ScreenSpec(**{**screen.model_dump(mode="json"), "accepted": True})
            for screen in project.screens
        ]

        await asyncio.to_thread(orchestrator.approve_screens, project_id, approved)
        updated_project = await asyncio.to_thread(orchestrator.generate_architecture, project_id)

        logger.info(
            "project.screens.approve.success project_id=%s elapsed_ms=%.2f",
            project_id,
            (time.perf_counter() - started) * 1000,
        )
        return updated_project
    except Exception as exc:
        logger.exception("project.screens.approve.failed project_id=%s error=%s", project_id, repr(exc))
        raise


@router.post("/projects/{project_id}/architecture", response_model=Project)
async def generate_architecture(project_id: str) -> Project:
    started = time.perf_counter()

    try:
        result = await asyncio.to_thread(orchestrator.generate_architecture, project_id)
        logger.info(
            "project.architecture.generate.success project_id=%s elapsed_ms=%.2f",
            project_id,
            (time.perf_counter() - started) * 1000,
        )
        return result
    except Exception as exc:
        logger.exception(
            "project.architecture.generate.failed project_id=%s error=%s",
            project_id,
            repr(exc),
        )
        raise


@router.post("/projects/{project_id}/code", response_model=Project)
async def generate_code(project_id: str) -> Project:
    started = time.perf_counter()

    try:
        result = await asyncio.to_thread(orchestrator.generate_code, project_id)
        logger.info(
            "project.code.generate.success project_id=%s angular=%s backend=%s elapsed_ms=%.2f",
            project_id,
            result.angular_path,
            result.backend_path,
            (time.perf_counter() - started) * 1000,
        )
        return result
    except HTTPException:
        raise
    except WorkspaceBuildError as exc:
        payload = exc.to_payload()
        logger.exception(
            "project.code.generate.angular_build_failed project_id=%s stage=%s return_code=%s root_cause=%r",
            project_id,
            payload.get("stage"),
            payload.get("return_code"),
            payload.get("root_cause"),
        )
        return JSONResponse(status_code=500, content=payload)
    except Exception as exc:
        logger.exception("project.code.generate.failed project_id=%s error=%s", project_id, repr(exc))
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "stage": "code-generation",
                "command": "orchestrator.generate_code",
                "return_code": None,
                "stdout": "",
                "stderr": "",
                "root_cause": "Error interno durante la generación de código",
                "build_log_path": "",
            },
        )


@router.post("/projects/{project_id}/package", response_model=Project)
async def package_project(project_id: str) -> Project:
    started = time.perf_counter()

    try:
        result = await asyncio.to_thread(orchestrator.package, project_id)
        logger.info(
            "project.package.success project_id=%s zip_path=%s elapsed_ms=%.2f",
            project_id,
            result.zip_path,
            (time.perf_counter() - started) * 1000,
        )
        return result
    except Exception as exc:
        logger.exception("project.package.failed project_id=%s error=%s", project_id, repr(exc))
        raise


@router.get("/projects/{project_id}/download")
async def download_project(project_id: str) -> FileResponse:
    started = time.perf_counter()

    try:
        project = store.get_project(project_id)

        if not project.zip_path:
            raise HTTPException(
                status_code=404,
                detail="El proyecto no ha sido empaquetado",
            )

        zip_file = Path(project.zip_path)

        if not zip_file.exists() or not zip_file.is_file():
            raise HTTPException(
                status_code=404,
                detail="El archivo empaquetado no está disponible",
            )

        logger.info(
            "project.download.success project_id=%s zip_path=%s elapsed_ms=%.2f",
            project_id,
            zip_file,
            (time.perf_counter() - started) * 1000,
        )

        return FileResponse(
            path=str(zip_file),
            filename=zip_file.name,
            media_type="application/zip",
        )
    except Exception as exc:
        logger.exception("project.download.failed project_id=%s error=%s", project_id, repr(exc))
        raise


@router.post("/projects/{project_id}/validate-full")
async def validate_full(
    project_id: str,
    e2e: bool = True,
) -> JSONResponse:
    """
    Ejecuta la validación completa del prototipo:
    compilación, TypeScript, build producción, unit tests, lint,
    análisis de arquitectura, E2E con Playwright y score final.
    """
    started = time.perf_counter()
    try:
        project = store.get_project(project_id)

        if not project.angular_path:
            raise HTTPException(
                status_code=400,
                detail="El proyecto no tiene código generado. Ejecuta primero /code y /package.",
            )

        validator = PrototypeValidator(store, e2e_enabled=e2e)
        report = await asyncio.to_thread(validator.validate, project)
        report_dict = report.to_dict()

        project = store.get_project(project_id)
        project.validation_report = report_dict
        store.save_project(project)

        logger.info(
            "project.validate_full.success project_id=%s grade=%s score=%s/%s elapsed_ms=%.2f",
            project_id,
            report_dict.get("grade"),
            report_dict.get("total_score"),
            report_dict.get("max_score"),
            (time.perf_counter() - started) * 1000,
        )
        return JSONResponse(status_code=200, content=report_dict)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "project.validate_full.failed project_id=%s error=%s", project_id, repr(exc)
        )
        raise HTTPException(status_code=500, detail="Error durante la validación del prototipo")


@router.get("/projects/{project_id}/validation-report")
async def get_validation_report(project_id: str) -> JSONResponse:
    """Devuelve el último reporte de validación del proyecto."""
    project = store.get_project(project_id)
    if not project.validation_report:
        raise HTTPException(
            status_code=404,
            detail="No existe reporte de validación. Ejecuta primero /validate-full.",
        )
    return JSONResponse(status_code=200, content=project.validation_report)
