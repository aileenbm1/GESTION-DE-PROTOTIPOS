from __future__ import annotations

from agents.angular_generator_agent import AngularGeneratorAgent
from agents.dotnet_generator_agent import DotnetGeneratorAgent
from agents.reviewer_agent import ReviewerAgent
from models.schemas import Project
from services.generation_service import GenerationService
from storage.file_store import FileStore


class ProjectGenerator:
    """
    Phase 7: Generate code only when traceability and completeness are satisfied.
    """

    def __init__(self, store: FileStore | None = None, generator: GenerationService | None = None) -> None:
        self.store = store or FileStore()
        self.generator = generator or GenerationService(self.store)
        self.angular = AngularGeneratorAgent(self.generator)
        self.dotnet = DotnetGeneratorAgent(self.generator)
        self.reviewer = ReviewerAgent()

    def run(self, project: Project) -> Project:
        self._assert_ready_for_generation(project)

        project.current_step = "Generando codigo con trazabilidad"
        project.progress = max(project.progress, 45)
        project.logs.append("Iniciando generacion de codigo con criterios enterprise.")

        self.angular.run(project)
        project.logs.append("Frontend Angular generado.")
        project.progress = 50
        project.current_step = "Angular generado"

        self.dotnet.run(project)
        project.logs.append("Backend C# Web API generado.")
        project.progress = 55
        project.current_step = "Backend generado"

        project.output_dir = str(self.store.project_output_dir(project.id))
        project.logs.extend(self.reviewer.run(project))
        project.progress = 56
        project.current_step = "Codigo generado"
        return project

    def _assert_ready_for_generation(self, project: Project) -> None:
        if not project.business_context:
            raise ValueError("Falta Business Context Document. Ejecuta fase de ingesta.")
        if not project.domain_analysis:
            raise ValueError("Falta Domain Analysis. Ejecuta fase de discovery.")
        if not project.requirement_engineering:
            raise ValueError("Falta Requirement Engineering.")
        if not project.screen_catalog:
            raise ValueError("Falta Screen Catalog.")
        if project.architecture is None:
            raise ValueError("Falta arquitectura.")
        if not project.completeness_audit or not project.completeness_audit.completed:
            raise ValueError("Completeness audit no aprobado.")
        if not project.traceability:
            raise ValueError("No existe trazabilidad completa requisito-pantalla-api-entidad.")
