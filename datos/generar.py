"""Genera el set de datos FICTICIO del comparador.

Todo lo que sale de acá es inventado: "Corralón Los Coihues" y "Distribuidora
Andina de Materiales" no existen, y los precios no corresponden a ninguna lista
real. La gracia del set es que conocemos de antemano qué artículo interno
corresponde a cuál del proveedor (archivo verdad.csv), así que podemos medir
el acierto del cruce en vez de suponerlo.

Uso:
    python datos/generar.py --semilla 42 --salida datos/demo
"""
from __future__ import annotations

import argparse
import csv
import itertools
import random
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Catálogo: cada familia describe el MISMO producto escrito de dos maneras,
# como lo carga el corralón en su sistema y como lo publica el proveedor.
# ---------------------------------------------------------------------------


def F(hoja, interno, prov, ejes, base, talla=None, peso=1.0):
    return dict(hoja=hoja, interno=interno, prov=prov, ejes=ejes, base=base, talla=talla, peso=peso)


MARCAS_CEM = ["LOMA ANDINA", "PATAGON", "CORDILLERA"]
MARCAS_2 = ["ANDINA", "LAGO"]

FAMILIAS = [
    # --- Cementos y cales ---
    F("CEMENTOS Y CALES", "CEMENTO PORTLAND {marca} X {kg}KG",
      ["Cemento Pórtland CPC40 {marca} - bolsa {kg} kg", "Cem. Portland {marca} bolsa x {kg} kg"],
      dict(marca=MARCAS_CEM, kg=[25, 50]), 4200, "kg", "kg"),
    F("CEMENTOS Y CALES", "CEMENTO ALBAÑILERIA {marca} X 40KG",
      ["Cemento de albañilería {marca} - bolsa 40 kg", "Cem. albañilería {marca} x 40 kg"],
      dict(marca=MARCAS_CEM[:2]), 5100, None, 40),
    F("CEMENTOS Y CALES", "CAL HIDRATADA {marca} X {kg}KG",
      ["Cal hidratada {marca} - bolsa {kg} kg", "Cal aérea hidratada {marca} x {kg} kilos"],
      dict(marca=MARCAS_2, kg=[25, 30]), 3300, "kg", "kg"),
    F("CEMENTOS Y CALES", "REVOQUE {tipo} {marca} X 25KG",
      ["Revoque {tipo} premezclado {marca} - bolsa 25 kg", "Mortero revoque {tipo} {marca} 25 kg"],
      dict(tipo=["FINO", "GRUESO"], marca=MARCAS_2), 3900, None, 25),
    F("CEMENTOS Y CALES", "YESO PARIS X {kg}KG",
      ["Yeso París - bolsa {kg} kg", "Yeso tipo París x {kg} kg"],
      dict(kg=[1, 40]), 900, "kg", "kg"),
    F("CEMENTOS Y CALES", "ADHESIVO CERAMICO {tipo} {marca} X 30KG",
      ["Adhesivo para cerámicos {tipo} {marca} - bolsa 30 kg", "Pegamento cerámico {tipo} {marca} 30 kg"],
      dict(tipo=["IMPERMEABLE", "PORCELLANATO", "COMUN"], marca=MARCAS_2), 6800, None, 30),
    F("CEMENTOS Y CALES", "PASTINA {color} X {kg}KG",
      ["Pastina para juntas {color} {kg} kg", "Pastina {color} bolsa x {kg} kg"],
      dict(color=["GRIS", "BLANCA", "BEIGE", "NEGRA"], kg=[1, 5]), 1500, "kg", "kg"),
    F("CEMENTOS Y CALES", "HIDROFUGO {marca} X {kg}KG",
      ["Hidrófugo en pasta {marca} - {kg} kg", "Hidrófugo {marca} balde x {kg} kilos"],
      dict(marca=MARCAS_2, kg=[1, 4, 10, 20]), 2100, "kg", "kg"),
    # --- Hierros y mallas ---
    F("HIERROS", "HIERRO ADN420 {d}MM X 12M",
      ["Barra acero aletado ADN 420 ø {d} mm - 12 mts", "Hierro construcción nervado {d} mm x 12 m ADN420"],
      dict(d=[6, 8, 10, 12, 16, 20, 25]), 5200, "d", 8),
    F("HIERROS", "MALLA SIMA {cuadro} {d}MM 2X5M",
      ["Malla electrosoldada {cuadro} cm - alambre {d} mm - paño 2 x 5 m", "Malla sima {cuadro} / {d} mm (2x5)"],
      dict(cuadro=["15X15", "15X25"], d=[4, 5, 6]), 21000, "d", 18),
    F("HIERROS", "ALAMBRE {tipo} N{n} X {kg}KG",
      ["Alambre {tipo} nº {n} - rollo {kg} kg", "Alambre {tipo} N°{n} x {kg} kg"],
      dict(tipo=["NEGRO RECOCIDO", "GALVANIZADO"], n=[14, 16], kg=[1, 25]), 3100, "kg", "kg"),
    F("HIERROS", "PERFIL C {h}X50X15 {e}MM X 12M",
      ["Perfil C galvanizado {h}x50x15x{e} - barra 12 m", "Perfil estructural C {h} mm esp. {e} mm x 12 mts"],
      dict(h=[80, 100, 120, 140, 160], e=[1.6, 2, 2.5]), 38000, "h", 35),
    F("HIERROS", "CLAVO PUNTA PARIS {p}\" X {kg}KG",
      ["Clavos punta París {p} pulg. - caja {kg} kg", "Clavo P.P. {p}\" x {kg} kg"],
      dict(p=[1.5, 2, 2.5, 3, 4], kg=[1, 5]), 3400, "kg", "kg"),
    # --- Ladrillos y premoldeados ---
    F("LADRILLOS", "LADRILLO HUECO {a}X18X33",
      ["Ladrillo cerámico hueco {a}x18x33 cm", "Lad. hueco {a} x 18 x 33 - 9 tubos"],
      dict(a=[8, 12, 18]), 420, "a", 4),
    F("LADRILLOS", "BLOQUE HORMIGON {a}X20X40",
      ["Bloque de hormigón {a}x20x40 cm", "Bloque cemento {a} x 20 x 40 liso"],
      dict(a=[10, 13, 15, 20]), 780, "a", 12),
    F("LADRILLOS", "VIGUETA PRETENSADA {l}M",
      ["Vigueta pretensada largo {l} m", "Vigueta de hormigón pretensado {l} mts"],
      dict(l=[3.0, 3.4, 3.8, 4.2, 4.6, 5.0]), 14500, "l", 60),
    F("LADRILLOS", "{arido} BOLSON X 1M3",
      ["{arido} - bolsón 1 m3", "Bolsón {arido} x 1 m³"],
      dict(arido=["ARENA FINA", "ARENA GRUESA", "PIEDRA PARTIDA", "RIPIO"]), 42000, None, 1500),
    F("LADRILLOS", "{arido} BOLSA X 25KG",
      ["{arido} - bolsa 25 kg", "{arido} embolsada x 25 kilos"],
      dict(arido=["ARENA FINA", "ARENA GRUESA", "PIEDRA PARTIDA", "RIPIO"]), 1300, None, 25),
    # --- Sanitarios ---
    F("SANITARIOS", "CAÑO PVC {d}MM X 4M {tipo}",
      ["Caño PVC cloacal {tipo} ø{d} mm - tira 4 m", "Tubo PVC desagüe {d} mm x 4 mts {tipo}"],
      dict(d=[40, 50, 63, 110, 160], tipo=["LIVIANO", "REFORZADO"]), 5600, "d", 5),
    F("SANITARIOS", "CODO PVC {d}MM {g}°",
      ["Codo PVC cloacal {d} mm a {g}°", "Codo {g} grados PVC ø {d}"],
      dict(d=[40, 50, 63, 110], g=[45, 90]), 650, "d", 0.3),
    F("SANITARIOS", "CAÑO TERMOFUSION {d}MM X 4M",
      ["Caño PPR termofusión agua {d} mm - tira 4 m", "Tubo termofusión {d}mm x 4 mts"],
      dict(d=[20, 25, 32]), 7200, "d", 1.2),
    F("SANITARIOS", "CODO TERMOFUSION {d}MM 90°",
      ["Codo PPR termofusión {d} mm a 90°", "Codo 90 grados termofusión ø {d}"],
      dict(d=[20, 25, 32]), 480, "d", 0.1),
    F("SANITARIOS", "CAÑO EPOXI GAS {d}\" X 6.40M",
      ["Caño epoxi para gas {d} pulg. - tira 6,40 m", "Caño gas revestido epoxi {d}\" x 6.40 mts"],
      dict(d=["1/2", "3/4", "1"]), 31000, None, 9),
    F("SANITARIOS", "CODO EPOXI GAS {d}\" 90°",
      ["Codo epoxi para gas {d} pulg. a 90°", "Codo gas epoxi 90 grados {d}\""],
      dict(d=["1/2", "3/4", "1"]), 2400, None, 0.3),
    F("SANITARIOS", "TANQUE AGUA {capa} X {l}L",
      ["Tanque de agua {capa} {l} litros", "Tanque polietileno {capa} {l} lts"],
      dict(capa=["BICAPA", "TRICAPA"], l=[500, 750, 1000, 1100]), 98000, "l", 20),
    # --- Chapas y zinguería ---
    F("CHAPAS", "CHAPA ACANALADA {tipo} C{c} X {l}M",
      ["Chapa sinusoidal {tipo} calibre {c} - largo {l} m", "Chapa acanalada {tipo} C{c} x {l} mts"],
      dict(tipo=["GALVANIZADA", "CINCALUM"], c=[25, 27], l=[3, 3.5, 4, 4.5, 5, 6]), 9800, "l", 18),
    F("CHAPAS", "CUMBRERA {tipo} C25 X {l}M",
      ["Cumbrera {tipo} calibre 25 - largo {l} m", "Cumbrera lisa {tipo} C25 x {l} mts"],
      dict(tipo=["GALVANIZADA", "CINCALUM"], l=[2, 3]), 8700, "l", 6),
    F("CHAPAS", "TORNILLO AUTOPERFORANTE 14X{l}\" {ar} X 100U",
      ["Tornillo autoperforante hexagonal 14 x {l} pulg. {ar} - caja 100 un.", "Autoperforante hex. 14x{l}\" {ar} x100"],
      dict(l=[1, 1.5, 2, 2.5, 3], ar=["C/ARANDELA", "S/ARANDELA"]), 7400, "l", 1),
    # --- Pinturas ---
    F("PINTURAS", "LATEX {uso} {marca} X {l}L {color}",
      ["Látex {uso} {color} {marca} - balde {l} lts", "Pintura látex {uso} {marca} {l} L {color} mate"],
      dict(uso=["INTERIOR", "EXTERIOR"], marca=MARCAS_2, l=[4, 10, 20], color=["BLANCO", "MARFIL"]), 5200, "l", 6),
    F("PINTURAS", "ESMALTE SINTETICO {color} X {l}L",
      ["Esmalte sintético brillante {color} {l} lt", "Esm. sint. {color} x {l} litros"],
      dict(color=["BLANCO", "NEGRO", "GRIS"], l=[1, 4]), 7900, "l", 1.2),
    F("PINTURAS", "MEMBRANA LIQUIDA {color} X {kg}KG",
      ["Membrana líquida impermeabilizante {color} - balde {kg} kg", "Imperm. techos membrana en pasta {color} {kg} kg"],
      dict(color=["BLANCO", "ROJO"], kg=[5, 10, 20]), 6100, "kg", "kg"),
    F("PINTURAS", "PROTECTOR MADERA {color} X {l}L",
      ["Protector para madera {color} {l} lt", "Impregnante madera {color} x {l} litros"],
      dict(color=["NATURAL", "CEDRO", "NOGAL", "ROBLE"], l=[1, 4]), 9200, "l", 1.1),
    F("PINTURAS", "ENDUIDO PLASTICO {uso} X {kg}KG",
      ["Enduido plástico {uso} {kg} kg", "Enduido {uso} listo para usar x {kg} kilos"],
      dict(uso=["INTERIOR", "EXTERIOR"], kg=[1, 4, 10, 25]), 2300, "kg", "kg"),
    F("PINTURAS", "FIJADOR SELLADOR X {l}L",
      ["Fijador sellador al agua {l} lts", "Sellador fijador concentrado x {l} L"],
      dict(l=[1, 4, 10, 20]), 4100, "l", 1.1),
    F("PINTURAS", "SELLADOR SILICONA {tipo} {color} X 280ML",
      ["Sellador de silicona {tipo} {color} - cartucho 280 ml", "Silicona {tipo} {color} 280ml"],
      dict(tipo=["ACETICA", "NEUTRA"], color=["TRANSPARENTE", "BLANCO", "NEGRO"]), 5300, None, 0.35),
    F("PINTURAS", "ESPUMA POLIURETANO X {ml}ML",
      ["Espuma de poliuretano expandible {ml} ml", "Espuma PU aerosol x {ml}ml"],
      dict(ml=[300, 500, 750]), 6900, "ml", 0.6),
    # --- Techos y aislaciones ---
    F("AISLACIONES", "MEMBRANA ASFALTICA {term} {kg}KG X 10M2",
      ["Membrana asfáltica c/{term} {kg} kg - rollo 10 m2", "Memb. asfáltica {term} rollo 10m2 {kg}kg"],
      dict(term=["ALUMINIO", "GEOTEXTIL"], kg=[35, 40]), 52000, "kg", "kg"),
    F("AISLACIONES", "LANA VIDRIO {e}MM {rev}",
      ["Lana de vidrio {e} mm {rev} - rollo", "Aislante lana vidrio esp. {e}mm {rev}"],
      dict(e=[50, 80, 100], rev=["C/ALUMINIO", "S/ALUMINIO"]), 46000, "e", 12),
    F("AISLACIONES", "TELGOPOR PLACA {e}MM D{dens} 1X1M",
      ["Placa poliestireno expandido {e} mm densidad {dens} - 1 x 1 m", "Telgopor placa {e}mm dens. {dens} (1x1)"],
      dict(e=[10, 20, 30, 50], dens=[15, 20]), 1900, "e", 0.5),
    F("AISLACIONES", "FIELTRO ASFALTICO N{n} X 40M2",
      ["Fieltro asfáltico nº {n} - rollo 40 m2", "Fieltro N°{n} rollo x 40m2"],
      dict(n=[15, 20]), 27000, "n", 15),
    F("AISLACIONES", "POLIETILENO NEGRO {mic} MICRONES X 50M",
      ["Film polietileno negro {mic} micrones - rollo 50 m", "Polietileno negro {mic} mic. x 50 mts"],
      dict(mic=[100, 150, 200]), 58000, "mic", 20),
    # --- Construcción en seco ---
    F("SECO", "PLACA YESO {tipo} {e}MM 1.20X2.40",
      ["Placa de yeso {tipo} {e} mm - 1,20 x 2,40 m", "Placa cartón-yeso {tipo} esp. {e}mm 120x240 cm"],
      dict(tipo=["ESTANDAR", "RESISTENTE HUMEDAD"], e=[9.5, 12.5]), 11800, "e", 25),
    F("SECO", "{pieza} {a}MM X 2.60M",
      ["{pieza} galvanizado {a} mm - tira 2,60 m", "Perfil {pieza} {a}mm x 2.60 mts"],
      dict(pieza=["MONTANTE", "SOLERA"], a=[35, 70]), 3600, "a", 1.5),
    F("SECO", "MASILLA PLACA YESO X {kg}KG",
      ["Masilla para placas de yeso lista para usar - balde {kg} kg", "Masilla placa yeso x {kg} kilos"],
      dict(kg=[7, 15, 32]), 5800, "kg", "kg"),
    F("SECO", "TORNILLO T{t} PUNTA {punta} X {n}U",
      ["Tornillo drywall T{t} punta {punta} - caja x {n} un.", "Tornillos T{t} p/{punta} x{n}"],
      dict(t=[1, 2], punta=["AGUJA", "MECHA"], n=[100, 500]), 2600, "n", 0.5),
    F("SECO", "CINTA {tipo} PLACA YESO X {m}M",
      ["Cinta de {tipo} para juntas de placa de yeso - rollo {m} m", "Cinta {tipo} juntas x {m} mts"],
      dict(tipo=["PAPEL", "MALLA"], m=[23, 75, 150]), 1800, "m", 0.3),
    # --- Maderas ---
    F("MADERAS", "TIRANTE PINO {sec}\" X {l}M",
      ["Tirante pino cepillado {sec} pulg. - largo {l} m", "Pino elliotis tirante {sec} x {l} mts"],
      dict(sec=["2X4", "2X6", "3X6"], l=[3.05, 3.66, 4.27]), 8900, "l", 12),
    F("MADERAS", "FENOLICO {e}MM 1.22X2.44",
      ["Terciado fenólico {e} mm - placa 1,22 x 2,44 m", "Fenólico pino {e}mm 1.22x2.44"],
      dict(e=[9, 12, 15, 18]), 24000, "e", 22),
    F("MADERAS", "OSB {e}MM 1.22X2.44",
      ["Tablero OSB {e} mm 1,22 x 2,44", "Placa OSB estructural {e}mm (1.22x2.44)"],
      dict(e=[9, 11, 15, 18]), 17500, "e", 20),
    F("MADERAS", "MACHIMBRE PINO {e}\" X {l}M",
      ["Machimbre de pino {e} pulg. - largo {l} m", "Machimbre pino {e}\" x {l} mts"],
      dict(e=["1/2", "3/4"], l=[3.05, 3.66]), 3900, "l", 3),
    F("MADERAS", "PUERTA PLACA {a}CM {mano}",
      ["Puerta placa cedro {a} cm mano {mano}", "Puerta placa {a} {mano} con marco"],
      dict(a=[70, 80], mano=["DERECHA", "IZQUIERDA"]), 86000, "a", 22),
    # --- Electricidad ---
    F("ELECTRICIDAD", "CABLE UNIPOLAR {s}MM2 {color} X 100M",
      ["Cable unipolar {s} mm² {color} - rollo 100 m", "Cable unip. {s}mm2 {color} x 100 mts"],
      dict(s=[1.5, 2.5, 4, 6], color=["ROJO", "AZUL", "VERDE", "NEGRO", "MARRON"]), 39000, "s", 3),
    F("ELECTRICIDAD", "CAÑO CORRUGADO {d}\" X 25M",
      ["Caño corrugado PVC {d} pulg. - rollo 25 m", "Corrugado ignífugo {d}\" x 25 mts"],
      dict(d=["3/4", "7/8", "1"]), 7800, None, 2),
    # --- Pisos ---
    F("PISOS", "CERAMICA PISO {m} {color} {cal}",
      ["Cerámico piso {m} cm {color} - {cal} calidad - caja", "Piso cerámico {color} {m} {cal}"],
      dict(m=["30X30", "45X45", "60X60"], color=["GRIS", "BEIGE", "MARRON"], cal=["1RA", "2DA"]), 9400, None, 22),
    F("PISOS", "PORCELANATO {m} {term} {color}",
      ["Porcelanato {term} {color} {m} cm - caja", "Porcellanato {m} {color} {term} rectificado"],
      dict(m=["60X60", "80X80"], term=["PULIDO", "MATE"], color=["GRIS", "BEIGE"]), 21000, None, 28),
    # --- Herramientas ---
    F("HERRAMIENTAS", "DISCO {tipo} {d}MM",
      ["Disco {tipo} ø {d} mm", "Disco de {tipo} {d}mm"],
      dict(tipo=["CORTE METAL", "DIAMANTADO"], d=[115, 180, 230]), 2900, "d", 0.2),
    F("HERRAMIENTAS", "PALA {tipo}",
      ["Pala {tipo} cabo de madera", "Pala {tipo} forjada"],
      dict(tipo=["ANCHA", "PUNTA", "CORAZON"]), 23000, None, 2),
    F("HERRAMIENTAS", "BALDE ALBAÑIL X {l}L",
      ["Balde de albañil plástico {l} lts", "Balde albañil reforzado x {l} L"],
      dict(l=[8, 10]), 3200, "l", 0.5),
]

