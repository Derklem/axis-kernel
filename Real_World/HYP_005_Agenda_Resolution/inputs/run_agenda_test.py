import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

def run_agenda(planner_input, planner_spec, out_path, env_python):
    base_dir = Path(__file__).resolve().parent.parent
    inputs_dir = base_dir / "inputs"
    
    input_path = inputs_dir / "temp_input.json"
    spec_path = inputs_dir / "temp_spec.json"
    
    with open(input_path, "w") as f: json.dump(planner_input, f, indent=2)
    with open(spec_path, "w") as f: json.dump(planner_spec, f, indent=2)
    
    subprocess.run([
        env_python, "-m", "agenda.cli",
        "--input", str(input_path),
        "--spec", str(spec_path),
        "--output", str(out_path)
    ], check=True)
    
    with open(out_path, "r") as f:
        return json.load(f)

def main():
    base_dir = Path(__file__).resolve().parent.parent
    agenda_dir = base_dir / "agenda"
    if agenda_dir.exists():
        shutil.rmtree(agenda_dir)
    agenda_dir.mkdir(parents=True, exist_ok=True)
    
    env_python = str(base_dir.parent / "env" / "Scripts" / "python.exe")
    
    spec = {
        "planner_spec_schema_version": "1.0.0",
        "gain_weight": 2,
        "compute_cost_weight": 1,
        "attention_cost_weight": 1,
        "max_agenda_items": 10,
        "max_compute_budget": 100,
        "max_attention_budget": 100
    }
    
    # Candidates
    c1 = {
        "candidate_id": "c1_high_gain_low_cost",
        "expected_information_gain": 50, # score = 100 - 10 - 10 = 80
        "estimated_compute_cost": 10,
        "estimated_attention_cost": 10,
        "experiment_spec_root": "a"*64
    }
    c2 = {
        "candidate_id": "c2_med_gain_high_compute",
        "expected_information_gain": 30, # score = 60 - 50 - 10 = 0
        "estimated_compute_cost": 50,
        "estimated_attention_cost": 10,
        "experiment_spec_root": "b"*64
    }
    c3 = {
        "candidate_id": "c3_blows_budget",
        "expected_information_gain": 40, # score = 80 - 60 - 10 = 10
        "estimated_compute_cost": 60,
        "estimated_attention_cost": 10,
        "experiment_spec_root": "c"*64
    }
    c4 = {
        "candidate_id": "c4_negative_score",
        "expected_information_gain": 10, # score = 20 - 150 - 50 = -180
        "estimated_compute_cost": 150, # Exceeds absolute max budget (100)
        "estimated_attention_cost": 50,
        "experiment_spec_root": "d"*64
    }
    
    planner_input = {
        "planner_input_schema_version": "1.0.0",
        "state_root": "1"*64,
        "strategy_decision_root": "2"*64,
        "candidates": [c1, c2, c3, c4]
    }
    
    print("Running Agenda ranking...")
    res = run_agenda(planner_input, spec, agenda_dir / "agenda_1.json", env_python)
    
    assert res["status"] == "SUCCESS"
    assert res["summary"]["total_compute_cost"] <= 100
    assert res["summary"]["total_attention_cost"] <= 100
    
    ranked_ids = [i["candidate_id"] for i in res["ranked_items"]]
    deferred_ids = [i["candidate_id"] for i in res["deferred_items"]]
    rejected_ids = [i["candidate_id"] for i in res["rejected_items"]]
    
    print("Ranked:", ranked_ids)
    print("Deferred:", deferred_ids)
    print("Rejected:", rejected_ids)
    
    # Expected ordering by score: c1 (80), c3 (10), c2 (0), c4 (-80)
    # c1 computes = 10, total = 10
    # c3 computes = 60, total = 70
    # c2 computes = 50, total = 120 (blows compute budget!) -> should be deferred
    # c4 score = -80 (negative) -> rejected maybe, or deferred due to negative score
    
    print("Agenda engine evaluated limits successfully!")

if __name__ == "__main__":
    main()
