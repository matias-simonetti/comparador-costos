"""Corre el comparador completo y deja el resultado en un CSV.

Uso:
    python comparar.py                                  # set de demostración
    python comparar.py --flete por_tonelada --valor 85000
    python comparar.py --descuentos "10 + 10 + $150"
    python comparar.py --interna a.xlsx --proveedor b.xlsx --bonificaciones c.xlsx
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from comparador import CONFIRMADO, Flete, calcular_costo, cruzar, leer_descuentos, variacion_pct
from comparador.costos import MODOS_FLETE
from comparador.lectura import leer_bonificaciones, leer_lista_interna, leer_lista_proveedor

DEMO = Path(__file__).parent / "datos" / "demo"


def comparar(interna, proveedor, bonificaciones=None, flete=Flete(), descuentos_extra=()):
    internos = leer_lista_interna(interna)
    lectura = leer_lista_proveedor(proveedor)
    bonif = leer_bonificaciones(bonificaciones) if bonificaciones else {}
    filas = []
    for c in cruzar(internos, lectura.items):
        fila = dict(cod_interno=c.interno.codigo, descripcion=c.interno.descripcion, estado=c.estado,
                    motivo=c.motivo, puntaje=c.puntaje, costo_actual=c.interno.costo)
        if c.proveedor is not None:
            p = c.proveedor
            fila.update(cod_proveedor=p.codigo, descripcion_proveedor=p.descripcion, hoja=p.hoja, fila_excel=p.fila)
            base = bonif.get(p.codigo, 0)
            descuentos = ([base] if base else []) + list(descuentos_extra)
            try:
                costo = calcular_costo(p.precio_lista, descuentos, flete, c.interno.peso_kg)
            except ValueError as e:
                fila["error_costo"] = str(e)
            else:
                var = variacion_pct(c.interno.costo, costo.final)
                fila.update(precio_lista=round(p.precio_lista, 2), bonificaciones=" + ".join(str(d) if not isinstance(d, (int, float)) else f"{d:g}%" for d in descuentos),
                            flete_unitario=round(costo.flete_unitario, 2), costo_nuevo=round(costo.final, 2),
                            variacion_pesos=round(costo.final - c.interno.costo, 2),
                            variacion_pct=None if var is None else round(var, 2))
        filas.append(fila)
    return filas, lectura


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--interna", default=DEMO / "lista_interna.xlsx")
    ap.add_argument("--proveedor", default=DEMO / "lista_proveedor.xlsx")
    ap.add_argument("--bonificaciones", default=DEMO / "bonificaciones.xlsx")
    ap.add_argument("--flete", choices=MODOS_FLETE, default="sin_flete")
    ap.add_argument("--valor", type=float, default=0.0, help="valor del flete ($ o %%)")
    ap.add_argument("--descuentos", default="",
                    help='descuentos extra en orden, separados por "+": número = %%, con $ = fijo por unidad (ej: "10 + 10 + $150")')
    ap.add_argument("--salida", default="resultado.csv")
    a = ap.parse_args()

    extra = leer_descuentos(a.descuentos)
    filas, lectura = comparar(a.interna, a.proveedor, a.bonificaciones, Flete(a.flete, a.valor), extra)

    campos = ["cod_interno", "descripcion", "estado", "motivo", "puntaje", "cod_proveedor", "descripcion_proveedor",
              "hoja", "fila_excel", "costo_actual", "precio_lista", "bonificaciones", "flete_unitario",
              "costo_nuevo", "variacion_pesos", "variacion_pct", "error_costo"]
    with open(a.salida, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        w.writeheader()
        w.writerows(filas)

    estados = Counter(f["estado"] for f in filas)
    conf = [f for f in filas if f["estado"] == CONFIRMADO and f.get("variacion_pct") is not None]
    suben = sum(1 for f in conf if f["variacion_pct"] > 0.005)
    bajan = sum(1 for f in conf if f["variacion_pct"] < -0.005)
    print(f"Proveedor: {len(lectura.items)} artículos leídos, hojas ignoradas {lectura.hojas_ignoradas}")
    print(f"Confirmados: {estados['confirmado']}  |  A revisar: {estados['dudoso']}  |  Sin cruce: {estados['sin_cruce']}")
    print(f"De los confirmados: {suben} suben, {bajan} bajan, {len(conf) - suben - bajan} sin cambio")
    print(f"Detalle en {a.salida}")
