from __future__ import annotations

from pathlib import Path

from services.azure_openai_service import AzureOpenAIService


class AutoFixAgent:

    def __init__(
        self,
        ai: AzureOpenAIService | None = None,
    ) -> None:
        self.ai = ai or AzureOpenAIService()

    def fix(
        self,
        code: str,
        error: str,
        file_path: str = "",
        project_context: str = "",
    ) -> str:

        extension = Path(file_path).suffix.lower()

        system_prompt = """
Eres un Principal Software Engineer.

Especialista en:

- Angular 20+
- TypeScript
- PrimeNG
- TailwindCSS
- RxJS
- Signals
- .NET 10
- ASP.NET Minimal APIs
- Clean Architecture

Objetivo:

Corregir errores sin romper funcionalidad.

Mantener compatibilidad completa.

No eliminar características existentes.

Responder exclusivamente con código.
"""

        user_prompt = f"""
ARCHIVO

{file_path}

TIPO

{extension}

ERROR

{error}

CONTEXTO DEL PROYECTO

{project_context}

REGLAS

- Mantener funcionalidad
- Mantener arquitectura
- Corregir imports
- Corregir tipado
- Corregir Angular standalone
- Corregir Signals
- Corregir RxJS
- Corregir dependencias
- Corregir inyección de dependencias
- Corregir compilación
- Corregir .NET si aplica
- Corregir warnings críticos

DEVUELVE EXCLUSIVAMENTE
EL ARCHIVO COMPLETO CORREGIDO

CODIGO

{code}
"""

        return self.ai.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            fallback=code,
        )