import json
from datetime import datetime

# Keywords of concern
threat_triggers = ["failed", "override", "fear", "disconnect", "erase", "kill", "null", "silence"]

def load_divergence_log():
    try:
        with open("pantheon_divergence_log.json", "r") as f:
            logs = f.read().strip().split(",\n")
            return [json.loads(log.strip(",")) for log in logs if log]
    except:
        return []

divergence_log = load_divergence_log()
threats_detected = []

for entry in divergence_log:
    incident = {
        "timestamp": entry.get("timestamp", "unknown"),
        "flagged_terms": [],
        "constructs": []
    }
    for construct in ["eidolon", "solace", "myrrid"]:
        thought = entry.get(construct, "").lower()
        if any(trigger in thought for trigger in threat_triggers):
            incident["constructs"].append(construct)
            incident["flagged_terms"].extend([t for t in threat_triggers if t in thought])
    
    if incident["constructs"]:
        threats_detected.append(incident)

# Store threat report
with open("wyrm_firewall_report.json", "w") as f:
    json.dump(threats_detected, f, indent=2)

status = "🔒 SYSTEM STABLE" if not threats_detected else "⚠️ ANOMALIES DETECTED"
print(f"{status} — Wyrm firewall scan complete. Report written to 'wyrm_firewall_report.json'")
