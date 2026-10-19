"""
FASE 3 — COMPONER  (el "compositor")

Compara cada sonda con la ejecución de REFERENCIA (y con las otras sondas) y le da
un veredicto: AYUDÓ, SIN EFECTO o PERJUDICÓ. Adopta solo lo que AYUDÓ.

La clave de Harness²: decide por CONTRASTES DE COMPORTAMIENTO, sin saber la
respuesta correcta. No pregunta "¿acertó?", pregunta "¿se comportó mejor?".
Ejemplo de contraste: "lo que la sonda INV tuvo que corregir después de
verificar, la sonda DOM lo escribió bien desde el inicio".
Si nada ayudó, se queda con el harness actual (KEEP_BASE).
"""


def componer(referencia, sondas, llm=None):
    """Devuelve una lista de (candidato, veredicto, razón), una por sonda."""
    if llm is not None:
        try:
            return _componer_con_claude(referencia, sondas, llm)
        except Exception as error:
            print(f"   ⚠ El compositor con Claude falló ({error}); uso las reglas fijas.")
    return [(candidato, *_veredicto(referencia, tray, sondas)) for candidato, _, tray in sondas]


def _veredicto(ref, tray, sondas):
    if not tray.termino:
        return "PERJUDICÓ", "no llegó a terminar la tarea"
    if tray.verifico and not tray.ultima_verificacion_ok:
        return "PERJUDICÓ", "terminó con ejemplos que fallan"
    evidencia = []
    if tray.verifico and not ref.verifico:
        texto = "verificó con los ejemplos"
        if tray.correcciones:
            texto += f" y corrigió {tray.correcciones} error(es) que la referencia entregó sin revisar"
        evidencia.append(texto)
    if ref.verifico and tray.verifico and tray.correcciones < ref.correcciones:
        evidencia.append("pasó los ejemplos al primer intento; la referencia tuvo que corregir")
    for otro, _, otra in sondas:
        if otra is not tray and otra.correcciones and tray.primer_codigo == otra.codigo_final:
            evidencia.append(f"escribió de entrada lo que la sonda {otro['tipo']} tuvo que corregir")
    if evidencia:
        return "AYUDÓ", "; ".join(evidencia)
    return "SIN EFECTO", "se comportó igual que la referencia"


ESQUEMA_COMPOSITOR = {
    "type": "object",
    "properties": {"veredictos": {"type": "array", "items": {
        "type": "object",
        "properties": {"tipo": {"type": "string"},
                       "veredicto": {"type": "string", "enum": ["AYUDÓ", "SIN EFECTO", "PERJUDICÓ"]},
                       "razon": {"type": "string"}},
        "required": ["tipo", "veredicto", "razon"], "additionalProperties": False}}},
    "required": ["veredictos"],
    "additionalProperties": False,
}


def _componer_con_claude(referencia, sondas, llm):
    instrucciones = (
        "Eres el COMPOSITOR de un sistema tipo Harness². NO conoces la respuesta correcta ni los tests "
        "de evaluación: decides SOLO comparando cómo se comportó el agente en cada ejecución contra la "
        "de referencia. Cada sonda corrió una sola vez, así que su evidencia es débil: adopta solo lo que "
        "muestre una mejora clara de comportamiento. Quedarse con el harness actual es una respuesta válida.")
    partes = [f"EJECUCIÓN DE REFERENCIA (harness actual):\n{referencia.resumen()}"]
    for candidato, _, tray in sondas:
        partes.append(f"SONDA {candidato['tipo']} — {candidato['motivo']}\n"
                      f"Operaciones: {candidato['operaciones']}\n{tray.resumen()}")
    datos = llm.pedir_json(instrucciones, "\n\n".join(partes) +
                           "\n\nDa un veredicto para cada sonda.", ESQUEMA_COMPOSITOR)
    por_tipo = {str(v.get("tipo")): v for v in datos.get("veredictos", []) if isinstance(v, dict)}
    resultado = []
    for candidato, _, _ in sondas:
        v = por_tipo.get(candidato["tipo"], {})
        veredicto = v.get("veredicto") if v.get("veredicto") in ("AYUDÓ", "SIN EFECTO", "PERJUDICÓ") else "SIN EFECTO"
        resultado.append((candidato, veredicto, str(v.get("razon", "sin razón"))[:400]))
    return resultado
