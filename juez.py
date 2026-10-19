"""
EL JUEZ — solo para el informe final.

Evalúa con los TESTS OCULTOS el código que dejó el agente. Ninguna fase de
mejora lo usa: así medimos si el harness mejoró de verdad, sin hacer trampa.
"""
from evaluador import evaluar


def puntuar(tarea, trayectoria):
    """Devuelve (aciertos, total) del código final de una ejecución."""
    resultados = evaluar(trayectoria.carpeta, tarea, tarea.tests_ocultos)
    return sum(acierto for *_, acierto in resultados), len(resultados)
