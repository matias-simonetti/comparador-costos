"""API web de la demo (FastAPI). Solo lectura: no recibe archivos ni guarda nada.

Rutas, relativas a donde se monte el router:

    GET /zonas                                         opciones de flete
    GET /resultado?zona=cordillera&descuentos=10+%2B+5  el motor con esos parámetros

Así la usa simonetti.uno, montada en /a/proyectos/api/comparador/.
Para probarla sola en tu compu: python servir.py
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from . import demo

router = APIRouter(tags=["demo"])


@router.get("/zonas")
def zonas():
    return {"zonas": demo.zonas()}


@router.get("/resultado")
def resultado(zona: str = "", descuentos: str = ""):
    try:
        return demo.resultado(zona or None, descuentos)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
