# tcg-scraper-python

Scripts para actualizar colecciones de cartas de Magic: The Gathering y Pokémon TCG a partir de listas de mazos.

## Descripción

El proyecto contiene dos apps independientes:

- **`magic.app/`**: lee mazos de Magic desde URLs de `mtgdecks.net`, suma las cantidades por carta y clasifica cada carta por **legalidad Pauper** y **tipo** (criatura, instantáneo/conjuro, planeswalker, artefacto, encantamiento, tierra) consultando la API de Scryfall. Tierras básicas se ignoran.
- **`pokemon.app/`**: scrapea decklists de Pokémon desde Limitless TCG (`play.limitlesstcg.com`), separa Pokémon de Trainers y subclasifica los Trainers en **Supporter / Item / Tool / Stadium** consultando `limitlesstcg.com`. Energías básicas se ignoran.

## Apps disponibles

| Carpeta | Juego | Fuente |
|---|---|---|
| `magic.app/` | Magic: The Gathering | `mtgdecks.net` + Scryfall |
| `pokemon.app/` | Pokemon TCG | `play.limitlesstcg.com` + `limitlesstcg.com` |

## Requisitos

```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
# Linux/macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

Dependencias principales: `requests`, `beautifulsoup4`, `curl_cffi`.

## Uso

```bash
# Magic
(cd magic.app && python scraper.py && python merger.py)

# Pokémon
(cd pokemon.app && python scraper.py && python merger.py)
```

## Salida

### `magic.app`

Lee las URLs de `urls.json`, descarga la versión de texto de cada mazo desde `mtgdecks.net` y clasifica cada carta por tipo y legalidad Pauper consultando Scryfall con cache en `cards_db.json`.

La estructura de datos es:

```text
magic.app/
├── pauper/
│   ├── collection/
│   └── export/
└── no_pauper/
    ├── collection/
    └── export/
```

**Archivos actualizados:**
- `<formato>/collection/<tipo>.txt` — cartas que ya tienes, con formato `<cantidad> <nombre>`.
- `<formato>/export/<tipo>.txt` — cartas o copias que faltan para cubrir los mazos.
- `<formato>/export/unknown.txt` — cartas que Scryfall no pudo resolver.
- `decks_cache.json` — información descargada de cada URL para evitar consultas repetidas.

El script crea automáticamente las carpetas y los archivos de exportación que no existan. El valor `<formato>` es `pauper` o `no_pauper`.

**Archivos de entrada que mantiene el usuario:**
- `urls.json` — URLs de los mazos de `mtgdecks.net`.
- `<formato>/collection/<tipo>.txt` (6 archivos: `creatures`, `spells`, `planeswalkers`, `artifacts`, `enchantments`, `lands`) — cartas que ya tienes, formato `<cantidad> <nombre>`.

Los archivos `urls.json`, `collection/` y `export/` no están excluidos por `.gitignore` y pueden mantenerse en el repositorio.

**Generación de exportación por carta:**
- `collection/` no se modifica automáticamente.
- Se exporta `max(cantidad_en_mazo - cantidad_en_collection, 0)`.
- Las cartas de la colección que no están en el mazo se conservan.
- La separación `pauper`/`no_pauper` usa la legalidad Pauper de Scryfall.

**Salida en consola:**

Solo se muestran las cartas nuevas o las copias faltantes. Las cartas que ya tienen una cantidad suficiente no se exportan.

**Prioridad de tipos** cuando una carta tiene varios (p.ej. *Artifact Creature*): Creature > Land > Planeswalker > Instant/Sorcery > Artifact > Enchantment.

**Cache local:** `cards_db.json` guarda `{nombre: {is_pauper, type_category}}` para evitar llamadas repetidas a Scryfall. Este archivo forma parte del repo (no se ignora en git) y nunca debe borrarse manualmente: se actualiza automáticamente al final de cada ejecución.

**Formato de `urls.json`:**

Escribe una o varias URLs de mazos de `mtgdecks.net`:

```json
[
  "https://mtgdecks.net/Pauper/nombre-del-mazo-decklist-1234567"
]
```

El script añade `/txt` a cada URL para obtener la lista de cartas.

Si una URL ya está en `decks_cache.json`, no se vuelve a consultar. Para forzar la actualización de todos los mazos usa `python scraper.py --refresh`. Esta opción vuelve a descargar las decklists y actualiza `decks_cache.json`; no borra las colecciones ni fuerza la actualización de las cartas que ya están en `cards_db.json`.

**Transferir exportaciones a la colección:**

Después de revisar las cartas faltantes y obtenerlas, ejecuta `python merger.py`. El script suma las cantidades de cada archivo de `export/` a su archivo correspondiente de `collection/`, conserva las cartas que ya estaban en la colección y vacía las exportaciones procesadas. `export/unknown.txt` no se modifica.

**Formato de la lista descargada:**

Cada mazo debe devolver líneas con este formato:

```
4 Hearth Elemental
4 Sunderflock
...
6 Island

