# AGENTS.md - Guia de Desarrollo para `src/app`

## 1) Alcance de este AGENTS
Este archivo aplica a todo lo que vive dentro de `src/app/`.
Define reglas para mantener separacion de capas, contratos estables y cambios seguros.

## 2) Regla de arquitectura (obligatoria)
- `api/` maneja HTTP (validacion, status codes, serializacion) y delega.
- `services/` concentra logica de negocio y no depende de FastAPI.
- `graph/` contiene orquestacion de agentes, prompts y herramientas.
- `models/` define persistencia (SQLModel).
- `schemas/` define contratos de entrada/salida.
- `core/` centraliza configuracion, sesion y utilidades transversales.
- `db/` contiene inicializacion y seed de datos.

No mezclar responsabilidades entre carpetas.

## 3) Reglas de cambios por carpeta
### `api/`
- Endpoints cortos y sin logica de negocio.
- Validar entradas antes de llamar services.
- Mantener errores consistentes con `HTTPException`.

### `services/`
- Metodos pequenos, testeables y con tipado.
- Manejo explicito de errores y transacciones.
- Sin acoplarse a detalles de UI/frontend.

### `graph/`
- Cualquier cambio en prompts/routing debe justificar impacto.
- Mantener guardrails anti-alucinacion.
- No agregar tools sin revisar seguridad y costo.

### `models/` y `schemas/`
- Separar persistencia de contratos publicos.
- Si cambia un contrato API, actualizar endpoint y cliente relacionados.

## 4) Calidad minima obligatoria
Antes de cerrar cambios en `src/app/`, correr:
- `uv run ruff check .`
- `uv run ruff format --check .`

Si agregas o modificas comportamiento significativo:
- `uv run pytest`

## 5) Seguridad y datos sensibles
- Nunca hardcodear secretos.
- Nunca loggear datos clinicos sensibles en texto plano.
- No commitear `.env`, dumps o archivos con datos reales de pacientes.

## 6) Criterio de done en `src/app`
Un cambio esta listo cuando:
- respeta limites de capa,
- mantiene contratos coherentes,
- pasa validaciones de calidad,
- y deja trazabilidad tecnica suficiente para mantenimiento.
