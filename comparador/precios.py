"""Lectura de precios escritos "a la argentina".

Las listas de proveedores mezclan números reales con textos como "$ 1.234,56".
Sacarle las comas a ciegas (lo que hacía la primera versión) convierte
"1.234,56" en 1.23456: un error de tres órdenes de magnitud que no avisa.
"""
from __future__ import annotations

import math
import re

_SOLO_NUMERO = re.compile(r"^-?[\d.,]+$")


def leer_precio(valor) -> float | None:
    """Devuelve el precio como float, o None si no se puede interpretar.

    Reglas (formato argentino por defecto):
    - Con punto y coma: el que aparece último es el separador decimal.
    - Solo coma: es decimal ("1234,5").
    - Solo punto: si hay varios, o hay exactamente tres dígitos después,
      es separador de miles ("1.234" = 1234). Si no, es decimal ("12.5").
    """
    if valor is None:
        return None
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return None if (isinstance(valor, float) and math.isnan(valor)) else float(valor)

    txt = str(valor).strip().replace("$", "").replace(" ", "").replace(" ", "")
    if not txt or not _SOLO_NUMERO.match(txt) or not any(c.isdigit() for c in txt):
        return None

    tiene_punto, tiene_coma = "." in txt, "," in txt
    if tiene_punto and tiene_coma:
        if txt.rfind(",") > txt.rfind("."):          # 1.234,56
            txt = txt.replace(".", "").replace(",", ".")
        else:                                        # 1,234.56
            txt = txt.replace(",", "")
    elif tiene_coma:
        if txt.count(",") > 1:
            return None
        txt = txt.replace(",", ".")
    elif tiene_punto:
        ultimo = txt.rsplit(".", 1)[1]
        if txt.count(".") > 1 or len(ultimo) == 3:
            txt = txt.replace(".", "")
    try:
        return float(txt)
    except ValueError:
        return None
