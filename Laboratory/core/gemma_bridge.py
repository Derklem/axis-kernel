import json
import urllib.request
import urllib.error
import sys

def query_gemma(prompt, model="gemma3:4b", endpoint="http://localhost:11434/api/generate", temperature=0.0):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": 16384,
            "temperature": temperature
        }
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "")
    except urllib.error.URLError as e:
        print(f"Gemma request failed: {e}")
        return ""

if __name__ == "__main__":
    prompt = sys.stdin.read()
    if not prompt.strip():
        if len(sys.argv) > 1:
            try:
                with open(sys.argv[1], 'r', encoding='utf-8') as f:
                    prompt = f.read()
            except IOError:
                prompt = " ".join(sys.argv[1:])
                
    if prompt.strip():
        print(query_gemma(prompt))
    else:
        print("Error: No prompt provided via stdin or argument.")
