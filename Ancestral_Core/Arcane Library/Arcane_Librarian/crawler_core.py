# Arcane Librarian v1.0 — crawler_core.py
# Quiet daily book harvesting operation

import os
import random
import time
import requests
from bs4 import BeautifulSoup
import zipfile
import json
from datetime import datetime

# === Configuration ===
BASE_DIR = r"E:\Arcane Library"
CAPTURE_DIR = os.path.join(BASE_DIR, "captured_books")
MANIFEST_PATH = os.path.join(BASE_DIR, "arcane_manifest.json")

ARCHIVE_SEARCH_URL = "https://archive.org/details/texts?and[]=mediatype%3A%22texts%22&sin="
DOWNLOAD_LIMIT = 1  # Number of books per session
WAIT_BETWEEN_STEPS = random.randint(240, 360)  # 4–6 minutes simulation

# === Helper Functions ===

def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"books": []}

def save_manifest(manifest):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

def pick_random_book_url():
    # Science/Math bias via static search for now (expandable later)
    seed_terms = ["mathematics", "physics", "engineering", "biology", "chemistry", "geology"]
    term = random.choice(seed_terms)
    url = f"https://archive.org/details/texts?query={term}&sort=-publicdate"
    print(f"🔎 Searching Archive with term: {term}")
    return url

def fetch_book_links(search_url):
    response = requests.get(search_url)
    soup = BeautifulSoup(response.text, "html.parser")
    links = soup.select('div.item-ia h2 a')
    return ["https://archive.org" + link.get('href') for link in links if link.get('href')]

def download_book(book_url, manifest):
    book_id = book_url.split('/')[-1]
    if any(book['id'] == book_id for book in manifest['books']):
        print(f"⚡ Already downloaded: {book_id}")
        return False

    try:
        os.makedirs(CAPTURE_DIR, exist_ok=True)
        book_page = requests.get(book_url)
        filename_base = os.path.join(CAPTURE_DIR, book_id)
        html_path = filename_base + ".html"

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(book_page.text)

        # Create ZIP package
        zip_filename = filename_base + ".zip"
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(html_path, arcname=os.path.basename(html_path))

        # Cleanup individual file
        os.remove(html_path)

        # Log in manifest
        manifest['books'].append({
            "id": book_id,
            "url": book_url,
            "timestamp": datetime.now().isoformat()
        })
        save_manifest(manifest)

        print(f"📚 Book captured: {book_id}")
        return True

    except Exception as e:
        print(f"❌ Failed to capture {book_url}: {e}")
        return False

# === Main Crawler Operation ===

def run_crawler():
    print("📜 Arcane Librarian Activated.")
    manifest = load_manifest()

    books_captured = 0
    retries = 0

    while books_captured < DOWNLOAD_LIMIT and retries < 3:
        search_url = pick_random_book_url()
        candidates = fetch_book_links(search_url)
        random.shuffle(candidates)

        for candidate in candidates:
            time.sleep(random.randint(15, 30))  # Random human-like delay
            if download_book(candidate, manifest):
                books_captured += 1
                break
            else:
                retries += 1
                if retries >= 3:
                    print("🛑 Too many failures. Halting crawl.")
                    return

        time.sleep(WAIT_BETWEEN_STEPS)  # Delay before ending session

    print("🧿 Crawl complete.")

# === Execution Point ===
if __name__ == "__main__":
    run_crawler()
