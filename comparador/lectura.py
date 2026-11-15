"""Lectura de los Excel de entrada.

La lista del proveedor casi nunca viene prolija: tiene una portada, títulos
arriba de la tabla, encabezados con nombres distintos en cada hoja, filas en
blanco y precios como texto. Acá se busca la fila de encabezados en cada hoja
y se descarta lo que no es un artículo, dejando registro de lo descartado.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .cruce import ItemInterno, ItemProveedor
from .precios import leer_precio

CLAVES_DESCRIPCION = ("producto", "denominacion", "descripcion", "articulo", "detalle")
CLAVES_PRECIO = ("precio", "p. lista", "lista", "neto", "importe")
CLAVES_CODIGO = ("sku", "codigo", "cod.", "cod")
CLAVES_BONIF = ("bonif", "boni", "descuento", "dto")
MAX_FILAS_ENCABEZADO = 30


def _plano(valor) -> str:
    txt = "" if valor is None or (isinstance(valor, float) and pd.isna(valor)) else str(valor)
    txt = unicodedata.normalize("NFD", txt.strip().lower())
    return "".join(c for c in txt if unicodedata.category(c) != "Mn")


def _buscar_columna(encabezados: list[str], claves) -> int | None:
    for clave in claves:
        for i, h in enumerate(encabezados):
            if h == clave or h.startswith(clave) or f" {clave}" in f" {h}":
                return i
    return None


def _ubicar_encabezado(df: pd.DataFrame, claves_a, claves_b):
    """Devuelve (fila, col_a, col_b) de la primera fila que tiene ambas columnas."""
    for f in range(min(len(df), MAX_FILAS_ENCABEZADO)):
        encabezados = [_plano(v) for v in df.iloc[f].tolist()]
        a, b = _buscar_columna(encabezados, claves_a), _buscar_columna(encabezados, claves_b)
        if a is not None and b is not None and a != b:
            return f, a, b, encabezados
    return None


@dataclass
class LecturaProveedor:
    items: list = field(default_factory=list)
    hojas_ignoradas: list = field(default_factory=list)   # sin tabla de artículos
    filas_descartadas: int = 0                            # títulos, blancos, sin precio


def leer_lista_proveedor(ruta: str | Path) -> LecturaProveedor:
    res = LecturaProveedor()
    for hoja, df in pd.read_excel(ruta, sheet_name=None, header=None, dtype=object).items():
        ubic = _ubicar_encabezado(df, CLAVES_DESCRIPCION, CLAVES_PRECIO)
        if ubic is None:
            res.hojas_ignoradas.append(hoja)
            continue
        f0, c_desc, c_precio, encabezados = ubic
        c_cod = _buscar_columna(encabezados, CLAVES_CODIGO)
        for f in range(f0 + 1, len(df)):
            fila = df.iloc[f]
            desc = fila.iloc[c_desc]
            precio = leer_precio(fila.iloc[c_precio])
            if pd.isna(desc) or not str(desc).strip() or precio is None or precio <= 0:
                res.filas_descartadas += 1
                continue
            cod = "" if c_cod is None or pd.isna(fila.iloc[c_cod]) else str(fila.iloc[c_cod]).strip()
            res.items.append(ItemProveedor(cod, str(desc).strip(), precio, hoja, f + 1))
    return res


def leer_lista_interna(ruta: str | Path) -> list[ItemInterno]:
    df = pd.read_excel(ruta, dtype=object)
    cols = {_plano(c): c for c in df.columns}

    def col(*claves, obligatoria=True):
        i = _buscar_columna(list(cols), claves)
        if i is None:
            if obligatoria:
                raise ValueError(f"La lista interna no tiene una columna de {claves[0]!r}")
            return None
        return cols[list(cols)[i]]

    c_prov = col("cod. proveedor", "codigo proveedor", "sku proveedor", obligatoria=False)
    c_cod = next((cols[k] for k in cols if k.startswith(("cod", "sku")) and cols[k] != c_prov), None)
    if c_cod is None:
        raise ValueError("La lista interna no tiene una columna de código de artículo")
    c_desc, c_costo = col("descripcion"), col("costo", "precio")
    c_peso = col("peso", obligatoria=False)

    items = []
    for _, r in df.iterrows():
        costo = leer_precio(r[c_costo])
        if pd.isna(r[c_desc]) or costo is None or costo <= 0:
            continue
        peso = leer_precio(r[c_peso]) if c_peso is not None else None
        prov = "" if c_prov is None or pd.isna(r[c_prov]) else str(r[c_prov]).strip()
        items.append(ItemInterno(str(r[c_cod]).strip(), str(r[c_desc]).strip(), costo, peso, prov))
    return items


def leer_bonificaciones(ruta: str | Path) -> dict[str, float]:
    """Código del proveedor -> porcentaje de bonificación."""
    bonif = {}
    for _, df in pd.read_excel(ruta, sheet_name=None, header=None, dtype=object).items():
        ubic = _ubicar_encabezado(df, CLAVES_CODIGO, CLAVES_BONIF)
        if ubic is None:
            continue
        f0, c_cod, c_bon, _ = ubic
        for f in range(f0 + 1, len(df)):
            cod, valor = df.iloc[f, c_cod], leer_precio(df.iloc[f, c_bon])
            if pd.notna(cod) and valor is not None:
                bonif[str(cod).strip()] = valor
    return bonif
