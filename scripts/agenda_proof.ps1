$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
Push-Location $repoRoot

try {
    Write-Host "--- 1. Building Agenda Package ---"
    python -m build "$repoRoot\Agenda"
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to build Agenda" }

    Write-Host "`n--- 2. Creating Clean Verification Environment ---"
    $testEnv = "$repoRoot\agenda_proof_env"
    if (Test-Path $testEnv) { Remove-Item -Recurse -Force $testEnv }
    New-Item -ItemType Directory -Path $testEnv | Out-Null
    
    $venvPath = "$testEnv\.venv"
    python -m venv $venvPath
    $pythonExe = "$venvPath\Scripts\python.exe"
    $pipExe = "$venvPath\Scripts\pip.exe"
    
    Write-Host "Installing Agenda and dependencies..."
    $wheel = Get-ChildItem "$repoRoot\Agenda\dist\*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    # We also need Laboratory for canonical_hash
    $labWheel = Get-ChildItem "$repoRoot\Laboratory\dist\*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    
    & $pipExe install --no-input $wheel.FullName $labWheel.FullName
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install wheels" }
    
    Write-Host "`n--- 3. Running Agenda Proof Script ---"
    $proofDir = "$testEnv\proof_run"
    New-Item -ItemType Directory -Path $proofDir | Out-Null
    
    $proofScript = @"
import json
import subprocess
import sys
import copy
from pathlib import Path

def run_agenda(planner_input, planner_spec):
    with open("input.json", "w") as f: json.dump(planner_input, f)
    with open("spec.json", "w") as f: json.dump(planner_spec, f)
    
    result = subprocess.run([
        sys.executable, "-m", "agenda.cli",
        "--input", "input.json",
        "--spec", "spec.json",
        "--output", "agenda.json"
    ], capture_output=True)
    
    if result.returncode != 0:
        return None
        
    with open("agenda.json", "r") as f:
        return json.load(f)

def main():
    base_dir = Path(".")
    
    base_candidates = [
        {
            "candidate_id": "c1_high_value",
            "expected_information_gain": 100,
            "estimated_compute_cost": 10,
            "estimated_attention_cost": 5,
            "experiment_spec_root": "hash1"
        },
        {
            "candidate_id": "c2_too_expensive",
            "expected_information_gain": 200,
            "estimated_compute_cost": 1000,
            "estimated_attention_cost": 10,
            "experiment_spec_root": "hash2"
        },
        {
            "candidate_id": "c3_filler",
            "expected_information_gain": 50,
            "estimated_compute_cost": 5,
            "estimated_attention_cost": 5,
            "experiment_spec_root": "hash3"
        },
        {
            "candidate_id": "c4_tie_a",
            "expected_information_gain": 50,
            "estimated_compute_cost": 5,
            "estimated_attention_cost": 5,
            "experiment_spec_root": "hash4"
        }
    ]
    
    planner_input_base = {
        "planner_input_schema_version": "1.0.0",
        "state_root": "dummy_state_root",
        "strategy_decision_root": "dummy_strategy_decision_root",
        "candidates": base_candidates
    }
    
    planner_spec = {
        "planner_spec_schema_version": "1.0.0",
        "gain_weight": 1,
        "compute_cost_weight": 1,
        "attention_cost_weight": 1,
        "max_agenda_items": 2,
        "max_compute_budget": 100,
        "max_attention_budget": 100
    }
    
    # 1. Baseline Evaluation
    agenda = run_agenda(planner_input_base, planner_spec)
    assert agenda["status"] == "SUCCESS"
    assert len(agenda["ranked_items"]) == 2
    assert agenda["ranked_items"][0]["candidate_id"] == "c1_high_value"
    assert agenda["ranked_items"][1]["candidate_id"] == "c3_filler"
    assert len(agenda["rejected_items"]) == 1
    assert agenda["rejected_items"][0]["candidate_id"] == "c2_too_expensive"
    assert len(agenda["deferred_items"]) == 1
    assert agenda["deferred_items"][0]["candidate_id"] == "c4_tie_a"
    
    def strip_roots(a):
        # Remove input roots so we can strictly compare structural outputs
        c = copy.deepcopy(a)
        c.pop("planner_input_root", None)
        return c

    expected_stripped = strip_roots(agenda)
    
    # 2. Input Permutation Invariance
    permutations = {
        "reverse": base_candidates[::-1],
        "alphabetical": sorted(base_candidates, key=lambda x: x["candidate_id"]),
        "pairwise_swap": [base_candidates[1], base_candidates[0], base_candidates[3], base_candidates[2]],
        "cyclic_rotation": base_candidates[1:] + [base_candidates[0]]
    }
    
    for name, perm in permutations.items():
        inp = copy.deepcopy(planner_input_base)
        inp["candidates"] = perm
        res = run_agenda(inp, planner_spec)
        res_stripped = strip_roots(res)
        assert res_stripped == expected_stripped, f"Permutation invariance failed on: {name}"
        
    print("SUCCESS: Agenda correctly processed all permutations with identical deterministic output.")
    
    # 3. Duplicate Candidate Rejection
    inp_dupe = copy.deepcopy(planner_input_base)
    inp_dupe["candidates"].append(base_candidates[0]) # Duplicate c1_high_value
    res_dupe = run_agenda(inp_dupe, planner_spec)
    assert res_dupe["status"] == "FAILED_INPUT_VALIDATION", "Agenda failed to reject duplicate candidate IDs"
    print("SUCCESS: Agenda correctly rejected duplicate candidate IDs.")

if __name__ == '__main__':
    main()
"@
    Set-Content -Path "$proofDir\prove_agenda.py" -Value $proofScript
    
    Push-Location $proofDir
    try {
        & $pythonExe "prove_agenda.py"
        if ($LASTEXITCODE -ne 0) { Write-Error "Agenda proof failed" }
    } finally {
        Pop-Location
    }
    
    Write-Host "`nAGENDA PROOF PASSED."

} finally {
    Pop-Location
}
