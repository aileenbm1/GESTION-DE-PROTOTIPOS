from __future__ import annotations

import json

from models.schemas import BusinessContextDocument, DomainAnalysis
from services.azure_openai_service import AzureOpenAIService


class DomainAnalysisAgent:
    def __init__(self, ai: AzureOpenAIService | None = None) -> None:
        self.ai = ai or AzureOpenAIService()

    def run(self, business_context: BusinessContextDocument) -> DomainAnalysis:
        fallback = {
            "modules": ["Dashboard", "Operacion", "Aprobaciones", "Auditoria", "Reportes"],
            "entities": ["Registro", "Proceso", "Evidencia", "Bitacora", "Usuario", "Rol"],
            "roles": business_context.actors_involved or ["Administrador", "Operador", "Revisor", "Auditor"],
            "permissions": [
                "read:dashboard",
                "manage:operacion",
                "approve:workflow",
                "read:auditoria",
                "export:reportes",
            ],
            "processes": business_context.processes_mentioned or [
                "Captura",
                "Validacion",
                "Aprobacion",
                "Seguimiento",
            ],
            "flows": [
                "Registrar solicitud -> Validar -> Aprobar/Rechazar -> Auditar",
                "Consultar dashboard -> Filtrar -> Exportar reporte",
            ],
            "integrations": ["Identity Provider", "SharePoint/Repositorio documental"],
            "reports": ["Reporte operativo diario", "Reporte de auditoria", "KPI por modulo"],
            "catalogs": ["Catalogo de estados", "Catalogo de tipos de registro", "Catalogo de roles"],
            "approvals": ["Aprobacion operativa", "Aprobacion de excepcion"],
            "validations": [
                "Campos obligatorios",
                "Formato de identificadores",
                "Reglas de segregacion de funciones",
            ],
            "summary": "Analisis de dominio con foco en control operativo, seguridad por roles y trazabilidad completa.",
        }

        system_prompt = """
Eres un Senior Business Analyst + Domain Expert con experiencia en sistemas enterprise.
Tu tarea es hacer un Domain Analysis COMPLETO y ESPECIFICO basado en el Business Context.

INSTRUCCIONES:
1. Los modulos deben ser los modulos FUNCIONALES reales del sistema (no genericos como "General").
   Cada modulo debe corresponder a una funcion de negocio concreta.
2. Las entidades deben ser los OBJETOS DE DATOS reales del dominio (sustantivos del negocio).
3. Los roles deben ser los perfiles de usuario REALES identificados.
4. Los permissions deben seguir el patron accion:recurso (ej: "read:reportes", "approve:solicitud").
5. Los processes deben ser los flujos de negocio ESPECIFICOS con sus pasos.
6. Los flows deben describir el flujo completo de una operacion tipica (inicio → fin).
7. Los reports deben ser los reportes y dashboards ESPECIFICOS que necesita el negocio.
8. Los catalogs deben ser los catalogos de datos maestros necesarios.
9. Los approvals deben ser los tipos de aprobacion con su jerarquia.
10. Las validations deben ser las reglas de negocio especificas de validacion.

MINIMOS REQUERIDOS:
- Al menos 4 modulos especificos
- Al menos 6 entidades de dominio
- Al menos 3 roles diferenciados
- Al menos 8 permisos especificos
- Al menos 4 procesos de negocio con pasos
- Al menos 2 reportes especificos

FORMATO JSON valido:
{
  "modules": ["Modulo1", "Modulo2", ...],
  "entities": ["Entidad1", "Entidad2", ...],
  "roles": ["Rol1", "Rol2", ...],
  "permissions": ["accion:recurso1", "accion:recurso2", ...],
  "processes": ["Proceso con pasos 1", "Proceso con pasos 2", ...],
  "flows": ["Flujo completo 1", "Flujo completo 2", ...],
  "integrations": ["Sistema externo 1", ...],
  "reports": ["Reporte especifico 1", "Reporte especifico 2", ...],
  "catalogs": ["Catalogo 1", "Catalogo 2", ...],
  "approvals": ["Tipo de aprobacion 1", ...],
  "validations": ["Regla de validacion especifica 1", ...],
  "summary": "resumen del dominio"
}

NO generes codigo ni arquitectura. Responde SOLO el JSON.
"""
        user_prompt = f"BUSINESS_CONTEXT:\n{json.dumps(business_context.model_dump(mode='json'), ensure_ascii=False, indent=2)}"
        data = self.ai.chat_json(system_prompt, user_prompt, fallback)

        # GPT-4o sometimes returns objects instead of strings — flatten them
        def _flatten(items: list) -> list[str]:
            result: list[str] = []
            for item in items:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    # Extract name/title/description or join all string values
                    val = (item.get("name") or item.get("title") or item.get("description")
                           or " — ".join(str(v) for v in item.values() if isinstance(v, str)))
                    if val:
                        result.append(str(val))
            return result

        for field in ("processes", "flows", "approvals", "validations", "integrations",
                      "reports", "catalogs", "modules", "entities", "roles", "permissions"):
            if field in data and isinstance(data[field], list):
                data[field] = _flatten(data[field])

        return DomainAnalysis.model_validate(data)
