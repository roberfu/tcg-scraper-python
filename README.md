# tcg-scraper-python

Scripts de web scraping para construir listas de cartas coleccionables.

## Descripción

Proyecto para extraer datos de cartas de Magic: The Gathering y Pokemon TCG desde diversas fuentes. Cada scraper agrega listas de mazos, filtra cartas básicas/energías básicas, limita la cantidad máxima a 4 por carta y exporta una lista ordenada alfabéticamente.

## Scrapers disponibles

| Carpeta | Juego | Fuente |
|---|---|---|
| `limitless.app/` | Pokemon TCG | play.limitlesstcg.com |
| `mtgdecks.app/` | Magic: The Gathering | mtgdecks.net |
| `mtggoldfish.app/` | Magic: The Gathering | mtggoldfish.com |

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

## Configuración

Cada carpeta contiene un archivo `urls.json` con las URLs a scrapear. Edita ese archivo para agregar o quitar mazos.

## Uso

```bash
# Ejecutar un scraper específico
cd limitless.app && python scraper.py
cd mtgdecks.app && python scraper.py
cd mtggoldfish.app && python scraper.py
```

## Salida

Cada scraper genera un archivo `export.txt` dentro de su carpeta con el formato:

```
<cantidad> <nombre de carta>
```

Ejemplo:

```
2 Air Balloon
4 Applin (SCR-12)
3 Drakuloak (TWM-129)
```

## Tech Stack

- [Python](https://www.python.org/) - Lenguaje de programación
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) - Parseo de HTML
- [Requests](https://requests.readthedocs.io/) - Peticiones HTTP
- [Cloudscraper](https://github.com/VeNoMouS/cloudscraper) - Bypass de protección Cloudflare (mtgdecks)
