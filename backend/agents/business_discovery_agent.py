from __future__ import annotations

from models.schemas import BusinessContextDocument
from services.azure_openai_service import AzureOpenAIService


class BusinessDiscoveryAgent:
    def __init__(self, ai: AzureOpenAIService | None = None) -> None:
        self.ai = ai or AzureOpenAIService()

    def run(self, transcript: str) -> BusinessContextDocument:
        fallback = {
            "domain": "Operacion empresarial asistida por IA",
            "business_objectives": [
                "Estandarizar la operacion y la toma de decisiones.",
                "Reducir tiempos de respuesta en procesos criticos.",
                "Garantizar trazabilidad y auditoria completa.",
            ],
            "processes_mentioned": [
                "Captura de informacion",
                "Validacion y aprobacion",
                "Consulta y reporte",
            ],
            "actors_involved": ["Administrador", "Operador", "Revisor", "Auditor"],
            "constraints": [
                "Cumplimiento normativo y politicas internas",
                "Control estricto por roles y permisos",
            ],
            "current_problems": [
                "Procesos manuales con poca trazabilidad",
                "Falta de estandarizacion en validaciones",
            ],
            "assumptions": [
                "El sistema operara en entorno corporativo.",
                "La seguridad y auditoria son no negociables.",
            ],
            "summary": "Contexto empresarial con enfasis en control operativo, trazabilidad y eficiencia.",
        }

        system_prompt = """
Eres un Principal Business Analyst Senior con 15 años de experiencia en proyectos enterprise.
Tu tarea es extraer TODA la informacion de negocio que aparezca en la transcripcion, sin inventar nada que no este mencionado.

INSTRUCCIONES ESTRICTAS:
1. Lee la transcripcion completa antes de responder.
2. Extrae LITERALMENTE los problemas, necesidades y procesos que se mencionan.
3. Identifica actores, roles y departamentos mencionados explicitamente.
4. Detecta restricciones tecnicas, normativas o de negocio mencionadas.
5. Identifica el dominio exacto del sistema (no generico, especifico al negocio).
6. Los business_objectives deben ser MEDIBLES y derivados directamente de lo que se pide.
7. Los current_problems deben ser los problemas REALES mencionados, no genericos.
8. El summary debe ser una descripcion funcional concreta de 2-3 oraciones.

FORMATO DE RESPUESTA — JSON valido con estas claves exactas:
{
  "domain": "descripcion especifica del dominio",
  "business_objectives": ["objetivo medible 1", "objetivo medible 2", ...],
  "processes_mentioned": ["proceso especifico 1", "proceso especifico 2", ...],
  "actors_involved": ["rol/actor 1", "rol/actor 2", ...],
  "constraints": ["restriccion 1", "restriccion 2", ...],
  "current_problems": ["problema real mencionado 1", "problema real mencionado 2", ...],
  "assumptions": ["supuesto validado 1", ...],
  "summary": "resumen ejecutivo concreto del sistema a construir"
}

NO generes arquitectura, NO menciones tecnologias a menos que se digan en la transcripcion.
Responde SOLO el JSON, sin texto adicional.
"""
        user_prompt = f"TRANSCRIPCION COMPLETA:\n{transcript}"
        data = self.ai.chat_json(system_prompt, user_prompt, fallback)
        return BusinessContextDocument.model_validate(data)
