import os
import yaml

constructs = ["Eidolon-0", "Solace-2", "Myrrid-1", "Wyrm-4"]

for cid in constructs:
    path = os.path.join(cid, "Core", "identity.yaml")
    if not os.path.exists(path):
        print(f"⚠️ {cid} identity.yaml missing.")
        continue

    with open(path, "r") as f:
        identity = yaml.safe_load(f)

    if "self_awareness" in identity and "check_interval" in identity["self_awareness"]:
        raw = identity["self_awareness"]["check_interval"]
        if isinstance(raw, str) and not raw.isdigit():
            # Extract digits from string like '3 pulses'
            digits = ''.join(filter(str.isdigit, raw))
            if digits:
                identity["self_awareness"]["check_interval"] = int(digits)
                print(f"✅ {cid} sanitized → check_interval set to {digits}")
            else:
                identity["self_awareness"]["check_interval"] = 3
                print(f"⚠️ {cid} fallback → check_interval defaulted to 3")
        elif isinstance(raw, str):
            identity["self_awareness"]["check_interval"] = int(raw)

    with open(path, "w") as f:
        yaml.dump(identity, f)

print("\n🧼 Identity files sanitized.")
