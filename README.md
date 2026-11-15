# Comparador de costos de proveedores

Cruza la lista de artículos de un corralón de materiales con la lista de precios
de un proveedor y calcula cuánto cambia el costo neto puesto en depósito
(lista − bonificaciones + flete).

> Todos los datos de este repositorio son ficticios. "Corralón Los Coihues" y
> "Distribuidora Andina de Materiales" no existen y los precios son inventados.

## Cómo se hizo

El código lo escribió Claude (IA de Anthropic) trabajando con Matías Simonetti,
que trajo el problema y el primer prototipo, aportó las reglas del rubro y
definió el alcance. La medición está incluida para que cualquiera la repita.

## El problema

Cuando un proveedor manda una lista nueva, alguien tiene que cruzarla a mano
contra el sistema: el proveedor llama "Barra acero aletado ADN 420 ø 8 mm" a lo
que el corralón tiene cargado como "HIERRO ADN420 8MM X 12M". Son cientos de
renglones, en un Excel con portada, títulos intercalados y precios como texto.

El riesgo no es tardar. Es cruzar mal: "Cemento x 25 kg" y "Cemento x 50 kg" se
parecen en un 95 % como texto, y un cruce equivocado es un costo mal cargado
que nadie revisa.

## Resultado medido

Sobre un set de 300 artículos internos contra 295 del proveedor, donde se conoce
de antemano la respuesta correcta de cada uno (`datos/demo/verdad.csv`):

| | Similitud de texto (primera versión) | Este motor |
|---|---|---|
| Cruces dados por buenos sin revisión | 227 | 219 |
| De ellos, **erróneos** | **59** | **0** |
| Enviados a revisión, con sugerencias | no existía | 68 |
| Cruces reales no encontrados | 50 | 2 |
| Tiempo | ~4 s | ~0,07 s |

Para reproducirlo: `python benchmark.py`

Los umbrales del motor se definieron con un set generado con otra semilla; el
set de demostración no se usó para ajustar nada. En 20 sets adicionales
(6.000 artículos) el motor confirmó 4.483 cruces, ninguno erróneo.

**Qué no dice este número.** El set es sintético y lo generó el mismo proyecto,
así que mide el método en condiciones controladas, no garantiza el mismo
resultado con cualquier lista real. La prueba que vale es correrlo contra
listas propias.

## Cómo decide

Cada artículo interno termina en uno de tres estados:

- **Confirmado**: se puede usar sin mirar.
- **Dudoso**: hay candidato, pero una persona tiene que confirmarlo. Se muestra
  el motivo y hasta tres alternativas.
- **Sin cruce**: el proveedor no parece tener ese artículo.

Decisiones de diseño:

1. **Los números son identidad.** Cada descripción se separa en palabras,
   números y medidas (número + unidad). Dos artículos con la misma unidad y
   distinto valor (25 kg / 50 kg, 8x18x33 / 12x18x33) no se cruzan nunca, por
   más parecido que sea el texto.
2. **Ante la duda, a revisión.** Un cruce solo se confirma si el puntaje es
   alto, le saca ventaja clara al segundo candidato, los números coinciden y no
   hay una palabra distinta de cada lado (que suele ser otra marca, otro color o
   interior/exterior).
3. **Trazabilidad.** Cada artículo del proveedor guarda la hoja y la fila del
   Excel de donde salió.
4. **Jerga del rubro como configuración.** `comparador/texto.py` tiene un
   diccionario corto de sinónimos (barra = hierro, sinusoidal = acanalada,
   pegamento = adhesivo). Sin ese diccionario el motor sigue sin confirmar
   cruces erróneos, pero manda más artículos a revisión (85 en vez de 68).

## Errores de la primera versión que corrige

- **Flete por tonelada con peso fijo.** Calculaba todo como si pesara 25 kg.
  Ahora usa el peso de cada artículo y, si falta, avisa en vez de suponer.
- **Cruce silencioso.** Tomaba el texto más parecido por encima de un umbral,
  sin mostrar puntaje ni lo que quedaba afuera.
- **Precios en formato argentino.** Borraba las comas, así que "1.234,56" se
  leía como 1,23456.
- **Descuentos ambiguos.** Un valor menor a 1 se tomaba como fracción: una
  bonificación de 0,5 % se aplicaba como 50 %.

## Descuentos

Se cargan como una cadena de pasos que se aplican en el orden escrito:
`10 + 10 + $150` es 10 %, después 10 % sobre lo que quedó, después $150 fijos
por unidad. El orden lo define quien carga, porque cambia el resultado
(`10 + $50` sobre 1.000 da 850; `$50 + 10` da 855) y depende de cada
negociación.

## Demo web y API

La demo de [simonetti.uno](https://simonetti.uno) corre este mismo motor en un
servidor, a través de una API de solo lectura hecha con FastAPI
(`comparador/api.py`):

| Ruta | Qué devuelve |
|---|---|
| `GET /zonas` | Opciones de flete: sin flete y las zonas de la lista del proveedor |
| `GET /resultado?zona=cordillera&descuentos=10 + $150` | Cada artículo con su estado, motivo, alternativas y costo nuevo |

Decisiones:

- **Sin pandas en el servidor.** Los Excel del set se pasan una vez a
  `datos/demo/demo.json` (`datos/exportar_json.py`) y el motor corre con la
  biblioteca estándar. Un test controla que el JSON siga saliendo de los Excel.
- **El cruce se calcula una sola vez.** Lo que cambia en cada consulta (flete y
  descuentos) es aritmética: unos milisegundos.
- **No se suben archivos.** Es una demo pública: solo datos ficticios
  precargados, y los parámetros tienen límites de largo y de rango.
- **Cada resultado trae su control.** Como el set tiene las respuestas
  conocidas, cada artículo dice si la decisión del motor coincide con la real.

Para probarla en tu compu: `python servir.py` y abrir http://127.0.0.1:8000/docs

## Limitaciones conocidas

- No convierte unidades: "1.20x2.40" (metros) contra "120x240 cm" queda sin
  cruce. Son los dos casos perdidos del set de demostración.
- El diccionario de jerga es chico y específico de corralón.
- Un artículo sin ningún número en la descripción depende solo de las palabras.

## Uso

```bash
pip install -r requirements.txt
python datos/generar.py            # regenera el set ficticio (semilla 42)
python -m pytest                   # 63 pruebas
python benchmark.py                # medición contra las respuestas conocidas
python comparar.py --flete por_tonelada --valor 85000   # deja resultado.csv
python comparar.py --descuentos "10 + 10 + $150"        # descuentos extra en cadena
python datos/exportar_json.py      # pasa el set a JSON para la demo web
python servir.py                   # API de la demo en http://127.0.0.1:8000/docs
```

## Estructura

```
comparador/
  precios.py   lectura de precios en formato argentino
  costos.py    bonificaciones en cascada y modalidades de flete
  texto.py     normalización: palabras, números, medidas, dimensiones
  cruce.py     motor de cruce y reglas de decisión
  lectura.py   lectura de los Excel (detecta encabezados, descarta ruido)
  demo.py      el motor sobre el set ficticio, sin pandas, para la web
  api.py       API de solo lectura de la demo (FastAPI)
datos/generar.py        generador del set ficticio con respuestas conocidas
datos/exportar_json.py  pasa el set a JSON para la demo web
benchmark.py            medición: método original contra este motor
comparar.py             corrida completa por línea de comandos
servir.py               levanta la API de la demo en tu compu
tests/                  pruebas unitarias y de punta a punta
```

El motor no depende de ninguna interfaz: se puede usar desde la línea de
comandos, desde una API web o desde un script.
