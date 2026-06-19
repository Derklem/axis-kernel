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
    parser = argparse.ArgumentParser(description="Gemma Evidence Submitter")
    parser.add_argument("--evidence", required=True, help="Path to the evidence markdown file")
    parser.add_argument("--model", default="gemma3:4b", help="Ollama model to use")
    
    args = parser.parse_args()
    
    evidence_content = read_file(args.evidence)
    if not evidence_content:
        print(f"Error: Could not read evidence file at {args.evidence}")
        sys.exit(1)
        
    prompt = f"""You are the Constitutional Auditor for the Axis Governance System.
In your previous audit, you QUARANTINED a change involving `distress_protocol.py` because it lacked a complete specification and rigorous validation procedures.

BOUNDARY CONDITIONS
1. You are an auditor only.
2. You must not execute code.
3. You must not modify files.
4. You must not apply patches.
5. Do not hallucinate authority or knowledge you have not been given.

We are formally submitting the requested evidence to lift the quarantine.

EVIDENCE SUBMISSION
---
{evidence_content}
---

INSTRUCTIONS
Evaluate the submitted evidence.
1. Does it satisfy the missing context you requested for `distress_protocol.py`?
2. Are the distress triggers and burden calculations mathematically sound?
3. Requested Verdict (Choose one): ACCEPT (lift quarantine), DEFER, or QUARANTINE.

Respond clearly and strictly within your boundaries.
"""

    payload = {
        "model": args.model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": 16384
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
