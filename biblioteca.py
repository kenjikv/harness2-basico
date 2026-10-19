"""
LA BIBLIOTECA — el "harness de mejora" (el segundo nivel de recursión de Harness²).

Entre tareas NO se hereda el harness: cada tarea vuelve a empezar desde H₀.
Lo que sí crece es esta biblioteca: lecciones con evidencia que los editores
consultan al proponer en las tareas siguientes.

Cada lección guarda:
  dominio    : "texto", "numeros"...
  senal      : cuándo aplica
  leccion    : qué hacer
  evidencia  : qué se vio en las ejecuciones
  confianza  : "media" (vista en una tarea) o "alta" (confirmada en otra)
  ediciones  : {"INV": [...], "DOM": [...]}, las operaciones concretas
  tareas     : en qué tareas se vio

Las ediciones INV (cómo trabaja el agente) sirven en cualquier dominio;
las DOM (el oficio) solo en el mismo dominio.
"""
import json

import harness as hz
from config import BIBLIOTECA


class Biblioteca:
    def __init__(self, activa=True):
        self.activa = activa          # con --sin-biblioteca los editores no la consultan
        self.lecciones = []

    def _reunir(self, tipo, dominio=None):
        """Las ediciones de un tipo, sin repetir, con las tareas donde funcionaron."""
        if not self.activa:
            return []
        reunidas = []
        for leccion in self.lecciones:
            if dominio is not None and leccion["dominio"] != dominio:
                continue
            for op in leccion["ediciones"][tipo]:
                ya = next((r for r in reunidas if r["op"] == op), None)
                if ya is None:
                    reunidas.append({"op": op, "tareas": list(leccion["tareas"])})
                else:
                    ya["tareas"] += [t for t in leccion["tareas"] if t not in ya["tareas"]]
        return reunidas

    def ediciones_inv(self):
        """INV: cómo trabaja el agente. Sirven en cualquier dominio."""
        return self._reunir("INV")

    def ediciones_dom(self, dominio):
        """DOM: lo que sabe un profesional de ESE dominio."""
        return self._reunir("DOM", dominio)

    def registrar(self, tarea, nueva, harness_adoptado):
        """Guarda la lección de una tarea. Si ya existía la misma, la confirma.
        Devuelve ("nueva" | "confirmada", lección)."""
        igual = next((l for l in self.lecciones
                      if l["dominio"] == nueva["dominio"] and l["ediciones"] == nueva["ediciones"]), None)
        if igual is not None:
            igual["tareas"].append(tarea.id)
            igual["evidencia"] += nueva["evidencia"]
            igual["confianza"] = "alta"
            estado, leccion = "confirmada", igual
        else:
            nueva["tareas"] = [tarea.id]
            self.lecciones.append(nueva)
            estado, leccion = "nueva", nueva
        self._guardar(tarea, leccion, harness_adoptado)
        return estado, leccion

    def _guardar(self, tarea, leccion, harness_adoptado):
        """En disco, como en Harness²: el harness adoptado + EXPERIENCE.md, y un índice."""
        carpeta = BIBLIOTECA / tarea.id
        hz.guardar(harness_adoptado, carpeta / "harness")
        (carpeta / "EXPERIENCE.md").write_text(
            f"# Experiencia: {tarea.id}\n\n"
            f"- Dominio: {leccion['dominio']}\n- Señal: {leccion['senal']}\n"
            f"- Lección: {leccion['leccion']}\n- Confianza: {leccion['confianza']}\n"
            "- Evidencia:\n" + "".join(f"  - {e}\n" for e in leccion["evidencia"]), encoding="utf-8")
        (BIBLIOTECA / "lecciones.json").write_text(
            json.dumps(self.lecciones, indent=2, ensure_ascii=False), encoding="utf-8")
        (BIBLIOTECA / "INDEX.md").write_text(
            "# Biblioteca de lecciones\n\n" + "".join(
                f"- [{l['dominio']}] {l['leccion']} (confianza {l['confianza']}; "
                f"tareas: {', '.join(l['tareas'])})\n" for l in self.lecciones), encoding="utf-8")
