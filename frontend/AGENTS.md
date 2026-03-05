# AGENTS.md - Guia de Desarrollo para `frontend/`

## 1) Alcance de este AGENTS
Este archivo aplica a todo lo que vive dentro de `frontend/`.
Define reglas para mantener una UI simple, estable y alineada con el contrato de la API.

## 2) Responsabilidad del frontend
- `frontend/` consume la API y presenta resultados al usuario.
- No mover logica de negocio clinica al cliente.
- Mantener la UI desacoplada de detalles internos del backend.

## 3) Reglas de integracion con API
- Usar URL base configurable por variables de entorno/secrets.
- Mantener consistencia estricta con los contratos de respuesta.
- Manejar estados de error de red, timeout y respuestas no validas.
- Mostrar mensajes claros al usuario cuando falle la API.

## 4) Estado y flujo de la interfaz
- Limitar `session_state` a datos necesarios para UX.
- No persistir datos sensibles de pacientes en texto plano.
- Evitar duplicar estado entre variables globales y `session_state`.
- Mantener nombres de claves consistentes en historial y payloads.

## 5) Calidad minima obligatoria
Antes de cerrar cambios en `frontend/`, correr:
- `uv run ruff check .`
- `uv run ruff format --check .`

Si hay cambios de flujo importantes entre frontend y backend:
- validar manualmente escenario feliz + escenario de error

## 6) Seguridad y datos sensibles
- Nunca hardcodear secretos o tokens.
- No loggear datos clinicos sensibles en consola ni en UI.
- No commitear archivos con credenciales o datos reales de pacientes.

## 7) Criterio de done en `frontend/`
Un cambio esta listo cuando:
- mantiene compatibilidad con el contrato API,
- maneja errores de forma clara para el usuario,
- no filtra datos sensibles,
- y respeta el estilo y validaciones del repositorio.
