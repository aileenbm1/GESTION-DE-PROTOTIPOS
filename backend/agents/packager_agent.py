from __future__ import annotations

from pathlib import Path

from models.schemas import Project
from services.generation_service import GenerationService


class PackagerAgent:

    def __init__(
        self,
        generator: GenerationService | None = None
    ) -> None:
        self.generator = generator or GenerationService()

    def run(
        self,
        project: Project
    ) -> Path:

        if not project.angular_path:
            raise ValueError(
                "Frontend no generado."
            )

        if not project.backend_path:
            raise ValueError(
                "Backend no generado."
            )

        package = self.generator.package_project(
            project
        )

        project.package_path = str(package)

        return package