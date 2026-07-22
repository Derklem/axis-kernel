import os
import json

class AffordanceDiscovery:
    """Phase 95/192/200: Discovers and validates ecosystem affordances."""
    
    def __init__(self, affordance_dir=r"D:\Infinite\Infinity\Runtime\Affordances"):
        self.affordance_dir = affordance_dir

    def discover_affordances(self):
        """Scans the runtime environment for active affordances."""
        affordances = {}
        if not os.path.exists(self.affordance_dir):
            return affordances
            
        for f in os.listdir(self.affordance_dir):
            if f.endswith(".affordance"):
                path = os.path.join(self.affordance_dir, f)
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        data = json.load(file)
                        if self._is_safe_to_propose(data):
                            affordances[data.get("affordance_id")] = data
                except Exception as e:
                    print(f"[-] Affordance Load Error ({f}): {e}")
                    
        return affordances

    def _is_safe_to_propose(self, affordance_def):
        """Validates that an affordance does not violate core security domains."""
        aff_type = affordance_def.get("type")
        

            
        target_path = affordance_def.get("target_path", "")
        
        # Disallow tampering with core engine logic unless strictly bounded
        if "strategy_engine.py" in target_path or "ecosystem_mapping_engine.py" in target_path:
            return False
            
        # Core state protections
        if "calibration_continuity_anchor.json" in target_path:
            return False
            
        return True
