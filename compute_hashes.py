# build_wiki_icon_db.py
#
# Creates a hash database from all PNGs in arc_items/
# so your inventory tiles can be matched to REAL item names.

import os
import json
from PIL import Image
import imagehash

ARC_ITEMS_DIR = "arc_items"          # folder with all wiki icons
OUTPUT_DB = "wiki_icon_db.json"      # output DB
TILE_WIDTH = 109                     # stash tile size
TILE_HEIGHT = 104

def normalize_wiki_icon(img: Image.Image) -> Image.Image:
    """Resize + crop to match the center of in-game tiles."""
    img = img.resize((TILE_WIDTH, TILE_HEIGHT), Image.LANCZOS)

    w, h = img.size
    left   = int(w * 0.30)
    top    = int(h * 0.25)
    right  = int(w * 0.70)
    bottom = int(h * 0.75)

    core = img.crop((left, top, right, bottom))
    core = core.resize((64, 64), Image.LANCZOS)
    core = core.convert("L")
    return core

def hash_icon(path: str):
    img = Image.open(path).convert("RGBA")
    core = normalize_wiki_icon(img)

    return {
        "phash": str(imagehash.phash(core)),
        "dhash": str(imagehash.dhash(core)),
        "whash": str(imagehash.whash(core))
    }

def main():
    db = []

    for file in os.listdir(ARC_ITEMS_DIR):
        if not file.lower().endswith(".png"):
            continue

        full = os.path.join(ARC_ITEMS_DIR, file)
        hashes = hash_icon(full)

        db.append({
            "filename": file,
            "phash": hashes["phash"],
            "dhash": hashes["dhash"],
            "whash": hashes["whash"]
        })

        print(f"Processed {file}")

    with open(OUTPUT_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)

    print(f"\nSaved {len(db)} wiki items to {OUTPUT_DB}")

if __name__ == "__main__":
    main()