# Cómo escribe el proveedor algunos valores que el corralón abrevia.
TRADUCCION = {
    "C/ALUMINIO": "con foil de aluminio", "S/ALUMINIO": "sin aluminio",
    "C/ARANDELA": "con arandela", "S/ARANDELA": "sin arandela",
    "ESTANDAR": "estándar", "RESISTENTE HUMEDAD": "resistente a la humedad",
    "1RA": "1ra", "2DA": "2da", "COMUN": "común", "ACETICA": "acética",
    "MARRON": "marrón", "CORAZON": "corazón",
}

# Abreviaturas típicas de un sistema de gestión con campo de descripción corto.
ABREV_INTERNAS = {
    "GALVANIZADA": "GALV", "GALVANIZADO": "GALV", "INTERIOR": "INT", "EXTERIOR": "EXT",
    "IMPERMEABLE": "IMPERM", "SINTETICO": "SINT", "BLANCO": "BCO", "HORMIGON": "H°",
    "REFORZADO": "REF", "TERMOFUSION": "TERMOF", "AUTOPERFORANTE": "AUTOPERF",
}


def num(valor, coma=False):
    if isinstance(valor, float):
        txt = f"{valor:g}"
        return txt.replace(".", ",") if coma else txt
    return str(valor)


def error_de_tipeo(texto, rng):
    """Intercambia dos letras vecinas dentro de una palabra larga."""
    palabras = texto.split(" ")
    candidatas = [i for i, p in enumerate(palabras) if len(p) >= 6 and p.isalpha()]
    if not candidatas:
        return texto
    i = rng.choice(candidatas)
    p = palabras[i]
    k = rng.randrange(1, len(p) - 2)
    palabras[i] = p[:k] + p[k + 1] + p[k] + p[k + 2:]
    return " ".join(palabras)


