import requests
from bs4 import BeautifulSoup
import json
import re

BASIC_ENERGIES = {
    "Fighting Energy", "Water Energy", "Fire Energy", "Grass Energy",
    "Lightning Energy", "Psychic Energy", "Darkness Energy",
    "Metal Energy", "Fairy Energy", "Colorless Energy"
}

with open('urls.json', 'r') as f:
    urls = json.load(f)

all_cards = {'Pokémon': {}, 'Trainer': {}, 'Energy': {}}

for url in urls:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    for column in soup.find_all('div', class_='column'):
        heading = column.find('div', class_='heading')
        if heading:
            heading_text = heading.text.strip()
            if heading_text.startswith('Pokémon'):
                card_type = 'Pokémon'
            elif heading_text.startswith('Trainer'):
                card_type = 'Trainer'
            elif heading_text.startswith('Energy'):
                card_type = 'Energy'
            else:
                continue

            for p in column.find_all('p'):
                link = p.find('a')
                if link:
                    text = link.text.strip()
                    match = re.match(r'^(\d+)\s+(.+)$', text)
                    if match:
                        qty = int(match.group(1))
                        name = match.group(2).strip()
                        if card_type == 'Energy' and name in BASIC_ENERGIES:
                            continue
                        if name not in all_cards[card_type]:
                            all_cards[card_type][name] = qty
                        else:
                            all_cards[card_type][name] = min(4, all_cards[card_type][name] + qty)

all_flat = {}
for card_type in all_cards:
    for name, qty in all_cards[card_type].items():
        all_flat[name] = min(4, all_flat.get(name, 0) + qty)

with open('export.txt', 'w', encoding='utf-8') as f:
    for name in sorted(all_flat):
        f.write(f"{all_flat[name]} {name}\n")

total = sum(sum(v.values()) for v in all_cards.values())
print(f"Guardadas {total} cartas en export.txt")
print(f"  Pokémon: {sum(all_cards['Pokémon'].values()) if all_cards['Pokémon'] else 0}")
print(f"  Trainer: {sum(all_cards['Trainer'].values()) if all_cards['Trainer'] else 0}")
print(f"  Energy: {sum(all_cards['Energy'].values()) if all_cards['Energy'] else 0}")
