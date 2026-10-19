"""
llm.py — Claude como "cerebro" de las fases de mejora (editores, compositor y reflector).

En modo simulado estas fases usan reglas fijas. En modo --claude le preguntamos a Claude
y le pedimos la respuesta con un esquema JSON fijo (structured outputs), que luego validamos.
"""
import json

# Modelos que aceptan el respaldo del servidor si un pedido es declinado (fallbacks="default").
MODELOS_CON_RESPALDO = {"claude-sonnet-5-5", "claude-opus-5-5", "claude-opus-5", "claude-fable-5-1"}

OPERACION = {   # una operación de edición, tal como la pedimos en los esquemas
    "type": "object",
    "properties": {"op": {"type": "string", "enum": ["agregar_regla", "activar_guardarrail"]},
                   "texto": {"type": "string"}, "nombre": {"type": "string"}},
    "required": ["op", "texto", "nombre"],
    "additionalProperties": False,
}


class LLM:
    def __init__(self, api_key, modelo):
        try:
            import anthropic
        except ImportError:
            raise SystemExit("Falta el SDK de Anthropic. Instálalo con:  pip install anthropic")
        self.cliente = anthropic.Anthropic(api_key=api_key)
        self.modelo = modelo

    def pedir_json(self, instrucciones, mensaje, esquema):
        """Envía un mensaje y devuelve la respuesta como diccionario con la forma del esquema."""
        pedido = dict(model=self.modelo, max_tokens=16000, system=instrucciones,
                      messages=[{"role": "user", "content": mensaje}],
                      output_config={"format": {"type": "json_schema", "schema": esquema}})
        if self.modelo in MODELOS_CON_RESPALDO:
            respuesta = self.cliente.beta.messages.create(
                **pedido, betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        else:
            respuesta = self.cliente.messages.create(**pedido)
        if respuesta.stop_reason == "refusal":
            raise ValueError("Claude declinó responder")
        texto = next(b.text for b in respuesta.content if b.type == "text")
        return json.loads(texto)
