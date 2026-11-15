import pytest

from comparador import Descuento, Flete, calcular_costo, leer_descuentos, leer_precio, variacion_pct
from comparador.costos import FIJO_POR_UNIDAD, POR_TONELADA, PORCENTAJE, aplicar_descuentos


@pytest.mark.parametrize("texto, esperado", [
    ("$ 1.234,56", 1234.56),        # formato argentino
    ("1.234.567,8", 1234567.8),
    ("1234,5", 1234.5),
    ("1.234", 1234.0),              # punto de miles, no decimal
    ("12.5", 12.5),
    ("1,234.56", 1234.56),          # formato anglosajón
    (" $27.906,38 ", 27906.38),
    (4200, 4200.0),
    (13124.37, 13124.37),
])
def test_leer_precio(texto, esperado):
    assert leer_precio(texto) == pytest.approx(esperado)


@pytest.mark.parametrize("basura", [None, "", "consultar", "--- continuación ---", float("nan"), "1,2,3"])
def test_leer_precio_devuelve_none_si_no_es_un_precio(basura):
    assert leer_precio(basura) is None


def test_descuentos_en_cascada():
    # 10 % y después 5 % no es 15 %
    assert aplicar_descuentos(1000, [10, 5]) == pytest.approx(855)


def test_descuento_menor_a_uno_es_porcentaje_no_fraccion():
    # La versión original aplicaba 0.5 como 50 %.
    assert aplicar_descuentos(1000, [0.5]) == pytest.approx(995)


def test_descuento_fuera_de_rango():
    with pytest.raises(ValueError):
        aplicar_descuentos(1000, [120])


def test_flete_por_tonelada_usa_el_peso_real():
    flete = Flete(POR_TONELADA, 80000)
    bolsa_50 = calcular_costo(10000, [], flete, peso_kg=50)
    bolsa_25 = calcular_costo(10000, [], flete, peso_kg=25)
    assert bolsa_50.flete_unitario == pytest.approx(4000)
    assert bolsa_25.flete_unitario == pytest.approx(2000)


def test_flete_por_tonelada_sin_peso_es_error():
    with pytest.raises(ValueError, match="peso"):
        calcular_costo(10000, [], Flete(POR_TONELADA, 80000), peso_kg=None)


def test_flete_porcentual_sobre_lista_o_sobre_neto():
    sobre_lista = calcular_costo(1000, [20], Flete(PORCENTAJE, 10))
    sobre_neto = calcular_costo(1000, [20], Flete(PORCENTAJE, 10, base_porcentaje="neto"))
    assert sobre_lista.final == pytest.approx(800 + 100)
    assert sobre_neto.final == pytest.approx(800 + 80)


def test_flete_fijo_y_sin_flete():
    assert calcular_costo(1000, [10], Flete(FIJO_POR_UNIDAD, 150)).final == pytest.approx(1050)
    assert calcular_costo(1000, [10]).final == pytest.approx(900)


def test_variacion():
    assert variacion_pct(1000, 1100) == pytest.approx(10)
    assert variacion_pct(0, 1100) is None


def test_cotizacion_real_10_mas_10():
    # 80 unidades a 13 con 10 % + 10 %: 1040 -> 842,40 (es 19 %, no 20 %)
    assert aplicar_descuentos(1040, leer_descuentos("10 + 10")) == pytest.approx(842.40)


def test_el_orden_del_descuento_fijo_cambia_el_resultado():
    fijo_despues = aplicar_descuentos(1000, leer_descuentos("10 + $50"))
    fijo_antes = aplicar_descuentos(1000, leer_descuentos("$50 + 10"))
    assert fijo_despues == pytest.approx(850)
    assert fijo_antes == pytest.approx(855)


def test_leer_descuentos_acepta_coma_decimal_y_signo_de_porcentaje():
    assert leer_descuentos("11,11% + $ 1.250,50 ; 2") == [
        Descuento(11.11), Descuento(1250.50, "fijo"), Descuento(2.0)]
    assert leer_descuentos("") == []


def test_descuento_fijo_mayor_al_precio_es_error():
    with pytest.raises(ValueError, match="negativo"):
        aplicar_descuentos(100, [Descuento(150, "fijo")])


def test_descuento_ilegible_es_error():
    with pytest.raises(ValueError):
        leer_descuentos("10 + diez")
