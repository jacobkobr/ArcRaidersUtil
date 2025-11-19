# analyze_inventory.py
#
# Match your inventory tiles to REAL wiki filenames from arc_items/
# Output in Option A format:
#
# "Advanced_Fuse.png": {
#     "stacks": [
#         { "qty": 15, "pos": [0,1] },
#         { "qty": 5,  "pos": [0,2] }
#     ]
# }

import os
import json
from PIL import Image, ImageStat
import imagehash
import pytesseract

WIKI_DB = "wiki_icon_db.json"       # built from wiki icons
INVENTORY_IMAGE = "inventory.png"   # your cropped 6×4 stash screenshot
OUTPUT = "inventory_counts.json"

ROWS = 6
COLS = 4
PH_THRESH = 6
DH_THRESH = 6
WH_THRESH = 6

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -----------------------

def core_crop(tile: Image.Image) -> Image.Image:
    w, h = tile.size
    left   = int(w * 0.30)
    top    = int(h * 0.25)
    right  = int(w * 0.70)
    bottom = int(h * 0.75)
    core = tile.crop((left, top, right, bottom))
    core = core.resize((64, 64), Image.LANCZOS)
    return core.convert("L")

def normalize_tile_for_hash(tile: Image.Image):
    core = core_crop(tile)
    return (
        imagehash.phash(core),
        imagehash.dhash(core),
        imagehash.whash(core)
    )

def slice_grid(img: Image.Image):
    w, h = img.size
    tiles = []
    cw = w / COLS
    ch = h / ROWS
    for r in range(ROWS):
        for c in range(COLS):
            x0, y0 = int(c*cw), int(r*ch)
            x1, y1 = int((c+1)*cw), int((r+1)*ch)
            tiles.append((r, c, img.crop((x0, y0, x1, y1))))
    return tiles

def is_empty(tile):
    gray = tile.convert("L")
    stat = ImageStat.Stat(gray)
    return stat.mean[0] < 25 and stat.var[0] < 35

def load_wiki_db():
    with open(WIKI_DB, "r", encoding="utf-8") as f:
        db = json.load(f)

    for item in db:
        item["_ph"] = imagehash.hex_to_hash(item["phash"])
        item["_dh"] = imagehash.hex_to_hash(item["dhash"])
        item["_wh"] = imagehash.hex_to_hash(item["whash"])

    return db

def match_to_wiki(tile_hashes, db):
    ph, dh, wh = tile_hashes

    best = None
    best_sum = 999

    for item in db:
        d1 = ph - item["_ph"]
        d2 = dh - item["_dh"]
        d3 = wh - item["_wh"]
        s = d1 + d2 + d3
        if s < best_sum:
            best_sum = s
            best = (item, (d1, d2, d3))

    (d1, d2, d3) = best[1]
    if d1 <= PH_THRESH and d2 <= DH_THRESH and d3 <= WH_THRESH:
        return best[0]["filename"]  # REAL wiki filename
    return None

def read_stack(tile):
    w, h = tile.size
    x0, y0 = int(w*0.55), int(h*0.78)
    x1, y1 = int(w*0.97), int(h*0.98)
    region = tile.crop((x0, y0, x1, y1)).convert("L")
    bw = region.point(lambda p: 255 if p > 160 else 0)

    text = pytesseract.image_to_string(
        bw,
        config="--psm 7 -c tessedit_char_whitelist=0123456789"
    ).strip()

    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else 1

# -----------------------

def main():
    db = load_wiki_db()

    img = Image.open(INVENTORY_IMAGE)
    tiles = slice_grid(img)

    output = {}

    for (r, c, tile) in tiles:
        if is_empty(tile):
            continue

        hashes = normalize_tile_for_hash(tile)
        wiki_name = match_to_wiki(hashes, db)

        if wiki_name is None:
            print(f"({r},{c}) = no match")
            continue

        qty = read_stack(tile)

        if wiki_name not in output:
            output[wiki_name] = {"stacks": []}

        output[wiki_name]["stacks"].append({
            "qty": qty,
            "pos": [r, c]
        })

        print(f"({r},{c}) -> {wiki_name}, qty={qty}")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4)

    print("\nSaved:", OUTPUT)

if __name__ == "__main__":
    main()
