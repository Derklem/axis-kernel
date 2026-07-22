import json
import os
import uuid
from datetime import datetime, timezone
import F8_Epistemic_Theory_Market_v2 as init_script

MARKET_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_theory_market_v2.jsonl"
OBSERVATIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_observations.jsonl"
REJECTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_rejections.jsonl"
OVERRIDES_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_operational_overrides.jsonl"
REGISTRY_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\source_authority_registry.json"
PREDICTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_predictions.jsonl"
RESOLUTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_prediction_resolutions.jsonl"
CALIBRATION_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_theory_calibration.jsonl"
ADJUSTMENTS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_calibration_adjustments.jsonl"

def load_market():
    market = []
    if not os.path.exists(MARKET_PATH): return market
    with open(MARKET_PATH, 'r') as f:
        for line in f:
            if line.strip():
                market.append(json.loads(line))
    return market

def save_market(market):
    with open(MARKET_PATH, 'w') as f:
        for m in market:
            f.write(json.dumps(m) + "\n")

def load_registry():
    if not os.path.exists(REGISTRY_PATH): return {"sources": {}}
    with open(REGISTRY_PATH, 'r') as f:
        return json.load(f)

def save_registry(reg):
    with open(REGISTRY_PATH, 'w') as f:
        json.dump(reg, f, indent=4)

def is_authenticated(event):
    prov = event.get('provenance')
    if isinstance(prov, dict) and 'type' in prov and 'ref' in prov:
        return True
    return False

def validate_observation(event):
    registry = load_registry()
    source_name = event.get('source')
    
    # 0. Source Ban Check
    if source_name not in registry.get('sources', {}):
        return False, f"Source '{source_name}' is not registered."
    
    source_info = registry['sources'][source_name]
    if source_info.get('trust_score', 1.0) < 0.50:
        return False, f"Source '{source_name}' trust score is below 0.50. Auto-rejected."

    # 1. Required fields
    required = ['theory_group_id', 'supports_theory_id', 'evidence_weight', 'reason', 'is_drill', 'source']
    missing = [f for f in required if f not in event]
    if missing:
        return False, f"Missing required fields: {missing}"
        
    # 2. Source Scope Match
    if event['theory_group_id'] not in source_info.get('allowed_groups', []):
        return False, f"Source '{source_name}' not authorized for {event['theory_group_id']}."

    # 3. Taxonomy match
    market = load_market()
    valid_theory = False
    for m in market:
        if m['theory_id'] == event['supports_theory_id'] and m['theory_group_id'] == event['theory_group_id']:
            valid_theory = True
            break
    if not valid_theory:
        return False, f"Taxonomy mismatch: {event['supports_theory_id']} does not belong to {event['theory_group_id']} in market"
        
    # 4. Weight cap
    weight = event['evidence_weight']
    if not (isinstance(weight, (int, float)) and 0 < weight <= 5.0):
        return False, f"evidence_weight out of bounds (0 < weight <= 5.0): {weight}"
        
    # 5. Reason validation
    if not isinstance(event['reason'], str) or not event['reason'].strip():
        return False, "reason must be a non-empty string"
        
    # 6. Uniqueness of event_id
    if 'event_id' in event:
        if os.path.exists(OBSERVATIONS_PATH):
            with open(OBSERVATIONS_PATH, 'r') as f:
                for line in f:
                    if line.strip():
                        obs = json.loads(line)
                        if obs.get('event_id') == event['event_id']:
                            return False, f"Duplicate event_id: {event['event_id']}"
                            
    # 7. is_drill boolean
    if not isinstance(event['is_drill'], bool):
        return False, "is_drill must be a boolean"
        
    # 8. Source identification / Drill compatibility
    if not isinstance(event['source'], str) or not event['source'].strip():
        return False, "source must be a non-empty string"
    if event['source'] == "test harness" and not event['is_drill']:
        return False, "'test harness' source requires is_drill=True"
        
    # 9. Provenance for non-drills (structured)
    if not event['is_drill']:
        if not is_authenticated(event):
            return False, "Structured provenance (type, ref) is required for non-drill events."
            
    # 10. Cross-source confirmation
    if not event['is_drill'] and weight > 1.0:
        conf_source = event.get('confirming_source')
        if not conf_source or conf_source == source_name:
            return False, "Independent confirming_source required for non-drill weight > 1.0"
        if conf_source == "calibration engine":
            return False, "Derived evidence cannot be used as a confirming source."
        if conf_source not in registry.get('sources', {}):
            return False, f"Confirming source '{conf_source}' is not registered."
        if event['theory_group_id'] not in registry['sources'][conf_source].get('allowed_groups', []):
            return False, f"Confirming source '{conf_source}' not authorized for {event['theory_group_id']}."
        conf_prov = event.get('confirming_provenance')
        if not (isinstance(conf_prov, dict) and 'type' in conf_prov and 'ref' in conf_prov):
            return False, "Structured confirming_provenance is required."
            
    # 11. Forecast validation
    if not event['is_drill'] and weight > 1.0:
        if 'forecast' not in event:
            return False, "forecast block is mandatory for non-drill events with weight > 1.0"
        fc = event['forecast']
        if not isinstance(fc, dict):
            return False, "forecast must be a structured dictionary"
        if not fc.get('claim') or not isinstance(fc['claim'], str):
            return False, "forecast.claim must be a non-empty string"
        if not fc.get('expected_metric') or not isinstance(fc['expected_metric'], str):
            return False, "forecast.expected_metric must be a non-empty string"
        if fc.get('direction') not in ['increase', 'decrease', 'maintain']:
            return False, "forecast.direction must be 'increase', 'decrease', or 'maintain'"
        
        days = fc.get('evaluation_after_days')
        if not isinstance(days, (int, float)) or not (1 <= days <= 365):
            return False, "forecast.evaluation_after_days must be between 1 and 365"
            
        if not fc.get('success_condition') or not isinstance(fc['success_condition'], str):
            return False, "forecast.success_condition must be a non-empty string"
        
    return True, None

