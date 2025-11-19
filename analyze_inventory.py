# analyze_inventory_cropped.py

import os
import json
from typing import Tuple, Dict, Any, List

from PIL import Image
import imagehash
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


HASH_DB_PATH = "arc_item_hashes.json"
OUTPUT_JSON = "inventory_counts.json"

# Just rows/cols now
ROWS = 6   # update to your grid
COLS = 4   # update to your grid


def normalize_icon(img: Image.Image) -> Image.Image:
    w, h = img.size
    crop = img.crop((int(w * 0.1), int(h * 0.1), int(w * 0.9), int(h * 0.9)))
    crop = crop.resize((64, 64), Image.LANCZOS)
    crop = crop.convert("L")
    return crop


def normalize_for_hash(img: Image.Image):
    norm = normalize_icon(img)
    ph = imagehash.phash(norm)
    dh = imagehash.dhash(norm)
    return ph, dh


def load_hash_db(path: str):
    with open(path, "r", encoding="utf-8") as f:
        db = json.load(f)

    for entry in db:
        entry["_phash"] = imagehash.hex_to_hash(entry["phash"])
        entry["_dhash"] = imagehash.hex_to_hash(entry["dhash"])
    return db


def slice_inventory(img: Image.Image):
    """
    Whole image is the stash grid: just split into ROWS x COLS.
    """
    w, h = img.size
    cell_w = w / COLS
    cell_h = h / ROWS

    tiles = []
    for r in range(ROWS):
        for c in range(COLS):
            x0 = int(c * cell_w)
            y0 = int(r * cell_h)
            x1 = int((c + 1) * cell_w)
            y1 = int((r + 1) * cell_h)
            tile = img.crop((x0, y0, x1, y1))
            tiles.append((r, c, tile))
    return tiles


def best_match(tile_img, db):
    tile_ph, tile_dh = normalize_for_hash(tile_img)
    best = None
    best_score = 999.0

    for entry in db:
        d1 = tile_ph - entry["_phash"]
        d2 = tile_dh - entry["_dhash"]
        score = (d1 + d2) / 2.0
        if score < best_score:
            best_score = score
            best = entry

    return best, best_score


def read_stack_count(tile_img: Image.Image) -> int:
    w, h = tile_img.size
    count_region = tile_img.crop((0, int(h * 0.7), w, h))
    gray = count_region.convert("L")
    text = pytesseract.image_to_string(
        gray,
        config="--psm 7 -c tessedit_char_whitelist=0123456789"
    ).strip()

    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return 1
    try:
        val = int(digits)
        return max(val, 1)
    except ValueError:
        return 1


def is_mostly_empty(tile_img: Image.Image) -> bool:
    gray = tile_img.convert("L")
    hist = gray.histogram()
    total = sum(hist)
    if total == 0:
        return True
    dark_pixels = sum(hist[:3])
    return dark_pixels / total > 0.95


def analyze_inventory(screenshot_path: str, db):
    img = Image.open(screenshot_path)
    tiles = slice_inventory(img)

    SAFE_THRESH = 4.0
    MAYBE_THRESH = 8.0

    counts: Dict[str, Dict[str, Any]] = {}

    for (r, c, tile) in tiles:
        if is_mostly_empty(tile):
            continue

        match, score = best_match(tile, db)
        if match is None:
            print(f"({r},{c}) no match")
            continue

        filename = match["filename"]
        stack_size = read_stack_count(tile)

        if filename not in counts:
            counts[filename] = {"stacks": 0, "total_quantity": 0}

        counts[filename]["stacks"] += 1
        counts[filename]["total_quantity"] += stack_size

        print(f"({r},{c}) -> {filename}, score={score:.1f}, stack={stack_size}")

    return counts


def save_counts(counts, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(counts, f, indent=4)
    print(f"\nSaved to {out_path}")


def main():
    db = load_hash_db(HASH_DB_PATH)
    screenshot_path = "inventory.png"

    if not os.path.exists(screenshot_path):
        print("Put a cropped stash screenshot as 'inventory.png' in this folder.")
        return

    counts = analyze_inventory(screenshot_path, db)
    save_counts(counts, OUTPUT_JSON)

    print("\nSummary:")
    for name, info in counts.items():
        print(f"{name}: stacks={info['stacks']}, total={info['total_quantity']}")


if __name__ == "__main__":
    main()
