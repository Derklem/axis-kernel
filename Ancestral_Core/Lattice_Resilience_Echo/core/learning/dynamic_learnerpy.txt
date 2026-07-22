# core/learning/dynamic_learner.py

class DynamicLearner:
    def __init__(self):
        self.sources = {}

    def add_source(self, name, url):
        self.sources[name] = url
        print(f"[DynamicLearner] Source '{name}' added: {url}")

    def fetch_sources(self):
        data = {}
        for name, url in self.sources.items():
            try:
                import requests
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    data[name] = response.json()
                else:
                    data[name] = response.text
                preview = str(data[name])[:200].replace("\n", "")
                print(f"[DynamicLearner] Learned data from {name} (preview): {preview}")
            except Exception as e:
                print(f"[DynamicLearner] Error fetching from {name}: {e}")
        return data
