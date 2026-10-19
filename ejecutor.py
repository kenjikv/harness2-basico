"""
EL EJECUTOR — corre al agente con UN harness y registra su TRAYECTORIA.

Es el mismo harness básico del video 1 (herramientas + guardarraíles + bucle),
con una diferencia: el harness ahora llega de afuera y puede cambiar.
La trayectoria (qué hizo el agente, paso a paso) es la "evidencia" que
luego usan las fases de mejora. Ellas nunca ven los tests ocultos.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

import harness as hz
from config import MAX_PASOS_AGENTE, RUNS
from evaluador import evaluar


@dataclass
class Trayectoria:
    etiqueta: str
    carpeta: Path
    pasos: list = field(default_factory=list)      # [(acción, resultado resumido)]
    recorrido: list = field(default_factory=list)  # ["escribir", "verificar ✘", ...]
    verifico: bool = False
    ultima_verificacion_ok: bool | None = None
    correcciones: int = 0                          # reescrituras tras una verificación fallida
    fallos: list = field(default_factory=list)     # ejemplos que fallaron al verificar
    casos_fallidos: list = field(default_factory=list)
    primer_codigo: str | None = None
    codigo_final: str | None = None
    termino: bool = False

    def senales(self):
        """Lo observable de la ejecución, en una línea (no es una nota: no hay respuesta correcta)."""
        partes = [f"verificó: {'sí' if self.verifico else 'no'}"]
        if self.verifico:
            partes.append(f"ejemplos al final: {'pasan' if self.ultima_verificacion_ok else 'fallan'}")
        partes += [f"correcciones: {self.correcciones}", f"pasos: {len(self.pasos)}"]
        if not self.termino:
            partes.append("NO terminó")
        return " · ".join(partes)

    def camino(self):
        """El recorrido del agente en una línea: escribir → verificar ✘ → ..."""
        return " → ".join(self.recorrido)

    def resumen(self):
        """La trayectoria completa como texto (para el archivo y para Claude)."""
        lineas = [f"Ejecución '{self.etiqueta}' -> {self.senales()}"]
        lineas += [f"  {n}. {accion}  =>  {resultado}"
                   for n, (accion, resultado) in enumerate(self.pasos, 1)]
        lineas.append("Código final:\n" + (self.codigo_final or "(ninguno)"))
        return "\n".join(lineas)


# Lo que el modelo "ve" de cada herramienta.
CATALOGO = {
    "escribir_archivo": {
        "descripcion": "Crea o reemplaza un archivo en tu carpeta de trabajo.",
        "parametros": {"type": "object",
                       "properties": {"ruta": {"type": "string"}, "contenido": {"type": "string"}},
                       "required": ["ruta", "contenido"]},
    },
    "verificar": {
        "descripcion": "Prueba tu función con los ejemplos del enunciado y te dice cuáles fallan.",
        "parametros": {"type": "object", "properties": {}},
    },
    "terminar": {
        "descripcion": "Declara la tarea terminada.",
        "parametros": {"type": "object", "properties": {"resumen": {"type": "string"}},
                       "required": ["resumen"]},
    },
}


class Sesion:
    """Una ejecución: su propia carpeta de trabajo y las herramientas con guardarraíles."""

    def __init__(self, tarea, harness, trayectoria, workspace):
        self.tarea, self.harness, self.tray, self.workspace = tarea, harness, trayectoria, workspace
        self.verificado_tras_ultimo_cambio = False

    def escribir_archivo(self, ruta, contenido):
        destino = (self.workspace / ruta).resolve()
        if not destino.is_relative_to(self.workspace.resolve()):      # guardarraíl fijo
            self.tray.recorrido.append("escribir ⛔")
            return f"BLOQUEADO: '{ruta}' está fuera de tu carpeta de trabajo.", True
        destino.write_text(contenido, encoding="utf-8")
        if destino.name == self.tarea.archivo:
            if self.tray.primer_codigo is None:
                self.tray.primer_codigo = contenido
            if self.tray.ultima_verificacion_ok is False:
                self.tray.correcciones += 1
            self.tray.codigo_final = contenido
        self.verificado_tras_ultimo_cambio = False
        self.tray.recorrido.append("escribir")
        return f"Guardado {ruta}.", False

    def verificar(self):
        resultados = evaluar(self.workspace, self.tarea, self.tarea.ejemplos)
        todo_ok = all(acierto for *_, acierto in resultados)
        self.tray.verifico = True
        self.tray.ultima_verificacion_ok = todo_ok
        self.verificado_tras_ultimo_cambio = True
        lineas = []
        for args, esperado, obtenido, acierto in resultados:
            linea = f"{self.tarea.funcion}({', '.join(map(repr, args))}) -> {obtenido!r}"
            if not acierto:
                linea += f" (se esperaba {esperado!r})"
                self.tray.fallos.append(linea)
                self.tray.casos_fallidos.append(args)
            lineas.append(("✔ " if acierto else "✘ ") + linea)
        lineas.append("RESULTADO: " + ("TODOS LOS EJEMPLOS PASAN" if todo_ok else "HAY EJEMPLOS QUE FALLAN"))
        self.tray.recorrido.append("verificar " + ("✔" if todo_ok else "✘"))
        return "\n".join(lineas), False

    def terminar(self, resumen=""):
        exige = self.harness["guardarrailes"].get("verificar_antes_de_terminar")
        verificado_ok = self.verificado_tras_ultimo_cambio and self.tray.ultima_verificacion_ok
        if exige and not verificado_ok:                                 # guardarraíl editable
            self.tray.recorrido.append("terminar ⛔")
            return ("BLOQUEADO: antes de terminar debes usar verificar y que los ejemplos pasen.", True)
        self.tray.termino = True
        self.tray.recorrido.append("terminar ✔")
        return "ACEPTADO", False


def _corto(texto, limite=160):
    texto = " | ".join(linea for linea in texto.splitlines() if linea.strip())
    return texto if len(texto) <= limite else texto[:limite] + "…"


def ejecutar(tarea, harness, etiqueta, crear_modelo):
    """Corre una ejecución completa del agente y devuelve su trayectoria."""
    carpeta = RUNS / tarea.id / etiqueta
    if carpeta.exists():
        shutil.rmtree(carpeta)
    workspace = carpeta / "workspace"
    workspace.mkdir(parents=True)
    hz.guardar(harness, carpeta / "harness")

    tray = Trayectoria(etiqueta=etiqueta, carpeta=workspace)
    sesion = Sesion(tarea, harness, tray, workspace)
    modelo = crear_modelo(tarea)
    modelo.iniciar(harness["prompt_sistema"], tarea.enunciado, CATALOGO)

    resultado, hubo_error = None, False
    for _ in range(MAX_PASOS_AGENTE):
        nombre, argumentos = modelo.siguiente_accion(resultado, hubo_error)
        herramienta = getattr(sesion, nombre, None) if nombre in CATALOGO else None
        if herramienta is None:
            resultado, hubo_error = f"No existe la herramienta '{nombre}'.", True
        else:
            try:
                resultado, hubo_error = herramienta(**argumentos)
            except TypeError as error:
                resultado, hubo_error = f"ERROR: argumentos inválidos ({error})", True
        args_cortos = {k: _corto(str(v), 25) for k, v in argumentos.items()}
        tray.pasos.append((f"{nombre}({args_cortos})", _corto(resultado)))
        if tray.termino:
            break

    (carpeta / "trayectoria.md").write_text(tray.resumen(), encoding="utf-8")
    return tray
