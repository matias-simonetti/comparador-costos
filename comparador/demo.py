"""La demo: el motor corriendo sobre el set ficticio, lista para una API web.

Los Excel del set se pasan una sola vez a datos/demo/demo.json
(datos/exportar_json.py). Desde ahí todo corre con la biblioteca estándar de
Python, sin pandas ni Excel, que es lo que necesita un servidor web liviano.

El cruce se calcula una sola vez y queda en memoria. Lo que cambia en cada
consulta (flete y descuentos extra) es solo aritmética sobre los confirmados.
"""
from __future__ import annotations

import json
import unicodedata
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .costos import POR_TONELADA, Descuento, Flete, calcular_costo, leer_descuentos, variacion_pct
from .cruce import CONFIRMADO, DUDOSO, SIN_CRUCE, Cruce, ItemInterno, ItemProveedor, cruzar

DATOS = Path(__file__).resolve().parent.parent / "datos" / "demo" / "demo.json"
SIN_FLETE = "sin-flete"
MAX_DESCUENTOS = 60   # caracteres: es una demo, no un campo libre
MAX_PASOS = 6


@dataclass(frozen=True)
class Escenario:
    internos: tuple
    proveedor: tuple
    bonificaciones: dict
    zonas: dict           # id -> {"id", "nombre", "tarifa_tn"}
    verdad: dict          # código interno -> código del proveedor ("" si no lo tiene)
    lectura: dict


def _id_zona(nombre: str) -> str:
    plano = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower()
    return "-".join(plano.split()) or "zona"


@lru_cache(maxsize=4)
def cargar(ruta: str = str(DATOS)) -> Escenario:
    d = json.loads(Path(ruta).read_text(encoding="utf-8"))
    zonas = {}
    for z in d.get("fletes", []):
        zid = _id_zona(z["zona"])
        zonas[zid] = {"id": zid, "nombre": z["zona"], "tarifa_tn": float(z["tarifa_tn"])}
    return Escenario(
        internos=tuple(ItemInterno(**i) for i in d["internos"]),
        proveedor=tuple(ItemProveedor(**p) for p in d["proveedor"]),
        bonificaciones={k: float(v) for k, v in d.get("bonificaciones", {}).items()},
        zonas=zonas,
        verdad=dict(d.get("verdad", {})),
        lectura=dict(d.get("lectura", {})),
    )


@lru_cache(maxsize=4)
def cruces(ruta: str = str(DATOS)) -> tuple:
    e = cargar(ruta)
    return tuple(cruzar(list(e.internos), list(e.proveedor)))


def zonas(ruta: str = str(DATOS)) -> list[dict]:
    """Opciones de flete: sin flete y las zonas de la hoja FLETES del proveedor."""
    return [{"id": SIN_FLETE, "nombre": "Sin flete", "tarifa_tn": 0.0}, *cargar(ruta).zonas.values()]


def _flete(e: Escenario, zona: str | None) -> tuple[Flete, dict]:
    if not zona:
        zona = next(iter(e.zonas), SIN_FLETE)   # por defecto, la primera zona del proveedor
    if zona == SIN_FLETE:
        return Flete(), {"id": SIN_FLETE, "nombre": "Sin flete", "tarifa_tn": 0.0}
    z = e.zonas.get(zona)
    if z is None:
        raise ValueError(f"No conozco la zona {zona!r}. Opciones: {', '.join([SIN_FLETE, *e.zonas])}")
    return Flete(POR_TONELADA, z["tarifa_tn"]), z


def _descuentos(texto: str) -> list[Descuento]:
    texto = (texto or "").strip()
    if len(texto) > MAX_DESCUENTOS:
        raise ValueError(f"Los descuentos extra no pueden pasar de {MAX_DESCUENTOS} caracteres")
    pasos = leer_descuentos(texto)
    if len(pasos) > MAX_PASOS:
        raise ValueError(f"Como máximo {MAX_PASOS} descuentos extra")
    return pasos


