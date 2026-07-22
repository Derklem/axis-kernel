import os
import json
import datetime
from collections import defaultdict

PREDICTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_predictions.jsonl"
RESOLUTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_prediction_resolutions.jsonl"
CALIBRATION_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_theory_calibration.jsonl"

def read_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except: pass
    return rows

def evaluate_state(resolved, successful):
    if resolved < 5:
        return "UNPROVEN"
    
    acc = successful / resolved
    if acc >= 0.70:
        return "CALIBRATED"
    elif acc < 0.50:
        return "DEGRADED"
    else:
        return "MIXED"

def calculate_calibration():
    predictions = read_jsonl(PREDICTIONS_PATH)
    resolutions = read_jsonl(RESOLUTIONS_PATH)
    calibrations = read_jsonl(CALIBRATION_PATH)
    
    # Map predictions to theory
    pred_to_theory = {}
    for p in predictions:
        p_id = p.get('prediction_id')
        t_id = p.get('theory_id')
        if p_id and t_id:
            pred_to_theory[p_id] = t_id
            
    # Accumulate resolutions by theory
    stats_by_theory = defaultdict(lambda: {"resolved": 0, "successful": 0, "resolution_ids": []})
    for r in resolutions:
        p_id = r.get('prediction_id')
        t_id = pred_to_theory.get(p_id)
        if not t_id: continue
        
        stats_by_theory[t_id]['resolved'] += 1
        stats_by_theory[t_id]['resolution_ids'].append(r.get('resolution_id', p_id))
        if r.get('success') is True:
            stats_by_theory[t_id]['successful'] += 1
            
    # Map current states
    last_state = {}
    for c in calibrations:
        t_id = c.get('theory_id')
        if t_id:
            last_state[t_id] = c
            
    # Calculate and diff
    import uuid
    import re
    import F8_1_Market_Dynamics_Engine as engine
    
    new_writes = []
    adjustments_to_emit = []
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
    
    for t_id, stats in stats_by_theory.items():
        res_cnt = stats['resolved']
        suc_cnt = stats['successful']
        res_ids = stats['resolution_ids']
        acc = suc_cnt / res_cnt if res_cnt > 0 else 0.0
        state = evaluate_state(res_cnt, suc_cnt)
        
        prev = last_state.get(t_id, {})
        prev_res = prev.get('resolved_predictions', 0)
        prev_suc = prev.get('successful_predictions', 0)
        prev_state = prev.get('calibration_state', 'UNPROVEN')
        stable_runs = prev.get('stable_runs', 0)
        adjustment_emitted = prev.get('adjustment_emitted', False)
        cal_id = prev.get('calibration_id')
        
        if state == prev_state:
            stable_runs += 1
        else:
            stable_runs = 0
            adjustment_emitted = False
            
        needs_write = False
        if res_cnt != prev_res or suc_cnt != prev_suc or state != prev_state:
            needs_write = True
            
        emit_adjustment = False
        if state in ["CALIBRATED", "DEGRADED"] and stable_runs >= 1 and not adjustment_emitted:
            emit_adjustment = True
            adjustment_emitted = True
            needs_write = True
            
        if needs_write:
            if state != prev_state or not cal_id:
                cal_id = f"CAL-{uuid.uuid4().hex[:8].upper()}"
                
            new_writes.append({
                "calibration_id": cal_id,
                "theory_id": t_id,
                "resolved_predictions": res_cnt,
                "successful_predictions": suc_cnt,
                "forecast_accuracy": round(acc, 4),
                "calibration_state": state,
                "stable_runs": stable_runs,
                "adjustment_emitted": adjustment_emitted,
                "timestamp_utc": ts
            })
            
            if emit_adjustment:
                m = re.match(r"^T(\d+)", t_id)
                g_id = f"G{m.group(1)}" if m else "G0"
                target_theory = t_id if state == "CALIBRATED" else f"T{g_id[1:]}U"
                
                adj = {
                    "theory_group_id": g_id,
                    "supports_theory_id": target_theory,
                    "evidence_weight": 1.0,
                    "reason": f"Theory state stabilized as {state}",
                    "is_drill": False,
                    "is_derived": True,
                    "source": "calibration engine",
                    "provenance": {
                        "type": "calibration_record", 
                        "ref": cal_id,
                        "derived_from_resolutions": res_ids
                    }
                }
                adjustments_to_emit.append(adj)
            
    if new_writes:
        with open(CALIBRATION_PATH, 'a', encoding='utf-8') as f:
            for w in new_writes:
                f.write(json.dumps(w) + "\n")
                
    for adj in adjustments_to_emit:
        engine.append_observation(adj)
                
    return len(new_writes)

if __name__ == "__main__":
    calculate_calibration()