Sideboard
2 Annul
1 Broadside Barrage
...
```

- Una línea por carta: `<cantidad> <nombre>` (puede tener `x` opcional: `4x Lightning Bolt`).
- Las líneas vacías y las que empiezan por `#` o `//` se ignoran.
- Una sección opcional `Sideboard` (líneas que empiecen por `SB:` también se reconocen) cuyas cartas también se procesan.
- Las tierras básicas (`Plains`, `Island`, `Swamp`, `Mountain`, `Forest` y variantes `Snow-Covered`, `Wastes`) se ignoran automáticamente.

El script procesa todas las URLs y agrega las cartas tomando la cantidad máxima vista entre mazos.

### `pokemon.app`

Scrapea decklists de Limitless TCG (`play.limitlesstcg.com/.../decklist`), separa las cartas en Pokémon y Trainers, y subclasifica los Trainers en **Supporter / Item / Tool / Stadium** consultando `limitlesstcg.com` (que expone el subtipo de cada carta). Las energías básicas se ignoran.

**Estructura y archivos actualizados:**

```text
pokemon.app/
├── collection/
│   ├── pokemon.txt
│   ├── supporters.txt
│   ├── items.txt
│   ├── tools.txt
│   ├── stadiums.txt
│   └── energies.txt
└── export/
    ├── pokemon.txt
    ├── supporters.txt
    ├── items.txt
    ├── tools.txt
    ├── stadiums.txt
    ├── energies.txt
    └── unknown.txt
```

- Los archivos `collection/` contienen las cartas que ya tienes.
- Los archivos `export/` contienen las cartas o copias que faltan.
- `export/unknown.txt` contiene Trainers cuyo subtipo no se pudo determinar.
- `decks_cache.json` — información descargada de cada URL para evitar consultas repetidas.

El script crea automáticamente las carpetas y los archivos de exportación que no existan.

**Archivos de entrada que mantiene el usuario:**
- `urls.json` — URLs de los mazos a procesar.
- `collection/pokemon.txt` — cartas Pokémon que ya tienes, formato `<cantidad> <nombre>`.
- `collection/supporters.txt`, `collection/items.txt`, `collection/tools.txt`, `collection/stadiums.txt` — Trainers que ya tienes, mismo formato.
- `collection/energies.txt` — Energías no básicas que ya tienes.

Los archivos `urls.json` y las carpetas `collection/` y `export/` no están excluidos por `.gitignore` y pueden mantenerse en el repositorio.

**Generación de exportación por carta:**
- Los archivos de `collection/` no se modifican automáticamente.
- Se exporta `max(cantidad_en_mazo - cantidad_en_collection, 0)`.
- Las cartas de la colección que no están en el mazo se conservan.
- Las cartas en `export/unknown.txt` no se agregan porque no se pueden clasificar.

**Salida en consola:**

Solo se muestran las cartas nuevas o las copias faltantes. Las cartas que ya tienen una cantidad suficiente no se exportan.

**Cache local:** `cards_db.json` guarda `{nombre|set|numero: {supertype, subtype}}` para evitar llamadas repetidas a `limitlesstcg.com`. Este archivo forma parte del repo (no se ignora en git) y nunca debe borrarse manualmente.

**Configuración:** edita `urls.json` con las URLs de los mazos a procesar (formato: `https://play.limitlesstcg.com/tournament/.../player/.../decklist`).

Si una URL ya está en `decks_cache.json`, no se vuelve a consultar. Para forzar la actualización de todos los mazos usa `python scraper.py --refresh`. Esta opción vuelve a descargar las decklists y actualiza `decks_cache.json`; no borra las colecciones ni fuerza la actualización de las cartas que ya están en `cards_db.json`.

**Transferir exportaciones a la colección:**

Después de revisar las cartas faltantes y obtenerlas, ejecuta `python merger.py`. El script suma las cantidades de cada archivo de `export/` a su archivo correspondiente de `collection/`, conserva las cartas que ya estaban en la colección y vacía las exportaciones procesadas. `export/unknown.txt` no se modifica.

**Uso:**
```bash
cd pokemon.app
# Editar urls.json con las URLs de play.limitlesstcg.com a procesar
# Rellenar los archivos de collection/ con las cartas que ya tienes
python scraper.py
```

## Tech Stack

- [Python](https://www.python.org/) - Lenguaje de scripting.
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) - Parseo de HTML.
- [Requests](https://requests.readthedocs.io/) - Peticiones HTTP.
- [Scryfall API](https://scryfall.com/docs/api) - Datos y legalidades de cartas de Magic.
- [Limitless TCG](https://limitlesstcg.com) - Decks y datos de cartas de Pokémon.
