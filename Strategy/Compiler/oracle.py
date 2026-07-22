import json
import os

POLICY_PATH = r"D:\Infinite\Infinity\Strategy\Compiler\oracle_policy.v1.json"

class Oracle:
    def __init__(self):
        self.policy = self._load_policy()

    def _load_policy(self):
        if not os.path.exists(POLICY_PATH):
            return {}
        with open(POLICY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    def validate_proposal(self, current_state, metrics, proposal):
        if not isinstance(current_state, dict):
            return "error", f"invalid_state_type:{type(current_state).__name__}"
        if not isinstance(metrics, dict):
            return "error", f"invalid_metrics_type:{type(metrics).__name__}"
        if not isinstance(proposal, dict):
            return "error", f"invalid_proposal_type:{type(proposal).__name__}"
            
        category = proposal.get("category")
        if category == "structural_delta":
            return "requires_human_signature", "structural_delta:human_review_mandated"
            
        target_surface = proposal.get("target_surface")
        proposed_change = proposal.get("proposed_change")
        if not isinstance(proposed_change, dict):
            return "error", "invalid_proposed_change_type"
            
        artifact_type = proposed_change.get("artifact_type")
        
        # 1. Global Auto-Apply Guards
        guards = self.policy.get("auto_apply_guards")
        if not isinstance(guards, dict):
            return "requires_human_signature", "invalid_guards_format"
        
        # Phase 8: Surface Whitelisting
        whitelisted_surfaces = guards.get("whitelist_auto_apply_surfaces", [])
        is_whitelisted = target_surface in whitelisted_surfaces or target_surface == "telemetry_policy"
        
        if not is_whitelisted and target_surface != "telemetry_policy":
            return "requires_human_signature", f"unsupported_surface:{target_surface}"
            
        # Phase 8: Justification Gate
        if guards.get("require_justification_delta") and is_whitelisted:
            full_content = proposed_change.get("full_content", {})
            if not isinstance(full_content, dict): return "error", "full_content_not_dict"
            justification = full_content.get("justification_delta")
            if not justification:
                return "requires_human_signature", "missing_required_justification"

        # Phase 8: Resolution Gate (Judgment under Uncertainty)
        evaluation = proposal.get("evaluation", {})
        if not isinstance(evaluation, dict): return "error", "evaluation_not_dict"
        confidence = evaluation.get("prediction_conf", 1.0)
        min_conf = guards.get("min_autonomous_confidence", 0.8)
        if confidence < min_conf:
            return "requires_human_signature", f"low_confidence:{confidence}<{min_conf}"

        if artifact_type == "legacy_cleanup":
            return "auto_approved", f"justified_cleanup:{target_surface}"
        
        # 1. Global Auto-Apply Guards
        if "require_coherence" in guards:
            coh = current_state.get("coherence", "unknown")
            if not isinstance(coh, str): coh = str(coh)
            if coh.lower() not in guards["require_coherence"]:
                return "requires_human_signature", f"guard_failed:coherence_{coh}"
                
        if "deny_if_stability_below" in guards:
            metrics_stability = metrics.get("stability_index", 100)
            if metrics_stability < guards["deny_if_stability_below"]:
                return "requires_human_signature", f"guard_failed:stability_too_low_{metrics_stability}"
                
        if "deny_if_parse_errors_last_24h_above" in guards:
            metrics_data_health = metrics.get("data_health", {})
            if not isinstance(metrics_data_health, dict): 
                total_errs = int(metrics_data_health) if isinstance(metrics_data_health, (int, float)) else 0
            else:
                errs_obj = metrics_data_health.get("parse_errors_last_24h", 0)
                if isinstance(errs_obj, dict):
                    total_errs = sum(errs_obj.values())
                else:
                    total_errs = int(errs_obj) if errs_obj is not None else 0

            if total_errs > guards["deny_if_parse_errors_last_24h_above"]:
                return "requires_human_signature", f"guard_failed:parse_errors_{total_errs}"
                
        if "deny_if_circuit_trips_last_24h_above" in guards:
            trips = metrics.get("circuit_trips_last_24h", 0)
            if trips > guards["deny_if_circuit_trips_last_24h_above"]:
                return "requires_human_signature", f"guard_failed:circuit_trips_{trips}"

        # 2. Delta Bounds Validation
        bounds_map = self.policy.get("safe_delta_bounds", {})
        bounds_key = artifact_type
        if artifact_type == "stale_thresholds": bounds_key = "stale_thresholds_sec"
            
        bounds = bounds_map.get(bounds_key)
        if not bounds or not isinstance(bounds, dict):
             return "requires_human_signature", f"no_valid_bounds_defined_for:{bounds_key}"
             
        if bounds.get("locked"):
             return "requires_human_signature", f"surface_locked:{bounds_key}"
             
        delta = proposed_change.get("delta", {})
        if not isinstance(delta, dict): return "error", "delta_not_dict"
            
        locked_keys = bounds.get("locked_keys", [])
        
        for comp_key, comp_delta in delta.items():
            if comp_key in locked_keys:
                return "requires_human_signature", f"mutation_on_locked_key:{comp_key}"
                
            if not isinstance(comp_delta, dict): continue
            
            val_from = comp_delta.get("from")
            val_to = comp_delta.get("to")
            
            if val_from is None or val_to is None: continue
                
            try:
                v_from, v_to = float(val_from), float(val_to)
            except Exception: continue
                
            min_abs = bounds.get("min_abs")
            max_abs = bounds.get("max_abs")
            if min_abs is not None and v_to < min_abs:
                return "requires_human_signature", f"below_min_abs:{comp_key}"
            if max_abs is not None and v_to > max_abs:
                return "requires_human_signature", f"above_max_abs:{comp_key}"
                
            max_pct = bounds.get("max_pct_change")
            if max_pct is not None and v_from != 0:
                pct_change = abs(v_to - v_from) / abs(v_from)
                if pct_change > max_pct:
                    return "requires_human_signature", f"bounds_exceeded:{comp_key}_{pct_change*100:.1f}%>{max_pct*100:.1f}%"
                    
        return "auto_approved", f"within_bounds:{artifact_type}"
