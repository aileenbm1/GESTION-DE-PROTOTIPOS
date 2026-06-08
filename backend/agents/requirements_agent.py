from __future__ import annotations

from models.schemas import (
    BusinessContextDocument,
    DomainAnalysis,
    FunctionalRequirement,
    Requirement,
    RequirementEngineeringDocument,
)


class RequirementsAgent:
    """
    Compatibility adapter:
    - Keeps returning legacy Requirement[] used by code generator.
    - Uses Requirement Engineering outputs (not raw transcript) as the source of truth.
    """

    def run(
        self,
        transcript: str,
        *,
        business_context: BusinessContextDocument | None = None,
        domain_analysis: DomainAnalysis | None = None,
        requirement_engineering: RequirementEngineeringDocument | None = None,
    ) -> list[Requirement]:
        if requirement_engineering and requirement_engineering.functional_requirements:
            return [
                self._from_functional_requirement(item, requirement_engineering)
                for item in requirement_engineering.functional_requirements
            ]
 
        modules = domain_analysis.modules if domain_analysis and domain_analysis.modules else ["General"]
        roles = domain_analysis.roles if domain_analysis and domain_analysis.roles else ["Operador"]
        entities = domain_analysis.entities if domain_analysis and domain_analysis.entities else ["Registro"]
        processes = (
            domain_analysis.processes
            if domain_analysis and domain_analysis.processes
            else ["Captura", "Validacion", "Aprobacion"]
        )

        fallback_functional = [
            FunctionalRequirement(
                id="RF-001",
                title="Gestionar informacion operativa",
                description=(
                    "Permitir registrar, consultar y actualizar informacion operacional con "
                    "validaciones de negocio y trazabilidad."
                ),
                priority="high",
                actor=roles[0],
                module=modules[0],
                main_flow=["Registrar datos", "Validar", "Guardar", "Confirmar"],
                exceptions=["Campos obligatorios faltantes", "Formato invalido"],
                entities=entities[:2],
                processes=processes[:2],
            ),
            FunctionalRequirement(
                id="RF-002",
                title="Aprobar procesos criticos",
                description="Soportar flujo de aprobacion/rechazo con evidencia y auditoria.",
                priority="high",
                actor=roles[min(1, len(roles) - 1)],
                module="Aprobaciones" if "Aprobaciones" in modules else modules[0],
                main_flow=["Consultar pendientes", "Revisar", "Aprobar/Rechazar", "Notificar"],
                exceptions=["Solicitud incompleta", "Estado no valido"],
                entities=entities[:3],
                processes=["Aprobacion"],
            ),
        ]
        return [self._from_functional_requirement(item) for item in fallback_functional]

    def _from_functional_requirement(
        self,
        item: FunctionalRequirement,
        requirement_engineering: "RequirementEngineeringDocument | None" = None,
    ) -> Requirement:
        # Enrich business_rules from requirement engineering document
        business_rules: list[str] = []
        acceptance_criteria: list[str] = []

        if requirement_engineering:
            business_rules = [
                br.description
                for br in (requirement_engineering.business_rules or [])
            ][:4]

            # Match acceptance criteria for this requirement
            for ac in (requirement_engineering.acceptance_criteria or []):
                if ac.requirement_id == item.id:
                    acceptance_criteria.append(
                        f"Dado {ac.given}, cuando {ac.when}, entonces {ac.then}."
                    )

        if not business_rules:
            business_rules = [
                "Aplicar control de permisos por rol antes de cualquier operacion.",
                "Registrar trazabilidad completa de operaciones criticas en bitacora.",
                "Validar integridad de datos antes de persistir cambios.",
                "No permitir operaciones sobre registros en estado cerrado o cancelado.",
            ]

        if not acceptance_criteria:
            acceptance_criteria = [
                f"Dado un usuario con el rol adecuado y sesion activa, "
                f"cuando ejecuta '{item.title}' con datos validos, "
                f"entonces el sistema completa el flujo correctamente y muestra confirmacion.",
                f"Dado un usuario sin permisos suficientes, "
                f"cuando intenta ejecutar '{item.title}', "
                f"entonces el sistema muestra error de autorizacion y registra el intento.",
            ]

        return Requirement(
            id=item.id,
            title=item.title,
            description=item.description,
            module=item.module,
            priority=item.priority,
            actors=[item.actor] if item.actor else ["Operador"],
            entities=item.entities or ["Registro"],
            validations=item.exceptions or [
                "Campos obligatorios no pueden estar vacios.",
                "Formato de datos debe ser valido segun el tipo de campo.",
                "No se permiten duplicados en identificadores unicos.",
            ],
            business_rules=business_rules,
            acceptance_criteria=acceptance_criteria,
            workflows=item.main_flow or [
                "Abrir formulario o vista",
                "Cargar datos existentes si aplica",
                "Capturar o modificar informacion",
                "Validar datos en cliente",
                "Enviar al servidor",
                "Confirmar resultado al usuario",
            ],
            dependencies=item.processes or [],
            accepted=True,
        )
