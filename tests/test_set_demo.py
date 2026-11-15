"""Pruebas de punta a punta sobre el set ficticio.

Fijan el piso de calidad: si un cambio en el motor empieza a confirmar cruces
equivocados, estas pruebas fallan.
"""
from pathlib import Path

import pytest

from benchmark import medir
from comparar import comparar
from comparador import Flete
from comparador.lectura import leer_bonificaciones, leer_lista_interna, leer_lista_proveedor

DEMO = Path(__file__).parent.parent / "datos" / "demo"


@pytest.fixture(scope="module")
def medicion():
    return medir(DEMO, repeticiones=1)


def test_lee_la_lista_desprolija_del_proveedor():
    lectura = leer_lista_proveedor(DEMO / "lista_proveedor.xlsx")
    assert len(lectura.items) == 295
    assert set(lectura.hojas_ignoradas) == {"PORTADA", "FLETES"}
    assert all(p.precio_lista > 0 and p.codigo.startswith("DA-") for p in lectura.items)


def test_lee_lista_interna_y_bonificaciones():
    internos = leer_lista_interna(DEMO / "lista_interna.xlsx")
    assert len(internos) == 300 and all(i.peso_kg for i in internos)
    bonif = leer_bonificaciones(DEMO / "bonificaciones.xlsx")
    assert bonif and set(bonif.values()) <= {5, 10, 15, 20}


def test_ningun_cruce_confirmado_es_erroneo(medicion):
    assert medicion["motor"]["confirmados_erroneos"] == 0


def test_confirma_solo_la_mayoria_de_los_cruces_reales(medicion):
    m = medicion["motor"]
    assert m["confirmados"] >= 200
    assert m["sin_cruce_perdidos"] <= 3


def test_el_metodo_original_cruza_mal_decenas_de_articulos(medicion):
    assert medicion["original"]["cruces_erroneos"] > 30


def test_comparacion_completa_con_flete_por_tonelada():
    filas, _ = comparar(DEMO / "lista_interna.xlsx", DEMO / "lista_proveedor.xlsx",
                        DEMO / "bonificaciones.xlsx", Flete("por_tonelada", 85000))
    assert len(filas) == 300
    conf = [f for f in filas if f["estado"] == "confirmado"]
    assert all("error_costo" not in f and f["costo_nuevo"] > 0 for f in conf)
    # Con peso real, el flete de un bolsón de 1500 kg no es el de una bolsa de 25 kg.
    assert len({f["flete_unitario"] for f in conf}) > 10
