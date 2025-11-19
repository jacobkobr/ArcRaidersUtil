# compute_hashes.py

import os
import json
from PIL import Image
import imagehash

INPUT_DIR = "arc_items"             # Folder with downloaded wiki icons
OUTPUT_JSON = "arc_item_hashes.json"


def normalize_icon(img: Image.Image) -> Image.Image:
    """
    Normalize an icon image so wiki icons and inventory tiles are comparable:
    - Crop central area (remove borders/glow)
    - Resize to fixed size
    - Convert to grayscale
    """
    w, h = img.size
    # central 80% region
    crop = img.crop((int(w * 0.1), int(h * 0.1), int(w * 0.9), int(h * 0.9)))
    crop = crop.resize((64, 64), Image.LANCZOS)
    crop = crop.convert("L")
    return crop


def main():
    entries = []

    for filename in os.listdir(INPUT_DIR):
        if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue

        path = os.path.join(INPUT_DIR, filename)
        try:
            img = Image.open(path)
        except Exception as e:
            print(f"Skipping {filename}: cannot open ({e})")
            continue

        norm = normalize_icon(img)

        ph = imagehash.phash(norm)
        dh = imagehash.dhash(norm)

        entries.append({
            "filename": filename,
            "phash": str(ph),
            "dhash": str(dh)
        })
        print(f"Hashed {filename}: phash={ph}, dhash={dh}")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=4)

    print(f"\nDone! Saved {len(entries)} entries to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
