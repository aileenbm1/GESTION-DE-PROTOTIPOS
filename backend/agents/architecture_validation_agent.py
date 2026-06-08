from __future__ import annotations

from models.schemas import (
    ArchitectureSpec,
    CompletenessAudit,
    Project,
    Requirement,
    ScreenCatalogItem,
    ScreenSpec,
    TraceabilityLink,
)


class ArchitectureValidationAgent:
    """
    Phase 6: Completeness validation and automatic gap filling.
    """

    def run(self, project: Project) -> tuple[CompletenessAudit, list[TraceabilityLink]]:
        requirements = [req for req in project.requirements if req.accepted]
        screens = [screen for screen in project.screens if screen.accepted]
        architecture = project.architecture
        screen_catalog = project.screen_catalog

        audit = CompletenessAudit()
        if architecture is None:
            audit.missing_entities.append("Arquitectura no generada")
            return audit, []

        self._ensure_requirement_entities(requirements, audit)
        self._ensure_screen_per_requirement(requirements, screens, screen_catalog, audit)
        self._ensure_permission_coverage(project, screens, audit)
        self._ensure_report_coverage(project, screens, audit)
        self._ensure_process_coverage(project, requirements, audit)
        self._ensure_architecture_entities(architecture, requirements, audit)
        self._ensure_architecture_endpoints(architecture, requirements, audit)

        traceability = self._build_traceability(requirements, screens, architecture)
        if not traceability:
            audit.missing_requirements.append("No fue posible construir trazabilidad requisito-pantalla-api-entidad.")
        else:
            missing_links = [req.id for req in requirements if req.id not in {t.requirement_id for t in traceability}]
            audit.missing_requirements.extend(missing_links)

        audit.completed = (
            not audit.missing_requirements
            and not audit.missing_entities
            and not audit.missing_screens
            and not audit.missing_permissions
            and not audit.missing_reports
            and not audit.incomplete_processes
            and bool(traceability)
        )
        return audit, traceability

    def _ensure_requirement_entities(self, requirements: list[Requirement], audit: CompletenessAudit) -> None:
        for req in requirements:
            if not req.entities:
                req.entities = ["Registro"]
                audit.auto_fixes_applied.append(f"{req.id}: entidad default 'Registro' agregada.")

    def _ensure_screen_per_requirement(
        self,
        requirements: list[Requirement],
        screens: list[ScreenSpec],
        screen_catalog: list[ScreenCatalogItem],
        audit: CompletenessAudit,
    ) -> None:
        linked = self._requirements_linked_to_screens(screens, screen_catalog)
        for req in requirements:
            if req.id in linked:
                continue
            route = f"/{req.module.lower().replace(' ', '-')}/{req.id.lower()}"
            new_screen = ScreenSpec(
                name=f"{req.module} - {req.title}",
                module=req.module,
                route=route,
                purpose=req.description,
                screen_type="workspace",
                roles=req.actors,
                permissions=[f"manage:{req.module.lower().replace(' ', '-')}"],
                components=["Formulario", "Tabla", "Detalle", "Bitacora"],
                forms=["Formulario principal"],
                tables=["Listado principal"],
                actions=["Crear", "Editar", "Consultar", "Aprobar"],
                validations=req.validations or ["Validacion de reglas de negocio"],
                prompt_notes=f"linked_requirements={req.id}",
                accepted=True,
            )
            screens.append(new_screen)
            screen_catalog.append(
                ScreenCatalogItem(
                    name=new_screen.name,
                    module=new_screen.module,
                    route=new_screen.route,
                    objective=new_screen.purpose,
                    components=new_screen.components,
                    actions=new_screen.actions,
                    validations=new_screen.validations,
                    permissions=new_screen.permissions,
                    linked_requirement_ids=[req.id],
                )
            )
            audit.auto_fixes_applied.append(f"{req.id}: pantalla auto-generada.")

        linked_after = self._requirements_linked_to_screens(screens, screen_catalog)
        for req in requirements:
            if req.id not in linked_after:
                audit.missing_screens.append(req.id)

    def _ensure_permission_coverage(
        self,
        project: Project,
        screens: list[ScreenSpec],
        audit: CompletenessAudit,
    ) -> None:
        expected_permissions = set(project.domain_analysis.permissions if project.domain_analysis else [])
        existing_permissions = {perm for screen in screens for perm in screen.permissions}
        missing = sorted(expected_permissions - existing_permissions)
        if missing and screens:
            screens[0].permissions.extend(missing)
            audit.auto_fixes_applied.append(
                f"Permisos faltantes agregados a {screens[0].name}: {', '.join(missing)}"
            )
        elif missing:
            audit.missing_permissions.extend(missing)

    def _ensure_report_coverage(
        self,
        project: Project,
        screens: list[ScreenSpec],
        audit: CompletenessAudit,
    ) -> None:
        expected_reports = project.domain_analysis.reports if project.domain_analysis else []
        if not expected_reports:
            return
        content = " ".join([screen.name + " " + screen.purpose for screen in screens]).lower()
        for report in expected_reports:
            if report.lower() not in content and "reporte" not in content and "report" not in content:
                if screens:
                    route = f"/reportes/{report.lower().replace(' ', '-')}"
                    screens.append(
                        ScreenSpec(
                            name=f"Reporte - {report}",
                            module="Reportes",
                            route=route,
                            purpose=f"Consultar y exportar {report}.",
                            screen_type="report",
                            roles=["Administrador", "Revisor", "Auditor"],
                            permissions=["read:reportes", "export:reportes"],
                            components=["Filtros", "Tabla", "Grafica", "Exportador"],
                            forms=[],
                            tables=["Resultados"],
                            actions=["Filtrar", "Exportar", "Drill-down"],
                            validations=["Rango de fechas valido"],
                            prompt_notes="auto_generated_for_report_coverage",
                            accepted=True,
                        )
                    )
                    audit.auto_fixes_applied.append(f"Pantalla de reporte auto-generada: {report}")
                else:
                    audit.missing_reports.append(report)

    def _ensure_process_coverage(
        self,
        project: Project,
        requirements: list[Requirement],
        audit: CompletenessAudit,
    ) -> None:
        processes = project.domain_analysis.processes if project.domain_analysis else []
        covered = {step.lower() for req in requirements for step in req.workflows}
        for process in processes:
            token = process.lower()
            if not any(token in text for text in covered):
                if requirements:
                    requirements[0].workflows.append(process)
                    audit.auto_fixes_applied.append(
                        f"Proceso faltante agregado al workflow de {requirements[0].id}: {process}"
                    )
                else:
                    audit.incomplete_processes.append(process)

    def _ensure_architecture_entities(
        self,
        architecture: ArchitectureSpec,
        requirements: list[Requirement],
        audit: CompletenessAudit,
    ) -> None:
        existing = {
            (item.get("name") if isinstance(item, dict) else str(item))
            for item in architecture.entities
        }
        for req in requirements:
            for entity in req.entities:
                if entity not in existing:
                    architecture.entities.append({"name": entity, "type": "Aggregate"})
                    existing.add(entity)
                    audit.auto_fixes_applied.append(f"Entidad faltante agregada a arquitectura: {entity}")

        if not architecture.entities:
            audit.missing_entities.append("No hay entidades en arquitectura.")

    def _ensure_architecture_endpoints(
        self,
        architecture: ArchitectureSpec,
        requirements: list[Requirement],
        audit: CompletenessAudit,
    ) -> None:
        existing_req_ids = {
            endpoint.get("requirement_id")
            for endpoint in architecture.endpoints
            if isinstance(endpoint, dict)
        }
        for req in requirements:
            if req.id in existing_req_ids:
                continue
            architecture.endpoints.append(
                {
                    "id": f"API-AUTO-{req.id}",
                    "method": "POST",
                    "path": f"/api/{req.module.lower().replace(' ', '-')}/{req.id.lower()}",
                    "requirement_id": req.id,
                    "entity": req.entities[0] if req.entities else "Registro",
                }
            )
            audit.auto_fixes_applied.append(f"API faltante auto-generada para {req.id}.")

    def _build_traceability(
        self,
        requirements: list[Requirement],
        screens: list[ScreenSpec],
        architecture: ArchitectureSpec,
    ) -> list[TraceabilityLink]:
        links: list[TraceabilityLink] = []
        endpoint_by_req: dict[str, dict] = {}
        for endpoint in architecture.endpoints:
            if not isinstance(endpoint, dict):
                continue
            req_id = str(endpoint.get("requirement_id") or "")
            if req_id:
                endpoint_by_req[req_id] = endpoint

        for req in requirements:
            screen = self._find_screen_for_requirement(req, screens)
            endpoint = endpoint_by_req.get(req.id)
            if not screen or not endpoint:
                continue
            links.append(
                TraceabilityLink(
                    requirement_id=req.id,
                    screen_id=screen.id,
                    api_id=str(endpoint.get("id") or f"API-{req.id}"),
                    entity=str(endpoint.get("entity") or (req.entities[0] if req.entities else "Registro")),
                )
            )
        return links

    def _find_screen_for_requirement(self, req: Requirement, screens: list[ScreenSpec]) -> ScreenSpec | None:
        req_id_token = req.id.lower()
        for screen in screens:
            hint = (screen.prompt_notes or "").lower()
            if req_id_token in hint:
                return screen
        for screen in screens:
            if screen.module == req.module:
                return screen
        return None

    def _requirements_linked_to_screens(
        self,
        screens: list[ScreenSpec],
        screen_catalog: list[ScreenCatalogItem],
    ) -> set[str]:
        linked: set[str] = set()
        for item in screen_catalog:
            linked.update(item.linked_requirement_ids)
        for screen in screens:
            note = screen.prompt_notes or ""
            if "linked_requirements=" in note:
                payload = note.split("linked_requirements=", 1)[1]
                linked.update([token.strip() for token in payload.split(",") if token.strip()])
        return linked
