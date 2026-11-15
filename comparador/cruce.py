"""Cruce entre la lista interna y la lista del proveedor.

Cada artículo interno termina en uno de tres estados:

- CONFIRMADO: el cruce es lo bastante claro como para usarlo sin mirar.
- DUDOSO: hay un candidato razonable pero una persona tiene que confirmarlo.
- SIN_CRUCE: el proveedor no parece tener ese artículo.

El objetivo no es cruzar la mayor cantidad posible, sino no cruzar MAL sin
avisar: un cruce equivocado es un costo mal cargado que nadie revisa.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache

from .texto import Texto, medidas_en_conflicto, normalizar, numeros_compatibles

CONFIRMADO, DUDOSO, SIN_CRUCE = "confirmado", "dudoso", "sin_cruce"


@dataclass(frozen=True)
class ItemInterno:
    codigo: str
    descripcion: str
    costo: float
    peso_kg: float | None = None
    cod_proveedor: str = ""      # equivalencia ya cargada en el sistema, si existe


@dataclass(frozen=True)
class ItemProveedor:
    codigo: str
    descripcion: str
    precio_lista: float
    hoja: str = ""
    fila: int = 0                # fila del Excel, para poder ir a mirar


@dataclass(frozen=True)
class Config:
    umbral_confirmado: float = 0.70   # puntaje mínimo para confirmar solo
    margen_minimo: float = 0.08       # ventaja mínima sobre el segundo candidato
    umbral_dudoso: float = 0.40       # por debajo, ni se sugiere
    max_alternativas: int = 3
    sinonimos: dict | None = None     # None = diccionario de jerga por defecto


@dataclass
class Cruce:
    interno: ItemInterno
    estado: str
    proveedor: ItemProveedor | None = None
    puntaje: float = 0.0
    metodo: str = ""                  # "codigo" o "descripcion"
    motivo: str = ""
    alternativas: list = field(default_factory=list)   # [(ItemProveedor, puntaje)]


@lru_cache(maxsize=200_000)
def _similitud_palabra(a: str, b: str) -> float:
    if a == b:
        return 1.0
    corta, larga = sorted((a, b), key=len)
    if len(corta) >= 3 and larga.startswith(corta):       # galv ~ galvanizada
        return 0.9
    if len(corta) >= 5:                                   # errores de tipeo
        r = SequenceMatcher(None, a, b).ratio()
        if r >= 0.84:
            return r
    return 0.0


class Cruzador:
    """Prepara la lista del proveedor una vez y cruza artículos contra ella."""

    def __init__(self, proveedores: list[ItemProveedor], config: Config = Config()):
        self.config = config
        self.proveedores = proveedores
        self._textos = [normalizar(p.descripcion, config.sinonimos) for p in proveedores]
        self._por_codigo = {p.codigo: p for p in proveedores if p.codigo}

        # Peso de cada token: los raros identifican más que los comunes.
        frecuencia = Counter(tok for t in self._textos for tok in t.tokens)
        n = max(len(proveedores), 1)
        self._idf = {tok: math.log(1 + n / f) for tok, f in frecuencia.items()}
        self._idf_max = math.log(1 + n)

        # Índice para no comparar todo contra todo.
        self._indice = defaultdict(set)
        for i, t in enumerate(self._textos):
            for clave in self._claves(t):
                self._indice[clave].add(i)

    @staticmethod
    def _claves(t: Texto):
        return {p[:3] for p in t.palabras}

    def _peso(self, token: str) -> float:
        return self._idf.get(token, self._idf_max)

    def comparar(self, a: Texto, b: Texto) -> tuple[float, set, set]:
        """Devuelve (puntaje 0-1, palabras de `a` sin par, palabras de `b` sin par)."""
        if not a.tokens or not b.tokens:
            return 0.0, set(a.palabras), set(b.palabras)
        peso_a = sum(self._peso(t) for t in a.tokens)
        peso_b = sum(self._peso(t) for t in b.tokens)
        comun = sum(self._peso(f"#{n}") for n in a.numeros & b.numeros)
        libres, sobran_a = set(b.palabras), set()
        for pa in sorted(a.palabras):
            mejor, sim = None, 0.0
            for pb in sorted(libres):
                s = _similitud_palabra(pa, pb)
                if s > sim:
                    mejor, sim = pb, s
            if mejor:
                libres.discard(mejor)
                comun += sim * (self._peso(pa) + self._peso(mejor)) / 2
            else:
                sobran_a.add(pa)
        return min(1.0, 2 * comun / (peso_a + peso_b)), sobran_a, libres

    def puntaje(self, a: Texto, b: Texto) -> float:
        """Similitud 0-1 entre dos descripciones normalizadas."""
        return self.comparar(a, b)[0]

    def candidatos(self, texto: Texto) -> list[tuple[int, float]]:
        """Candidatos del proveedor ordenados de mayor a menor puntaje."""
        idx = set()
        for clave in self._claves(texto):
            idx |= self._indice.get(clave, set())
        res = []
        for i in idx:
            t = self._textos[i]
            if medidas_en_conflicto(texto, t):
                continue
            s = self.puntaje(texto, t)
            if s >= self.config.umbral_dudoso:
                res.append((i, s))
        res.sort(key=lambda x: (-x[1], x[0]))
        return res

    def cruzar_uno(self, item: ItemInterno) -> Cruce:
        cfg = self.config
        if item.cod_proveedor:
            p = self._por_codigo.get(item.cod_proveedor)
            if p is not None:
                return Cruce(item, CONFIRMADO, p, 1.0, "codigo", "equivalencia de código cargada")

        texto = normalizar(item.descripcion, cfg.sinonimos)
        cands = self.candidatos(texto)
        if not cands:
            return Cruce(item, SIN_CRUCE, motivo="sin candidatos compatibles en la lista del proveedor")

        alternativas = [(self.proveedores[i], round(s, 3)) for i, s in cands[:cfg.max_alternativas]]
        i, mejor = cands[0]
        segundo = cands[1][1] if len(cands) > 1 else 0.0
        cruce = Cruce(item, DUDOSO, self.proveedores[i], round(mejor, 3), "descripcion", alternativas=alternativas)

        _, sobran_int, sobran_prov = self.comparar(texto, self._textos[i])
        if mejor < cfg.umbral_confirmado:
            cruce.motivo = f"puntaje bajo ({mejor:.2f})"
        elif mejor - segundo < cfg.margen_minimo:
            cruce.motivo = f"hay otro candidato casi igual ({segundo:.2f})"
        elif not numeros_compatibles(texto, self._textos[i]):
            cruce.motivo = "los números de las dos descripciones no coinciden"
        elif sobran_int and sobran_prov:
            # Una palabra distinta de cada lado suele ser otra variante del
            # mismo producto: otra marca, otro color, interior/exterior.
            cruce.motivo = ("posible variante distinta: "
                            f"{', '.join(sorted(sobran_int))} / {', '.join(sorted(sobran_prov))}")
        else:
            cruce.estado, cruce.motivo = CONFIRMADO, "descripción y medidas coinciden"
        return cruce

    def cruzar(self, internos: list[ItemInterno]) -> list[Cruce]:
        cruces = [self.cruzar_uno(it) for it in internos]
        # Un artículo del proveedor no puede quedar confirmado para dos internos.
        usos = defaultdict(list)
        for c in cruces:
            if c.estado == CONFIRMADO:
                usos[id(c.proveedor)].append(c)
        for repetidos in usos.values():
            if len(repetidos) < 2:
                continue
            repetidos.sort(key=lambda c: (c.metodo != "codigo", -c.puntaje))
            ganador, segundo = repetidos[0], repetidos[1]
            claro = ganador.metodo == "codigo" or ganador.puntaje - segundo.puntaje >= self.config.margen_minimo
            for c in repetidos[0 if not claro else 1:]:
                if c.metodo != "codigo":
                    c.estado = DUDOSO
                    c.motivo = "el mismo artículo del proveedor quedó asignado a más de un artículo interno"
        return cruces


def cruzar(internos, proveedores, config: Config = Config()) -> list[Cruce]:
    return Cruzador(proveedores, config).cruzar(internos)
