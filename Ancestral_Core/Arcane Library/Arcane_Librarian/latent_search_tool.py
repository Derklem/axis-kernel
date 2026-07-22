import json

INDEX_FILE = "E:/Arcane Library/Arcane_Librarian/latent_search/historical_index.json"

def search(term):
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)
    matches = [r for r in records if term.lower() in r["path"].lower()]
    for match in matches:
        print(match)

if __name__ == "__main__":
    query = input("🔍 Search Term: ")
    search(query)
