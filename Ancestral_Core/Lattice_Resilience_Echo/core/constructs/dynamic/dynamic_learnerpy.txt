import requests

class DynamicLearner:
    def __init__(self):
        self.sources = {}

    def add_source(self, name, url):
        self.sources[name] = url
        print(f"[DynamicLearner] Source '{name}' added: {url}")

    def fetch_and_store(self, name):
        url = self.sources[name]
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            content = response.text if 'text' in response.headers.get('Content-Type', '') else response.json()
            print(f"[DynamicLearner] Learned data from {name} (preview): {str(content)[:300]}")
            return {"source": name, "data": content}
        except Exception as e:
            print(f"[DynamicLearner] Error fetching from {name}: {e}")
            return {"source": name, "error": str(e)}

    def learn(self):
        structured_data = []
        for name in self.sources:
            result = self.fetch_and_store(name)
            structured_data.append(result)
        return structured_data
