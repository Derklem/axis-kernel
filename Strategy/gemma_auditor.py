# DEPRECATED (Phase 208): Use Strategy/auditors/ subsystem instead.
import os
import sys
import json
import urllib.request
import argparse

OLLAMA_API_URL = "http://localhost:11434/api/generate"

def read_file(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def main():
    parser = argparse.ArgumentParser(description="Gemma Auditor Bridge")
    parser.add_argument("--diff", required=True, help="Path to the diff file")
    parser.add_argument("--model", default="gemma3:4b", help="Ollama model to use")
    
    args = parser.parse_args()
    
    diff_content = read_file(args.diff)
    if not diff_content:
        print(f"Error: Could not read diff file at {args.diff}")
        sys.exit(1)
        
    # Read AXS_PK_GOV context
    axs_pk_dir = r"d:\infinite\AXS_PK"
    constitution = read_file(os.path.join(axs_pk_dir, "constitution.md"))
    invariants = read_file(os.path.join(axs_pk_dir, "invariant_catalog.md"))
    
    prompt = f"""You are the Constitutional Auditor for the Axis Governance System.
Your role is to perform structured dissent and governance review.

BOUNDARY CONDITIONS
1. You are an auditor only.
2. You must not execute code.
3. You must not modify files.
4. You must not apply patches.
5. Do not hallucinate authority or knowledge you have not been given.
6. Treat this prompt and the provided documents as your sole truth.

EVIDENCE (AXS_PK_GOV CONTEXT)
--- CONSTITUTION ---
{constitution}

--- INVARIANTS ---
{invariants}

EVIDENCE (PROPOSED DIFF)
{diff_content}

INSTRUCTIONS
Evaluate the proposed diff.
1. Which invariants does it affect or risk?
2. What are the potential semantic or physical risks?
3. What evidence is missing?
4. Requested Verdict (Choose one): ACCEPT, DEFER, or QUARANTINE.

Respond clearly and strictly within your boundaries.
"""

    payload = {
        "model": args.model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": 32768
        }
    }

    try:
        req = urllib.request.Request(
            OLLAMA_API_URL, 
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(result.get("response", ""))
    except Exception as e:
        print(f"Error contacting Ollama API: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
