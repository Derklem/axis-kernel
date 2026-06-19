import os
import json

class BaseAuditor:
    def __init__(self, config):
        self.config = config
        self.auditor_id = config.get("id", "unknown")
        
        # Load schema
        base_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(base_dir, "verdict_schema.json")
        with open(schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)

    def read_file(self, path):
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def get_context(self):
        # We assume the script is executed inside Strategy/auditors/ or Strategy/
        axs_pk_dir = r"d:\infinite\AXS_PK"
        constitution = self.read_file(os.path.join(axs_pk_dir, "constitution.md"))
        invariants = self.read_file(os.path.join(axs_pk_dir, "invariant_catalog.md"))
        return constitution, invariants

    def build_prompt(self, payload):
        constitution, invariants = self.get_context()
        diff_content = payload.get("diff", "")
        
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

OUTPUT FORMAT
You MUST output strictly valid JSON matching the following schema. Do NOT wrap it in markdown code blocks or add any conversational text.

```json
{json.dumps(self.schema, indent=2)}
```
"""
        return prompt

    def parse_verdict(self, raw_text):
        """
        Attempts to parse the raw text as JSON.
        Adds parsing_reliability flag.
        """
        import re
        
        reliability = "strict"
        json_str = raw_text.strip()
        
        # Try to extract JSON if it was wrapped in markdown
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', json_str, re.DOTALL)
        if match:
            json_str = match.group(1)
            reliability = "extracted"
        else:
            # Maybe the model just started with {
            match = re.search(r'\{.*\}', json_str, re.DOTALL)
            if match:
                json_str = match.group(0)
                if json_str != raw_text.strip():
                    reliability = "extracted"
                    
        try:
            verdict = json.loads(json_str)
            # Ensure required fields exist
            for req in self.schema.get("required", []):
                if req not in verdict:
                    return {"error": f"Missing required field: {req}", "raw_output": raw_text, "parsing_reliability": "failed"}
                    
            verdict["parsing_reliability"] = reliability
            return verdict
        except json.JSONDecodeError as e:
            return {
                "error": "Invalid JSON",
                "exception": str(e),
                "raw_output": raw_text,
                "parsing_reliability": "failed",
                "verdict": "AUDITOR_VERDICT_INVALID"
            }

    def audit(self, payload):
        """
        Subclasses must implement this.
        Takes a payload dict (e.g. {"diff": "..."}), queries the model, and returns a dict parsed by parse_verdict.
        """
        raise NotImplementedError("Subclasses must implement audit()")
