"""Comparador de costos de proveedores.

Cruza la lista interna de un corralón con la lista de precios de un proveedor
y calcula la variación del costo neto puesto en depósito.
"""
from .costos import Costo, Descuento, Flete, calcular_costo, leer_descuentos, variacion_pct
from .cruce import CONFIRMADO, DUDOSO, SIN_CRUCE, Config, Cruce, Cruzador, ItemInterno, ItemProveedor, cruzar
from .precios import leer_precio

__all__ = [
    "Costo", "Descuento", "Flete", "calcular_costo", "leer_descuentos", "variacion_pct",
    "CONFIRMADO", "DUDOSO", "SIN_CRUCE", "Config", "Cruce", "Cruzador",
    "ItemInterno", "ItemProveedor", "cruzar", "leer_precio",
]
