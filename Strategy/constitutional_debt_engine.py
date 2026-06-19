class ConstitutionalDebtEngine:
    def __init__(self):
        self.scoring_version = "199.1"

    def evaluate_delta_weight(self, target_file, diff_content, semantic_risk_score):
        """
        Deterministically evaluates the strategic utility and risk burden of a diff.
        """
        import os
        
        added_lines = [l for l in diff_content.splitlines() if l.startswith("+") and not l.startswith("+++")]
        removed_lines = [l for l in diff_content.splitlines() if l.startswith("-") and not l.startswith("---")]
        
        # UTILITY PROXIES
        # 1. test_surface_delta: +def test_ or +class Test
        test_surface_delta = sum(1 for l in added_lines if "def test_" in l or "class Test" in l) * 0.1
        
        # 2. maintainability_proxy: more lines removed than added (if significant)
        maintainability_proxy = 0.0
        if len(removed_lines) > len(added_lines) and len(removed_lines) > 5:
            maintainability_proxy = 0.1
            
        # 3. dependency_reduction_proxy: -import
        dependency_reduction_proxy = sum(1 for l in removed_lines if "import " in l) * 0.05
        
        # 4. churn_penalty: broad diff across many hunks
        hunk_count = diff_content.count("@@ -")
        churn_penalty = 0.0
        if hunk_count > 5:
            churn_penalty = 0.1
            
        # Basic utility baseline (prevents 0.0 for normal functional changes)
        baseline_utility = 0.0
        if len(added_lines) > 0 and test_surface_delta == 0 and maintainability_proxy == 0:
            baseline_utility = 0.1
            
        # Strategy relevance
        if "strategy" in target_file.lower():
            baseline_utility += 0.2
            
        utility_score = (baseline_utility + test_surface_delta + maintainability_proxy + dependency_reduction_proxy) - churn_penalty
        
        # BURDEN PROXIES
        # 1. complexity_delta_proxy: loops, ifs, try/except
        complexity_keywords = ["if ", "for ", "while ", "try:", "except"]
        complexity_delta_proxy = sum(1 for l in added_lines for kw in complexity_keywords if kw in l) * 0.02
        
        # 2. dependency_addition_penalty: +import
        dependency_addition_penalty = sum(1 for l in added_lines if "import " in l) * 0.05
        
        # 3. replay_cost_proxy: large diff size
        replay_cost_proxy = 0.1 if len(added_lines) + len(removed_lines) > 100 else 0.0
        
        # 4. semantic_risk
        semantic_risk = semantic_risk_score * 0.8
        
        burden_score = semantic_risk + complexity_delta_proxy + replay_cost_proxy + dependency_addition_penalty
        
        # Cap scores
        utility_score = min(1.0, max(0.0, utility_score))
        burden_score = min(1.0, max(0.0, burden_score))
        
        # Classification
        if burden_score > 0.4:
            classification = "increases_constitutional_burden"
        elif utility_score <= 0.2 and burden_score <= 0.3:
            classification = "safe_but_useless"
        else:
            classification = "safe_and_useful"
            
        return {
            "scoring_version": self.scoring_version,
            "utility_score": round(utility_score, 2),
            "burden_score": round(burden_score, 2),
            "classification": classification,
            "authority": "advisory_governance"
        }

    def evaluate_recovery_weight(self, patch_content, applies_cleanly, files_touched, validator_surface_touched):
        """
        Deterministically evaluates a recovery patch.
        A reverse patch generally reduces burden by removing complexity, but carries risk if it touches validators.
        """
        # Re-use evaluate_delta_weight with zero semantic risk (since the semantic gate was for forward diffs)
        # But we treat the patch as a standard diff.
        base_eval = self.evaluate_delta_weight("synthetic.patch", patch_content, 0.0)
        
        # In a revert patch, lines added are old code coming back, lines removed are the bad code leaving.
        added_lines = [l for l in patch_content.splitlines() if l.startswith("+") and not l.startswith("+++")]
        removed_lines = [l for l in patch_content.splitlines() if l.startswith("-") and not l.startswith("---")]
        
        # Burden reduction is correlated with how much complexity was removed (which appears as - lines in the revert patch)
        complexity_keywords = ["if ", "for ", "while ", "try:", "except"]
        complexity_removed = sum(1 for l in removed_lines for kw in complexity_keywords if kw in l) * 0.02
        lines_removed_proxy = len(removed_lines) * 0.005
        
        burden_reduction_estimate = complexity_removed + lines_removed_proxy + base_eval["utility_score"]
        
        recovery_risk_score = 0.1
        if validator_surface_touched:
            recovery_risk_score += 0.5
        if not applies_cleanly:
            recovery_risk_score += 1.0
            
        return {
            "scoring_version": self.scoring_version,
            "burden_reduction_estimate": round(min(1.0, burden_reduction_estimate), 2),
            "recovery_risk_score": round(min(1.0, recovery_risk_score), 2),
            "applies_cleanly": applies_cleanly,
            "files_touched": files_touched,
            "validator_surface_touched": validator_surface_touched,
            "authority": "advisory_governance"
        }
