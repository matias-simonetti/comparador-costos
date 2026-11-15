"""Pasa el set de demostración de Excel a JSON.

La demo web corre el motor en un servidor liviano, sin pandas ni Excel: lee
datos/demo/demo.json, que sale de acá. Si se regenera el set con
datos/generar.py, hay que volver a correr este script (un test lo controla).

Uso:
    python datos/exportar_json.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from comparador.lectura import leer_bonificaciones, leer_lista_interna, leer_lista_proveedor  # noqa: E402
from comparador.precios import leer_precio  # noqa: E402

DEMO = RAIZ / "datos" / "demo"


def leer_fletes(ruta: Path) -> list[dict]:
    """Tarifas por zona de la hoja FLETES de la lista del proveedor."""
    hojas = pd.read_excel(ruta, sheet_name=None, header=None, dtype=object)
    df = next((d for nombre, d in hojas.items() if str(nombre).strip().upper() == "FLETES"), None)
    if df is None:
        return []
    zonas = []
    for f in range(1, len(df)):  # la fila 0 es el encabezado
        zona, tarifa = df.iloc[f, 0], leer_precio(df.iloc[f, 1])
        if pd.notna(zona) and str(zona).strip() and tarifa:
            zonas.append({"zona": str(zona).strip(), "tarifa_tn": tarifa})
    return zonas


def exportar(carpeta: Path = DEMO) -> dict:
    internos = leer_lista_interna(carpeta / "lista_interna.xlsx")
    lectura = leer_lista_proveedor(carpeta / "lista_proveedor.xlsx")
    with open(carpeta / "verdad.csv", encoding="utf-8") as f:
        verdad = {r["cod_interno"]: r["cod_proveedor"] for r in csv.DictReader(f)}
    return {
        "nota": "Datos ficticios generados por datos/generar.py (semilla 42). "
                "No editar a mano: se regenera con python datos/exportar_json.py.",
        "internos": [dict(codigo=i.codigo, descripcion=i.descripcion, costo=i.costo,
                          peso_kg=i.peso_kg, cod_proveedor=i.cod_proveedor) for i in internos],
        "proveedor": [dict(codigo=p.codigo, descripcion=p.descripcion, precio_lista=p.precio_lista,
                           hoja=p.hoja, fila=p.fila) for p in lectura.items],
        "lectura": {"hojas_ignoradas": lectura.hojas_ignoradas,
                    "filas_descartadas": lectura.filas_descartadas},
        "bonificaciones": leer_bonificaciones(carpeta / "bonificaciones.xlsx"),
        "fletes": leer_fletes(carpeta / "lista_proveedor.xlsx"),
        "verdad": verdad,
    }


def texto(datos: dict) -> str:
    return json.dumps(datos, ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    salida = DEMO / "demo.json"
    salida.write_text(texto(exportar()), encoding="utf-8")
    print(f"Escrito {salida.relative_to(RAIZ)}")