def construir_catalogo(rng):
    catalogo = []
    for fam in FAMILIAS:
        nombres = list(fam["ejes"])
        for combo in itertools.product(*fam["ejes"].values()):
            v = dict(zip(nombres, combo))
            # --- descripción interna ---
            interno = fam["interno"].format(**{k: num(x) for k, x in v.items()})
            for larga, corta in ABREV_INTERNAS.items():
                if larga in interno and rng.random() < 0.35:
                    interno = interno.replace(larga, corta)
            # --- descripción del proveedor ---
            coma = rng.random() < 0.5
            vp = {}
            for k, x in v.items():
                if isinstance(x, str):
                    vp[k] = TRADUCCION.get(x, x.lower() if not x[0].isdigit() else x.lower())
                    if k == "marca":
                        vp[k] = x.title()
                else:
                    vp[k] = num(x, coma)
            prov = rng.choice(fam["prov"]).format(**vp)
            if rng.random() < 0.06:
                prov = error_de_tipeo(prov, rng)
            # --- precio y peso ---
            factor = 1.0
            if fam["talla"]:
                valores = fam["ejes"][fam["talla"]]
                factor = (v[fam["talla"]] / valores[0]) ** 0.9
            costo = round(fam["base"] * factor * rng.uniform(0.92, 1.08), 2)
            peso = v[fam["peso"]] if isinstance(fam["peso"], str) else fam["peso"]
            catalogo.append(dict(hoja=fam["hoja"], interno=interno, prov=prov, costo=costo, peso=float(peso)))
    return catalogo


