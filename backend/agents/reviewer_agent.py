from __future__ import annotations

from pathlib import Path

from agents.project_validation_agent import (
    ProjectValidationAgent,
)

from models.schemas import Project


class ReviewerAgent:

    def run(
        self,
        project: Project,
    ) -> list[str]:

        findings: list[str] = []

        if not project.requirements:
            findings.append(
                "No hay requerimientos aprobados."
            )

        if not project.screens:
            findings.append(
                "No hay pantallas generadas."
            )

        if project.architecture is None:
            findings.append(
                "No se genero arquitectura tecnica."
            )

        if not project.angular_path:
            findings.append(
                "No se genero frontend Angular."
            )

        if not project.backend_path:
            findings.append(
                "No se genero backend .NET."
            )

        findings.extend(
            self.validate_architecture(project)
        )

        findings.extend(
            self.validate_frontend(project)
        )

        findings.extend(
            self.validate_backend(project)
        )

        findings.extend(
            self.validate_build(project)
        )

        findings.extend(
            self.validate_dependencies(project)
        )

        return findings or [
            "Revision enterprise completada sin bloqueos criticos."
        ]

    def validate_architecture(
        self,
        project: Project,
    ) -> list[str]:

        findings: list[str] = []

        if project.architecture is None:
            findings.append(
                "Arquitectura no generada."
            )

        return findings

    def validate_frontend(
        self,
        project: Project,
    ) -> list[str]:

        findings: list[str] = []

        if not project.angular_path:
            findings.append(
                "Frontend Angular no encontrado."
            )

        elif not Path(project.angular_path).exists():
            findings.append(
                f"No existe la ruta Angular: {project.angular_path}"
            )

        return findings

    def validate_backend(
        self,
        project: Project,
    ) -> list[str]:

        findings: list[str] = []

        if not project.backend_path:
            findings.append(
                "Backend .NET no encontrado."
            )

        elif not Path(project.backend_path).exists():
            findings.append(
                f"No existe la ruta .NET: {project.backend_path}"
            )

        return findings

    def validate_build(
        self,
        project: Project,
    ) -> list[str]:

        validator = ProjectValidationAgent()

        return validator.run(project)

    def validate_dependencies(
        self,
        project: Project,
    ) -> list[str]:

        findings: list[str] = []

        if project.angular_path:
            package_json = (
                Path(project.angular_path)
                / "package.json"
            )

            if not package_json.exists():
                findings.append(
                    "package.json no encontrado."
                )

        if project.backend_path:

            csproj_files = list(
                Path(project.backend_path).rglob(
                    "*.csproj"
                )
            )

            if not csproj_files:
                findings.append(
                    "Archivo .csproj no encontrado."
                )

        return findings