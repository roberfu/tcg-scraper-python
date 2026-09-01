import argparse
import json
import os
import re
import time

import requests
from curl_cffi import requests as cffi_requests

BASIC_LANDS = {
    "Plains", "Island", "Swamp", "Mountain", "Forest",
    "Snow-Covered Plains", "Snow-Covered Island",
    "Snow-Covered Swamp", "Snow-Covered Mountain",
    "Snow-Covered Forest", "Wastes",
}

CATEGORIES = (
    "creatures",
    "lands",
    "planeswalkers",
    "spells",
    "artifacts",
    "enchantments",
)

FORMAT_BUCKETS = ("pauper", "no_pauper")

SCRYFALL_HEADERS = {
    "User-Agent": "magic-app/1.0",
    "Accept": "*/*",
}


def parse_card_line(line):
    line = re.sub(r"^SB:\s*", "", line, flags=re.IGNORECASE).strip()
    m = re.match(r"^(\d+)\s+x?\s*(.+)$", line)
    if not m:
        return None
    return int(m.group(1)), m.group(2).strip().rstrip(",")


def classify_type(type_line):
    tl = type_line or ""
    if "Creature" in tl:
        return "creatures"
    if "Land" in tl:
        return "lands"
    if "Planeswalker" in tl:
        return "planeswalkers"
    if "Instant" in tl or "Sorcery" in tl:
        return "spells"
    if "Artifact" in tl:
        return "artifacts"
    if "Enchantment" in tl:
        return "enchantments"
    return None


def fetch_card_info(name, cards_db):
    if name in cards_db:
        return cards_db[name], True

    url = "https://api.scryfall.com/cards/named?exact=" + requests.utils.quote(name)
    backoffs = [2, 4, 8, 16, 30, 30]
    for attempt, wait in enumerate(backoffs, start=1):
        try:
            resp = requests.get(url, headers=SCRYFALL_HEADERS, timeout=15)
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

    data = resp.json()
    if data.get("object") == "error":
        return None, False

    if data.get("card_faces"):
        faces_type_lines = [f.get("type_line", "") for f in data["card_faces"]]
        type_line = " // ".join([t for t in faces_type_lines if t]) or data.get("type_line", "")
    else:
        type_line = data.get("type_line", "")

    category = classify_type(type_line)
    info = {
        "is_pauper": data.get("legalities", {}).get("pauper") == "legal",
        "type_category": category,
    }
    cards_db[name] = info
    return info, False


def load_cards_db():
    try:
        with open("cards_db.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return {}


def load_urls():
    with open("urls.json", "r", encoding="utf-8") as f:
        return json.load(f)


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
    aggregated = {}
    cache = load_deck_cache()
    unique_urls = list(dict.fromkeys(urls))
    for url in unique_urls:
        txt_url = url.rstrip("/") + "/txt"
        if not refresh and url in cache and isinstance(cache[url], list):
            print(f"-> cache: {txt_url}")
            deck_cards = cache[url]
        else:
            print(f"-> {txt_url}")
            try:
                response = cffi_requests.get(txt_url, impersonate="chrome", timeout=15)
            except Exception as e:
                print(f"  ! Error de red: {e}")
                continue
            if response.status_code != 200:
                print(f"  ! HTTP {response.status_code}")
                continue
            deck_cards = []
            for line in response.text.splitlines():
                parsed = parse_card_line(line)
                if not parsed:
                    continue
                qty, name = parsed
                if name not in BASIC_LANDS:
                    deck_cards.append([qty, name])
            cache[url] = deck_cards
            write_deck_cache(cache)

        for qty, name in deck_cards:
            aggregated[name] = max(aggregated.get(name, 0), qty)
    return aggregated


def read_collection_file(path):
    aggregated = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("//"):
                    continue
                m = re.match(r"^(\d+)\s+(.+)$", line)
                if not m:
                    continue
                qty = int(m.group(1))
                name = m.group(2).strip()
                aggregated[name] = aggregated.get(name, 0) + qty
    except FileNotFoundError:
        pass
    return aggregated


def write_collection_file(path, items):
    with open(path, "w", encoding="utf-8") as f:
        for name in sorted(items):
            f.write(f"{items[name]} {name}\n")


def update_collection(path, card_name, needed_qty):
    existing = read_collection_file(path)
    current_qty = existing.get(card_name, 0)
    existing[card_name] = max(current_qty, needed_qty)
    if existing[card_name] != current_qty:
        write_collection_file(path, existing)
        if current_qty == 0:
            print(f"  Nueva carta: {needed_qty} {card_name}")
        else:
            print(f"  Nueva cantidad: {existing[card_name]} {card_name}")


def write_export_file(path, items):
    with open(path, "w", encoding="utf-8") as f:
        for name in sorted(items):
            if items[name] > 0:
                f.write(f"{items[name]} {name}\n")


def process_bucket(format_name, category, cards):
    collection_dir = os.path.join(format_name, "collection")
    export_dir = os.path.join(format_name, "export")
    os.makedirs(collection_dir, exist_ok=True)
    os.makedirs(export_dir, exist_ok=True)

    collection_path = os.path.join(collection_dir, f"{category}.txt")
    collection = read_collection_file(collection_path)
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
    all_cards = scrape_decks(load_urls(), refresh=args.refresh)
    print(f"Cartas unicas (excluyendo basicas): {len(all_cards)}")

    if not all_cards:
        print("Sin cartas que procesar.")
        return

    cards_db = load_cards_db()

    buckets = {
        format_name: {category: {} for category in CATEGORIES}
        for format_name in FORMAT_BUCKETS
    }
    unknown = {format_name: set() for format_name in FORMAT_BUCKETS}

    for name in sorted(all_cards):
        info, was_cached = fetch_card_info(name, cards_db)
        if not was_cached:
            time.sleep(0.12)
        format_name = "pauper" if info and info.get("is_pauper") else "no_pauper"
        if info is None or info.get("type_category") is None:
            unknown[format_name].add(name)
            continue
        category = info["type_category"]
        if category not in CATEGORIES:
            unknown[format_name].add(name)
            continue
        buckets[format_name][category][name] = all_cards[name]

    with open("cards_db.json", "w", encoding="utf-8") as f:
        json.dump(cards_db, f, indent=2, ensure_ascii=False)
        f.write("\n")

    for format_name in FORMAT_BUCKETS:
        for category in CATEGORIES:
            process_bucket(format_name, category, buckets[format_name][category])
        export_dir = os.path.join(format_name, "export")
        with open(os.path.join(export_dir, "unknown.txt"), "w", encoding="utf-8") as f:
            for name in sorted(unknown[format_name]):
                f.write(f"{name}\n")
        if unknown[format_name]:
            print(f"  {format_name}/export/unknown.txt: {len(unknown[format_name])} cartas")


if __name__ == "__main__":
    main()
