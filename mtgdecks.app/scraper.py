import cloudscraper
import re
import json

BASIC_LANDS = {"Plains", "Island", "Swamp", "Mountain", "Forest"}

scraper = cloudscraper.create_scraper()

with open('urls.json', 'r') as f:
    urls = json.load(f)

all_cards = {}

for url in urls:
    txt_url = url.rstrip('/') + '/txt'
    response = scraper.get(txt_url)
    if response.status_code != 200:
        print(f"Error {response.status_code} en {txt_url}")
        continue

    for line in response.text.splitlines():
        line = line.strip()
        match = re.match(r'^(\d+)\s+(.+)$', line)
        if match:
            qty = int(match.group(1))
            name = match.group(2).strip()
            if name not in BASIC_LANDS:
                all_cards[name] = max(all_cards.get(name, 0), qty)

db = {}
try:
    with open('database.txt', 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^(\d+)\s+(.+)$', line.strip())
            if m:
                db[m.group(2).strip()] = int(m.group(1))
except FileNotFoundError:
    pass

export = {name: all_cards[name] - db.get(name, 0) for name in all_cards}
export = {name: qty for name, qty in export.items() if qty > 0}

with open('export.txt', 'w', encoding='utf-8') as f:
    for name in sorted(export):
        f.write(f"{export[name]} {name}\n")

print(f"Guardadas {len(export)} cartas en export.txt")
