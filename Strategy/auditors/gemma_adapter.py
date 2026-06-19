import urllib.request
import json
import time
from base_auditor import BaseAuditor

class GemmaAdapter(BaseAuditor):
    def audit(self, payload):
        prompt = self.build_prompt(payload)

        api_url = self.config.get("api_url", "http://localhost:11434/api/generate")
        model = self.config.get("id", "gemma3:4b")
        num_ctx = self.config.get("context_window", 32768)

        max_retries = 3

        for attempt in range(max_retries):
            req_payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx": num_ctx
                }
            }

            try:
                req = urllib.request.Request(
                    api_url,
                    data=json.dumps(req_payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    raw_output = result.get("response", "")

                    parsed = self.parse_verdict(raw_output)
                    if parsed.get("parsing_reliability") != "failed":
                        # Make sure auditor_id matches expected
                        parsed["auditor_id"] = model
                        return parsed

                    # If it failed, append the error to the prompt for the next retry
                    if attempt < max_retries - 1:
                        prompt += f"\n\nERROR ON PREVIOUS ATTEMPT: {parsed.get('error')}. YOU MUST OUTPUT VALID JSON MATCHING THE SCHEMA."
                        time.sleep(1) # brief pause
                        continue

                    return parsed # return the failed parse result after all retries exhausted

            except Exception as e:
                return {
                    "error": "API Connection Failed",
                    "exception": str(e),
                    "verdict": "AUDITOR_VERDICT_INVALID",
                    "parsing_reliability": "failed"
                }

        return {"error": "Unknown error", "verdict": "AUDITOR_VERDICT_INVALID", "parsing_reliability": "failed"}

def get_auditor(config):
    return GemmaAdapter(config)