def _control(c: Cruce, real: str) -> str:
    """Qué tan bien decidió el motor este artículo, contra la respuesta conocida del set."""
    if c.estado == CONFIRMADO:
        return "correcto" if c.proveedor.codigo == real else "erroneo"
    if c.estado == DUDOSO:
        if not real:
            return "sin_par"
        if c.proveedor.codigo == real:
            return "sugerencia_correcta"
        if any(p.codigo == real for p, _ in c.alternativas):
            return "en_alternativas"
        return "no_sugerido"
    return "perdido" if real else "bien_descartado"


def _proveedor(p: ItemProveedor) -> dict:
    return {"codigo": p.codigo, "descripcion": p.descripcion, "precio_lista": round(p.precio_lista, 2),
            "hoja": p.hoja, "fila": p.fila}


def _costo(c: Cruce, e: Escenario, flete: Flete, extra: list[Descuento]) -> tuple[dict, str | None]:
    """Costo nuevo de un confirmado y si sube, baja o queda igual."""
    i, p = c.interno, c.proveedor
    base = e.bonificaciones.get(p.codigo, 0.0)
    pasos = ([Descuento(base)] if base else []) + extra
    try:
        costo = calcular_costo(p.precio_lista, pasos, flete, i.peso_kg)
    except ValueError as err:
        return {"actual": round(i.costo, 2), "error": str(err)}, None
    var = variacion_pct(i.costo, costo.final)
    tendencia = None if var is None else "suben" if var > 0.005 else "bajan" if var < -0.005 else "igual"
    return {
        "actual": round(i.costo, 2),
        "lista": round(costo.precio_lista, 2),
        "descuentos": " + ".join(str(d) for d in pasos),
        "neto": round(costo.neto, 2),
        "flete": round(costo.flete_unitario, 2),
        "nuevo": round(costo.final, 2),
        "variacion_pct": None if var is None else round(var, 2),
    }, tendencia


def resultado(zona: str | None = None, descuentos: str = "", ruta: str = str(DATOS)) -> dict:
    """Corre la demo con un flete y descuentos extra.

    Lanza ValueError con un mensaje para mostrar si los parámetros no sirven.
    """
    e = cargar(ruta)
    flete, z = _flete(e, zona)
    extra = _descuentos(descuentos)

    items, estados, controles, costos = [], Counter(), Counter(), Counter()
    for c in cruces(ruta):
        real = e.verdad.get(c.interno.codigo, "")
        control = _control(c, real)
        estados[c.estado] += 1
        controles[control] += 1
        item = {
            "codigo": c.interno.codigo,
            "descripcion": c.interno.descripcion,
            "estado": c.estado,
            "metodo": c.metodo,
            "puntaje": c.puntaje,
            "motivo": c.motivo,
            "control": control,
            "proveedor": _proveedor(c.proveedor) if c.proveedor is not None else None,
            # La primera alternativa es la sugerida; acá van las otras.
            "alternativas": ([{**_proveedor(p), "puntaje": s} for p, s in c.alternativas[1:]]
                             if c.estado == DUDOSO else []),
        }
        if c.estado == CONFIRMADO:
            item["costo"], tendencia = _costo(c, e, flete, extra)
            costos[tendencia or "con_error"] += 1
        items.append(item)

    return {
        "parametros": {"zona": z, "descuentos": " + ".join(str(d) for d in extra)},
        "resumen": {
            "internos": len(e.internos),
            "proveedor": len(e.proveedor),
            "lectura": e.lectura,
            "confirmados": estados[CONFIRMADO],
            "por_codigo": sum(1 for c in cruces(ruta) if c.estado == CONFIRMADO and c.metodo == "codigo"),
            "dudosos": estados[DUDOSO],
            "sin_cruce": estados[SIN_CRUCE],
            "control": dict(controles),
            "costos": {k: costos[k] for k in ("suben", "bajan", "igual", "con_error")},
        },
        "items": items,
    }
