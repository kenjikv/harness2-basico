"""
main.py — Punto de entrada.

  python main.py                   -> todo simulado (sin llave, sin internet)
  python main.py --pasos 2         -> modo secuencial: 2 rondas de proponer-probar-componer por tarea
  python main.py --sin-biblioteca  -> experimento: los editores no consultan la biblioteca
  python main.py --claude          -> Claude real como ejecutor y como editor (necesita .env)
"""
import argparse
import os
import shutil
import sys

import juez
from biblioteca import Biblioteca
from config import BIBLIOTECA, CARPETA, RUNS
from ejecutor import ejecutar
from harness2 import mejorar_tarea
from modelos import EjecutorSimulado, ModeloClaude
from tareas import TAREAS


def cargar_env():
    """Lee el archivo .env (líneas CLAVE=valor) sin librerías extra."""
    archivo = CARPETA / ".env"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def preparar_modelos(usar_claude):
    """Devuelve (fabrica_de_ejecutores, llm_para_las_fases_de_mejora)."""
    if not usar_claude:
        print("Modo SIMULADO: ejecutor obediente + editores, compositor y reflector con reglas fijas.")
        return EjecutorSimulado, None

    from llm import LLM
    cargar_env()
    llave = os.environ.get("ANTHROPIC_API_KEY", "")
    if not llave or llave.startswith("pega-aqui"):
        sys.exit("Falta la llave. Copia .env.example como .env y pega tu ANTHROPIC_API_KEY.")
    modelo_ejecutor = os.environ.get("MODELO_EJECUTOR", "claude-haiku-5-5")
    modelo_editor = os.environ.get("MODELO_EDITOR", "claude-sonnet-5-5")
    print(f"Modo CLAUDE: ejecutor = {modelo_ejecutor} · editores/compositor/reflector = {modelo_editor}")
    return (lambda tarea: ModeloClaude(llave, modelo_ejecutor)), LLM(llave, modelo_editor)


def main():
    parser = argparse.ArgumentParser(description="Harness² explicado con un ejemplo pequeño")
    parser.add_argument("--claude", action="store_true", help="usar Claude real (necesita .env)")
    parser.add_argument("--pasos", type=int, default=1, help="rondas de proponer-probar-componer por tarea")
    parser.add_argument("--sin-biblioteca", action="store_true", help="los editores no usan lo aprendido")
    args = parser.parse_args()

    crear_ejecutor, llm = preparar_modelos(args.claude)
    if RUNS.exists():
        shutil.rmtree(RUNS)
    ejecutar_con_modelo = lambda tarea, harness, etiqueta: ejecutar(tarea, harness, etiqueta, crear_ejecutor)
    biblioteca = Biblioteca(activa=not args.sin_biblioteca)

    resultados = []
    for numero, tarea in enumerate(TAREAS, 1):
        print(f"\n{'═' * 68}\n TAREA {numero}/{len(TAREAS)}: {tarea.id}  (dominio: {tarea.dominio})\n"
              f" {tarea.enunciado}\n{'═' * 68}")
        resultados.append(mejorar_tarea(tarea, ejecutar_con_modelo, biblioteca, llm, args.pasos))

    print(f"\n{'═' * 68}\n INFORME DEL JUEZ (tests ocultos: ninguna fase de mejora los vio)\n{'═' * 68}")
    print(f" {'tarea':<12}{'harness base':>14}{'harness refinado':>19}{'correcciones':>15}{'ejecuciones':>13}")
    for r in resultados:
        base_ok, total = juez.puntuar(r["tarea"], r["tray_base"])
        final_ok, _ = juez.puntuar(r["tarea"], r["tray_final"])
        print(f" {r['tarea'].id:<12}{f'{base_ok}/{total}':>14}{f'{final_ok}/{total}':>19}"
              f"{r['tray_final'].correcciones:>15}{r['ejecuciones']:>13}")
    print(" (correcciones: las que necesitó el agente en la ejecución final, con el harness refinado)")

    print(f"\n Biblioteca ({BIBLIOTECA.relative_to(CARPETA)}/INDEX.md): {len(biblioteca.lecciones)} lección(es)")
    for l in biblioteca.lecciones:
        print(f"   [{l['dominio']}] confianza {l['confianza']} · {', '.join(l['tareas'])}: {l['leccion']}")
    print(f"\nTodo quedó en {RUNS.relative_to(CARPETA)}/: el harness y la trayectoria de cada ejecución.")


if __name__ == "__main__":
    main()
