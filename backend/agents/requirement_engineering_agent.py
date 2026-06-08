from __future__ import annotations

import json

from models.schemas import (
    AcceptanceCriterionItem,
    BusinessRuleItem,
    DomainAnalysis,
    FunctionalRequirement,
    NonFunctionalRequirement,
    RequirementEngineeringDocument,
    UserStoryItem,
    UseCaseItem,
)
from services.azure_openai_service import AzureOpenAIService


class RequirementEngineeringAgent:
    def __init__(self, ai: AzureOpenAIService | None = None) -> None:
        self.ai = ai or AzureOpenAIService()

    def run(self, domain_analysis: DomainAnalysis) -> RequirementEngineeringDocument:
        modules = domain_analysis.modules or ["General"]
        entities = domain_analysis.entities or ["Registro"]
        roles = domain_analysis.roles or ["Operador"]

        fallback = {
            "functional_requirements": [
                {
                    "id": "RF-001",
                    "title": "Registrar informacion operativa",
                    "description": "Permitir registrar datos del proceso con validaciones de negocio.",
                    "priority": "high",
                    "actor": roles[0],
                    "module": modules[0],
                    "main_flow": ["Abrir formulario", "Completar campos", "Guardar", "Confirmar resultado"],
                    "exceptions": ["Datos invalidos", "Permiso insuficiente"],
                    "entities": entities[:2],
                    "processes": domain_analysis.processes[:2] if domain_analysis.processes else ["Captura"],
                },
                {
                    "id": "RF-002",
                    "title": "Aprobar o rechazar solicitudes",
                    "description": "Gestionar el flujo de aprobacion con evidencia y trazabilidad.",
                    "priority": "high",
                    "actor": roles[min(1, len(roles) - 1)],
                    "module": "Aprobaciones" if "Aprobaciones" in modules else modules[0],
                    "main_flow": ["Listar pendientes", "Revisar detalle", "Aprobar/Rechazar", "Notificar"],
                    "exceptions": ["Solicitud incompleta", "Conflicto de estado"],
                    "entities": entities[:3],
                    "processes": ["Aprobacion"],
                },
            ],
            "non_functional_requirements": [
                {
                    "id": "RNF-001",
                    "category": "Seguridad",
                    "description": "Aplicar autenticacion y autorizacion basada en roles (RBAC).",
                    "measurable_target": "100% de endpoints protegidos segun perfil.",
                },
                {
                    "id": "RNF-002",
                    "category": "Observabilidad",
                    "description": "Registrar auditoria de operaciones criticas.",
                    "measurable_target": "Traza completa por cada cambio de estado.",
                },
            ],
            "business_rules": [
                {"id": "RN-001", "description": "No permitir aprobacion de registros incompletos."},
                {"id": "RN-002", "description": "Toda accion critica debe quedar en bitacora."},
            ],
            "use_cases": [
                {
                    "id": "CU-001",
                    "name": "Registrar solicitud",
                    "primary_actor": roles[0],
                    "main_flow": ["Captura", "Validacion", "Persistencia"],
                    "alternative_flows": ["Error de validacion", "Cancelacion"],
                },
                {
                    "id": "CU-002",
                    "name": "Aprobar solicitud",
                    "primary_actor": roles[min(1, len(roles) - 1)],
                    "main_flow": ["Revisar", "Decidir", "Notificar"],
                    "alternative_flows": ["Rechazar", "Solicitar ajustes"],
                },
            ],
            "user_stories": [
                {
                    "id": "US-001",
                    "as_a": roles[0],
                    "i_want": "registrar informacion de forma guiada",
                    "so_that": "el proceso sea confiable y trazable",
                },
                {
                    "id": "US-002",
                    "as_a": roles[min(1, len(roles) - 1)],
                    "i_want": "aprobar solicitudes con evidencia",
                    "so_that": "se cumpla la gobernanza del proceso",
                },
            ],
            "acceptance_criteria": [
                {
                    "id": "AC-001",
                    "requirement_id": "RF-001",
                    "given": "un usuario autorizado con formulario abierto",
                    "when": "captura datos validos y guarda",
                    "then": "el sistema persiste el registro y muestra confirmacion",
                },
                {
                    "id": "AC-002",
                    "requirement_id": "RF-002",
                    "given": "una solicitud en estado pendiente",
                    "when": "el aprobador decide y confirma",
                    "then": "el estado cambia y queda evidencia en auditoria",
                },
            ],
        }

        system_prompt = """
Eres un Principal Business Analyst + Product Owner Senior especializado en sistemas enterprise.
Tu tarea es generar un Requirement Engineering Document COMPLETO, ESPECIFICO y DETALLADO.

REGLAS CRITICAS:
1. Genera MINIMO 5 requerimientos funcionales (RF), maximo 15.
2. Cada RF debe ser ESPECIFICO al dominio — no generico. El titulo debe describir la accion concreta.
3. Cada RF debe tener:
   - description: descripcion funcional completa de 2-3 oraciones con el QUE hace y el PARA QUE
   - main_flow: al menos 5 pasos detallados del flujo principal
   - exceptions: al menos 3 excepciones o errores posibles
   - entities: las entidades de datos que manipula
   - processes: los procesos de negocio que involucra
4. Los criterios de aceptacion deben ser Gherkin ESPECIFICOS:
   - given: estado inicial concreto
   - when: accion concreta del usuario
   - then: resultado observable y verificable
5. Las reglas de negocio deben ser ESPECIFICAS y medibles, no genericas.
6. Los casos de uso deben tener flujos alternativos detallados.
7. Las historias de usuario deben incluir criterios de valor medibles.

DISTRIBUCION DE REQUERIMIENTOS:
- Distribuye los RF entre todos los modulos del dominio.
- Al menos 1 RF por modulo principal.
- Incluye RFs para: CRUD de entidades principales, flujos de aprobacion, reportes, administracion.

IDs: RF-001, RF-002... | RNF-001... | RN-001... | CU-001... | US-001... | AC-001...

FORMATO JSON — EXACTAMENTE estas claves:
{
  "functional_requirements": [
    {
      "id": "RF-001",
      "title": "titulo especifico de la funcionalidad",
      "description": "descripcion completa y especifica de 2-3 oraciones",
      "priority": "high|medium|low",
      "actor": "rol especifico",
      "module": "modulo al que pertenece",
      "main_flow": ["paso 1 detallado", "paso 2 detallado", "paso 3", "paso 4", "paso 5"],
      "exceptions": ["excepcion especifica 1", "excepcion 2", "excepcion 3"],
      "entities": ["entidad1", "entidad2"],
      "processes": ["proceso1", "proceso2"]
    }
  ],
  "non_functional_requirements": [
    {
      "id": "RNF-001",
      "category": "Seguridad|Rendimiento|Usabilidad|Disponibilidad|Escalabilidad",
      "description": "descripcion especifica del RNF",
      "measurable_target": "metrica concreta y medible"
    }
  ],
  "business_rules": [
    {"id": "RN-001", "description": "regla de negocio especifica y medible"}
  ],
  "use_cases": [
    {
      "id": "CU-001",
      "name": "nombre del caso de uso",
      "primary_actor": "actor principal",
      "main_flow": ["paso 1", "paso 2", "paso 3"],
      "alternative_flows": ["flujo alternativo 1", "flujo alternativo 2"]
    }
  ],
  "user_stories": [
    {
      "id": "US-001",
      "as_a": "rol especifico",
      "i_want": "accion concreta que desea realizar",
      "so_that": "valor de negocio especifico que obtiene"
    }
  ],
  "acceptance_criteria": [
    {
      "id": "AC-001",
      "requirement_id": "RF-001",
      "given": "estado inicial especifico y concreto",
      "when": "accion especifica del usuario",
      "then": "resultado observable, verificable y especifico"
    }
  ]
}

NO generes codigo ni arquitectura. Responde SOLO el JSON valido.
"""
        user_prompt = (
            "DOMAIN_ANALYSIS (usa TODOS estos datos para generar requerimientos especificos):\n"
            + json.dumps(domain_analysis.model_dump(mode="json"), ensure_ascii=False, indent=2)
        )
        data = self.ai.chat_json(system_prompt, user_prompt, fallback)

        return RequirementEngineeringDocument(
            functional_requirements=[
                FunctionalRequirement.model_validate(item)
                for item in data.get("functional_requirements", [])
            ],
            non_functional_requirements=[
                NonFunctionalRequirement.model_validate(item)
                for item in data.get("non_functional_requirements", [])
            ],
            business_rules=[
                BusinessRuleItem.model_validate(item)
                for item in data.get("business_rules", [])
            ],
            use_cases=[UseCaseItem.model_validate(item) for item in data.get("use_cases", [])],
            user_stories=[
                UserStoryItem.model_validate(item) for item in data.get("user_stories", [])
            ],
            acceptance_criteria=[
                AcceptanceCriterionItem.model_validate(item)
                for item in data.get("acceptance_criteria", [])
            ],
        )
