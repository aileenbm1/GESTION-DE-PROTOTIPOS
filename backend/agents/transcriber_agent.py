from __future__ import annotations

import logging
from pathlib import Path

from services.azure_openai_service import AzureOpenAIService

logger = logging.getLogger(__name__)


def _transcribe_whisper_local(file_path: str) -> str:
    """
    Fallback: usa openai-whisper (modelo local) si Azure no está disponible.
    Solo se activa si Azure falla por error real (no por falta de configuración).
    """
    try:
        import whisper  # type: ignore
        logger.info("transcriber.whisper_local.start path=%s", file_path)
        model = whisper.load_model("base")
        result = model.transcribe(file_path, language="es", verbose=False)
        text: str = result.get("text", "") or ""
        logger.info("transcriber.whisper_local.done chars=%s", len(text))
        return text.strip()
    except Exception as exc:
        logger.error("transcriber.whisper_local.failed error=%s", repr(exc))
        return ""


class TranscriberAgent:
    def __init__(self, ai: AzureOpenAIService | None = None) -> None:
        self.ai = ai or AzureOpenAIService()

    def run(self, file_path: str) -> str:
        """
        Pipeline de transcripción:
        1. Azure OpenAI (gpt-4o-transcribe) — IA en la nube, principal.
        2. Whisper local — solo si Azure falla por error (red, cuota, etc.).
        3. Limpieza y estructuración con GPT-4o.
        """
        transcript = ""
        used_azure = False

        # ── 1. Intentar con Azure OpenAI ─────────────────────────────────────
        has_azure_transcription = (
            not self.ai.settings.mock_ai
            and bool(self.ai.settings.azure_openai_transcription_deployment)
            and bool(self.ai.settings.azure_openai_endpoint)
        )

        if has_azure_transcription:
            try:
                logger.info("transcriber.azure.start deployment=%s",
                            self.ai.settings.azure_openai_transcription_deployment)
                transcript = self.ai.transcribe(file_path)
                used_azure = True
                logger.info("transcriber.azure.done chars=%s", len(transcript))
            except Exception as exc:
                logger.warning("transcriber.azure.failed error=%s — fallback a Whisper local", repr(exc))
                transcript = ""
        else:
            logger.info("transcriber.azure.skipped — deployment no configurado")

        # ── 2. Fallback a Whisper local ────────────────────────────────────────
        is_simulation = transcript.startswith("Simulación:") or not transcript.strip()
        if is_simulation:
            if has_azure_transcription:
                logger.warning("transcriber.azure_returned_empty — usando Whisper local como respaldo")
            else:
                logger.info("transcriber.using_whisper_local — no hay deployment Azure configurado")
            transcript = _transcribe_whisper_local(file_path)

        if not transcript.strip():
            logger.error("transcriber.all_methods_failed")
            return "No fue posible transcribir el audio. Verifica el archivo y la configuración de Azure OpenAI."

        logger.info("transcriber.raw_done chars=%s source=%s",
                    len(transcript), "azure" if used_azure else "whisper_local")

        # ── 3. Limpiar y estructurar con GPT-4o ──────────────────────────────
        if not self.ai.enabled:
            return transcript

        cleaned = self.ai.chat(
            """Eres un experto en análisis de reuniones de negocios.
Recibirás la transcripción de un video o audio de una reunión.

Tu tarea:
1. Corrige errores de transcripción automática (palabras mal reconocidas).
2. Separa el texto en párrafos claros por tema o idea.
3. Elimina muletillas, repeticiones y frases sin contenido relevante.
4. Conserva TODA la información relevante: funcionalidades pedidas, módulos,
   procesos, actores, restricciones técnicas, nombres de sistemas, fechas.
5. Si se mencionan componentes específicos de UI (calendarios, tablas, formularios,
   buscadores, filtros), consérvalo literalmente.
6. NO resumas ni omitas requerimientos. El texto limpio debe ser fiel a lo que se dijo.

Devuelve solo el texto limpio estructurado, sin títulos extra ni explicaciones.
""",
            transcript,
            fallback=transcript,
        )

        result = cleaned or transcript
        logger.info("transcriber.cleaned_done chars=%s", len(result))
        return result
