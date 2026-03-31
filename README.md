# tcg-scraper-python

Scripts de web scraping para construir una base de datos de cartas coleccionables.

## Requisitos

```bash
pip install -r requirements.txt
```

## Uso

Ejecutar todos los scrapers:

```bash
python main.py
```

O ejecutar individualmente:

```bash
cd magic.app && python scraper.py
cd poke.app && python scraper.py
```

## Salida

- `magic.app/magic.cards.csv` - Cartas de Magic: The Gathering con tipo
- `poke.app/poke.cards.csv` - Cartas de Pokemon TCG con cantidad y tipo
