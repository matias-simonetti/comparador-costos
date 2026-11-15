"""La demo web: datos en JSON al día, mismos números que la medición y API de solo lectura."""
import sys
from pathlib import Path

import pytest

from comparador import demo

RAIZ = Path(__file__).resolve().parent.parent


def test_demo_json_al_dia_con_los_excel():
    """demo.json tiene que salir exactamente de los Excel del set; si no, la demo mostraría otra cosa."""
    sys.path.insert(0, str(RAIZ / "datos"))
    from exportar_json import exportar, texto
    assert demo.DATOS.read_text(encoding="utf-8") == texto(exportar())


def test_mismos_numeros_que_la_medicion():
    from benchmark import cargar, evaluar_motor
    from comparador import cruzar
    internos, lectura, verdad = cargar(RAIZ / "datos" / "demo")
    b = evaluar_motor(cruzar(internos, lectura.items), verdad)
    r = demo.resultado()["resumen"]
    assert (r["confirmados"], r["dudosos"], r["sin_cruce"]) == (b["confirmados"], b["dudosos"], b["sin_cruce"])
    assert r["por_codigo"] == b["por_codigo"]
    assert r["control"].get("erroneo", 0) == b["confirmados_erroneos"] == 0
    assert r["control"].get("perdido", 0) == b["sin_cruce_perdidos"]
    assert r["control"].get("sugerencia_correcta", 0) == b["dudosos_sugerencia_correcta"]
    assert r["control"].get("sin_par", 0) == b["dudosos_sin_par_real"]


def _confirmados(zona, descuentos=""):
    return {i["codigo"]: i for i in demo.resultado(zona, descuentos)["items"] if i["estado"] == "confirmado"}


def test_flete_por_tonelada_con_el_peso_real():
    sin = _confirmados("sin-flete")
    con = _confirmados("cordillera")
    pesos = {i.codigo: i.peso_kg for i in demo.cargar().internos}
    tarifa = demo.cargar().zonas["cordillera"]["tarifa_tn"]
    for cod in list(sin)[:20]:
        assert con[cod]["costo"]["flete"] == pytest.approx(tarifa * pesos[cod] / 1000, abs=0.01)
        assert con[cod]["costo"]["nuevo"] == pytest.approx(sin[cod]["costo"]["nuevo"] + con[cod]["costo"]["flete"], abs=0.02)


def test_descuentos_extra_en_cascada():
    sin = _confirmados("sin-flete")
    con = _confirmados("sin-flete", "10 + 10")
    for cod in list(sin)[:20]:
        assert con[cod]["costo"]["nuevo"] == pytest.approx(sin[cod]["costo"]["nuevo"] * 0.81, abs=0.02)


def test_un_descuento_fijo_que_deja_el_precio_negativo_avisa_en_ese_articulo():
    r = demo.resultado("sin-flete", "$5000")
    errores = [i for i in r["items"] if "error" in i.get("costo", {})]
    assert errores and all("negativo" in i["costo"]["error"] for i in errores)
    assert r["resumen"]["costos"]["con_error"] == len(errores)


@pytest.mark.parametrize("zona, descuentos", [
    ("marte", ""),          # zona que no existe
    (None, "diez"),         # descuento que no se entiende
    (None, "150"),          # más de 100 %
    (None, "1 + " * 20),    # demasiado largo
    (None, "1+1+1+1+1+1+1"),  # demasiados pasos
])
def test_parametros_que_no_sirven(zona, descuentos):
    with pytest.raises(ValueError):
        demo.resultado(zona, descuentos)


def test_api_de_solo_lectura():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from comparador.api import router
    app = FastAPI()
    app.include_router(router)
    c = TestClient(app)
    assert [z["id"] for z in c.get("/zonas").json()["zonas"]] == ["sin-flete", "cordillera", "valle"]
    r = c.get("/resultado", params={"zona": "valle", "descuentos": "10 + $150"})
    assert r.status_code == 200
    assert r.json()["parametros"] == {"zona": {"id": "valle", "nombre": "Valle", "tarifa_tn": 62000.0},
                                      "descuentos": "10% + $150"}
    malo = c.get("/resultado", params={"zona": "marte"})
    assert malo.status_code == 422 and "marte" in malo.json()["detail"]
    assert c.post("/resultado").status_code == 405
