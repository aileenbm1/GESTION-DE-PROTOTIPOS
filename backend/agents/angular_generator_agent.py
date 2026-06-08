from __future__ import annotations

from pathlib import Path

from models.schemas import Project
from services.generation_service import GenerationService


class AngularGeneratorAgent:

    def __init__(
        self,
        generator: GenerationService | None = None
    ) -> None:

        self.generator = generator or GenerationService()

    def run(self, project: Project) -> Path:

        generated_path = self.generator.generate_angular(project)

        project.angular_path = str(generated_path)

        self.generator.ensure_build_success(generated_path)

        return generated_path