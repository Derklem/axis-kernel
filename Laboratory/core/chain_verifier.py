import os
import sys
import json
import hashlib
from datetime import datetime, timezone

MIND_DIR = r"D:\Mind"
AUDIT_DIR = os.path.join(MIND_DIR, "MutationAudits")
RECEIPT_DIR = os.path.join(MIND_DIR, "MutationReceipts")
GOV_DIR = os.path.join(MIND_DIR, "GovernanceDecisions")
APPROVED_DIR = os.path.join(MIND_DIR, "BeliefUpdates", "approved")
EVAL_DIR = os.path.join(MIND_DIR, "Evaluations")
RESULT_DIR = os.path.join(MIND_DIR, "Laboratory", "sandbox_results")
MANIFEST_DIR = os.path.join(MIND_DIR, "ExecutionManifests")
AGENDA_DIR = os.path.join(MIND_DIR, "Agenda")
DESIGN_DIR = os.path.join(MIND_DIR, "Predictions", "approved")
HYP_DIR = os.path.join(MIND_DIR, "Hypotheses", "active")
BACKUP_HYP_DIR = os.path.join(MIND_DIR, "Hypotheses", "backup")
BUNDLE_DIR = os.path.join(MIND_DIR, "Laboratory", "research_bundles")
VERIFY_DIR = os.path.join(MIND_DIR, "ChainVerifications")

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def hash_file(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Cannot hash missing file: {path}")
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def get_latest_passed_audit() -> str:
    if not os.path.exists(AUDIT_DIR):
        return ""
    audits = [f for f in os.listdir(AUDIT_DIR) if f.startswith("MUTATION_AUDIT_") and f.endswith(".json")]
    audits.sort(reverse=True)
    
    for audit_file in audits:
        path = os.path.join(AUDIT_DIR, audit_file)
        data = load_json(path)
        if data.get("status") == "passed":
            return path
    return ""

def main():
    os.makedirs(VERIFY_DIR, exist_ok=True)
    
    audit_path = get_latest_passed_audit()
    if not audit_path:
        print("No passed MUTATION_AUDIT found.")
        return
        
    audit = load_json(audit_path)
    print(f"Starting Chain Verification from {audit.get('id')}")
    
    lineage = {}
    verified_stages = []
    missing_artifacts = []
    hash_mismatches = []
    authorization_breaks = []
    fixture_lineage = False
    
    def log_missing(stage, artifact_id, expected_dir):
        msg = f"Stage: {stage} | Missing: {artifact_id} expected in {expected_dir}"
        missing_artifacts.append(msg)
        print(f"ERROR: {msg}")
        
    def log_auth_break(stage, reason):
        msg = f"Stage: {stage} | Auth Break: {reason}"
        authorization_breaks.append(msg)
        print(f"ERROR: {msg}")
        
    def check_fixture(data):
        nonlocal fixture_lineage
        if data.get("fixture") is True or data.get("fixture_source") is True:
            fixture_lineage = True
            
    # Stage 1: Audit
    lineage["MUTATION_AUDIT"] = audit.get("id")
    verified_stages.append("MUTATION_AUDIT")
    if audit.get("status") != "passed":
        log_auth_break("MUTATION_AUDIT", "Audit status is not 'passed'")
    
    # Stage 2: Receipt
    receipt_id = audit.get("source_receipt")
    if not receipt_id:
        log_missing("MUTATION_RECEIPT", "None", RECEIPT_DIR)
        return emit_result(lineage, verified_stages, missing_artifacts, hash_mismatches, authorization_breaks, fixture_lineage)
        
    receipt_path = os.path.join(RECEIPT_DIR, f"{receipt_id}.json")
    if not os.path.exists(receipt_path):
        log_missing("MUTATION_RECEIPT", receipt_id, RECEIPT_DIR)
        return emit_result(lineage, verified_stages, missing_artifacts, hash_mismatches, authorization_breaks, fixture_lineage)
        
    receipt = load_json(receipt_path)
    lineage["MUTATION_RECEIPT"] = receipt_id
    verified_stages.append("MUTATION_RECEIPT")
    
    # Stage 3: Governance Decision
    gov_id = receipt.get("gov_decision")
    gov_path = os.path.join(GOV_DIR, f"{gov_id}.json")
    if not os.path.exists(gov_path):
        log_missing("GOV_DECISION", gov_id, GOV_DIR)
        return emit_result(lineage, verified_stages, missing_artifacts, hash_mismatches, authorization_breaks, fixture_lineage)
        
    gov = load_json(gov_path)
    lineage["GOV_DECISION"] = gov_id
    verified_stages.append("GOV_DECISION")
    check_fixture(gov)
    
    if not gov.get("mutation_authorized"):
        log_auth_break("GOV_DECISION", "Mutation was not authorized by governance")
        
    # Stage 4: Belief Update
    update_id = gov.get("source_belief_update")
    update_path = os.path.join(APPROVED_DIR, f"{update_id}.json")
    if not os.path.exists(update_path):
        log_missing("BELIEF_UPDATE", update_id, APPROVED_DIR)
        return emit_result(lineage, verified_stages, missing_artifacts, hash_mismatches, authorization_breaks, fixture_lineage)
        
    update = load_json(update_path)
    lineage["BELIEF_UPDATE"] = update_id
    verified_stages.append("BELIEF_UPDATE")
    check_fixture(update)
    
    if not update.get("requires_human_or_governance_approval"):
        log_auth_break("BELIEF_UPDATE", "Did not require governance approval")
        
    # Stage 5: Evaluation
    eval_id = update.get("source_evaluation")
    eval_path = os.path.join(EVAL_DIR, f"{eval_id}.json")
    if not os.path.exists(eval_path):
        log_missing("EVALUATION", eval_id, EVAL_DIR)
        return emit_result(lineage, verified_stages, missing_artifacts, hash_mismatches, authorization_breaks, fixture_lineage)
        
    evaluation = load_json(eval_path)
    lineage["EVALUATION"] = eval_id
    verified_stages.append("EVALUATION")
    check_fixture(evaluation)
    
    # Stage 6: Experiment Result
    result_id = evaluation.get("source_result")
    if not result_id:
        log_missing("EXPERIMENT_RESULT", "None (Missing source_result backlink)", RESULT_DIR)
        return emit_result(lineage, verified_stages, missing_artifacts, hash_mismatches, authorization_breaks, fixture_lineage)
        
    result_path = os.path.join(RESULT_DIR, f"{result_id}.json")
    if not os.path.exists(result_path):
        log_missing("EXPERIMENT_RESULT", result_id, RESULT_DIR)
        return emit_result(lineage, verified_stages, missing_artifacts, hash_mismatches, authorization_breaks, fixture_lineage)
        
    result = load_json(result_path)
    lineage["EXPERIMENT_RESULT"] = result_id
    verified_stages.append("EXPERIMENT_RESULT")
    check_fixture(result)
    
    # Stage 7: Execution Manifest
    manifest_id = result.get("source_manifest")
    manifest_path = os.path.join(MANIFEST_DIR, f"{manifest_id}.json")
    if not os.path.exists(manifest_path):
        log_missing("EXEC_MANIFEST", manifest_id, MANIFEST_DIR)
        return emit_result(lineage, verified_stages, missing_artifacts, hash_mismatches, authorization_breaks, fixture_lineage)
        
    manifest = load_json(manifest_path)
    lineage["EXEC_MANIFEST"] = manifest_id
    verified_stages.append("EXEC_MANIFEST")
    check_fixture(manifest)
    
    # Stage 8: Agenda
    agenda_filename = manifest.get("source_agenda")
    if not agenda_filename:
        log_missing("AGENDA", "None (Missing source_agenda backlink)", AGENDA_DIR)
        return emit_result(lineage, verified_stages, missing_artifacts, hash_mismatches, authorization_breaks, fixture_lineage)
        
    agenda_id = agenda_filename.replace(".json", "")
    agenda_path = os.path.join(AGENDA_DIR, agenda_filename)
    if not os.path.exists(agenda_path):
        log_missing("AGENDA", agenda_id, AGENDA_DIR)
        return emit_result(lineage, verified_stages, missing_artifacts, hash_mismatches, authorization_breaks, fixture_lineage)
        
    agenda = load_json(agenda_path)
    lineage["AGENDA"] = agenda_id
    verified_stages.append("AGENDA")
    check_fixture(agenda)
    
    # Stage 9: Experimental Design
    design_id = agenda.get("selected_experiment")
    if not design_id:
        log_missing("EXP_DESIGN", "None (Missing selected_experiment backlink)", DESIGN_DIR)
        return emit_result(lineage, verified_stages, missing_artifacts, hash_mismatches, authorization_breaks, fixture_lineage)
        
    design_path = os.path.join(DESIGN_DIR, f"{design_id}.json")
    if not os.path.exists(design_path):
        log_missing("EXP_DESIGN", design_id, DESIGN_DIR)
        return emit_result(lineage, verified_stages, missing_artifacts, hash_mismatches, authorization_breaks, fixture_lineage)
        
    design = load_json(design_path)
    lineage["EXP_DESIGN"] = design_id
    verified_stages.append("EXP_DESIGN")
    check_fixture(design)
    
    # Stage 10: Hypothesis
    hyp_id = design.get("source_hypothesis_id")
    if not hyp_id:
        log_missing("HYPOTHESIS", "None (Missing source_hypothesis_id backlink)", HYP_DIR)
        
    hyp_path = os.path.join(HYP_DIR, f"{hyp_id}.json")
    if hyp_id and not os.path.exists(hyp_path):
        log_missing("HYPOTHESIS", hyp_id, HYP_DIR)
        # Note: If mutated, the active hypothesis has changed, but it should still physically exist.
        
    if hyp_id and os.path.exists(hyp_path):
        hypothesis = load_json(hyp_path)
        lineage["HYPOTHESIS"] = hyp_id
        verified_stages.append("HYPOTHESIS")
        check_fixture(hypothesis)
        
        # Stage 11: Research Bundle
        # We might not have a research bundle ID explicitly in the hypothesis if it wasn't tracked early on, but we check if it exists.
        bundle_id = hypothesis.get("source_bundle")
        if bundle_id:
            bundle_path = os.path.join(BUNDLE_DIR, f"{bundle_id}.json")
            if not os.path.exists(bundle_path):
                log_missing("RESEARCH_BUNDLE", bundle_id, BUNDLE_DIR)
            else:
                lineage["RESEARCH_BUNDLE"] = bundle_id
                verified_stages.append("RESEARCH_BUNDLE")
                check_fixture(load_json(bundle_path))
    
    emit_result(lineage, verified_stages, missing_artifacts, hash_mismatches, authorization_breaks, fixture_lineage)


def emit_result(lineage, verified_stages, missing_artifacts, hash_mismatches, authorization_breaks, fixture_lineage):
    is_passed = len(missing_artifacts) == 0 and len(hash_mismatches) == 0 and len(authorization_breaks) == 0
    status = "passed" if is_passed else "failed"
    final_result = "complete_chain_verified" if is_passed else "chain_broken"
    
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    verify_id = f"CHAIN_VERIFY_{timestamp}"
    
    verify_artifact = {
        "id": verify_id,
        "status": status,
        "lineage": lineage,
        "verified_stages": verified_stages,
        "missing_artifacts": missing_artifacts,
        "hash_mismatches": hash_mismatches,
        "authorization_breaks": authorization_breaks,
        "fixture_lineage": fixture_lineage,
        "final_result": final_result
    }
    
    verify_path = os.path.join(VERIFY_DIR, f"{verify_id}.json")
    save_json(verify_path, verify_artifact)
    
    print(f"Chain Verification {status.upper()}: {final_result}")
    if not is_passed:
        if missing_artifacts: print(f"Missing Artifacts: {missing_artifacts}")
        if hash_mismatches: print(f"Hash Mismatches: {hash_mismatches}")
        if authorization_breaks: print(f"Auth Breaks: {authorization_breaks}")
    print(f"Verification Artifact generated: {verify_id}")


if __name__ == "__main__":
    main()
