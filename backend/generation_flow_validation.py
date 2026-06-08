from __future__ import annotations

import subprocess

from models.schemas import Project, ProjectStatus, Requirement, ScreenSpec
from services.generation_service import GenerationService


def main() -> None:
    project = Project(
        id="proj_validation_enterprise",
        name="Validacion Enterprise",
        status=ProjectStatus.architecture_ready,
        requirements=[
            Requirement(
                title="Gestionar solicitudes",
                description="Registrar, consultar, filtrar y aprobar solicitudes con reglas de negocio.",
                module="Solicitudes",
                priority="high",
                actors=["Operador", "Revisor"],
                entities=["Solicitud"],
                validations=["Folio obligatorio", "Descripcion minima"],
                business_rules=["Toda aprobacion debe registrar usuario y fecha."],
                acceptance_criteria=["El usuario puede guardar una solicitud valida."],
                workflows=["Crear solicitud", "Aprobar solicitud"],
                dependencies=[],
            )
        ],
        screens=[
            ScreenSpec(
                name="Gestion de Solicitudes",
                module="Solicitudes",
                route="/solicitudes",
                purpose="Operar solicitudes con formulario, tabla y auditoria.",
                components=["Formulario reactivo", "Tabla con filtros"],
                forms=["Solicitud"],
                tables=["Solicitudes"],
                actions=["Crear", "Editar", "Aprobar"],
                validations=["Folio obligatorio"],
            )
        ],
    )

    generator = GenerationService()
    angular = generator.generate_angular(project)
    dotnet = generator.generate_dotnet(project)
    package = generator.package_project(project)

    print(f"ANGULAR={angular}")
    print(f"DOTNET={dotnet}")
    print(f"PACKAGE={package}")

    build = subprocess.run(["dotnet", "build"], cwd=dotnet, capture_output=True, text=True, timeout=180)
    print(f"DOTNET_BUILD={build.returncode}")
    if build.returncode != 0:
        print(build.stdout)
        print(build.stderr)
        raise SystemExit(build.returncode)


if __name__ == "__main__":
    main()
