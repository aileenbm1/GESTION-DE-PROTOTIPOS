from __future__ import annotations

from pathlib import Path

from models.schemas import Project
from services.generation_service import GenerationService


class DotnetGeneratorAgent:

    def __init__(
        self,
        generator: GenerationService | None = None,
    ) -> None:
        self.generator = (
            generator
            or GenerationService()
        )

    def run(
        self,
        project: Project,
    ) -> Path:

        if project.architecture is None:
            raise ValueError(
                "No existe arquitectura."
            )

        if not project.requirements:
            raise ValueError(
                "No existen requerimientos."
            )

        if not project.screens:
            raise ValueError(
                "No existen pantallas."
            )

        project.current_step = (
            "Generando backend C# Web API"
        )

        project.progress = 70

        project.logs.append(
            "Iniciando generación backend C# ASP.NET Core Web API"
        )

        generated_path = (
            self.generator.generate_dotnet(
                project
            )
        )

        project.backend_path = str(
            generated_path
        )

        project.logs.append(
            f"Backend generado: {generated_path}"
        )

        project.progress = 80

        return generated_path