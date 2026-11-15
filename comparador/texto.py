"""Normalización de descripciones de materiales.

Idea central: en un corralón, los NÚMEROS de una descripción son identidad.
"Cemento x 25 kg" y "Cemento x 50 kg" se parecen en un 95 % como texto y son
dos productos distintos. Por eso separamos cada descripción en palabras,
números y medidas (número + unidad), y cada parte se compara con su regla.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

# unidad escrita -> unidad canónica
UNIDADES = {
    "kg": "kg", "kgs": "kg", "kilo": "kg", "kilos": "kg",
    "mm2": "mm2", "mm": "mm", "cm": "cm",
    "m2": "m2", "m3": "m3", "m": "m", "mt": "m", "mts": "m", "metros": "m",
    "l": "l", "lt": "l", "lts": "l", "litro": "l", "litros": "l",
    "ml": "ml", "cc": "ml",
    "pulg": "pulg", "pulgadas": "pulg",
    "grados": "grados",
    "un": "un", "u": "un", "unidades": "un",
}

# Jerga del rubro: palabras distintas para lo mismo.
SINONIMOS = {
    "barra": "hierro", "acero": "hierro", "nervado": "aletado",
    "tubo": "cano", "desague": "cloacal",
    "sinusoidal": "acanalada",
    "pegamento": "adhesivo", "ceramicos": "ceramico", "ceramica": "ceramico",
    "porcellanato": "porcelanato",
    "bco": "blanco", "clavos": "clavo", "tornillos": "tornillo",
    "terciado": "fenolico", "electrosoldada": "sima",
    "poliestireno": "telgopor", "impregnante": "protector",
    "placas": "placa", "juntas": "junta",
}

VACIAS = {"de", "del", "para", "por", "la", "el", "en", "y", "a", "al", "tipo", "x"}

_NUM = r"\d+(?:\.\d+)?"
# Una dimensión arranca en un número "suelto": en "C25 x 4 m" el 25 es un
# calibre pegado a su letra, no el primer lado de una medida.
_RE_DIM = re.compile(rf"(?<![a-z\d.]){_NUM}(?:\s*x\s*{_NUM})+")
_UNIDADES_RE = "|".join(sorted(map(re.escape, UNIDADES), key=len, reverse=True))
_RE_MEDIDA = re.compile(rf"(\d+/\d+|{_NUM})\s*({_UNIDADES_RE})\b")
_RE_FRACCION = re.compile(r"\d+/\d+")
_RE_TOKEN = re.compile(r"[a-z]+|\d+(?:\.\d+)?")


@dataclass(frozen=True)
class Texto:
    original: str
    palabras: frozenset
    numeros: frozenset     # todos los valores numéricos, como texto canónico
    medidas: frozenset     # pares (unidad, valor)
    dimensiones: frozenset  # tuplas ordenadas de números tipo 8x18x33

    @property
    def tokens(self) -> frozenset:
        return self.palabras | {f"#{n}" for n in self.numeros}


def _canon(numero: str) -> str:
    return numero if "/" in numero else f"{float(numero):g}"


def _sin_acentos(txt: str) -> str:
    txt = txt.replace("ñ", "n").replace("Ñ", "n")
    return "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")


def normalizar(descripcion, sinonimos=None) -> Texto:
    """Convierte una descripción en palabras, números, medidas y dimensiones.

    `sinonimos` permite reemplazar el diccionario de jerga (pasar {} lo apaga).
    """
    if sinonimos is None:
        sinonimos = SINONIMOS
    original = "" if descripcion is None else str(descripcion)
    t = _sin_acentos(original.lower())
    t = t.replace("²", "2").replace("³", "3").replace("ø", " ")
    t = re.sub(r"\bc/", " con ", t)                 # c/aluminio -> con aluminio
    t = re.sub(r"\bs/", " sin ", t)                 # s/aluminio -> sin aluminio
    t = re.sub(r"\bp/", " ", t)
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)           # 2,60 -> 2.60
    t = re.sub(r"(\d)\s*(?:''|\"|”|“)", r"\1 pulg ", t)
    t = re.sub(r"(\d)\s*[°º]", r"\1 grados ", t)
    t = re.sub(r"\bn\s*[°º]\s*(?=\d)", " ", t)      # nº 16 -> 16
    t = re.sub(r"[°º]", " ", t)

    numeros, medidas, dims = set(), set(), set()

    def _dim(m):
        partes = tuple(sorted(_canon(p) for p in re.findall(_NUM, m.group(0))))
        dims.add(partes)
        numeros.update(partes)
        return " "

    t = _RE_DIM.sub(_dim, t)

    def _medida(m):
        valor, unidad = _canon(m.group(1)), UNIDADES[m.group(2)]
        medidas.add((unidad, valor))
        numeros.add(valor)
        return " "

    t = _RE_MEDIDA.sub(_medida, t)

    def _fraccion(m):
        numeros.add(m.group(0))
        return " "

    t = _RE_FRACCION.sub(_fraccion, t)

    palabras = set()
    for tok in _RE_TOKEN.findall(t):                # "adn420" -> "adn" + "420"
        if tok[0].isdigit():
            numeros.add(_canon(tok))
            continue
        tok = sinonimos.get(tok, tok)
        if len(tok) > 1 and tok not in VACIAS and tok not in UNIDADES:
            palabras.add(tok)

    return Texto(original, frozenset(palabras), frozenset(numeros), frozenset(medidas), frozenset(dims))


def medidas_en_conflicto(a: Texto, b: Texto) -> bool:
    """True si las dos descripciones declaran datos incompatibles.

    - Misma unidad con valores que no coinciden (25 kg vs 50 kg). Se acepta
      que una descripción dé un dato más que la otra (1.6 mm vs 140 mm y 1.6 mm).
    - Dimensiones que no coinciden (8x18x33 vs 12x18x33), con la misma
      tolerancia (80x50x15 vs 80x50x15x2).
    - Una dice "con" y la otra "sin" (c/aluminio vs s/aluminio).
    """
    if ("con" in a.palabras and "sin" in b.palabras) or ("sin" in a.palabras and "con" in b.palabras):
        return True
    ua, ub = {}, {}
    for u, v in a.medidas:
        ua.setdefault(u, set()).add(v)
    for u, v in b.medidas:
        ub.setdefault(u, set()).add(v)
    for u in ua.keys() & ub.keys():
        if not (ua[u] <= ub[u] or ub[u] <= ua[u]):
            return True
    if a.dimensiones and b.dimensiones:
        menos, mas = sorted((a.dimensiones, b.dimensiones), key=len)
        for d in menos:
            if not any(_dim_compatible(d, otra) for otra in mas):
                return True
    return False


def _dim_compatible(d1: tuple, d2: tuple) -> bool:
    c1, c2 = Counter(d1), Counter(d2)
    return not (c1 - c2) or not (c2 - c1)


def numeros_compatibles(a: Texto, b: Texto) -> bool:
    """Los números de una descripción están contenidos en los de la otra."""
    return a.numeros <= b.numeros or b.numeros <= a.numeros
