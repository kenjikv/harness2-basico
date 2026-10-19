"""
FASE 2 — PROBAR  (las "sondas")

Cada candidato se aplica al harness y se EJECUTA una vez sobre la MISMA tarea,
con el mismo modelo. No se le pone nota: solo se registra cómo se comportó.
"""
import harness as hz


def probar(tarea, harness_actual, candidatos, ejecutar, paso):
    """Devuelve una lista de (candidato, harness_probado, trayectoria)."""
    sondas = []
    for candidato in candidatos:
        harness_probado = hz.aplicar(harness_actual, candidato["operaciones"])
        etiqueta = f"paso{paso}_sonda_{candidato['tipo']}"
        sondas.append((candidato, harness_probado, ejecutar(tarea, harness_probado, etiqueta)))
    return sondas
