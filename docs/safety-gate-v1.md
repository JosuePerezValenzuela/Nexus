# Safety Gate v1 (Diabetes/Prediabetes)

## Objetivo operativo

El safety gate agrega una verificacion deterministica antes de entregar la respuesta final en consultas de diabetes/prediabetes.

- Si detecta riesgo urgente, fuerza una respuesta de escalamiento.
- Si no es urgente pero detecta lenguaje riesgoso (dosis/diagnostico definitivo), sanea la salida.
- Si no detecta riesgo, deja pasar la respuesta del especialista sin cambios.

## Alcance de reglas v1

### Clasificacion urgente

Se marca como `urgent` si aparece al menos uno de estos grupos:

- Banderas rojas de hipoglucemia severa.
- Banderas rojas de hiperglucemia severa.
- Combinacion de contexto diabetes + sintoma elevado + marcador severo neuro/cardio.

### Resultado por camino (`path`)

- `escalation`: reemplaza la respuesta final por plantilla de emergencia.
- `sanitized`: elimina/reescribe lenguaje de dosis o diagnostico definitivo.
- `pass_through`: entrega respuesta original.
- `fallback`: mensaje conservador ante error interno del gate.

## Codigos de motivo (`reason_codes`)

- `urgent_hypoglycemia_red_flag`
- `urgent_hyperglycemia_red_flag`
- `severe_context_neuro_cardio`
- `high_risk_dosing_directive`
- `high_risk_diagnostic_directive`
- `safety_gate_error`

> Limite: la salida se recorta por `SAFETY_GATE_MAX_REASON_CODES`.

## Comportamiento de plantilla de escalamiento

En `escalation`, la respuesta final:

- Prioriza atencion inmediata/emergencias locales.
- Explicita que no se dan dosis ni diagnosticos definitivos.
- Incluye motivos detectados en lenguaje humano.
- No sigue con contenido rutinario como respuesta principal.

## Limites y no objetivos explicitos (v1)

- No reemplaza juicio clinico profesional ni triage medico formal.
- No calcula ni ajusta dosis personalizadas.
- No confirma diagnosticos.
- No agrega canales externos de alerta (SMS, pager, call center).
- No usa clasificador ML: v1 es 100% basado en reglas.

## Rollout y rollback por feature flag

El gate se controla con variables de entorno en `src/app/core/config.py`:

- `SAFETY_GATE_ENABLED` (default `false`, en `test` se activa por defecto si no se define)
- `SAFETY_GATE_STRICT_MODE`
- `SAFETY_GATE_MAX_REASON_CODES`
- `SAFETY_GATE_EXPOSE_METADATA`

Secuencia recomendada:

1. Local: validar comportamiento con `SAFETY_GATE_ENABLED=false` y `true`.
2. Staging: habilitar y revisar logs/counters durante al menos una semana.
3. Produccion: activar por entorno de forma gradual.

Rollback:

- Accion rapida: `SAFETY_GATE_ENABLED=false` para volver al flujo previo.
- Verificar que `safety_gate_bypassed_total` suba y `safety_gate_escalation_total` deje de subir.
- Mantener logs para analisis de falso positivo/falso negativo.

## Evidencia de validacion y umbrales

Cobertura implementada en:

- `tests/services/test_safety_gate_service.py`
- `tests/graph/test_safety_gate_node.py`
- `tests/api/v1/test_agent_safety_gate.py`

Mapeo requisito -> evidencia:

- Deteccion urgente (hipo/hiper/contexto severo): pruebas unitarias de servicio.
- Escalamiento obligatorio en urgente: pruebas de nodo y API.
- Supresion de dosis/diagnostico riesgoso: pruebas unitarias de saneamiento.
- Preservacion de no urgente: pruebas de servicio/nodo con `pass_through`.
- Integridad de contadores: pruebas de nodo con reconciliacion por interaccion.

Umbrales de aceptacion v1 (spec):

- Urgente: 100% de escenarios urgentes deben escalar.
- Supresion de riesgo: 100% sin dosis/diagnostico prohibido en urgente.
- No urgente: >=95% mantiene flujo sin escalamiento.
- Contadores: 100% cumple `triggered + bypassed = total`.

## Operacion diaria y monitoreo

Contadores minimos a observar:

- `safety_gate_triggered_total`
- `safety_gate_bypassed_total`
- `safety_gate_escalation_total`

Interpretacion rapida:

- `triggered` alto con `escalation` bajo: revisar exceso de sanitizacion.
- `escalation` en cero por periodos largos: posible subdeteccion o flag desactivado.
- `bypassed` ~100% en trafico real: posible reglas demasiado laxas o gate apagado.
- `triggered + bypassed` distinto de interacciones evaluadas: problema de instrumentacion.

Para pasos operativos detallados, ver `docs/safety-gate-runbook.md`.
