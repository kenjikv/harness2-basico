# Harness² explicado con un ejemplo pequeño

En el **harness básico** (video 1), una persona mejora el harness cuando el agente falla.
En **Harness²** esa mejora la hace el propio sistema, tarea por tarea, **sin cambiar el modelo**
y **sin mirar la respuesta correcta**.

Harness² es un trabajo de investigadores de Google Cloud AI Research (con un primer autor de
Northwestern University): [arXiv 2610.14224](https://arxiv.org/abs/2610.14224), octubre de 2026.
Código oficial: [google-research/harness2](https://github.com/google-research/harness2) (Apache 2.0,
"not an officially supported Google product").

Este proyecto reproduce su mecanismo a escala de aula, con el mismo palíndromo del video 1
([harness-basico](https://github.com/kenjikv/harness-basico)). No usa
el framework oficial, que necesita Vertex AI, OpenCode o Codex y sus propios benchmarks.

## Las dos recursiones

```
Por cada tarea (palíndromo, anagrama, primo), siempre desde el harness base H₀:

  Ejecución de REFERENCIA ──► trayectoria (cómo se comportó, no si acertó)
        │
        ▼
  1. PROPONER    dos editores:  INV (cómo trabaja el agente) · DOM (el oficio del dominio)
  2. PROBAR      cada cambio se ejecuta una vez sobre la MISMA tarea  → una "sonda" por cambio
  3. COMPONER    compara conductas contra la referencia y adopta lo que AYUDÓ → ejecución FINAL
        │        ↺ con --pasos N se repite N veces (modo secuencial)
        ▼
  4. REFLEXIONAR una lección (o NO_ENTRY) a la BIBLIOTECA ──► la consultan los editores de la tarea siguiente

Al final, un JUEZ con tests ocultos compara harness base vs. refinado.
```

## Cada pieza en su archivo

| Pieza de Harness² | Archivo | Qué hace aquí |
|---|---|---|
| Harness editable (H₀) | `harness_base/`, `harness.py` | 2 componentes (prompt y guardarraíles) y 2 operaciones de edición permitidas |
| Ejecutor del agente | `ejecutor.py`, `modelos.py` | Corre al agente con un harness y registra su trayectoria |
| Editores INV y DOM (Proponer) | `paso1_proponer.py` | Proponen un cambio cada uno, o `KEEP_BASE` si no hay evidencia |
| Sondas (Probar) | `paso2_probar.py` | Ejecutan cada cambio sobre la misma tarea |
| Compositor (Componer) | `paso3_componer.py` | Veredicto por contraste de conducta: AYUDÓ, SIN EFECTO o PERJUDICÓ |
| Reflector (Reflexionar) | `paso4_reflexionar.py` | Una lección con evidencia, o `NO_ENTRY` |
| Biblioteca (harness de mejora) | `biblioteca.py` | Lecciones entre tareas; INV sirve en cualquier dominio, DOM solo en el suyo |
| Juez (solo informe) | `juez.py`, `evaluador.py` | Tests ocultos que ninguna fase de mejora ve |
| Orquestador | `harness2.py` | Une las 4 fases para una tarea |
| Tareas | `tareas.py` | Enunciado + ejemplos públicos + tests ocultos |

## La regla de oro: sin respuesta correcta

- El agente solo puede verificarse con los **ejemplos del enunciado**.
- Los editores solo proponen lo que pueden apoyar en **evidencia**: algo que se vio en la trayectoria
  o una lección de la biblioteca. Si no la hay, responden `KEEP_BASE`.
- El compositor decide mirando **cómo se comportó** el agente: ¿verificó?, ¿tuvo que corregir?
  ¿una sonda hizo bien de entrada lo que otra tuvo que arreglar?
- Cada tarea **vuelve a empezar desde H₀**: no se hereda el harness, solo crece la biblioteca.
- Los **tests ocultos** solo aparecen en el informe final.

## Ejecutar

Requiere Python 3.9 o superior.

**Modo simulado** (sin llave ni costo):

```bash
python main.py                    # las 3 tareas
python main.py --pasos 2          # modo secuencial: 2 rondas por tarea
python main.py --sin-biblioteca   # experimento: los editores no usan lo aprendido
```

El ejecutor simulado es un modelo de juguete que **obedece al harness**: si las reglas traen la pista
de su dominio ("normaliza" en texto, "casos borde" en números), escribe la versión cuidadosa; si
dicen "verifica", verifica. Así se ve que, con el mismo modelo, cambiar el harness cambia el resultado.

**Modo Claude** (Claude real como ejecutor y como editor):

1. `pip install anthropic`
2. Copia `.env.example` como `.env` en esta carpeta (`copy` en Windows, `cp` en Mac/Linux).
3. Pega tu llave en `ANTHROPIC_API_KEY=`.
4. `python main.py --claude`

Por defecto el ejecutor es `claude-haiku-5-5` y el editor `claude-sonnet-5-5`, como en los
experimentos principales de Harness², donde un modelo potente edita el harness de otros. (El paper
también muestra que el mismo modelo puede mejorar su propio harness.) Con Claude real los resultados
varían de una corrida a otra, y si el ejecutor ya resuelve bien la tarea con el harness base, habrá
poco que mejorar. El archivo `.env` nunca se sube: está en `.gitignore`.

## Qué se simplificó respecto del Harness² real

| Harness² real | Este ejemplo |
|---|---|
| 8 componentes editables (prompt, guardarraíles, memoria, guía de herramientas, subagentes, skills, scripts, plugins) | 2 (prompt de sistema y guardarraíles) |
| Ejecutores OpenCode / Codex | Ejecutor propio (simulado o Claude) |
| Benchmarks profesionales (WorkBuddy-Bench, JobBench, LAB) | 3 tareas pequeñas |
| Modo paralelo (k referencias, k candidatos de cada tipo) o secuencial | Solo secuencial, con `--pasos` |
| La biblioteca guarda el harness adoptado + `EXPERIENCE.md` | Igual, en `runs/biblioteca/` (más un `lecciones.json`) |
| Editores, compositor y reflector siempre con un LLM | Reglas fijas (simulado) o Claude (`--claude`) |

Todo lo que ocurre queda en `runs/`: el harness y la trayectoria de cada ejecución, y la biblioteca
en `runs/biblioteca/` (`INDEX.md`, `lecciones.json` y una carpeta por tarea).
