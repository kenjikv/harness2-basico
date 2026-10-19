"""
EL HARNESS EDITABLE

En Harness² el harness es un DATO que se puede editar, no código fijo.
Harness² edita 8 componentes, cada uno en su archivo (prompt de sistema,
guardarraíles, memoria, guía de herramientas, subagentes, skills, scripts
y plugins). Aquí usamos 2:

  - prompt_sistema.md    : las reglas que lee el agente (una guía: el modelo puede ignorarla)
  - guardarrailes.json   : controles que el harness HACE CUMPLIR (como un plugin de Harness²)

Y solo hay 2 operaciones de edición permitidas (el editor no puede inventar otras):
  - agregar_regla(texto)          -> añade una línea al prompt de sistema
  - activar_guardarrail(nombre)   -> enciende un control de guardarrailes.json
"""
import copy
import json

from config import GUARDARRAILES_PERMITIDOS, HARNESS_BASE

DESCRIPCION_OPERACIONES = (
    "Solo puedes usar estas operaciones: "
    '{"op": "agregar_regla", "texto": "..."} añade una regla al prompt de sistema; '
    '{"op": "activar_guardarrail", "nombre": "verificar_antes_de_terminar"} obliga al agente '
    "a verificar con los ejemplos (y que pasen) antes de poder terminar."
)


def cargar_base():
    """Lee H₀, el harness inicial, desde la carpeta harness_base/."""
    return {
        "prompt_sistema": (HARNESS_BASE / "prompt_sistema.md").read_text(encoding="utf-8"),
        "guardarrailes": json.loads((HARNESS_BASE / "guardarrailes.json").read_text(encoding="utf-8")),
    }


def aplicar(harness, operaciones):
    """Devuelve un harness NUEVO con las operaciones aplicadas (el original no cambia)."""
    nuevo = copy.deepcopy(harness)
    for op in operaciones:
        if op["op"] == "agregar_regla" and op["texto"] not in nuevo["prompt_sistema"]:
            nuevo["prompt_sistema"] = nuevo["prompt_sistema"].rstrip() + f"\n- {op['texto']}\n"
        elif op["op"] == "activar_guardarrail":
            nuevo["guardarrailes"][op["nombre"]] = True
    return nuevo


def validar(operaciones):
    """Filtra lo que proponga un LLM: solo pasan operaciones permitidas y bien formadas."""
    validas = []
    for op in operaciones if isinstance(operaciones, list) else []:
        if not isinstance(op, dict):
            continue
        if op.get("op") == "agregar_regla" and isinstance(op.get("texto"), str) and op["texto"].strip():
            validas.append({"op": "agregar_regla", "texto": op["texto"].strip()[:300]})
        elif op.get("op") == "activar_guardarrail" and op.get("nombre") in GUARDARRAILES_PERMITIDOS:
            validas.append({"op": "activar_guardarrail", "nombre": op["nombre"]})
    return validas


def describir(op):
    """Texto corto de una operación, para mostrar en pantalla."""
    if op["op"] == "agregar_regla":
        return f'regla: "{op["texto"]}"'
    return f"guardarraíl: {op['nombre']} = activado"


def como_texto(harness):
    """El harness completo como texto (para guardarlo o mostrárselo a Claude)."""
    return (f"[prompt_sistema.md]\n{harness['prompt_sistema']}\n"
            f"[guardarrailes.json]\n{json.dumps(harness['guardarrailes'], ensure_ascii=False)}")


def guardar(harness, carpeta):
    """Escribe el harness en disco, igual que harness_base/, para poder inspeccionarlo."""
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "prompt_sistema.md").write_text(harness["prompt_sistema"], encoding="utf-8")
    (carpeta / "guardarrailes.json").write_text(
        json.dumps(harness["guardarrailes"], indent=2, ensure_ascii=False), encoding="utf-8")
