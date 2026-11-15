import pytest

from comparador import CONFIRMADO, DUDOSO, SIN_CRUCE, ItemInterno, ItemProveedor, cruzar
from comparador.texto import medidas_en_conflicto, normalizar


def prov(*descripciones):
    return [ItemProveedor(f"P{i}", d, 1000.0) for i, d in enumerate(descripciones, start=1)]


def uno(descripcion, proveedores, cod_proveedor=""):
    return cruzar([ItemInterno("1", descripcion, 1000.0, cod_proveedor=cod_proveedor)], proveedores)[0]


# --- normalización ---------------------------------------------------------

def test_medidas_escritas_distinto_son_la_misma():
    a, b = normalizar("CAÑO PVC 110MM X 4M"), normalizar("Caño PVC ø 110 mm - tira 4 mts")
    assert a.medidas == b.medidas == {("mm", "110"), ("m", "4")}


def test_coma_decimal_y_pulgadas():
    t = normalizar('Clavo 2,5" x 1 kg')
    assert ("pulg", "2.5") in t.medidas and ("kg", "1") in t.medidas


def test_calibre_pegado_a_la_letra_no_es_una_dimension():
    assert normalizar("CHAPA C25 X 4M").dimensiones == frozenset()
    assert normalizar("LADRILLO 8X18X33").dimensiones == {("18", "33", "8")}


@pytest.mark.parametrize("a, b", [
    ("CEMENTO X 25KG", "Cemento bolsa 50 kg"),
    ("LADRILLO HUECO 8X18X33", "Ladrillo hueco 12x18x33"),
    ("MALLA SIMA 15X15 5MM", "Malla sima 15x25 5 mm"),
    ("LANA VIDRIO 50MM C/ALUMINIO", "Lana de vidrio 50 mm sin aluminio"),
])
def test_conflictos(a, b):
    assert medidas_en_conflicto(normalizar(a), normalizar(b))


@pytest.mark.parametrize("a, b", [
    ("PERFIL C 80X50X15 2MM X 12M", "Perfil C galvanizado 80x50x15x2 - barra 12 m"),
    ("PERFIL C 140X50X15 1.6MM X 12M", "Perfil estructural C 140 mm esp. 1.6 mm x 12 mts"),
    ("CODO PVC 110MM 90°", "Codo 90 grados PVC ø 110"),
])
def test_un_dato_de_mas_no_es_conflicto(a, b):
    assert not medidas_en_conflicto(normalizar(a), normalizar(b))


# --- cruce -----------------------------------------------------------------

def test_cruza_el_mismo_producto_escrito_distinto():
    lista = prov("Barra acero aletado ADN 420 ø 8 mm - 12 mts", "Barra acero aletado ADN 420 ø 10 mm - 12 mts")
    c = uno("HIERRO ADN420 8MM X 12M", lista)
    assert c.estado == CONFIRMADO and c.proveedor.codigo == "P1"


def test_no_cruza_otra_medida_aunque_el_texto_sea_casi_igual():
    # El caso que la similitud de texto resuelve mal: 25 kg contra 50 kg.
    c = uno("CEMENTO PORTLAND PATAGON X 25KG", prov("Cemento Pórtland Patagon - bolsa 50 kg"))
    assert c.estado == SIN_CRUCE


def test_otra_marca_va_a_revision_no_se_confirma():
    c = uno("ADHESIVO CERAMICO COMUN ANDINA X 30KG", prov("Pegamento cerámico común Lago 30 kg"))
    assert c.estado == DUDOSO and "variante" in c.motivo


def test_dos_candidatos_parejos_van_a_revision():
    lista = prov("Cable unipolar 2,5 mm² rojo - rollo 100 m", "Cable unipolar 2,5 mm² azul - rollo 100 m")
    c = uno("CABLE UNIPOLAR 2.5MM2 X 100M", lista)
    assert c.estado == DUDOSO and len(c.alternativas) == 2


def test_la_equivalencia_de_codigo_manda():
    lista = prov("Cualquier descripción", "HIERRO ADN420 8MM X 12M")
    c = uno("HIERRO ADN420 8MM X 12M", lista, cod_proveedor="P1")
    assert c.estado == CONFIRMADO and c.metodo == "codigo" and c.proveedor.codigo == "P1"


def test_tolera_abreviaturas_y_errores_de_tipeo():
    c = uno("CHAPA ACANALADA GALV C25 X 4M", prov("Chapa acanlaada galvanizada C25 x 4 mts"))
    assert c.estado == CONFIRMADO


def test_un_articulo_del_proveedor_no_queda_confirmado_dos_veces():
    lista = prov("Pastina gris 1 kg")
    internos = [ItemInterno("1", "PASTINA GRIS X 1KG", 100.0), ItemInterno("2", "PASTINA GRIS 1KG", 100.0)]
    cruces = cruzar(internos, lista)
    assert [c.estado for c in cruces].count(CONFIRMADO) < 2


def test_lista_vacia():
    assert uno("CEMENTO X 50KG", []).estado == SIN_CRUCE
