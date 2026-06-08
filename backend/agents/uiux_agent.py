from __future__ import annotations

from models.schemas import (
    Requirement,
    ScreenCatalogItem,
    ScreenSpec,
)


class UiUxAgent:
    """
    Compatibility adapter:
    - Converts Screen Catalog discovery outputs into legacy ScreenSpec used by frontend/generator.
    """

    def run(
        self,
        requirements: list[Requirement] | None,
        *,
        screen_catalog: list[ScreenCatalogItem] | None = None,
    ) -> list[dict]:
        if screen_catalog:
            return [self._from_catalog(item) for item in screen_catalog]

        requirements = requirements or []
        modules = sorted({req.module for req in requirements if getattr(req, "accepted", True)}) or ["General"]
        screens: list[dict] = []
        screens.append(
            {
                "name": "Dashboard Ejecutivo",
                "module": "Dashboard" if "Dashboard" in modules else modules[0],
                "route": "/dashboard",
                "purpose": "Monitorear KPIs, alertas, pendientes y trazabilidad operativa.",
                "screen_type": "dashboard",
                "roles": ["Administrador", "Operador", "Revisor"],
                "permissions": ["read:dashboard"],
                "components": ["KPI cards", "Panel de alertas", "Tabla de pendientes"],
                "forms": [],
                "tables": ["Pendientes", "Eventos"],
                "actions": ["Filtrar", "Consultar", "Exportar"],
                "validations": ["Filtro de fecha valido"],
                "accepted": True,
            }
        )
        for req in requirements:
            if not req.accepted:
                continue
            module_slug = req.module.lower().replace(" ", "-")
            screens.append(
                {
                    "name": f"{req.module} - {req.title}",
                    "module": req.module,
                    "route": f"/{module_slug}/{req.id.lower()}",
                    "purpose": req.description,
                    "screen_type": "workspace",
                    "roles": req.actors or ["Operador"],
                    "permissions": [f"manage:{module_slug}"],
                    "components": ["Formulario", "Tabla", "Detalle", "Bitacora"],
                    "forms": ["Formulario principal"],
                    "tables": ["Listado principal"],
                    "actions": ["Crear", "Editar", "Consultar", "Aprobar"],
                    "validations": req.validations or ["Validaciones de negocio"],
                    "accepted": True,
                }
            )
        return screens

    def refine(self, screens: list[ScreenSpec], prompt: str) -> list[ScreenSpec]:
        refined = [screen.model_copy(deep=True) for screen in screens]
        if refined:
            refined[0].prompt_notes = prompt
            refined[0].purpose = f"{refined[0].purpose} Ajuste solicitado: {prompt}"
        return refined

    def _from_catalog(self, item: ScreenCatalogItem) -> dict:
        return {
            "id": item.id,
            "name": item.name,
            "module": item.module,
            "route": item.route,
            "purpose": item.objective,
            "screen_type": "workspace",
            "roles": [],
            "permissions": item.permissions,
            "components": item.components,
            "forms": [component for component in item.components if "form" in component.lower()] or ["Formulario principal"],
            "tables": [component for component in item.components if "tabla" in component.lower()] or ["Listado"],
            "actions": item.actions,
            "validations": item.validations,
            "prompt_notes": f"linked_requirements={','.join(item.linked_requirement_ids)}",
            "accepted": True,
        }
