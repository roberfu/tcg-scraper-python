import argparse
import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup

BASIC_ENERGIES = {
    "Fighting Energy", "Water Energy", "Fire Energy", "Grass Energy",
    "Lightning Energy", "Psychic Energy", "Darkness Energy",
    "Metal Energy", "Fairy Energy", "Colorless Energy",
}

SUBTYPE_TO_BUCKET = {
    "Supporter": "supporters",
    "Item": "items",
    "Tool": "tools",
    "Stadium": "stadiums",
}

TRAINER_BUCKETS = ("supporters", "items", "tools", "stadiums")

HEADERS = {
    "User-Agent": "pokemon-app/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def parse_card_text(text):
    m = re.match(r"^(\d+)\s+(.+)$", text.strip())
    if not m:
        return None
    return int(m.group(1)), normalize_card_name(m.group(2).strip())


def normalize_card_name(name):
    return re.sub(r"\s+\([A-Z0-9]+-\d+\)$", "", name)


def parse_card_href(href):
    m = re.search(r"/cards/([A-Za-z0-9]+)/(\d+)", href or "")
    if not m:
        return None
    return m.group(1).upper(), m.group(2)


def parse_card_type_text(raw):
    m = re.match(r"^\s*(\w+)\s*(?:-\s*(\w+))?\s*$", raw)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def load_urls():
    with open("urls.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_cards_db():
    try:
        with open("cards_db.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return {}


def fetch_card_subtype(name, set_code, number, cards_db):
    cache_key = f"{name}|{set_code}|{number}"
    if cache_key in cards_db:
        return cards_db[cache_key], True

    url = f"https://limitlesstcg.com/cards/{set_code}/{number}"
    backoffs = [2, 4, 8, 16, 30, 30]
    for attempt, wait in enumerate(backoffs, start=1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
        except requests.RequestException as e:
            print(f"  ! Error de red con '{name}': {e}")
            return None, False
        if resp.status_code == 429:
            print(f"  ! Rate limit (429) en '{name}'; esperando {wait}s (intento {attempt}/{len(backoffs)})...")
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            return None, False
        break
    else:
        return None, False

    soup = BeautifulSoup(resp.text, "html.parser")
    type_p = soup.select_one("p.card-text-type")
    if not type_p:
        return None, False
    supertype, subtype = parse_card_type_text(type_p.get_text(" ", strip=True))
    info = {"supertype": supertype, "subtype": subtype}
    cards_db[cache_key] = info
    return info, False


def detect_section(heading_text):
    if heading_text.startswith("Pok"):
        return "Pokemon"
    if heading_text.startswith("Trainer"):
        return "Trainer"
    if heading_text.startswith("Energy"):
        return "Energy"
    return None


def load_deck_cache(path="decks_cache.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return {}


def write_deck_cache(cache, path="decks_cache.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
        f.write("\n")


def scrape_decks(urls, refresh=False):
    aggregated = {"Pokemon": [], "Trainer": [], "Energy": []}
    cache = load_deck_cache()
    unique_urls = list(dict.fromkeys(urls))

    for url in unique_urls:
        if not refresh and url in cache and isinstance(cache[url], dict):
            print(f"-> cache: {url}")
            deck_cards = cache[url]
        else:
            print(f"-> {url}")
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15)
            except requests.RequestException as e:
                print(f"  ! Error de red: {e}")
                continue
            if resp.status_code != 200:
                print(f"  ! HTTP {resp.status_code}")
                continue
            deck_cards = {"Pokemon": [], "Trainer": [], "Energy": []}
            soup = BeautifulSoup(resp.content, "html.parser")
            for column in soup.find_all("div", class_="column"):
                heading = column.find("div", class_="heading")
                if not heading:
                    continue
                section = detect_section(heading.get_text(strip=True))
                if not section:
                    continue
                for p in column.find_all("p"):
                    link = p.find("a")
                    if not link:
                        continue
                    parsed = parse_card_text(link.get_text())
                    if not parsed:
                        continue
                    qty, name = parsed
                    href_info = parse_card_href(link.get("href", ""))
                    if not href_info:
                        continue
                    set_code, number = href_info
                    if section == "Energy" and name in BASIC_ENERGIES:
                        continue
                    deck_cards[section].append([name, set_code, number, qty])
            cache[url] = deck_cards
            write_deck_cache(cache)

        for section in aggregated:
            for entry in deck_cards.get(section, []):
                name, set_code, number, qty = entry
                name = normalize_card_name(name)
                for i, current in enumerate(aggregated[section]):
                    if current[0] == name and current[1] == set_code and current[2] == number:
                        if qty > current[3]:
                            aggregated[section][i] = (name, set_code, number, qty)
                        break
                else:
                    aggregated[section].append((name, set_code, number, qty))
    return aggregated


def read_collection(filename):
    aggregated = {}
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("//"):
                    continue
                m = re.match(r"^(\d+)\s+(.+)$", line)
                if not m:
                    continue
                qty = int(m.group(1))
                name = m.group(2).strip()
                name = re.sub(r"\s+\([A-Z0-9]+-\d+\)$", "", name)
                aggregated[name] = aggregated.get(name, 0) + qty
    except FileNotFoundError:
        pass
    return aggregated


def write_collection_file(path, items):
    with open(path, "w", encoding="utf-8") as f:
        for name in sorted(items):
            f.write(f"{items[name]} {name}\n")


def write_named(path, names):
    with open(path, "w", encoding="utf-8") as f:
        for name in sorted(set(names)):
            f.write(f"{name}\n")


def write_pokemon(path, items):
    with open(path, "w", encoding="utf-8") as f:
        for name, set_code, number, qty in sorted(items, key=lambda x: x[0]):
            if set_code and number:
                f.write(f"{qty} {name} ({set_code}-{number})\n")
            else:
                f.write(f"{qty} {name}\n")


def write_export_file(path, items):
    with open(path, "w", encoding="utf-8") as f:
        for name, qty in sorted(items.items()):
            if qty > 0:
                f.write(f"{qty} {name}\n")


def process_bucket(category, cards):
    collection_dir = os.path.join("collection")
    export_dir = os.path.join("export")
    os.makedirs(collection_dir, exist_ok=True)
    os.makedirs(export_dir, exist_ok=True)

    collection_path = os.path.join(collection_dir, f"{category}.txt")
    collection = read_collection(collection_path)
    missing = {
        name: max(needed_qty - collection.get(name, 0), 0)
        for name, needed_qty in cards.items()
    }
    write_export_file(os.path.join(export_dir, f"{category}.txt"), missing)
    for name, qty in sorted(missing.items()):
        if qty:
            print(f"  Exportar: {qty} {name}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Vuelve a descargar todos los mazos y actualiza el cache.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    urls = load_urls()
    aggregated = scrape_decks(urls, refresh=args.refresh)
    total = sum(len(v) for v in aggregated.values())
    print(f"Cartas unicas scrapeadas: {total}")

    if total == 0:
        print("Sin cartas que procesar.")
        return

    cards_db = load_cards_db()

    trainer_buckets = {bucket: {} for bucket in TRAINER_BUCKETS}
    trainer_unknown = []
    for name, set_code, number, qty in aggregated["Trainer"]:
        info, was_cached = fetch_card_subtype(name, set_code, number, cards_db)
        if not was_cached:
            time.sleep(0.12)
        if info is None or info.get("supertype") != "Trainer" or info.get("subtype") is None:
            trainer_unknown.append(name)
            continue
        bucket = SUBTYPE_TO_BUCKET.get(info["subtype"])
        if bucket in trainer_buckets:
            trainer_buckets[bucket][name] = qty
        else:
            trainer_unknown.append(name)

    with open("cards_db.json", "w", encoding="utf-8") as f:
        json.dump(cards_db, f, indent=2, ensure_ascii=False)
        f.write("\n")

    pokemon_qtys = {
        name: qty for name, _set, _num, qty in aggregated["Pokemon"]
    }
    process_bucket("pokemon", pokemon_qtys)

    for bucket, cards in trainer_buckets.items():
        process_bucket(bucket, cards)

    energy_qtys = {
        name: qty for name, _set, _num, qty in aggregated["Energy"]
    }
    process_bucket("energies", energy_qtys)

    os.makedirs("export", exist_ok=True)
    write_named("export/unknown.txt", trainer_unknown)
    print(f"  export/unknown.txt: {len(set(trainer_unknown))} cartas")


if __name__ == "__main__":
    main()
