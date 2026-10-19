"""
config.py — Ajustes generales.
"""
from pathlib import Path

CARPETA = Path(__file__).parent
HARNESS_BASE = CARPETA / "harness_base"      # H₀: el harness inicial, igual para todas las tareas
RUNS = CARPETA / "runs"                      # cada ejecución deja aquí su rastro
BIBLIOTECA = RUNS / "biblioteca"             # el "harness de mejora": lecciones entre tareas

MAX_PASOS_AGENTE = 12                        # freno por ejecución del agente
GUARDARRAILES_PERMITIDOS = {"verificar_antes_de_terminar"}
