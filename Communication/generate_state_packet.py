import os
import json
import datetime
import hashlib
import argparse
from pathlib import Path
from assessment_resolver import resolve_assessment_lineage

def compute_sha256(filepath):
    if not os.path.exists(filepath):
        return None
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest().lower()

def compute_content_sha256(content_str):
    if content_str is None:
        return None
    sha256 = hashlib.sha256()
    sha256.update(content_str.encode('utf-8'))
    return sha256.hexdigest().lower()

def read_json_files(directory):
    files_data = []
    if not os.path.exists(directory):
        return files_data
        
    for filename in os.listdir(directory):
        if filename.endswith(".json") or ".json." in filename:
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    files_data.append((filename, data))
            except Exception as e:
                print(f"Failed to read {filepath}: {e}")
    return files_data

def get_operator_context(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    return {}

def parse_time(iso_str):
    if not iso_str: return None
    try:
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"
        return datetime.datetime.fromisoformat(iso_str)
    except:
        return None

def read_proposals(directory: str) -> tuple[list[tuple[str, dict]], list[dict]]:
    proposals = []
    errors = []
    
    if not os.path.exists(directory):
        return proposals, errors
        
    for filename in os.listdir(directory):
        if not filename.endswith(".json"):
            continue
            
        path = os.path.join(directory, filename)
        try:
            with open(path, encoding="utf-8-sig") as file:
                proposals.append((filename, json.load(file)))
        except Exception as exc:
            errors.append({
                "filename": filename,
                "error": str(exc),
                "status": "PROPOSAL_JSON_INVALID"
            })
            
    return proposals, errors

def main():
    parser = argparse.ArgumentParser(description="State Packet Generator")
    parser.add_argument("--root", default=r"D:\Infinite\Infinity\Communication", help="Root directory of the communication ledger")
    args = parser.parse_args()
    
    COMM_DIR = args.root
    DRAFTS_DIR = os.path.join(COMM_DIR, "drafts")
    APPROVED_DIR = os.path.join(COMM_DIR, "approved")
    ARCHIVED_DIR = os.path.join(COMM_DIR, "archived")
    RECEIPTS_DIR = os.path.join(COMM_DIR, "receipts")
    RECEIPTS_INVALID_DIR = os.path.join(COMM_DIR, "receipts_invalid")
    OBSERVATIONS_DIR = os.path.join(COMM_DIR, "observations")
    ASSESSMENTS_DIR = os.path.join(COMM_DIR, "assessments")
    PROPOSALS_DIR = os.path.join(COMM_DIR, "proposals")
    proposals, proposal_errors = read_proposals(PROPOSALS_DIR)
    OPERATOR_CONTEXT_PATH = os.path.join(COMM_DIR, "operator_context.json")
    OUTPUT_PATH = os.path.join(COMM_DIR, "CURRENT_STATE.md")

    drafts = read_json_files(DRAFTS_DIR)
    approved = read_json_files(APPROVED_DIR)
    archived_raw = read_json_files(ARCHIVED_DIR)
    archived = {fname: data for fname, data in archived_raw}
    receipts = read_json_files(RECEIPTS_DIR)
    receipts_invalid = read_json_files(RECEIPTS_INVALID_DIR)
    observations = read_json_files(OBSERVATIONS_DIR)
    assessments = read_json_files(ASSESSMENTS_DIR)
    proposals = read_json_files(PROPOSALS_DIR)
    
    context = get_operator_context(OPERATOR_CONTEXT_PATH)
    
    experiments = {}
    
    def ensure_exp(exp_id):
        if exp_id not in experiments:
            experiments[exp_id] = {
                "draft_file": None,
                "approved_file": None,
                "archived_file": None,
                "receipts": [],
                "invalid_receipts": [],
                "corrections": [],
                "observations": [],
                "assessments": [],
                "draft_data": None,
                "archived_data": None,
                "state": "UNKNOWN",
                "hash_mismatch": False,
                "content_hash_mismatch": False
            }
            
    # Process drafts
    for fname, data in drafts:
        exp_id = data.get("experiment_id")
        if exp_id:
            ensure_exp(exp_id)
            experiments[exp_id]["draft_file"] = f"drafts/{fname}"
            experiments[exp_id]["draft_data"] = data
            experiments[exp_id]["state"] = "PLANNED"
            
    # Process approved
    for fname, data in approved:
        exp_id = data.get("experiment_id")
        if exp_id:
            ensure_exp(exp_id)
            experiments[exp_id]["approved_file"] = f"approved/{fname}"
            experiments[exp_id]["draft_data"] = data
            experiments[exp_id]["state"] = "APPROVED"
            
    # Process receipts
    for fname, data in receipts:
        exp_id = data.get("experiment_id")
        if exp_id:
            ensure_exp(exp_id)
            data["_filepath"] = f"receipts/{fname}"
            experiments[exp_id]["receipts"].append(data)
            
    # Process observations
    for fname, data in observations:
        exp_id = data.get("experiment_id")
        if exp_id:
            ensure_exp(exp_id)
            data["_filepath"] = f"observations/{fname}"
            if fname.endswith(".correction.json"):
                experiments[exp_id]["corrections"].append(data)
            else:
                experiments[exp_id]["observations"].append(data)

    # Process assessments
    for fname, data in assessments:
        exp_id = data.get("experiment_id")
        if exp_id:
            ensure_exp(exp_id)
            data["_filepath"] = f"assessments/{fname}"
            experiments[exp_id]["assessments"].append(data)

    # Process invalid receipts
    for fname, data in receipts_invalid:
        exp_id = data.get("experiment_id")
        if exp_id:
            ensure_exp(exp_id)
            if fname.endswith(".correction.json"):
                data["_filepath"] = f"receipts_invalid/{fname}"
                experiments[exp_id]["corrections"].append(data)
            else:
                data["_filepath"] = f"receipts_invalid/{fname}"
                experiments[exp_id]["invalid_receipts"].append(data)

    # Track referenced archives
    referenced_archives = set()
    
    # Resolve active/tracked state
    tracked_experiments = {}
    pending_queue = {}
    
    for exp_id, exp in experiments.items():
        if exp["receipts"] or exp["observations"] or exp["invalid_receipts"]:
            # Sort lists by timestamp
            exp["receipts"].sort(key=lambda r: parse_time(r.get("deployed_at")) or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
            exp["invalid_receipts"].sort(key=lambda r: parse_time(r.get("deployed_at")) or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
            exp["observations"].sort(key=lambda o: parse_time(o.get("observed_at")) or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
            
            # Link archived draft if available
            primary_receipt = exp["receipts"][-1] if exp["receipts"] else (exp["invalid_receipts"][-1] if exp["invalid_receipts"] else {})
            archive_path = primary_receipt.get("archive_path")
            if archive_path and archive_path.startswith("archived/"):
                arch_fname = archive_path.split("archived/")[1]
                referenced_archives.add(arch_fname)
                if arch_fname in archived:
                    exp["archived_file"] = archive_path
                    exp["archived_data"] = archived[arch_fname]
                    # Only verify Hash on valid receipts
                    if exp["receipts"]:
                        stored_hash = primary_receipt.get("draft_sha256")
                        actual_hash = compute_sha256(os.path.join(COMM_DIR, archive_path))
                        if stored_hash and actual_hash and stored_hash != actual_hash:
                            exp["hash_mismatch"] = True
                            
                        # Verify Content Hash
                        stored_content_hash = primary_receipt.get("content_sha256")
                        actual_content_hash = compute_content_sha256(exp["archived_data"].get("content"))
                        if stored_content_hash and actual_content_hash and stored_content_hash != actual_content_hash:
                            exp["content_hash_mismatch"] = True
            
            tracked_experiments[exp_id] = exp
        else:
            pending_queue[exp_id] = exp

    # Collect dynamic warnings
    integrity_warnings = [dict(w) for w in context.get("artifact_corrections", [])]
    for exp_id, exp in tracked_experiments.items():
        for correction in exp["corrections"]:
            # If the correction resolves an explicit operator context warning, mark it resolved
            target_artifact = correction.get("target_artifact") or correction.get("receipt_id")
            resolved_fields = [c.get("field") for c in correction.get("corrections", [])] if "corrections" in correction else []
            
            for w in integrity_warnings:
                if w.get("experiment_id") == exp_id and w.get("artifact") == target_artifact:
                    # Mark resolved if the field matches, or if no specific field is required
                    if not resolved_fields or w.get("field") in resolved_fields:
                        w["status"] = "RESOLVED_BY_CORRECTION"
                        w["correction_artifact"] = correction.get("_filepath", "Unknown")
            
            # Legacy generic tracking for receipt corrections not tied to operator_context
            if "reason" in correction and not target_artifact:
                integrity_warnings.append({
                    "experiment_id": exp_id,
                    "field": correction.get("receipt_id", "UNKNOWN"),
                    "status": correction.get("reason", "INVALID")
                })
    for exp_id, exp in tracked_experiments.items():
        if exp["hash_mismatch"]:
            integrity_warnings.append({
                "experiment_id": exp_id,
                "field": "draft_sha256",
                "status": "HASH_MISMATCH"
            })
        if exp["content_hash_mismatch"]:
            integrity_warnings.append({
                "experiment_id": exp_id,
                "field": "content_sha256",
                "status": "CONTENT_HASH_MISMATCH"
            })
        if not exp.get("archived_data") and exp.get("receipts") and exp_id != "EXP_015_REAL":
             integrity_warnings.append({
                "experiment_id": exp_id,
                "field": "archive_path",
                "status": "MISSING_ARCHIVED_DRAFT"
            })

        # Assessment Lineage Resolution
        if exp.get("assessments"):
            filepaths = [a["_filepath"] for a in exp["assessments"]]
            superseded_by = {}
            lineage_warning = None
            
            for a in exp["assessments"]:
                target = a.get("supersedes")
                if target:
                    if target not in filepaths:
                        lineage_warning = "ASSESSMENT_SUPERSEDES_TARGET_MISSING"
                    elif target == a["_filepath"]:
                        lineage_warning = "ASSESSMENT_SELF_SUPERSESSION"
                    elif a.get("experiment_id") != exp_id:
                        lineage_warning = "ASSESSMENT_EXPERIMENT_MISMATCH"
                    else:
                        if target in superseded_by:
                            lineage_warning = "ASSESSMENT_LINEAGE_CONFLICT" # Multiple branches superseded the same target
                        superseded_by[target] = a["_filepath"]
            
            # Check for cycles
            if not lineage_warning:
                for a in exp["assessments"]:
                    visited = set()
                    curr = a["_filepath"]
                    while curr in superseded_by:
                        if curr in visited:
                            lineage_warning = "ASSESSMENT_LINEAGE_CYCLE"
                            break
                        visited.add(curr)
                        curr = superseded_by[curr]
            
            if not lineage_warning:
                active_assessments = [a for a in exp["assessments"] if a["_filepath"] not in superseded_by.keys()]
                if len(active_assessments) > 1:
                    lineage_warning = "ASSESSMENT_LINEAGE_CONFLICT"
                elif len(active_assessments) == 1:
                    exp["latest_active_assessment"] = active_assessments[0]
                else:
                    lineage_warning = "ASSESSMENT_LINEAGE_CYCLE"
            
            if lineage_warning:
                integrity_warnings.append({
                    "experiment_id": exp_id,
                    "field": "assessments",
                    "status": lineage_warning
                })

    # Orphan detection
    for arch_fname in archived:
        if arch_fname not in referenced_archives:
            # Extract experiment ID from filename if possible, otherwise use UNKNOWN
            parts = arch_fname.split("__")
            exp_id = parts[0] if len(parts) > 0 else "UNKNOWN"
            integrity_warnings.append({
                "experiment_id": exp_id,
                "field": f"archived/{arch_fname}",
                "status": "ORPHANED_ARCHIVE"
            })

    active_warnings = [w for w in integrity_warnings if w.get("status") in ["UNRESOLVED", "HASH_MISMATCH", "CONTENT_HASH_MISMATCH", "MISSING_ARCHIVED_DRAFT", "ORPHANED_ARCHIVE", "PLATFORM_REFERENCE_MISMATCH", "ASSESSMENT_SUPERSEDES_TARGET_MISSING", "ASSESSMENT_LINEAGE_CONFLICT", "ASSESSMENT_LINEAGE_CYCLE", "ASSESSMENT_SELF_SUPERSESSION", "ASSESSMENT_EXPERIMENT_MISMATCH"]]

    lines = []
    lines.append("# Communication Control Plane — Current State\n")
    lines.append(f"**Generated at:** {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    lines.append(f"**Generator version:** v0.2.1")
    lines.append(f"**Source root:** `{COMM_DIR}`\n")
    
    lines.append("## Epistemic State Check")
    lines.append(f"- Draft artifacts: {len(drafts)}")
    lines.append(f"- Approved artifacts: {len(approved)}")
    lines.append(f"- Archived drafts: {len(archived)}")
    lines.append(f"- Deployment receipts: {len(receipts)}")
    lines.append(f"- Observation artifacts: {len(observations)}")
    
    if len(active_warnings) > 0:
        lines.append(f"- Integrity warnings: **{len(active_warnings)} unresolved**\n")
    else:
        lines.append("- Integrity warnings: none\n")
    
    lines.append("## Tracked Experiments")
    for exp_id, exp in tracked_experiments.items():
        lines.append(f"### {exp_id}")
        
        primary_receipt = exp["receipts"][-1] if exp["receipts"] else {}
        primary_obs = exp["observations"][-1] if exp["observations"] else {}
        draft = exp.get("archived_data") or exp.get("draft_data") or {}
        
        # Calculate Observation Window State
        deployed_time = parse_time(primary_receipt.get("deployed_at"))
        obs_window = primary_receipt.get("observation_window", "72h")
        window_state = "NOT_DEPLOYED"
        
        if deployed_time:
            hours = int(obs_window.replace("h", ""))
            due_time = deployed_time + datetime.timedelta(hours=hours)
            now = datetime.datetime.now(datetime.timezone.utc)
            
            is_complete = now >= due_time
            has_obs = len(exp["observations"]) > 0
            
            if is_complete and has_obs:
                window_state = "WINDOW_COMPLETE_OBSERVED"
            elif is_complete and not has_obs:
                window_state = "WINDOW_COMPLETE_UNOBSERVED"
            elif not is_complete and has_obs:
                window_state = "OPEN_WITH_OBSERVATION"
            else:
                window_state = "OPEN_NO_OBSERVATION"
                
        if not exp["receipts"] and exp["invalid_receipts"] and (exp.get("archived_data") or exp.get("archived_file")):
            window_state = "APPROVED_ARCHIVED_NOT_DEPLOYED"
        
        if not parse_time(primary_receipt.get("deployed_at")) and exp.get("receipts"):
            lines.append(f"- **Warning:** Invalid timestamp in receipt, window calculation failed.")
            
        lines.append(f"- **Lifecycle state:** {window_state}")
        
        platform = primary_receipt.get("platform", draft.get("platform", "Unknown"))
        intent = draft.get("intent", "N/A")
        hyp_obj = draft.get("hypothesis", {})
        if isinstance(hyp_obj, dict):
            hyp_str = hyp_obj.get("statement", "N/A")
        elif isinstance(hyp_obj, str):
            hyp_str = hyp_obj
        else:
            hyp_str = "N/A"
        
        if not draft and exp_id == "EXP_015_REAL":
            intent = "MISSING (Provenance Truncated)"
            hyp_str = "MISSING (Provenance Truncated)"
        
        lines.append(f"- **Platform:** {platform}")
        lines.append(f"- **Original intent:** {intent}")
        lines.append(f"- **Hypothesis:** {hyp_str}")
        
        if exp.get("receipts"):
            lines.append(f"- **Deployment evidence:** `{primary_receipt['_filepath']}` (Deployed at {primary_receipt.get('deployed_at', 'Unknown')})")
        else:
            lines.append(f"- **Deployment evidence:** NONE FOUND")
            
        lines.append(f"- **Valid deployment receipts:** {len(exp['receipts'])}")
        lines.append(f"- **Invalid receipts:** {len(exp['invalid_receipts'])}")
            
        if primary_obs:
            lines.append(f"- **Observation evidence:** `{primary_obs['_filepath']}` ({len(exp['observations'])} total)")
            lines.append(f"- **Execution quality:** {primary_obs.get('execution_quality', 'N/A')}")
            lines.append(f"- **Hypothesis result:** {primary_obs.get('hypothesis_result', 'N/A')}")
            lines.append(f"- **Next smallest experiment:** {primary_obs.get('next_smallest_experiment', 'N/A')}")
        else:
            lines.append(f"- **Observation evidence:** PENDING")
            
        if exp.get("assessments"):
            if "latest_active_assessment" in exp:
                latest = exp["latest_active_assessment"]
                lines.append(f"- **Assessment evidence:** `{latest['_filepath']}` ({len(exp['assessments'])} total, showing latest active)")
            else:
                lines.append(f"- **Assessment evidence:** ERROR [LINEAGE_UNRESOLVED]")
        else:
            lines.append(f"- **Assessment evidence:** PENDING")
            
        exp_warnings = [w for w in active_warnings if w.get("experiment_id") == exp_id]
        if exp_warnings:
            statuses = ", ".join([w.get("status", "WARNING") for w in exp_warnings])
            lines.append(f"- **Integrity status:** {statuses}")
        else:
            lines.append(f"- **Integrity status:** OK")
        lines.append("")
        
    lines.append("## Pending Queue")
    for exp_id, exp in pending_queue.items():
        draft = exp.get("draft_data") or {}
        platform = draft.get("platform", "Unknown")
        lines.append(f"- **{exp_id}** ({platform}) - State: {exp['state']}")
    if not pending_queue:
        lines.append("- Queue is empty.")
    lines.append("")
    
    lines.append("## Deferred Dependencies")
    for dep in context.get("deferred_dependencies", []):
        lines.append(f"- {dep}")
    if not context.get("deferred_dependencies"):
        lines.append("- None.")
    lines.append("")
    
    lines.append("## Integrity Warnings")
    if integrity_warnings:
        for w in integrity_warnings:
            exp_id = w.get("experiment_id")
            field = w.get("field")
            status = w.get("status")
            artifact = w.get("artifact", field)
            if status == "UNRESOLVED":
                stored = w.get("stored_value")
                intended = w.get("intended_value")
                lines.append(f"- **{exp_id}**: `{artifact}` -> `{field}` records `{stored}`, but `{intended}` was intended. ({status})")
            elif status == "RESOLVED_BY_CORRECTION":
                stored = w.get("stored_value")
                intended = w.get("intended_value")
                correction_path = w.get("correction_artifact", "UNKNOWN")
                lines.append(f"- ~~**{exp_id}**: `{artifact}` -> `{field}` records `{stored}`, but `{intended}` was intended.~~ (**{status}**: `{correction_path}`)")
            else:
                lines.append(f"- **{exp_id}**: `{artifact}` flagged as {status}")
    else:
        lines.append("- None.")
    lines.append("")
    
    lines.append("## Next Allowed Actions")
    for action in context.get("next_allowed_actions", []):
        lines.append(f"- {action}")
    if not context.get("next_allowed_actions"):
        lines.append("- None defined.")
    lines.append("")
    
    lines.append("## Source Artifact Index")
    for exp_id, exp in experiments.items():
        if exp.get('draft_file') or exp.get('approved_file') or exp.get('archived_file') or exp.get('receipts') or exp.get('observations') or exp.get('assessments'):
            lines.append(f"### {exp_id}")
            if exp.get('draft_file'): lines.append(f"- Draft: `{exp['draft_file']}`")
            if exp.get('approved_file'): lines.append(f"- Approved: `{exp['approved_file']}`")
            if exp.get('archived_file'): lines.append(f"- Archived Draft: `{exp['archived_file']}`")
            for r in exp.get('receipts', []):
                lines.append(f"- Receipt: `{r['_filepath']}`")
            for ir in exp.get('invalid_receipts', []):
                lines.append(f"- Invalid Receipt: `{ir['_filepath']}`")
            for c in exp.get('corrections', []):
                lines.append(f"- Correction: `{c['_filepath']}`")
            for o in exp.get('observations', []):
                lines.append(f"- Observation: `{o['_filepath']}`")
            for a in exp.get('assessments', []):
                lines.append(f"- Assessment: `{a['_filepath']}`")
            if exp_id == "EXP_015_REAL" and not exp.get('archived_file'):
                lines.append("- *Original approved draft artifact: MISSING (Provenance completeness: PARTIAL)*")
            lines.append("")
            
    # Include orphaned archives in source artifact index just in case
    for w in active_warnings:
        if w.get("status") == "ORPHANED_ARCHIVE":
            if w.get("experiment_id") not in experiments:
                lines.append(f"### {w.get('experiment_id')}")
                lines.append(f"- Archived Draft: `{w.get('field')}`")
                lines.append("")
        
    if proposals or proposal_errors:
        lines.append("## Blocked Proposals")
        
        ALLOWED_LIFECYCLE = {"PROPOSED", "DRAFT_READY", "WITHDRAWN", "SUPERSEDED"}
        ALLOWED_AUTH = {"BLOCKED_TARGET_UNRESOLVED", "BLOCKED_RULES_UNVERIFIED", "BLOCKED_ACCOUNT_UNVERIFIED", "AUTHORIZED_FOR_DRAFTING", "AUTHORIZED_FOR_DEPLOYMENT", "WITHDRAWN"}

        for fname, data in proposals:
            exp_id = data.get("experiment_id", fname)
            lines.append(f"### {exp_id}")
            
            # Validation
            schema_errors = []
            if not isinstance(exp_id, str) or not exp_id:
                schema_errors.append("experiment_id must be a non-empty string")
            if not isinstance(data.get("proposal_revision"), int) or data.get("proposal_revision", 0) <= 0:
                schema_errors.append("proposal_revision must be a positive integer")
            if not isinstance(data.get("revision_history"), list):
                schema_errors.append("revision_history must be a list")
            lifecycle = data.get("lifecycle_state")
            if lifecycle not in ALLOWED_LIFECYCLE:
                schema_errors.append(f"lifecycle_state must be one of {ALLOWED_LIFECYCLE}")
            auth = data.get("authorization_state")
            if auth not in ALLOWED_AUTH:
                schema_errors.append(f"authorization_state must be one of {ALLOWED_AUTH}")
            if not isinstance(data.get("intent"), str) or not data.get("intent"):
                schema_errors.append("intent must be a non-empty string")
            if not isinstance(data.get("hypothesis"), str) or not data.get("hypothesis"):
                schema_errors.append("hypothesis must be a non-empty string")
                
            t = data.get("target")
            if not isinstance(t, dict):
                schema_errors.append("target must be an object")
                rules_verified = False
            else:
                rules_verified = t.get("rules_verified")
                if not isinstance(rules_verified, bool):
                    schema_errors.append("target.rules_verified must be boolean")
            
            # Derived Actionability
            actionable = (
                not schema_errors
                and lifecycle == "DRAFT_READY"
                and auth in {"AUTHORIZED_FOR_DRAFTING", "AUTHORIZED_FOR_DEPLOYMENT"}
                and rules_verified is True
            )
            
            lines.append(f"- **Lifecycle state:** {lifecycle}")
            lines.append(f"- **Authorization state:** {auth}")
            if isinstance(t, dict):
                lines.append(f"- **Target constraints:** {t.get('platform', '?')} / {t.get('community', '?')}")
                lines.append(f"- **Rules verified:** {t.get('rules_verified', False)}")
            lines.append(f"- **Proposal revision:** {data.get('proposal_revision', 'UNKNOWN')}")
            lines.append(f"- **Hypothesis:** {data.get('hypothesis', 'UNKNOWN')}")
            
            blocking_condition = "No accessible, rules-verified AI-native target"
            if auth == "BLOCKED_RULES_UNVERIFIED":
                blocking_condition = "Target discovered but rules unverified"
            elif auth == "BLOCKED_ACCOUNT_UNVERIFIED":
                blocking_condition = "Target discovered but Reddit account unverified"
            elif actionable:
                blocking_condition = "None"
            
            lines.append(f"- **Blocking condition:** {blocking_condition}")
            lines.append(f"- **Actionable:** {'Yes' if actionable else 'No'}")
            
            for err in schema_errors:
                lines.append(f"- **PROPOSAL_SCHEMA_INVALID:** {err}")
                
            lines.append("")
            
        for err in proposal_errors:
            lines.append(f"### {err['filename']}")
            lines.append(f"- **Lifecycle state:** INVALID")
            lines.append(f"- **Actionable:** No")
            lines.append(f"- **PROPOSAL_JSON_INVALID:** {err['error']}")
            lines.append("")
            
    output_content = "\n".join(lines)
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(output_content)
        
    print(f"State packet generated successfully at: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
