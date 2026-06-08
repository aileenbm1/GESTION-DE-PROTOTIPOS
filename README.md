# Plataforma IA Generadora de Prototipos Fullstack

MVP funcional para crear prototipos empresariales a partir de audio o video de reuniones. La plataforma usa FastAPI, Azure OpenAI, LangGraph, React, Vite, TailwindCSS, Zustand y Axios. No usa base de datos, contenedores ni infraestructura enterprise: todo se guarda en JSON y carpetas locales.

## Arquitectura

```text
backend/
  agents/          Agentes de transcripcion, requerimientos, UI/UX, arquitectura, codigo, revision y ZIP
  api/             Endpoints FastAPI
  models/          Contratos Pydantic
  orchestrator/    Flujo LangGraph y coordinacion de pasos
  outputs/         Proyectos generados y ZIP finales
  prompts/         Prompts base
  services/        Azure OpenAI y generacion de archivos
  storage/         JSON de proyectos y archivos subidos
  websocket/       Progreso por WebSocket
  main.py
frontend/
  src/
    components/    Layout, sidebar y encabezados
    pages/         Wizard: carga, requerimientos, pantallas, generacion, descarga
    services/      Cliente Axios
    store/         Zustand
```

## Flujo MVP

1. El usuario sube audio o video.
2. El backend crea un proyecto y guarda el archivo localmente.
3. `transcriber_agent` transcribe con Azure OpenAI o con modo mock.
4. `requirements_agent` extrae requerimientos editables.
5. El usuario aprueba, edita, elimina o agrega requerimientos.
6. `uiux_agent` genera pantallas propuestas.
7. El usuario aprueba o refina pantallas con prompt.
8. `architecture_agent` genera arquitectura tecnica.
9. `angular_generator_agent` y `dotnet_generator_agent` escriben codigo inicial.
10. `packager_agent` genera un ZIP descargable.

## Ejecutar backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python main.py
```

Ejecucion estable sin reload (recomendada para procesos largos):

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Comportamiento de arranque:
- Host por defecto: `AI_PROTO_BACKEND_HOST=127.0.0.1`
- Puerto por defecto: `AI_PROTO_BACKEND_PORT=8000`
- Reload por defecto: `AI_PROTO_BACKEND_RELOAD=false`
- No hay fallback silencioso de puerto.
- Solo hay fallback si defines explicitamente `AI_PROTO_BACKEND_FALLBACK_PORT`.

Para usar Azure OpenAI, edita `backend/.env`:

```text
MOCK_AI=false
AZURE_OPENAI_ENDPOINT=https://tu-recurso.openai.azure.com/
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_CHAT_DEPLOYMENT=...
AZURE_OPENAI_TRANSCRIPTION_DEPLOYMENT=...
```

Con `MOCK_AI=true`, el flujo funciona sin credenciales.

## Ejecutar frontend

```powershell
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`. El frontend espera el backend en `http://localhost:8000/api`. Puedes cambiarlo con `VITE_API_URL`.

## Endpoints principales

- `POST /api/projects`
- `POST /api/projects/{project_id}/upload`
- `POST /api/projects/{project_id}/run-initial`
- `PUT /api/projects/{project_id}/requirements`
- `POST /api/projects/{project_id}/screens/generate`
- `POST /api/projects/{project_id}/screens/refine`
- `PUT /api/projects/{project_id}/screens`
- `POST /api/projects/{project_id}/architecture/generate`
- `POST /api/projects/{project_id}/code/generate`
- `POST /api/projects/{project_id}/package`
- `GET /api/projects/{project_id}/download`

## Notas de alcance

Este MVP prioriza simplicidad y velocidad de iteracion. Los outputs Angular y .NET son una base inicial generada para validar flujo, estructura y descarga. Para produccion faltarian autenticacion, persistencia robusta, colas, observabilidad, validacion avanzada del codigo generado y aislamiento de ejecuciones.
