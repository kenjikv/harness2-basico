"""
EL ORQUESTADOR — Harness² sobre UNA tarea.

  Ejecución de REFERENCIA con H₀ (cada tarea empieza desde el harness base)
     │
     ▼
  1. PROPONER   los editores INV y DOM proponen un cambio cada uno (o KEEP_BASE)
  2. PROBAR     cada cambio se ejecuta una vez sobre la MISMA tarea
  3. COMPONER   se adopta lo que AYUDÓ → harness compuesto → ejecución FINAL
     │          (con --pasos N se repite N veces: modo secuencial)
     ▼
  4. REFLEXIONAR → una lección para la biblioteca (o NO_ENTRY)
"""
import harness as hz
from paso1_proponer import proponer
from paso2_probar import probar
from paso3_componer import componer
from paso4_reflexionar import reflexionar


def titulo(texto):
    print(f"\n── {texto} " + "─" * max(3, 62 - len(texto)))


def mostrar(tray, sangria="   "):
    print(f"{sangria}camino:  {tray.camino()}")
    for fallo in tray.fallos[:1]:
        print(f"{sangria}         ✘ {fallo}")
    print(f"{sangria}señales: {tray.senales()}")


def mejorar_tarea(tarea, ejecutar, biblioteca, llm=None, pasos=1):
    actual = hz.cargar_base()
    print(f" Empieza desde el harness base (H₀). Biblioteca: "
          f"{len(biblioteca.lecciones)} lección(es){'' if biblioteca.activa else ' (desactivada)'}.")

    titulo("Ejecución de REFERENCIA (harness actual)")
    tray_base = ejecutar(tarea, actual, "referencia")
    mostrar(tray_base)
    tray_actual, trayectorias, adoptados = tray_base, [tray_base], []

    for paso in range(1, pasos + 1):
        sufijo = f" (paso {paso})" if pasos > 1 else ""
        titulo(f"1. PROPONER{sufijo}")
        candidatos = proponer(tarea, actual, tray_actual, biblioteca, llm)
        for c in candidatos:
            print(f"   {c['tipo']}  {c['decision']}: {c['motivo']}")
            for op in c["operaciones"]:
                print(f"        + {hz.describir(op)}")
        a_probar = [c for c in candidatos if c["decision"] == "EDITAR"]
        if not a_probar:
            print("   Los dos editores responden KEEP_BASE: no hay nada que probar.")
            break

        titulo(f"2. PROBAR{sufijo}")
        sondas = probar(tarea, actual, a_probar, ejecutar, paso)
        for candidato, _, tray in sondas:
            print(f"   sonda {candidato['tipo']}")
            mostrar(tray, sangria="      ")
            trayectorias.append(tray)

        titulo(f"3. COMPONER{sufijo}")
        veredictos = componer(tray_actual, sondas, llm)
        for candidato, veredicto, razon in veredictos:
            print(f"   {candidato['tipo']}  {veredicto}: {razon}")
        elegidos = [(c, razon) for c, veredicto, razon in veredictos if veredicto == "AYUDÓ"]
        if not elegidos:
            print("   KEEP_BASE: ningún cambio mostró evidencia de mejora. Se mantiene el harness.")
            break
        actual = hz.aplicar(actual, [op for c, _ in elegidos for op in c["operaciones"]])
        print(f"   → harness compuesto = harness anterior + {' + '.join(c['tipo'] for c, _ in elegidos)}")
        igual = next((c["tipo"] for c, h, _ in sondas if h == actual), None)
        if igual:
            print(f"     (es el mismo harness que probó la sonda {igual})")

        titulo(f"Ejecución FINAL (harness compuesto){sufijo}")
        tray_actual = ejecutar(tarea, actual, f"paso{paso}_final")
        mostrar(tray_actual)
        trayectorias.append(tray_actual)
        adoptados += elegidos

    titulo("4. REFLEXIONAR")
    leccion = reflexionar(tarea, adoptados, trayectorias, llm)
    if leccion is None:
        print("   NO_ENTRY: nada que valga la pena guardar.")
    else:
        estado, guardada = biblioteca.registrar(tarea, leccion, actual)
        print(f"   lección {estado} [{guardada['dominio']}] · confianza {guardada['confianza']} · "
              f"tareas: {', '.join(guardada['tareas'])}")
        print(f"     señal:     {leccion['senal']}")
        print(f"     lección:   {leccion['leccion']}")
        for e in leccion["evidencia"]:
            print(f"     evidencia: {e}")

    return {"tarea": tarea, "tray_base": tray_base, "tray_final": tray_actual,
            "harness_final": actual, "ejecuciones": len(trayectorias)}
