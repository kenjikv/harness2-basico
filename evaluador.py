"""
evaluador.py — Ejecuta la función que escribió el agente con una lista de casos.

Lo usan dos piezas DISTINTAS con casos DISTINTOS:
  - la herramienta verificar del agente  -> con los ejemplos del enunciado
  - el juez del informe final            -> con los tests ocultos
"""
import json
import subprocess
import sys

PLANTILLA = """
import json, sys
sys.path.insert(0, ".")
from {modulo} import {funcion}
salida = []
for args in json.loads(sys.argv[1]):
    try:
        salida.append({{"ok": True, "valor": {funcion}(*args)}})
    except Exception as error:
        salida.append({{"ok": False, "valor": type(error).__name__ + ": " + str(error)}})
print(json.dumps(salida))
"""


def evaluar(carpeta, tarea, casos):
    """Devuelve una lista de (argumentos, esperado, obtenido, acierto)."""
    if not (carpeta / tarea.archivo).exists():
        return [(args, esperado, "no existe el archivo", False) for args, esperado in casos]

    codigo = PLANTILLA.format(modulo=tarea.archivo.removesuffix(".py"), funcion=tarea.funcion)
    argumentos = json.dumps([list(args) for args, _ in casos])
    try:
        proceso = subprocess.run([sys.executable, "-c", codigo, argumentos],
                                 cwd=carpeta, capture_output=True, text=True, timeout=20)
        valores = json.loads(proceso.stdout.strip().splitlines()[-1])
    except subprocess.TimeoutExpired:
        return [(args, esperado, "tardó demasiado", False) for args, esperado in casos]
    except (IndexError, json.JSONDecodeError):
        lineas = proceso.stderr.strip().splitlines()
        error = lineas[-1] if lineas else "error desconocido"
        return [(args, esperado, error, False) for args, esperado in casos]

    return [(args, esperado,
             valor["valor"] if valor["ok"] else "ERROR " + valor["valor"],
             valor["ok"] and valor["valor"] == esperado)
            for (args, esperado), valor in zip(casos, valores)]
