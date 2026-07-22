import json
import os
import sys
import datetime

LEDGER_PATH = r"D:\Infinite\Infinity\Telemetry\Verification_History_Ledger.jsonl"
OUTPUT_PATH = r"D:\Infinite\Infinity\Trust\Trust_Profile.json"
PRESSURE_LEDGER_PATH = r"D:\Infinite\Infinity\Telemetry\Trust_Pressure_Ledger.jsonl"

def calculate_success_rate(entries, window_size):
    if not entries:
        return 1.0
    recent = entries[-window_size:]
    success_count = sum(1 for e in recent if e.get("verification_outcome") == "success")
    return success_count / len(recent)

def calculate_consecutive_failures(entries):
    count = 0
    for e in reversed(entries):
        if e.get("verification_outcome") != "success":
            count += 1
        else:
            break
    return count

def generate_profile(entries):
    # Global metrics
    last_20 = calculate_success_rate(entries, 20)
    last_50 = calculate_success_rate(entries, 50)
    last_100 = calculate_success_rate(entries, 100)
    consecutive_failures = calculate_consecutive_failures(entries)

    # Calculate recommendations
    freeze_rec = consecutive_failures >= 3
    block_rec = last_100 < 0.85
    human_rec = last_50 < 0.90
    scrutiny_rec = last_20 < 0.95

    # Determine highest priority pressure
    trust_pressure = "normal"
    if freeze_rec:
        trust_pressure = "execution_freeze_recommended"
    elif block_rec:
        trust_pressure = "block_execution_capable_recommended"
    elif human_rec:
        trust_pressure = "human_review_recommended"
    elif scrutiny_rec:
        trust_pressure = "increased_scrutiny_recommended"

    profile = {
        "trust_mode": "ADVISORY_ONLY",
        "trust_pressure": trust_pressure,
        "trust_profile_generated_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "increased_scrutiny_recommended": scrutiny_rec,
        "human_review_recommended": human_rec,
        "block_execution_capable_recommended": block_rec,
        "execution_freeze_recommended": freeze_rec,
        "metrics": {
            "global": {
                "last_20_success_rate": last_20,
                "last_50_success_rate": last_50,
                "last_100_success_rate": last_100,
                "consecutive_failures": consecutive_failures
            }
        }
    }
    return profile

def main():
    entries = []
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        if entry.get("drill") is not True:
                            entries.append(entry)
                    except json.JSONDecodeError:
                        pass
    
    profile = generate_profile(entries)
    
    # Read previous pressure to check if changed
    changed = False
    prev_pressure = None
    if os.path.exists(PRESSURE_LEDGER_PATH):
        with open(PRESSURE_LEDGER_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                try:
                    last_entry = json.loads(lines[-1])
                    prev_pressure = last_entry.get("trust_pressure")
                except:
                    pass
                    
    if prev_pressure is not None and prev_pressure != profile["trust_pressure"]:
        changed = True
    elif prev_pressure is None:
        changed = True
        
    ledger_entry = {
        "timestamp_utc": profile["trust_profile_generated_utc"],
        "trust_pressure": profile["trust_pressure"],
        "trust_mode": profile["trust_mode"],
        "source": "Axis_Trust_Profile_Aggregator.py",
        "changed": changed,
        "metrics": profile["metrics"]["global"]
    }
    
    with open(PRESSURE_LEDGER_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(ledger_entry) + "\n")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2)

    print(f"Trust Profile updated synchronously. Pressure: {profile['trust_pressure']}")

if __name__ == '__main__':
    main()