def log_rejection(event, reason):
    event_id = event.get('event_id', f"EVT-REJ-{uuid.uuid4().hex[:8].upper()}")
    rejected_utc = datetime.now(timezone.utc).isoformat() + "Z"
    
    # Bounded excerpt to prevent bloat
    excerpt = str(event)[:200]
    source_name = event.get("source", event.get("resolution_source", "unknown"))
    
    authenticated_spoof_guard = is_authenticated(event)
    
    # Degrade trust only if authenticated
    if authenticated_spoof_guard:
        registry = load_registry()
        if source_name in registry.get('sources', {}):
            registry['sources'][source_name]['trust_score'] *= 0.90
            save_registry(registry)
            
    record = {
        "event_id": event_id,
        "rejected_utc": rejected_utc,
        "rejection_reason": reason,
        "raw_event_excerpt": excerpt,
        "source": source_name,
        "authenticated_spoof_guard": authenticated_spoof_guard,
        "rejection_type": event.get("rejection_type", "observation")
    }
    with open(REJECTIONS_PATH, 'a') as f:
        f.write(json.dumps(record) + "\n")

def append_observation(event):
    if 'event_id' not in event:
        event['event_id'] = f"EVT-{uuid.uuid4().hex[:8].upper()}"
    if 'timestamp_utc' not in event:
        event['timestamp_utc'] = datetime.now(timezone.utc).isoformat() + "Z"
        
    valid, reject_reason = validate_observation(event)
    if not valid:
        log_rejection(event, reject_reason)
        print(f"Observation REJECTED by Admission Gate: {reject_reason}")
        return event
    
    # Operator Override Handling
    if event['source'] == 'operator':
        with open(OVERRIDES_PATH, 'a') as f:
            f.write(json.dumps(event) + "\n")
            
        market = load_market()
        for m in market:
            if m['theory_id'] == event['supports_theory_id']:
                m['operational_status'] = 'OPERATIONAL_OVERRIDE'
                m['history'].append({"event": "OPERATIONAL_OVERRIDE", "reason": event['reason'], "timestamp_utc": event['timestamp_utc']})
        save_market(market)
        print(f"Operator Override Applied to {event['supports_theory_id']}. Epistemic math bypassed.")
        return event

    if event['source'] == 'calibration engine':
        with open(ADJUSTMENTS_PATH, 'a') as f:
            f.write(json.dumps(event) + "\n")
    else:
        with open(OBSERVATIONS_PATH, 'a') as f:
            f.write(json.dumps(event) + "\n")
        
    if 'forecast' in event:
        forecast = event['forecast']
        pred_id = f"PRED-{uuid.uuid4().hex[:8].upper()}"
        record = {
            "prediction_id": pred_id,
            "linked_observation_id": event['event_id'],
            "theory_id": event['supports_theory_id'],
            "claim": forecast['claim'],
            "expected_metric": forecast['expected_metric'],
            "baseline": forecast.get('baseline'),
            "target": forecast.get('target'),
            "direction": forecast['direction'],
            "evaluation_after_days": forecast['evaluation_after_days'],
            "success_condition": forecast['success_condition'],
            "timestamp_utc": event['timestamp_utc'],
            "source": event['source']
        }
        with open(PREDICTIONS_PATH, 'a') as f:
            f.write(json.dumps(record) + "\n")
        
    process_observation(event, allow_retirement=True)
    return event

