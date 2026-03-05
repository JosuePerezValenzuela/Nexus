# AGENTS.md - Guia de Desarrollo del Repositorio Nexus

## 1) Proposito del repositorio
Este repo implementa un sistema clinico multiagente con:
- Backend API en FastAPI.
- Orquestacion de agentes con LangGraph.
- RAG con PostgreSQL + pgvector.
- Frontend demo en Streamlit.

Objetivo principal: respuestas clinicas asistidas por datos de pacientes y literatura medica, con trazabilidad y bajo riesgo de alucinacion.

## 2) Stack y herramientas oficiales
- Python 3.12.
- Gestor de dependencias/entorno: `uv`.
- Backend: FastAPI, SQLModel, asyncpg/psycopg, slowapi.
- IA: LangChain, LangGraph, endpoint compatible con OpenAI, embeddings HF.
- DB: PostgreSQL + extension `vector`.
- Frontend: Streamlit.
- Lint/format: Ruff.
- Type checking en editor: strict.

Regla: no introducir nuevas herramientas base (ORM, framework web, task runner) sin RFC corto en PR.

## 3) Estructura y limites arquitectonicos
- `src/app/api/`: capa HTTP (request/response, status codes, validacion de entrada).
- `src/app/services/`: logica de negocio (sin detalles HTTP).
- `src/app/graph/`: prompts, nodos, tools y workflow de agentes.
- `src/app/models/`: modelos SQLModel (persistencia).
- `src/app/schemas/`: DTOs/contratos publicos.
- `src/app/core/`: configuracion, sesion DB, concerns transversales.
- `src/app/db/`: seeding/bootstrapping de datos.
- `frontend/`: cliente Streamlit y consumo API.

Regla de oro: evitar mezclar responsabilidades entre capas.

## 4) Comandos de trabajo
- Instalar dependencias: `uv sync`
- Levantar backend local: `uv run dev`
- Levantar frontend: `uv run streamlit run frontend/app.py`
- Flujo con contenedores: `docker compose up --build` y luego ejecutar comandos dentro del servicio backend.

Antes de abrir PR, correr al menos:
- `uv run ruff check .`
- `uv run ruff format --check .`

Si agregas tests:
- `uv run pytest`

## 5) Convenciones de codigo
### Python
- Seguir Ruff (`E,F,I,B,UP`) y line-length 88.
- Usar type hints en APIs publicas de modulos.
- Evitar funciones con multiples responsabilidades.
- Evitar `except Exception` sin contexto y sin logging util.

### FastAPI
- Endpoints livianos: parseo, validacion, delegacion a services.
- Errores con `HTTPException` consistente y mensajes accionables.
- No meter logica de negocio en routers.

### Services
- Manejar transacciones de forma explicita.
- Mantener metodos pequenos, testeables y deterministas cuando aplique.
- No acoplar services a detalles de UI/frontend.

### Graph/Agents
- Cambios en prompts o reglas de ruteo requieren justificar impacto.
- Mantener guardrails anti-alucinacion.
- Evitar agregar tools sin evaluar seguridad y costo.

## 6) Datos, seguridad y compliance
- Nunca hardcodear secretos, tokens o credenciales.
- Nunca commitear `.env`, dumps de BD ni archivos con datos sensibles.
- Usar datos sinteticos para desarrollo y demos.
- No loggear informacion sensible del paciente en texto plano.
- Validar tamano/tipo de archivos subidos antes de procesarlos.

## 7) Politica de cambios
- Cambios pequenos y enfocados por PR.
- Commits en formato Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`).
- Si se modifica contrato API, actualizar doc y cliente en el mismo PR.
- Si se modifica modelo de datos, documentar estrategia de migracion/backfill.

## 8) Checklist minimo antes de merge
- [ ] Ruff check/format en verde.
- [ ] Sin secretos en diff.
- [ ] Logs y manejo de errores razonables.
- [ ] Contratos API consistentes (schemas + endpoints).
- [ ] Si hubo cambios en graph/prompts, validar al menos 3 escenarios:
  1) pregunta general,
  2) consulta de paciente,
  3) consulta de paciente + guias.

## 9) Riesgos actuales del repo (a vigilar)
- Falta de suite de tests automatizados.
- Ausencia de pipeline CI.
- Inicializacion/seeding acoplada al startup.
- Inconsistencias de entorno dev vs runtime productivo.
- Acumulacion de archivos temporales/cache en el arbol de trabajo.

## 10) Criterio de done
Un cambio se considera terminado cuando:
- respeta limites de capa,
- pasa validaciones de calidad,
- no rompe contratos,
- y deja trazabilidad suficiente para mantenimiento futuro.

## 11) AGENTS especificos por carpeta
Este archivo define reglas globales. Si existe un `AGENTS.md` mas especifico para una carpeta, ese archivo tiene prioridad dentro de su alcance.

- Backend (`src/app/`): `src/app/AGENTS.md`
- Frontend (`frontend/`): `frontend/AGENTS.md`