def precio_ar(valor):
    """1234.5 -> '$ 1.234,50' (así vienen muchas listas en Argentina)."""
    entero, dec = f"{valor:,.2f}".split(".")
    return f"$ {entero.replace(',', '.')},{dec}"


def generar(semilla: int, salida: Path, n_internos=300, n_comunes=255, n_extras=40):
    rng = random.Random(semilla)
    catalogo = construir_catalogo(rng)
    rng.shuffle(catalogo)
    assert len(catalogo) >= n_internos + n_extras, len(catalogo)

    internos = catalogo[:n_internos]
    comunes = internos[:n_comunes]                        # los vende el proveedor
    extras = catalogo[n_internos:n_internos + n_extras]   # el proveedor los vende, el corralón no los tiene

    for i, it in enumerate(sorted(internos, key=lambda x: x["interno"]), start=1):
        it["cod_interno"] = f"{10000 + i * 7}"
    en_proveedor = comunes + extras
    rng.shuffle(en_proveedor)
    for i, it in enumerate(en_proveedor, start=1):
        it["cod_prov"] = f"DA-{20000 + i * 3}"

    # Precio de lista y bonificación del proveedor.
    bonificaciones = {}
    for it in en_proveedor:
        if rng.random() < 0.25:                # sin cambios respecto del costo actual
            it["bonif"], it["lista"] = 0, it["costo"]
        else:
            it["bonif"] = rng.choice([0, 5, 10, 10, 15, 20])
            variacion = rng.uniform(-0.03, 0.18)
            it["lista"] = round(it["costo"] * (1 + variacion) / (1 - it["bonif"] / 100), 2)
        if it["bonif"]:
            bonificaciones[it["cod_prov"]] = it["bonif"]

    # Equivalencias ya cargadas en el sistema (solo una parte del catálogo).
    for it in comunes:
        it["equiv"] = it["cod_prov"] if rng.random() < 0.30 else ""

    salida.mkdir(parents=True, exist_ok=True)

    # ---- lista interna ----
    df_int = pd.DataFrame([{
        "Cód. Artículo": it["cod_interno"], "Descripción": it["interno"], "Costo": it["costo"],
        "Peso (kg)": it["peso"], "Cód. Proveedor": it.get("equiv", ""),
    } for it in sorted(internos, key=lambda x: x["cod_interno"])])
    df_int.to_excel(salida / "lista_interna.xlsx", index=False)

    # ---- lista del proveedor (desprolija a propósito) ----
    hojas = {}
    for it in en_proveedor:
        hojas.setdefault(it["hoja"], []).append(it)
    estilos = [("Código", "Producto", "Precio Lista"), ("Cod.", "Denominación", "Precio neto s/IVA"),
               ("SKU", "Descripción", "P. Lista ($)")]
    with pd.ExcelWriter(salida / "lista_proveedor.xlsx") as xw:
        pd.DataFrame([["DISTRIBUIDORA ANDINA DE MATERIALES S.A. (empresa ficticia)"],
                      ["Lista de precios N° 114"], ["Precios sin IVA. Sujetos a modificación sin previo aviso."]]
                     ).to_excel(xw, sheet_name="PORTADA", index=False, header=False)
        for n, (hoja, items) in enumerate(sorted(hojas.items())):
            c_cod, c_desc, c_precio = estilos[n % len(estilos)]
            como_texto = n % 2 == 1
            filas = [["DISTRIBUIDORA ANDINA DE MATERIALES S.A.", None, None, None],
                     [f"Rubro: {hoja}", None, None, None]]
            filas += [[None] * 4] * (n % 3)
            filas.append([c_cod, c_desc, "Unidad", c_precio])
            for j, it in enumerate(items):
                if j and j % 11 == 0:
                    filas.append([None, f"--- {hoja} (continuación) ---", None, None])
                if j and j % 17 == 0:
                    filas.append([None] * 4)
                precio = precio_ar(it["lista"]) if como_texto else it["lista"]
                filas.append([it["cod_prov"], it["prov"], "un", precio])
            pd.DataFrame(filas).to_excel(xw, sheet_name=hoja, index=False, header=False)
        pd.DataFrame([["Zona", "Tarifa $/Tn"], ["Cordillera", 85000], ["Valle", 62000]]
                     ).to_excel(xw, sheet_name="FLETES", index=False, header=False)

    # ---- bonificaciones ----
    pd.DataFrame([["Bonificaciones vigentes - cliente Corralón Los Coihues (ficticio)", None], [None, None],
                  ["SKU", "Bonif. %"]] + [[k, v] for k, v in bonificaciones.items()]
                 ).to_excel(salida / "bonificaciones.xlsx", index=False, header=False)

    # ---- verdad ----
    cod_real = {id(it): it["cod_prov"] for it in comunes}
    with open(salida / "verdad.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cod_interno", "cod_proveedor"])
        for it in sorted(internos, key=lambda x: x["cod_interno"]):
            w.writerow([it["cod_interno"], cod_real.get(id(it), "")])

    return dict(catalogo=len(catalogo), internos=len(internos), proveedor=len(en_proveedor),
                comunes=len(comunes), con_equivalencia=sum(1 for it in comunes if it["equiv"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--semilla", type=int, default=42)
    ap.add_argument("--salida", type=Path, default=Path(__file__).parent / "demo")
    a = ap.parse_args()
    print(generar(a.semilla, a.salida))
