"""
FASE 4 — REFLEXIONAR  (el "reflector de experiencia")

Al terminar la tarea revisa TODO lo que pasó (referencia, sondas, veredictos y la
ejecución final) y escribe COMO MÁXIMO UNA lección para la biblioteca, con su
evidencia. Si no hay nada que valga la pena, responde NO_ENTRY.

Además de los cambios adoptados, mira lo que el agente tuvo que corregir: si el
código que pasó los ejemplos hace algo que el primero no hacía, eso también es
evidencia (por ejemplo, "pasó cuando empezó a limpiar el texto").
"""
import difflib

import harness as hz
from llm import OPERACION
from paso1_proponer import OFICIO, evidencia_del_dominio


def reflexionar(tarea, adoptados, trayectorias, llm=None):
    """adoptados: [(candidato, razón)]. trayectorias: todas las ejecuciones de la tarea.
    Devuelve la lección (dict) o None si no hay nada que guardar (NO_ENTRY)."""
    if not adoptados:
        return None
    if llm is not None:
        try:
            return _reflexionar_con_claude(tarea, adoptados, trayectorias, llm)
        except Exception as error:
            print(f"   ⚠ El reflector con Claude falló ({error}); uso las reglas fijas.")
    return _reflexionar_con_reglas(tarea, adoptados, trayectorias)


def _ediciones_adoptadas(adoptados):
    ediciones = {"INV": [], "DOM": []}
    for candidato, _ in adoptados:
        ediciones[candidato["tipo"]] += [op for op in candidato["operaciones"]
                                         if op not in ediciones[candidato["tipo"]]]
    return ediciones


def correccion_observada(tarea, trayectorias):
    """Busca una ejecución que falló un ejemplo típico del dominio y luego pasó.
    Devuelve (ejemplo que falló, línea que agregó el código que pasó) o None."""
    for tray in trayectorias:
        if not (tray.correcciones and tray.ultima_verificacion_ok):
            continue
        if not any(evidencia_del_dominio(tarea, args) for args in tray.casos_fallidos):
            continue
        agregadas = [linea[1:].strip() for linea in difflib.ndiff(
            tray.primer_codigo.splitlines(), tray.codigo_final.splitlines())
            if linea.startswith("+ ") and not linea[1:].strip().startswith(('"""', "def "))]
        return tray.fallos[0], (agregadas[0] if agregadas else "")
    return None


def _reflexionar_con_reglas(tarea, adoptados, trayectorias):
    ediciones = _ediciones_adoptadas(adoptados)
    evidencia = [f"{tarea.id}: {c['tipo']} ayudó — {razon}" for c, razon in adoptados]
    vista = correccion_observada(tarea, trayectorias)
    if vista and not ediciones["DOM"]:
        fallo, linea = vista
        ediciones["DOM"].append({"op": "agregar_regla", "texto": OFICIO[tarea.dominio]})
        evidencia.append(f"{tarea.id}: falló {fallo} y pasó cuando el código agregó «{linea}»")
    partes = []
    if ediciones["INV"]:
        partes.append("Verificar con los ejemplos antes de terminar.")
    partes += [op["texto"] for op in ediciones["DOM"] if op["op"] == "agregar_regla"]
    return {
        "dominio": tarea.dominio,
        "senal": f"tareas de {tarea.dominio}" + ("; el agente termina sin verificar" if ediciones["INV"] else ""),
        "leccion": " ".join(partes),
        "evidencia": evidencia,
        "confianza": "media",
        "ediciones": ediciones,
    }


ESQUEMA_REFLECTOR = {
    "type": "object",
    "properties": {"decision": {"type": "string", "enum": ["ENTRADA", "NO_ENTRY"]},
                   "senal": {"type": "string"}, "leccion": {"type": "string"},
                   "evidencia": {"type": "string"},
                   "operaciones_dom_observadas": {"type": "array", "items": OPERACION}},
    "required": ["decision", "senal", "leccion", "evidencia", "operaciones_dom_observadas"],
    "additionalProperties": False,
}


def _reflexionar_con_claude(tarea, adoptados, trayectorias, llm):
    instrucciones = (
        "Eres el REFLECTOR DE EXPERIENCIA de un sistema tipo Harness². Conviertes lo que pasó en una "
        "tarea en COMO MÁXIMO UNA lección útil para tareas FUTURAS y distintas, solo si tiene evidencia "
        "en las ejecuciones. Si no hay nada que valga la pena, responde NO_ENTRY. "
        "En operaciones_dom_observadas puedes proponer reglas del dominio que la evidencia respalde. "
        + hz.DESCRIPCION_OPERACIONES)
    detalle = "\n".join(f"- ADOPTADO {c['tipo']}: {c['motivo']} | operaciones: {c['operaciones']} | "
                        f"evidencia: {razon}" for c, razon in adoptados)
    mensaje = (f"Tarea ({tarea.dominio}): {tarea.enunciado}\n\nCambios adoptados:\n{detalle}\n\n"
               "Ejecuciones:\n" + "\n\n".join(t.resumen() for t in trayectorias))
    datos = llm.pedir_json(instrucciones, mensaje, ESQUEMA_REFLECTOR)
    if datos.get("decision") != "ENTRADA":
        return None
    ediciones = _ediciones_adoptadas(adoptados)
    ediciones["DOM"] += [op for op in hz.validar(datos.get("operaciones_dom_observadas", []))
                         if op not in ediciones["DOM"]]
    return {"dominio": tarea.dominio, "senal": str(datos.get("senal", ""))[:200],
            "leccion": str(datos.get("leccion", ""))[:300],
            "evidencia": [f"{tarea.id}: {str(datos.get('evidencia', ''))[:300]}"],
            "confianza": "media", "ediciones": ediciones}
