import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote

base_url = "https://arc-raiders.fandom.com/wiki/Items"
base_site = "https://arc-raiders.fandom.com"
destination = "arc_items"


def find_items_table(soup: BeautifulSoup):
    tables = soup.select("#mw-content-text table")
    for table in tables:
        header_row = table.find("tr")
        if not header_row:
            continue
        header_text = " ".join(cell.get_text(strip=True) 
            for cell in header_row.find_all(["th", "td"]))
        if "Name" in header_text and "Rarity" in header_text:
            return table
    return None
def get_image_info_from_row(row):
    first_td = row.find("td")
    if not first_td:
        return None, None
    # Most Fandom rows have <a class="image"><img ...></a>
    a = first_td.find("a", class_="image")
    if not a:
        # any link in the first cell
        a = first_td.find("a")
    if not a:
        return None, None

    img = a.find("img")

    # prefer the original full-size image
    img_url = a.get("href") or (img.get("src") if img else None)
    if not img_url:
        return None, None

    # Make URL absolute if it's relative
    if img_url.startswith("/"):
        img_url = urljoin(base_site, img_url)

    filename = None
    if img and img.get("data-image-name"):
        filename = img["data-image-name"]
    else:
        # fall back to the path part
        filename = os.path.basename(urlparse(img_url).path)

    # Remove query params (like ?cb=12345)
    filename = unquote(filename).split("?")[0]

    return img_url, filename


def main():
    os.makedirs(destination, exist_ok=True)

    print(f"Fetching page: {base_url}")
    resp = requests.get(base_url, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    items_table = find_items_table(soup)
    if items_table is None:
        print("Could not find the items table.")
        return

    rows = items_table.find_all("tr")[1:]  # skip header row
    print(f"Found {len(rows)} item rows")

    for i, row in enumerate(rows, start=1):
        img_url, filename = get_image_info_from_row(row)
        if not img_url or not filename:
            print(f"[{i}] No image found, skipping.")
            continue

        out_path = os.path.join(destination, filename)
        if os.path.exists(out_path):
            print(f"[{i}] {filename} already exists, skipping.")
            continue

        print(f"[{i}] Downloading {filename} from {img_url}")

        try:
            img_resp = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"})
            img_resp.raise_for_status()
        except requests.RequestException as e:
            print(f"    Failed to download {img_url}: {e}")
            continue

        with open(out_path, "wb") as f:
            f.write(img_resp.content)

    print("Done.")


if __name__ == "__main__":
    main()
