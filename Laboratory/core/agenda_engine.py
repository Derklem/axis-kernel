import os
import json
from datetime import datetime, timezone

MIND_DIR = r"D:\Mind"
APPROVED_DIR = os.path.join(MIND_DIR, "Predictions", "approved")
HYP_DIR = os.path.join(MIND_DIR, "Hypotheses", "active")
AGENDA_DIR = os.path.join(MIND_DIR, "Agenda")

SCORING_FORMULA_VERSION = "agenda_v1_uncertainty_age_cost"
INCLUDE_FIXTURES = False

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def calculate_score(design: dict, hyp_path: str) -> tuple[float, dict, list]:
    # 1. Information Gain (maximized when probability is near 0.5)
    prob = design.get("expected_success_probability", 0.5)
    # distance from 0.5 (max 0.5). Scale to 0-1, inverted.
    # p=0.5 -> ig=1.0, p=1.0 -> ig=0.0
    information_gain = max(0.0, 1.0 - (abs(prob - 0.5) * 2.0))
    
    # 2. Epistemic Debt Age
    epistemic_debt_age = 0.0
    if os.path.exists(hyp_path):
        hyp = load_json(hyp_path)
        created_str = hyp.get("created_utc")
        if created_str:
            try:
                created_time = datetime.fromisoformat(created_str)
                age_hours = (datetime.now(timezone.utc) - created_time).total_seconds() / 3600.0
                # Give 0.1 points per hour (2.4 points per day)
                epistemic_debt_age = age_hours * 0.1
            except ValueError:
                pass
                
    # 3. Attention Penalty
    preflight = design.get("preflight_result", {})
    attn = preflight.get("attention_cost", "high")
    attention_penalty = -5.0 if attn == "high" else (-2.0 if attn == "medium" else 0.0)
    
    # 4. Compute Penalty
    compute_mins = preflight.get("estimated_compute_minutes", 60)
    compute_penalty = - (compute_mins / 10.0)
    
    total_score = information_gain + epistemic_debt_age + attention_penalty + compute_penalty
    
    breakdown = {
        "information_gain": round(information_gain, 2),
        "epistemic_debt_age": round(epistemic_debt_age, 2),
        "attention_penalty": round(attention_penalty, 2),
        "compute_penalty": round(compute_penalty, 2)
    }
    
    reasons = []
    if information_gain >= 0.7:
        reasons.append("highest estimated information gain (high uncertainty)")
    if epistemic_debt_age > 1.0:
        reasons.append("tests older unresolved hypothesis")
    if compute_penalty >= -1.0:
        reasons.append("low compute cost")
    if attn != "high":
        reasons.append(f"acceptable attention cost ({attn})")
        
    if not reasons:
        reasons.append("selected based on composite net score")
        
    return round(total_score, 2), breakdown, reasons

def main():
    if not os.path.exists(APPROVED_DIR):
        print("No approved directory.")
        return
        
    os.makedirs(AGENDA_DIR, exist_ok=True)
    
    candidates = []
    
    for filename in os.listdir(APPROVED_DIR):
        if not filename.endswith(".json"):
            continue
            
        file_path = os.path.join(APPROVED_DIR, filename)
        design = load_json(file_path)
        
        if design.get("fixture") is True and not INCLUDE_FIXTURES:
            print(f"Skipping fixture: {filename}")
            continue
        
        exp_id = design.get("id", filename)
        hyp_id = design.get("source_hypothesis_id", "")
        hyp_path = os.path.join(HYP_DIR, f"{hyp_id}.json")
        
        score, breakdown, reasons = calculate_score(design, hyp_path)
        
        candidates.append({
            "experiment_id": exp_id,
            "source_path": file_path,
            "agenda_score": score,
            "score_breakdown": breakdown,
            "_reasons": reasons  # Private key for processing the winner later
        })
        
    if not candidates:
        print("No approved experiments to schedule.")
        return
        
    # Sort descending
    candidates.sort(key=lambda x: x["agenda_score"], reverse=True)
    
    winner = candidates[0]
    
    # Clean up private keys for the final ranking array
    final_ranking = []
    for c in candidates:
        cleaned = {k: v for k, v in c.items() if not k.startswith("_")}
        final_ranking.append(cleaned)
        
    agenda = {
        "scoring_formula_version": SCORING_FORMULA_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "selected_experiment": winner["experiment_id"],
        "agenda_score": winner["agenda_score"],
        "ranking": final_ranking,
        "selection_reason": winner["_reasons"]
    }
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    agenda_filename = f"AGENDA_{timestamp}.json"
    agenda_path = os.path.join(AGENDA_DIR, agenda_filename)
    
    save_json(agenda_path, agenda)
    print(f"Agenda generated: {agenda_filename}")
    print(f"Top selection: {winner['experiment_id']} with score {winner['agenda_score']}")

if __name__ == "__main__":
    main()