def append_resolution(resolution):
    resolution['rejection_type'] = 'resolution'
    
    src = resolution.get('resolution_source', 'unknown')
    registry = load_registry()
    if src not in registry['sources']:
        return log_rejection(resolution, f"Unregistered resolution source: {src}")
        
    if not registry['sources'][src].get('can_resolve'):
        return log_rejection(resolution, f"Source lacks can_resolve authority: {src}")
        
    pred_id = resolution.get('prediction_id')
    if not pred_id:
        return log_rejection(resolution, "Missing prediction_id in resolution.")
        
    # Check predictions ledger
    found_pred = False
    if os.path.exists(PREDICTIONS_PATH):
        with open(PREDICTIONS_PATH, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        if json.loads(line).get('prediction_id') == pred_id:
                            found_pred = True
                            break
                    except: pass
                    
    if not found_pred:
        return log_rejection(resolution, f"prediction_id not found in ledger: {pred_id}")
        
    # Check resolutions ledger for duplicate
    if os.path.exists(RESOLUTIONS_PATH):
        with open(RESOLUTIONS_PATH, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        if json.loads(line).get('prediction_id') == pred_id:
                            return log_rejection(resolution, f"Prediction {pred_id} is already resolved.")
                    except: pass
                    
    prov = resolution.get('resolution_provenance')
    if not (isinstance(prov, dict) and 'type' in prov and 'ref' in prov):
        return log_rejection(resolution, "Structured resolution_provenance is required.")
        
    if not isinstance(resolution.get('success'), bool):
        return log_rejection(resolution, "resolution.success must be a boolean.")
        
    if not resolution.get('observed_metric') or not isinstance(resolution['observed_metric'], str):
        return log_rejection(resolution, "resolution.observed_metric must be a non-empty string.")
        
    if not isinstance(resolution.get('observed_value'), (int, float)):
        return log_rejection(resolution, "resolution.observed_value must be numeric.")
        
    res_id = f"RES-{uuid.uuid4().hex[:8].upper()}"
    resolution['resolution_id'] = res_id
    if 'resolved_utc' not in resolution:
        resolution['resolved_utc'] = datetime.now(timezone.utc).isoformat() + "Z"
        
    with open(RESOLUTIONS_PATH, 'a') as f:
        f.write(json.dumps(resolution) + "\n")
        
    return resolution

def process_observation(event, allow_retirement=True):
    market = load_market()
    
    DECAY_FACTOR = 0.90
    group_id = event['theory_group_id']
    
    # 1. Decay, apply evidence, and increment observation count
    for m in market:
        if m['theory_group_id'] == group_id and m.get('epistemic_status', m.get('status', 'ACTIVE')) != 'RETIRED':
            if 'accumulated_weight' not in m: m['accumulated_weight'] = 1.0
            if 'observation_count' not in m: m['observation_count'] = 0
            if 'unknown_dominant_streak' not in m: m['unknown_dominant_streak'] = 0
            m.setdefault('epistemic_status', m.get('status', 'ACTIVE'))
            m.setdefault('operational_status', 'NORMAL')
            
            m['accumulated_weight'] *= DECAY_FACTOR
            m['observation_count'] += 1
            
            if m['theory_id'] == event['supports_theory_id']:
                m['accumulated_weight'] += event['evidence_weight']
    
    # 2. Normalize confidence
    group_active = [m for m in market if m['theory_group_id'] == group_id and m.get('epistemic_status', m.get('status', 'ACTIVE')) != 'RETIRED']
    total_weight = sum(m['accumulated_weight'] for m in group_active)
    
    if total_weight > 0:
        for m in group_active:
            m['confidence_score'] = round(m['accumulated_weight'] / total_weight, 4)
            
    # 3. Check unknown persistence
    for m in group_active:
        if m['theory_id'].endswith('U'):
            unknown_conf = m['confidence_score']
            if unknown_conf > 0.50:
                m['unknown_dominant_streak'] += 1
                if m['unknown_dominant_streak'] >= 3 and m['epistemic_status'] != 'THEORY_BIRTH_REQUIRED':
                    m['epistemic_status'] = 'THEORY_BIRTH_REQUIRED'
                    m['history'].append({"event": "THEORY_BIRTH_REQUIRED", "reason": f"Unknown > 0.50 for 3 updates", "timestamp_utc": datetime.now(timezone.utc).isoformat() + "Z"})
            else:
                m['unknown_dominant_streak'] = 0
                if m['epistemic_status'] == 'THEORY_BIRTH_REQUIRED':
                    m['epistemic_status'] = 'ACTIVE'

    # 4. Check retirement (if allowed)
    if allow_retirement:
        final_retirement_evaluation(market, group_id)
    else:
        save_market(market)

def final_retirement_evaluation(market, group_id=None):
    groups_to_eval = {group_id} if group_id else {m['theory_group_id'] for m in market}
    
    for gid in groups_to_eval:
        group_active = [m for m in market if m['theory_group_id'] == gid and m.get('epistemic_status', m.get('status', 'ACTIVE')) != 'RETIRED']
        
        if not group_active: continue
        total_weight = sum(m['accumulated_weight'] for m in group_active)
        obs_count = max(m.get('observation_count', 0) for m in group_active)
        min_obs = group_active[0].get('min_observations_before_retirement', 5)
        min_weight = group_active[0].get('min_total_group_weight_before_retirement', 10.0)
        ret_thresh = group_active[0].get('retirement_threshold', 0.30)
        
        anti_snap_cleared = (obs_count >= min_obs) and (total_weight >= min_weight)
        
        retired_any = False
        if anti_snap_cleared:
            for m in group_active:
                if not m['theory_id'].endswith('U'): 
                    if m['confidence_score'] < ret_thresh:
                        m['epistemic_status'] = 'RETIRED'
                        m['history'].append({"event": "RETIRED", "reason": f"Conf {m['confidence_score']} < {ret_thresh} after {obs_count} obs and {total_weight:.2f} weight", "timestamp_utc": datetime.now(timezone.utc).isoformat() + "Z"})
                        retired_any = True
                        
        if retired_any:
            group_active_post = [m for m in market if m['theory_group_id'] == gid and m.get('epistemic_status', m.get('status', 'ACTIVE')) != 'RETIRED']
            if group_active_post:
                total_weight_post = sum(m['accumulated_weight'] for m in group_active_post)
                if total_weight_post > 0:
                    for m in group_active_post:
                        m['confidence_score'] = round(m['accumulated_weight'] / total_weight_post, 4)

    save_market(market)

def rebuild_market():
    observations = []
    if os.path.exists(OBSERVATIONS_PATH):
        with open(OBSERVATIONS_PATH, 'r') as f:
            for line in f:
                if line.strip():
                    observations.append(json.loads(line))
                    
    if os.path.exists(ADJUSTMENTS_PATH):
        with open(ADJUSTMENTS_PATH, 'r') as f:
            for line in f:
                if line.strip():
                    observations.append(json.loads(line))
                    
    observations.sort(key=lambda x: x.get('timestamp_utc', ''))
                    
    overrides = []
    if os.path.exists(OVERRIDES_PATH):
        with open(OVERRIDES_PATH, 'r') as f:
            for line in f:
                if line.strip(): overrides.append(json.loads(line))
                    
    if os.path.exists(MARKET_PATH): os.remove(MARKET_PATH)
        
    init_script.initialize_market()
    
    for obs in observations:
        process_observation(obs, allow_retirement=False)
        
    market = load_market()
    final_retirement_evaluation(market)
    
    # Replay overrides
    market = load_market()
    for ev in overrides:
        for m in market:
            if m['theory_id'] == ev['supports_theory_id']:
                m['operational_status'] = 'OPERATIONAL_OVERRIDE'
    save_market(market)
    
def emit_market_health():
    market = load_market()
    groups = {}
    for m in market:
        gid = m['theory_group_id']
        if gid not in groups:
            groups[gid] = []
        groups[gid].append(m)
        
    print("--- EPISTEMIC THEORY MARKET HEALTH ---")
    for gid, theories in groups.items():
        active_theories = [t for t in theories if t.get('epistemic_status', t.get('status', 'ACTIVE')) != 'RETIRED']
        obs_count = max([t.get('observation_count', 0) for t in active_theories]) if active_theories else 0
        total_weight = sum([t.get('accumulated_weight', 0) for t in active_theories]) if active_theories else 0
        
        print(f"\nGroup {gid} (Obs: {obs_count}, Total Weight: {total_weight:.2f}):")
        for t in theories:
            epistemic = t.get('epistemic_status', t.get('status', 'ACTIVE'))
            operational = t.get('operational_status', 'NORMAL')
            
            status_flag = f"[{epistemic}"
            if operational != 'NORMAL':
                status_flag += f" / {operational}"
            status_flag += "]"
            
            print(f"  {t['theory_id']:<4} {status_flag:<40} {t.get('confidence_score', 0):.4f} (Weight: {t.get('accumulated_weight', 0):.4f})")
            
if __name__ == "__main__":
    emit_market_health()
