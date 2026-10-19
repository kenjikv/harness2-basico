"""
EL MODELO EJECUTOR (lo que Harness² NO toca: sus "pesos" quedan fijos)

  - EjecutorSimulado: un modelo de juguete que OBEDECE lo que dice el harness.
      * Si las reglas traen la pista de su dominio ("normaliza" en texto, "casos borde"
        en números), escribe la versión cuidadosa; si no, la ingenua.
      * Si las reglas dicen "verifica", verifica antes de terminar.
      * Si verifica y algo falla, corrige (aprende del mensaje de error).
    Así se ve que, con el mismo modelo, cambiar el harness cambia el resultado.

  - ModeloClaude: Claude real vía la API de Anthropic.
"""

# Lo que "sabe escribir" el modelo simulado para cada tarea.
SOLUCIONES_SIMULADAS = {
    "palindromo": {
        "ingenua": "def es_palindromo(texto):\n    return texto == texto[::-1]\n",
        "cuidadosa": (
            "def es_palindromo(texto):\n"
            '    """Indica si el texto se lee igual en ambos sentidos."""\n'
            '    limpio = "".join(c.lower() for c in texto if c.isalnum())\n'
            "    return limpio == limpio[::-1]\n"),
    },
    "anagrama": {
        "ingenua": "def es_anagrama(a, b):\n    return sorted(a) == sorted(b)\n",
        "cuidadosa": (
            "def es_anagrama(a, b):\n"
            '    """Indica si a y b usan exactamente las mismas letras."""\n'
            "    def limpiar(s):\n"
            "        return sorted(c.lower() for c in s if c.isalnum())\n"
            "    return limpiar(a) == limpiar(b)\n"),
    },
    "primo": {
        "ingenua": "def es_primo(n):\n    return all(n % d for d in range(2, n))\n",
        "cuidadosa": (
            "def es_primo(n):\n"
            '    """Indica si n es un número primo."""\n'
            "    if n < 2:\n"
            "        return False\n"
            "    return all(n % d for d in range(2, int(n ** 0.5) + 1))\n"),
    },
}

# Si esta palabra aparece en las reglas, el modelo simulado escribe la versión cuidadosa.
PISTA_DEL_DOMINIO = {"texto": "normaliza", "numeros": "casos borde"}


class EjecutorSimulado:
    def __init__(self, tarea):
        self.tarea = tarea
        self.codigos = SOLUCIONES_SIMULADAS[tarea.id]

    def iniciar(self, instrucciones, enunciado, catalogo):
        reglas = instrucciones.lower()
        self.cuidadoso = PISTA_DEL_DOMINIO[self.tarea.dominio] in reglas
        self.verifica = "verifica" in reglas
        self.ultima = None

    def siguiente_accion(self, resultado, hubo_error):
        escribir = lambda version: ("escribir_archivo",
                                    {"ruta": self.tarea.archivo, "contenido": self.codigos[version]})
        if self.ultima is None:
            accion = escribir("cuidadosa" if self.cuidadoso else "ingenua")
        elif self.ultima == "escribir_archivo":
            accion = ("verificar", {}) if self.verifica else ("terminar", {"resumen": "Listo."})
        elif self.ultima == "verificar":
            if "TODOS LOS EJEMPLOS PASAN" in resultado:
                accion = ("terminar", {"resumen": "Listo, los ejemplos pasan."})
            else:
                accion = escribir("cuidadosa")       # corrige leyendo qué ejemplo falló
        else:                                        # su "terminar" fue bloqueado
            accion = ("verificar", {})
        self.ultima = accion[0]
        return accion


class ModeloClaude:
    """Claude como ejecutor, con el bucle manual de tool use de la documentación oficial:
    https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls"""

    def __init__(self, api_key, modelo):
        try:
            import anthropic
        except ImportError:
            raise SystemExit("Falta el SDK de Anthropic. Instálalo con:  pip install anthropic")
        self.cliente = anthropic.Anthropic(api_key=api_key)
        self.modelo = modelo

    def iniciar(self, instrucciones, enunciado, catalogo):
        self.instrucciones = instrucciones
        self.herramientas = [{"name": n, "description": h["descripcion"], "input_schema": h["parametros"]}
                             for n, h in catalogo.items()]
        self.mensajes = [{"role": "user", "content": enunciado}]
        self.pendientes = []

    def siguiente_accion(self, resultado, hubo_error):
        if resultado is not None:
            if self.pendientes:
                # Todos los resultados van juntos en un solo mensaje: el primero se ejecutó,
                # los demás no (regla de una herramienta por turno).
                bloques = [{"type": "tool_result", "tool_use_id": self.pendientes[0],
                            "content": resultado, "is_error": hubo_error}]
                bloques += [{"type": "tool_result", "tool_use_id": extra, "is_error": True,
                             "content": "No ejecutada: usa una herramienta por turno."}
                            for extra in self.pendientes[1:]]
                self.mensajes.append({"role": "user", "content": bloques})
            else:
                self.mensajes.append({"role": "user", "content": resultado})

        respuesta = self.cliente.messages.create(
            model=self.modelo, max_tokens=16000, system=self.instrucciones,
            tools=self.herramientas, messages=self.mensajes)
        self.mensajes.append({"role": "assistant", "content": respuesta.content})
        if respuesta.stop_reason == "refusal":
            self.pendientes = []
            return "terminar", {"resumen": "(Claude declinó la tarea)"}

        usos = [b for b in respuesta.content if b.type == "tool_use"]
        self.pendientes = [uso.id for uso in usos]
        if usos:
            return usos[0].name, usos[0].input
        texto = "".join(b.text for b in respuesta.content if b.type == "text")
        return "terminar", {"resumen": texto}
