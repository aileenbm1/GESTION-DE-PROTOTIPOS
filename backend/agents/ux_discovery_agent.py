from __future__ import annotations

import json

from models.schemas import DomainAnalysis, RequirementEngineeringDocument, ScreenCatalogItem
from services.azure_openai_service import AzureOpenAIService


class UXDiscoveryAgent:
    def __init__(self, ai: AzureOpenAIService | None = None) -> None:
        self.ai = ai or AzureOpenAIService()

    def run(
        self,
        domain_analysis: DomainAnalysis,
        requirement_engineering: RequirementEngineeringDocument,
    ) -> list[ScreenCatalogItem]:
        fr = requirement_engineering.functional_requirements
        modules = domain_analysis.modules or sorted({item.module for item in fr}) or ["General"]

        fallback_items = [
            {
                "id": "SCR-001",
                "name": "Dashboard Ejecutivo",
                "module": "Dashboard" if "Dashboard" in modules else modules[0],
                "route": "/dashboard",
                "objective": "Monitorear KPIs, alertas, pendientes y progreso de procesos.",
                "components": ["KPI cards", "Grafica de tendencia", "Tabla de pendientes", "Panel de alertas"],
                "actions": ["Filtrar", "Consultar", "Exportar"],
                "validations": ["Filtro de fecha valido", "Control por rol"],
                "permissions": ["read:dashboard"],
                "linked_requirement_ids": [item.id for item in fr[:1]],
            }
        ]

        for idx, req in enumerate(fr, start=2):
            module_slug = req.module.lower().replace(" ", "-")
            fallback_items.append(
                {
                    "id": f"SCR-{idx:03d}",
                    "name": f"{req.module} - {req.title}",
                    "module": req.module,
                    "route": f"/{module_slug}/{req.id.lower()}",
                    "objective": req.description,
                    "components": ["Formulario", "Tabla", "Panel de detalle", "Bitacora"],
                    "actions": ["Crear", "Editar", "Consultar", "Aprobar"],
                    "validations": req.exceptions or ["Validacion de reglas de negocio"],
                    "permissions": [f"manage:{module_slug}"],
                    "linked_requirement_ids": [req.id],
                }
            )

        fallback = {"screen_catalog": fallback_items}

        system_prompt = """
Eres UX Discovery Architect.
Genera Screen Catalog enterprise desde requisitos y dominio.
Responde JSON valido con "screen_catalog".
Cada pantalla requiere: id, name, module, route, objective, components, actions, validations, permissions, linked_requirement_ids.
"""
        user_prompt = (
            "DOMAIN_ANALYSIS:\n"
            + json.dumps(domain_analysis.model_dump(mode="json"), ensure_ascii=False, indent=2)
            + "\n\nREQUIREMENT_ENGINEERING:\n"
            + json.dumps(requirement_engineering.model_dump(mode="json"), ensure_ascii=False, indent=2)
        )
        data = self.ai.chat_json(system_prompt, user_prompt, fallback)
        catalog = data.get("screen_catalog", fallback_items)
        return [ScreenCatalogItem.model_validate(item) for item in catalog]
