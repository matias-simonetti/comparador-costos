"""Cálculo del costo neto puesto en depósito: lista - bonificaciones + flete."""
from __future__ import annotations

from dataclasses import dataclass

from .precios import leer_precio

SIN_FLETE = "sin_flete"
PORCENTAJE = "porcentaje"
POR_TONELADA = "por_tonelada"
FIJO_POR_UNIDAD = "fijo_por_unidad"
MODOS_FLETE = (SIN_FLETE, PORCENTAJE, POR_TONELADA, FIJO_POR_UNIDAD)


@dataclass(frozen=True)
class Flete:
    modo: str = SIN_FLETE
    valor: float = 0.0
    # Sobre qué se calcula el flete porcentual: "lista" (precio de lista, como
    # en la versión original) o "neto" (precio ya bonificado).
    base_porcentaje: str = "lista"

    def __post_init__(self):
        if self.modo not in MODOS_FLETE:
            raise ValueError(f"Modo de flete desconocido: {self.modo!r}")
        if self.valor < 0:
            raise ValueError("El valor del flete no puede ser negativo")
        if self.base_porcentaje not in ("lista", "neto"):
            raise ValueError("base_porcentaje debe ser 'lista' o 'neto'")


@dataclass(frozen=True)
class Costo:
    precio_lista: float
    neto: float            # después de bonificaciones
    flete_unitario: float
    final: float           # neto + flete


@dataclass(frozen=True)
class Descuento:
    """Un paso de descuento: porcentaje sobre lo que va quedando, o monto fijo por unidad."""
    valor: float
    tipo: str = "porcentaje"       # "porcentaje" o "fijo"

    def __post_init__(self):
        if self.tipo not in ("porcentaje", "fijo"):
            raise ValueError(f"Tipo de descuento desconocido: {self.tipo!r}")
        if self.valor < 0 or (self.tipo == "porcentaje" and self.valor > 100):
            raise ValueError(f"Descuento fuera de rango: {self.valor}")

    def __str__(self):
        return f"{self.valor:g}%" if self.tipo == "porcentaje" else f"${self.valor:g}"


def leer_descuentos(texto: str) -> list[Descuento]:
    """Interpreta una cadena de descuentos escrita por una persona.

    "10 + 10 + $150 + 2"  ->  10 %, 10 %, $150 fijo por unidad, 2 %

    Los pasos se separan con "+" o ";". Un número solo es porcentaje; con "$"
    adelante es monto fijo. Se aplican en el orden en que están escritos,
    porque el orden cambia el resultado y lo define cada negociación.
    """
    pasos = []
    for parte in texto.replace(";", "+").split("+"):
        parte = parte.strip().replace("%", "")
        if not parte:
            continue
        fijo = parte.startswith("$")
        valor = leer_precio(parte)
        if valor is None:
            raise ValueError(f"No entiendo el descuento {parte!r}")
        pasos.append(Descuento(valor, "fijo" if fijo else "porcentaje"))
    return pasos


def aplicar_descuentos(precio: float, descuentos) -> float:
    """Aplica los descuentos en cascada, en el orden dado.

    Cada paso es un `Descuento` o un número suelto, que se toma como
    porcentaje: 10 significa 10 %. La versión original trataba los valores
    menores a 1 como fracción (0.5 -> 50 %), con lo cual una bonificación real
    de 0,5 % se aplicaba como 50 %. Acá no hay doble interpretación.
    """
    for d in descuentos:
        if not isinstance(d, Descuento):
            d = Descuento(float(d))
        if d.tipo == "porcentaje":
            precio *= 1 - d.valor / 100
        else:
            precio -= d.valor
            if precio < 0:
                raise ValueError(f"El descuento fijo de ${d.valor:g} deja el precio en negativo")
    return precio


def calcular_costo(precio_lista: float, descuentos_pct=(), flete: Flete = Flete(),
                   peso_kg: float | None = None) -> Costo:
    """Costo final de una unidad.

    Para flete por tonelada hace falta el peso real del artículo. Si falta,
    se lanza un error en vez de asumir 25 kg para todo (el supuesto de la
    versión original, que solo era correcto para bolsas de 25 kg).
    """
    if precio_lista < 0:
        raise ValueError("El precio de lista no puede ser negativo")
    neto = aplicar_descuentos(float(precio_lista), descuentos_pct)

    if flete.modo == SIN_FLETE:
        f = 0.0
    elif flete.modo == PORCENTAJE:
        base = precio_lista if flete.base_porcentaje == "lista" else neto
        f = base * flete.valor / 100
    elif flete.modo == POR_TONELADA:
        if peso_kg is None or peso_kg <= 0:
            raise ValueError("Flete por tonelada: falta el peso del artículo")
        f = flete.valor * peso_kg / 1000
    else:
        f = flete.valor
    return Costo(float(precio_lista), neto, f, neto + f)


def variacion_pct(costo_actual: float, costo_nuevo: float) -> float | None:
    if not costo_actual:
        return None
    return (costo_nuevo - costo_actual) / costo_actual * 100
