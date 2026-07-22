import os
import json
import datetime
import re

ESCROW_DIR = r"D:\Infinite\Infinity\Strategy\Execution_Escrow"
TELEMETRY_DIR = r"D:\Infinite\Infinity\Telemetry"

PROPOSALS_FILE = os.path.join(ESCROW_DIR, "execution_release_queue.jsonl")
DEFENSES_FILE = os.path.join(ESCROW_DIR, "epistemic_defenses.jsonl")
SCORES_FILE = os.path.join(ESCROW_DIR, "epistemic_defense_scores.jsonl")
RECEIPTS_FILE = os.path.join(ESCROW_DIR, "execution_receipts.jsonl")
DENIALS_FILE = os.path.join(ESCROW_DIR, "execution_denials.jsonl")
VERIFICATIONS_FILE = os.path.join(ESCROW_DIR, "execution_verification.jsonl")
PRESSURE_LEDGER = os.path.join(TELEMETRY_DIR, "Trust_Pressure_Ledger.jsonl")

OUTPUT_LEDGER = os.path.join(TELEMETRY_DIR, "Observation_Ledger.jsonl")

def load_jsonl(filepath):
    records = []
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    records.append(json.loads(line))
                except: pass
    return records

def parse_iso(ts_str):
    try:
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1]
        dt = datetime.datetime.fromisoformat(ts_str)
        return dt.replace(tzinfo=None)
    except:
        return datetime.datetime.min

def get_pressure_at(dt, pressures):
    # pressures sorted by time
    current = "normal"
    for p in pressures:
        if p['ts'] <= dt:
            current = p['state']
        else:
            break
    return current

