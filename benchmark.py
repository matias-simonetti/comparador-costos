"""Mide el cruce contra las respuestas conocidas del set ficticio.

Compara dos métodos sobre los mismos datos:

- ORIGINAL: el de la primera versión de la herramienta. Código exacto y, si no,
  el artículo con mayor similitud de texto (difflib) por encima de un umbral.
- MOTOR: el de este repositorio (comparador/cruce.py).

Uso:
    python benchmark.py                 # set de demostración
    python benchmark.py datos/ajuste    # otro set
"""
from __future__ import annotations

import csv
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path

from comparador import CONFIRMADO, DUDOSO, SIN_CRUCE, Config, Cruzador
from comparador.lectura import leer_lista_interna, leer_lista_proveedor


def cargar(carpeta: Path):
    internos = leer_lista_interna(carpeta / "lista_interna.xlsx")
    lectura = leer_lista_proveedor(carpeta / "lista_proveedor.xlsx")
    with open(carpeta / "verdad.csv", encoding="utf-8") as f:
        verdad = {r["cod_interno"]: r["cod_proveedor"] for r in csv.DictReader(f)}
    return internos, lectura, verdad


def metodo_original(internos, proveedores, umbral=70.0):
    """Réplica fiel de la lógica de cruce de la primera versión."""
    por_codigo = {p.codigo: p for p in proveedores}
    res = {}
    for it in internos:
        match = por_codigo.get(it.cod_proveedor) if it.cod_proveedor else None
        if match is None:
            mejor = 0.0
            for p in proveedores:
                s = SequenceMatcher(None, it.descripcion.lower().strip(), p.descripcion.lower().strip()).ratio() * 100
                if s > mejor and s >= umbral:
                    mejor, match = s, p
        res[it.codigo] = match.codigo if match else ""
    return res


def evaluar_original(pred, verdad):
    ok = sum(1 for k, v in verdad.items() if pred[k] == v)
    mal_cruzado = sum(1 for k, v in verdad.items() if pred[k] and pred[k] != v)
    perdido = sum(1 for k, v in verdad.items() if not pred[k] and v)
    return dict(total=len(verdad), correctos=ok, cruces_erroneos=mal_cruzado, cruces_perdidos=perdido)


def evaluar_motor(cruces, verdad):
    r = dict(total=len(cruces), confirmados=0, confirmados_erroneos=0, por_codigo=0,
             dudosos=0, dudosos_sugerencia_correcta=0, dudosos_correcta_entre_alternativas=0,
             dudosos_sin_par_real=0, sin_cruce=0, sin_cruce_correctos=0, sin_cruce_perdidos=0)
    for c in cruces:
        real = verdad[c.interno.codigo]
        if c.estado == CONFIRMADO:
            r["confirmados"] += 1
            r["por_codigo"] += c.metodo == "codigo"
            r["confirmados_erroneos"] += c.proveedor.codigo != real
        elif c.estado == DUDOSO:
            r["dudosos"] += 1
            r["dudosos_sugerencia_correcta"] += c.proveedor.codigo == real
            r["dudosos_correcta_entre_alternativas"] += any(p.codigo == real for p, _ in c.alternativas)
            r["dudosos_sin_par_real"] += not real
        else:
            r["sin_cruce"] += 1
            r["sin_cruce_correctos"] += not real
            r["sin_cruce_perdidos"] += bool(real)
    return r


def medir(carpeta: Path, config: Config = Config(), repeticiones=5):
    internos, lectura, verdad = cargar(carpeta)
    proveedores = lectura.items

    t = time.perf_counter()
    pred = metodo_original(internos, proveedores)
    t_original = time.perf_counter() - t

    tiempos = []
    for _ in range(repeticiones):
        t = time.perf_counter()
        cruces = Cruzador(proveedores, config).cruzar(internos)
        tiempos.append(time.perf_counter() - t)

    return dict(internos=len(internos), proveedor=len(proveedores),
                hojas_ignoradas=lectura.hojas_ignoradas, filas_descartadas=lectura.filas_descartadas,
                original=evaluar_original(pred, verdad), t_original=t_original,
                motor=evaluar_motor(cruces, verdad), t_motor=min(tiempos), cruces=cruces, verdad=verdad)


def imprimir(m):
    o, r = m["original"], m["motor"]
    print(f"Artículos internos: {m['internos']}  |  Artículos del proveedor leídos: {m['proveedor']}")
    print(f"Hojas ignoradas: {m['hojas_ignoradas']}  |  Filas descartadas: {m['filas_descartadas']}\n")
    print("MÉTODO ORIGINAL (similitud de texto, umbral 70)")
    print(f"  Decisiones correctas : {o['correctos']}/{o['total']} ({o['correctos'] / o['total']:.1%})")
    print(f"  Cruces ERRÓNEOS      : {o['cruces_erroneos']}  (se cargan sin aviso)")
    print(f"  Cruces perdidos      : {o['cruces_perdidos']}")
    print(f"  Tiempo               : {m['t_original']:.2f} s\n")
    print("MOTOR NUEVO")
    print(f"  Confirmados solos    : {r['confirmados']}  (por código: {r['por_codigo']})")
    print(f"    de ellos erróneos  : {r['confirmados_erroneos']}")
    print(f"  A revisión (dudosos) : {r['dudosos']}")
    print(f"    sugerencia correcta: {r['dudosos_sugerencia_correcta']}")
    print(f"    correcta entre las alternativas: {r['dudosos_correcta_entre_alternativas']}")
    print(f"    el proveedor no lo tiene: {r['dudosos_sin_par_real']}")
    print(f"  Sin cruce            : {r['sin_cruce']}")
    print(f"    correctos          : {r['sin_cruce_correctos']}")
    print(f"    perdidos           : {r['sin_cruce_perdidos']}")
    print(f"  Tiempo               : {m['t_motor']:.2f} s")


if __name__ == "__main__":
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "datos" / "demo"
    imprimir(medir(carpeta))
