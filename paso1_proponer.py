"""
FASE 1 — PROPONER  (los dos "editores de harness")

Miran cómo se comportó el agente y proponen cambios al harness:
  - INV: cómo TRABAJA el agente (verificar, planificar...). Sirve en cualquier tarea.
  - DOM: lo que sabría un PROFESIONAL de este dominio (el "oficio").

Reglas de Harness² que se respetan aquí:
  - Cada cambio tiene que apoyarse en evidencia: algo que se vio en la trayectoria,
    o una lección de la biblioteca con su propia evidencia.
  - Si no hay evidencia, el editor responde KEEP_BASE: no cambiar nada es válido.
  - Ningún editor conoce la respuesta correcta ni los tests ocultos.
"""
import harness as hz
from llm import OPERACION

REGLA_VERIFICAR = ("Antes de terminar, verifica tu solución con los ejemplos del enunciado "
                   "usando la herramienta verificar.")
EDICIONES_VERIFICAR = [{"op": "activar_guardarrail", "nombre": "verificar_antes_de_terminar"},
                       {"op": "agregar_regla", "texto": REGLA_VERIFICAR}]

# Lo que sabe un profesional de cada dominio (el editor DOM simulado lo usa SOLO si hay evidencia).
OFICIO = {
    "texto": "En tareas que comparan textos, normaliza primero: minúsculas y sin espacios ni signos.",
    "numeros": "En tareas con números, revisa los casos borde: 0, 1 y negativos.",
}


def evidencia_del_dominio(tarea, args):
    """¿El caso que falló apunta a un problema típico del dominio?"""
    if tarea.dominio == "texto":
        return any(isinstance(a, str) and (a != a.lower() or " " in a) for a in args)
    if tarea.dominio == "numeros":
        return any(isinstance(a, int) and a < 2 for a in args)
    return False


def proponer(tarea, harness, trayectoria, biblioteca, llm=None):
    """Devuelve los candidatos de los dos editores: {"tipo", "decision", "motivo", "operaciones"}."""
    candidatos = []
    for tipo, editor in (("INV", _editor_inv), ("DOM", _editor_dom)):
        candidato = None
        if llm is not None:
            try:
                candidato = _editor_con_claude(tipo, tarea, harness, trayectoria, biblioteca, llm)
            except Exception as error:
                print(f"   ⚠ El editor {tipo} con Claude falló ({error}); uso las reglas fijas.")
        if candidato is None:
            candidato = editor(tarea, trayectoria, biblioteca)
        # Un cambio que el harness ya tiene no es un cambio.
        if candidato["decision"] == "EDITAR" and hz.aplicar(harness, candidato["operaciones"]) == harness:
            candidato = keep_base(tipo, "lo que propone ya está en el harness")
        candidatos.append(candidato)
    return candidatos


def keep_base(tipo, motivo):
    return {"tipo": tipo, "decision": "KEEP_BASE", "motivo": motivo, "operaciones": []}


def _editor_inv(tarea, trayectoria, biblioteca):
    """Editor INV simulado: ¿el agente terminó sin comprobar su trabajo?"""
    if trayectoria.verifico:
        return keep_base("INV", "el agente ya verifica su trabajo")
    paso = len(trayectoria.pasos)
    motivo = f"El agente terminó sin verificar (paso {paso}: terminar sin revisar los ejemplos)."
    de_la_biblioteca = [e for e in biblioteca.ediciones_inv() if e["op"] in EDICIONES_VERIFICAR]
    if de_la_biblioteca:
        motivo += f" 📚 Biblioteca: funcionó en {', '.join(de_la_biblioteca[0]['tareas'])}."
    return {"tipo": "INV", "decision": "EDITAR", "motivo": motivo, "operaciones": EDICIONES_VERIFICAR}


def _editor_dom(tarea, trayectoria, biblioteca):
    """Editor DOM simulado: necesita evidencia del dominio (un fallo visto, o la biblioteca)."""
    de_la_biblioteca = biblioteca.ediciones_dom(tarea.dominio)
    if de_la_biblioteca:
        tareas = sorted({t for e in de_la_biblioteca for t in e["tareas"]})
        return {"tipo": "DOM", "decision": "EDITAR",
                "motivo": f"📚 Biblioteca [{tarea.dominio}]: en {', '.join(tareas)} esto evitó el error.",
                "operaciones": [e["op"] for e in de_la_biblioteca]}
    fallidos = [args for args in trayectoria.casos_fallidos if evidencia_del_dominio(tarea, args)]
    if fallidos:
        caso = ", ".join(map(repr, fallidos[0]))
        return {"tipo": "DOM", "decision": "EDITAR",
                "motivo": f"Falló el ejemplo {tarea.funcion}({caso}): es un caso típico de {tarea.dominio}.",
                "operaciones": [{"op": "agregar_regla", "texto": OFICIO[tarea.dominio]}]}
    return keep_base("DOM", f"todavía no hay evidencia de un problema del dominio {tarea.dominio}")


ESQUEMA_EDITOR = {
    "type": "object",
    "properties": {"decision": {"type": "string", "enum": ["EDITAR", "KEEP_BASE"]},
                   "motivo": {"type": "string"},
                   "operaciones": {"type": "array", "items": OPERACION}},
    "required": ["decision", "motivo", "operaciones"],
    "additionalProperties": False,
}

FOCO = {
    "INV": ("Eres el editor INV: atacas defectos de CÓMO TRABAJA el agente que se repetirían en "
            "cualquier tarea (verificar su trabajo, planificar, usar las herramientas)."),
    "DOM": ("Eres el editor DOM: aportas lo que sabría un PROFESIONAL de este dominio sobre el "
            "entregable (casos especiales, formatos, reglas del oficio)."),
}


def _editor_con_claude(tipo, tarea, harness, trayectoria, biblioteca, llm):
    instrucciones = (
        "Eres un editor de harness en un sistema tipo Harness². No cambias el modelo: mejoras el "
        f"sistema que lo rodea. {FOCO[tipo]} No conoces la respuesta correcta ni los tests de evaluación. "
        "Cada edición debe apoyarse en algo concreto de la trayectoria o en una lección de la biblioteca. "
        "Si no hay evidencia, responde KEEP_BASE. " + hz.DESCRIPCION_OPERACIONES)
    ediciones = biblioteca.ediciones_inv() if tipo == "INV" else biblioteca.ediciones_dom(tarea.dominio)
    texto_biblioteca = "\n".join(f"- {hz.describir(e['op'])} (funcionó en {', '.join(e['tareas'])})"
                                 for e in ediciones) or "(vacía)"
    mensaje = (f"TAREA ({tarea.dominio}):\n{tarea.enunciado}\n\nHARNESS ACTUAL:\n{hz.como_texto(harness)}\n\n"
               f"LO QUE HIZO EL AGENTE CON ESE HARNESS:\n{trayectoria.resumen()}\n\n"
               f"BIBLIOTECA (ediciones {tipo} de tareas anteriores):\n{texto_biblioteca}")
    datos = llm.pedir_json(instrucciones, mensaje, ESQUEMA_EDITOR)
    operaciones = hz.validar(datos.get("operaciones", []))
    if datos.get("decision") != "EDITAR" or not operaciones:
        return keep_base(tipo, str(datos.get("motivo", ""))[:300])
    return {"tipo": tipo, "decision": "EDITAR", "motivo": str(datos.get("motivo", ""))[:300],
            "operaciones": operaciones}
