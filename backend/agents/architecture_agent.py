from __future__ import annotations

import json

from models.schemas import (
    ArchitectureSpec,
    DomainAnalysis,
    Requirement,
    RequirementEngineeringDocument,
    ScreenCatalogItem,
    ScreenSpec,
)
from services.azure_openai_service import AzureOpenAIService


class ArchitectureAgent:
    def __init__(self, ai: AzureOpenAIService | None = None) -> None:
        self.ai = ai or AzureOpenAIService()

    def run(
        self,
        requirements: list[Requirement],
        screens: list[ScreenSpec],
        *,
        domain_analysis: DomainAnalysis | None = None,
        requirement_engineering: RequirementEngineeringDocument | None = None,
        screen_catalog: list[ScreenCatalogItem] | None = None,
    ) -> ArchitectureSpec:
        accepted_requirements = [req for req in requirements if req.accepted]
        accepted_screens = [screen for screen in screens if screen.accepted]

        modules_from_analysis = domain_analysis.modules if domain_analysis else []
        modules_from_requirements = sorted({req.module for req in accepted_requirements})
        modules = modules_from_analysis or modules_from_requirements

        entities = []
        for req in accepted_requirements:
            entities.extend(req.entities)
        if domain_analysis:
            entities.extend(domain_analysis.entities)
        entities = sorted(set(entities))

        fallback = {
            "architecture_style": "Modular Monolith with Bounded Contexts",
            "summary": (
                "Arquitectura enterprise derivada de discovery funcional, "
                "requisitos y catalogo de pantallas con trazabilidad completa."
            ),
            "modules": modules,
            "frontend": {
                "framework": "Angular 20",
                "architecture": "Standalone + Feature Modules + Design System",
                "navigation": [item.route for item in accepted_screens],
                "state_management": "Signals + RxJS",
                "observability": "Error boundary, telemetry client, UX audit events",
            },
            "backend": {
                "framework": ".NET 10",
                "architecture": "Clean Architecture + CQRS light",
                "api_style": "REST",
                "security": "JWT + RBAC + audit middleware",
                "endpoints_count": max(1, len(accepted_requirements)),
            },
            "entities": [{"name": name, "type": "Aggregate"} for name in entities],
            "endpoints": [
                {
                    "id": f"API-{idx+1:03d}",
                    "method": "POST",
                    "path": f"/api/{req.module.lower().replace(' ', '-')}/{req.id.lower()}",
                    "requirement_id": req.id,
                    "entity": (req.entities[0] if req.entities else "Registro"),
                }
                for idx, req in enumerate(accepted_requirements)
            ],
            "services": [
                {"name": f"{module}Service", "module": module, "responsibility": "Application orchestration"}
                for module in modules
            ],
            "repositories": [
                {"name": f"{entity}Repository", "entity": entity, "storage": "Relational/Document adaptable"}
                for entity in entities[: max(1, min(len(entities), 12))]
            ],
            "workflows": [
                {"name": req.title, "requirement_id": req.id, "steps": req.workflows}
                for req in accepted_requirements
            ],
            "security": {
                "authentication": "OIDC/JWT",
                "authorization": "RBAC",
                "audit": "Immutable audit events",
                "compliance": ["least-privilege", "traceability"],
            },
            "persistence": {"strategy": "Repository abstraction", "default": "PostgreSQL", "cache": "Redis optional"},
            "integrations": [
                {"name": item, "type": "external"} for item in (domain_analysis.integrations if domain_analysis else [])
            ],
            "dependencies": {
                "frontend": ["@angular/*", "rxjs"],
                "backend": ["AspNetCore", "OpenAPI/Swagger"],
            },
            "testing": {
                "unit": True,
                "integration": True,
                "contract": True,
                "e2e": True,
            },
            "deployment": {
                "containers": True,
                "environments": ["dev", "qa", "prod"],
                "health_checks": ["/health", "/api/health"],
            },
            "coverage": [],
            "recommendations": [
                "Aplicar feature flags para rollout progresivo.",
                "Agregar data retention y data masking por cumplimiento.",
            ],
            "data_storage": "Repository abstraction with production-ready pluggable providers.",
            "risks": ["Dependencia de integraciones externas", "Gobernanza de permisos incompleta si no se mantiene el catalogo"],
        }

        system_prompt = """
Eres Principal Software Architect.
Genera arquitectura SOLO a partir de analisis funcional y trazabilidad.
No usar markdown.
Responder exclusivamente JSON valido compatible con ArchitectureSpec.
"""
        user_prompt = json.dumps(
            {
                "domain_analysis": domain_analysis.model_dump(mode="json") if domain_analysis else {},
                "requirement_engineering": (
                    requirement_engineering.model_dump(mode="json") if requirement_engineering else {}
                ),
                "requirements": [req.model_dump(mode="json") for req in accepted_requirements],
                "screen_catalog": [
                    item.model_dump(mode="json") for item in (screen_catalog or [])
                ],
                "screens": [screen.model_dump(mode="json") for screen in accepted_screens],
            },
            ensure_ascii=False,
            indent=2,
        )
        data = self.ai.chat_json(system_prompt, user_prompt, fallback)

        # GPT-4o sometimes wraps response in a top-level key — unwrap it
        if "summary" not in data:
            for key in ("architecture_spec", "architecture", "result", "spec"):
                if key in data and isinstance(data[key], dict) and "summary" in data[key]:
                    data = data[key]
                    break

        # Ensure required fields exist
        data.setdefault("summary", data.get("architecture_style", "Arquitectura enterprise generada automaticamente."))

        # Flatten list fields that might contain objects instead of strings
        for field in ("modules",):
            if field in data and isinstance(data[field], list):
                data[field] = [
                    item if isinstance(item, str)
                    else (item.get("name") or item.get("title") or str(item))
                    for item in data[field]
                ]

        return ArchitectureSpec.model_validate(data)