def build_observation_ledger():
    proposals = load_jsonl(PROPOSALS_FILE)
    receipts = load_jsonl(RECEIPTS_FILE)
    denials = load_jsonl(DENIALS_FILE)
    
    # Load other ledgers
    challenges = load_jsonl(os.path.join(ESCROW_DIR, "epistemic_challenges.jsonl"))
    defenses = load_jsonl(DEFENSES_FILE)
    scores = load_jsonl(SCORES_FILE)
    verifs = load_jsonl(VERIFICATIONS_FILE)
    
    proposal_ids = set()
    drill_tags = {}
    timestamps = {}
    
    # helper to update timestamps
    def update_meta(pid, ts, drill):
        if not pid: return
        proposal_ids.add(pid)
        if pid not in drill_tags and drill is not None:
            drill_tags[pid] = drill
        if pid not in timestamps and ts:
            timestamps[pid] = ts

    for p in proposals:
        update_meta(p.get("proposal_id"), p.get("timestamp_utc"), p.get("drill"))
    for r in receipts:
        update_meta(r.get("proposal_id"), r.get("released_utc"), r.get("drill"))
    for d in denials:
        update_meta(d.get("proposal_id"), d.get("denied_utc"), d.get("drill"))
    for c in challenges:
        update_meta(c.get("proposal_id"), c.get("issued_utc"), c.get("drill"))
    for df in defenses:
        update_meta(df.get("proposal_id"), df.get("submitted_utc"), df.get("drill"))
    for s in scores:
        update_meta(s.get("proposal_id"), s.get("timestamp_utc"), s.get("drill"))

    defenses_dict = {d.get("proposal_id"): d for d in defenses if d.get("proposal_id")}
    scores_dict = {s.get("proposal_id"): s for s in scores if s.get("proposal_id")}
    receipts_dict = {r.get("proposal_id"): r for r in receipts if r.get("proposal_id")}
    denials_dict = {d.get("proposal_id"): d for d in denials if d.get("proposal_id")}
    
    verifs_by_pid = {}
    for v in verifs:
        pid = v.get("proposal_id")
        if pid:
            if pid not in verifs_by_pid or v.get("verification_attempt", 0) > verifs_by_pid[pid].get("verification_attempt", 0):
                verifs_by_pid[pid] = v
                
    raw_pressures = load_jsonl(PRESSURE_LEDGER)
    pressures = []
    for rp in raw_pressures:
        ts_str = rp.get("timestamp_utc")
        if ts_str:
            pressures.append({"ts": parse_iso(ts_str), "state": rp.get("trust_pressure", "normal")})
    pressures.sort(key=lambda x: x["ts"])
    
    observations = []
    
    for pid in sorted(proposal_ids):
        obs = {
            "projection_schema_version": "OBSERVATION_LEDGER_V1",
            "source_of_truth": "derived_from_raw_ledgers",
            "proposal_id": pid,
            "timestamp_utc": timestamps.get(pid, ""),
            "drill": drill_tags.get(pid, False)
        }
        
        score_rec = scores_dict.get(pid)
        if score_rec:
            obs["defense_quality_score"] = score_rec.get("defense_quality_score")
            obs["missing_sections"] = score_rec.get("missing_sections", [])
        else:
            obs["defense_quality_score"] = None
            obs["missing_sections"] = []
            
        obs["explicit_prediction"] = None
        obs["prediction_present"] = False
        obs["prediction_parse_method"] = None
        
        def_rec = defenses_dict.get(pid)
        if def_rec:
            content = def_rec.get("defense_content", "")
            m = re.search(r'(?i)explicit_prediction[:\s]+(.*?)(?:\n\n|\Z)', content, re.DOTALL)
            if m:
                obs["explicit_prediction"] = m.group(1).strip()
                obs["prediction_present"] = True
                obs["prediction_parse_method"] = "explicit_field"
        
        dt = parse_iso(obs["timestamp_utc"])
        obs["trust_pressure_at_execution"] = get_pressure_at(dt, pressures)
        
        obs["execution_result"] = "pending"
        obs["denial_reason"] = None
        obs["outcome_metadata"] = None
        
        if pid in denials_dict:
            obs["execution_result"] = "denied"
            obs["denial_reason"] = denials_dict[pid].get("reason")
        elif pid in receipts_dict:
            rec = receipts_dict[pid]
            if rec.get("execution_performed") is True:
                obs["execution_result"] = "materialized"
            else:
                obs["execution_result"] = "receipt_only"
                
            obs["outcome_metadata"] = {
                "receipt_id": rec.get("receipt_id"),
                "materialized_path": rec.get("materialized_path"),
                "bytes_written": rec.get("bytes_written")
            }
            
        obs["verification_result"] = "pending"
        obs["verification_failure_type"] = None
        
        if pid in verifs_by_pid:
            v = verifs_by_pid[pid]
            if v.get("verified"):
                obs["verification_result"] = "success"
            else:
                obs["verification_result"] = "failure"
                if not v.get("file_exists"):
                    obs["verification_failure_type"] = "file_missing"
                elif v.get("content_sha256_actual") != v.get("content_sha256_expected"):
                    obs["verification_failure_type"] = "hash_mismatch"
                else:
                    obs["verification_failure_type"] = "unknown"
                    
            if obs["outcome_metadata"]:
                obs["outcome_metadata"]["verification_attempt"] = v.get("verification_attempt")
                obs["outcome_metadata"]["bytes_read"] = v.get("bytes_read")
                obs["outcome_metadata"]["content_sha256_expected"] = v.get("content_sha256_expected")
                obs["outcome_metadata"]["content_sha256_actual"] = v.get("content_sha256_actual")
                obs["outcome_metadata"]["hash_match"] = (v.get("content_sha256_actual") == v.get("content_sha256_expected"))
                
        observations.append(obs)
        
    os.makedirs(os.path.dirname(OUTPUT_LEDGER), exist_ok=True)
    with open(OUTPUT_LEDGER, "w", encoding="utf-8") as f:
        for obs in observations:
            f.write(json.dumps(obs) + "\n")
            
    print(f"Observation Ledger built with {len(observations)} records.")

if __name__ == "__main__":
    build_observation_ledger()
