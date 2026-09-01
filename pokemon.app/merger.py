import os
import re


CATEGORIES = (
    "pokemon",
    "supporters",
    "items",
    "tools",
    "stadiums",
    "energies",
)


def read_card_file(path):
    cards = {}
    with open(path, "r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            match = re.match(r"^(\d+)\s+(.+)$", line)
            if not match:
                raise ValueError(f"Formato inválido en {path}:{line_number}")
            quantity = int(match.group(1))
            name = re.sub(r"\s+\([A-Z0-9]+-\d+\)$", "", match.group(2).strip())
            cards[name] = cards.get(name, 0) + quantity
    return cards


def write_card_file(path, cards):
    with open(path, "w", encoding="utf-8") as file:
        for name in sorted(cards):
            if cards[name] > 0:
                file.write(f"{cards[name]} {name}\n")


def merge_file(export_path, collection_path):
    if not os.path.exists(export_path):
        return

    exported_cards = read_card_file(export_path)
    collection = read_card_file(collection_path) if os.path.exists(collection_path) else {}
    for name, quantity in exported_cards.items():
        collection[name] = collection.get(name, 0) + quantity

    os.makedirs(os.path.dirname(collection_path), exist_ok=True)
    write_card_file(collection_path, collection)
    with open(export_path, "w", encoding="utf-8"):
        pass

    if exported_cards:
        total = sum(exported_cards.values())
        print(f"  Transferidas {total} cartas desde {export_path} a {collection_path}")
    else:
        print(f"  Exportación vacía: {export_path}")


def main():
    for category in CATEGORIES:
        export_path = os.path.join("export", f"{category}.txt")
        collection_path = os.path.join("collection", f"{category}.txt")
        merge_file(export_path, collection_path)


if __name__ == "__main__":
    main()
