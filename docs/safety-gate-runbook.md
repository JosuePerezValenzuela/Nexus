# Runbook Operativo: Safety Gate v1

## 1) Configuracion

Variables en `src/app/core/config.py`:

- `SAFETY_GATE_ENABLED`: habilita/deshabilita el gate.
- `SAFETY_GATE_STRICT_MODE`: reserva para ajustes estrictos de politica.
- `SAFETY_GATE_MAX_REASON_CODES`: tope de codigos devueltos por respuesta.
- `SAFETY_GATE_EXPOSE_METADATA`: expone metadatos `safety` en API cuando aplica.

Valores recomendados por entorno:

- Local: `SAFETY_GATE_ENABLED=false` (pruebas manuales puntuales en `true`).
- Test: dejar default del sistema (auto `true` si no se define la variable).
- Staging: `true` para evaluar calidad de reglas.
- Produccion: `true` con rollout gradual.

## 2) Monitoreo minimo

Contadores obligatorios:

- `safety_gate_triggered_total`
- `safety_gate_bypassed_total`
- `safety_gate_escalation_total`

Reglas de lectura:

- Cada interaccion evaluada incrementa exactamente uno: `triggered` o `bypassed`.
- `escalation` solo sube cuando el `path` es `escalation`.

Eventos estructurados:

- Evento: `safety_gate_decision`
- Campos clave: `path`, `reason_codes`, `details.escalated`, `details.sanitized`.

## 3) Alertas e interpretacion

Alertas sugeridas:

- Integridad rota: `triggered + bypassed != evaluadas`.
- Escalamiento nulo por ventana larga con trafico real.
- Pico anomalo de `triggered` tras cambio de prompts/reglas.
- Aumento de `safety_gate_error` en `reason_codes`.

Interpretacion:

- **Mucho `triggered` + poco `escalation`**: probable sobrebloqueo por sanitizacion.
- **`escalation` muy alto sostenido**: posible alto riesgo real o reglas demasiado sensibles.
- **Todo `bypassed`**: gate apagado, subdeteccion o trafico fuera de alcance diabetes.
- **`safety_gate_error` frecuente**: degradacion interna; revisar excepciones del servicio.

## 4) Rollout

Checklist:

1. Confirmar variables en entorno destino.
2. Activar `SAFETY_GATE_ENABLED=true` en staging.
3. Monitorear contadores y logs por 7 dias.
4. Validar escenarios urgentes y no urgentes contra spec.
5. Activar en produccion por etapas (entorno/instancia).

## 5) Rollback

Pasos:

1. Setear `SAFETY_GATE_ENABLED=false`.
2. Reiniciar despliegue segun proceso de plataforma.
3. Verificar retorno al flujo previo (`bypassed` incrementa, `escalation` se estabiliza).
4. Capturar ventana de logs para postmortem.

## 6) Diagnostico rapido

- Caso urgente no escalado: revisar texto de entrada y coincidencia de red flags.
- Salida con dosis/diagnostico: revisar patrones de deteccion y sanitizacion.
- Metadatos faltantes en API: validar `SAFETY_GATE_EXPOSE_METADATA`.
- Comportamiento inesperado en test/local: confirmar `ENVIRONMENT` y overrides de variables.
