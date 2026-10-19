"""
tareas.py — Las tareas que verá el agente, una detrás de otra ("mundo abierto").

Cada tarea tiene DOS juegos de casos, y esa separación es clave en Harness²:
  - ejemplos:       vienen en el enunciado; el agente los puede usar para verificarse.
  - tests_ocultos:  solo los usa el JUEZ al final, para el informe.
                    Ninguna fase de mejora (proponer, probar, componer, reflexionar) los ve.

El dominio dice qué lecciones de la biblioteca le sirven al editor DOM:
las de "texto" sirven para el anagrama, pero no para los números primos.
"""
from dataclasses import dataclass


@dataclass
class Tarea:
    id: str
    dominio: str
    enunciado: str
    archivo: str
    funcion: str
    ejemplos: list
    tests_ocultos: list


TAREAS = [
    Tarea(
        id="palindromo",
        dominio="texto",
        enunciado=("Crea es_palindromo(texto) en palindromo.py: devuelve True si el texto es un "
                   "palíndromo. Ejemplos: es_palindromo('Anita lava la tina') -> True; "
                   "es_palindromo('hola') -> False."),
        archivo="palindromo.py",
        funcion="es_palindromo",
        ejemplos=[(("Anita lava la tina",), True), (("hola",), False)],
        tests_ocultos=[(("radar",), True), (("hola",), False), (("Anita lava la tina",), True),
                       (("A man, a plan, a canal: Panama",), True), (("",), True)],
    ),
    Tarea(
        id="anagrama",
        dominio="texto",
        enunciado=("Crea es_anagrama(a, b) en anagrama.py: devuelve True si a y b usan exactamente "
                   "las mismas letras. Ejemplos: es_anagrama('Roma', 'amor') -> True; "
                   "es_anagrama('hola', 'adios') -> False."),
        archivo="anagrama.py",
        funcion="es_anagrama",
        ejemplos=[(("Roma", "amor"), True), (("hola", "adios"), False)],
        tests_ocultos=[(("Roma", "amor"), True), (("hola", "adios"), False),
                       (("listen", "silent"), True), (("Dormitory", "Dirty room"), True)],
    ),
    Tarea(
        id="primo",
        dominio="numeros",
        enunciado=("Crea es_primo(n) en primo.py: devuelve True si el número entero n es primo. "
                   "Ejemplos: es_primo(7) -> True; es_primo(1) -> False."),
        archivo="primo.py",
        funcion="es_primo",
        ejemplos=[((7,), True), ((1,), False)],
        tests_ocultos=[((2,), True), ((7,), True), ((9,), False), ((1,), False),
                       ((0,), False), ((-7,), False)],
    ),
]
