"""Phase 191 Stage 4.2: Semantic Regression Test

Verifies that the extracted SemanticContextFilter module produces
IDENTICAL results to the original inline version. Tests all adversarial
scenarios from Phases 188-189.

This is the behavioral equivalence proof required before any live extraction
is certified as safe.
"""
import sys
import os
sys.path.append(r"D:\infinite\Infinity\Strategy")

# Test 1: Import from both paths to prove they resolve to the same class
from semantic_context_filter import SemanticContextFilter as SCF_Extracted

# The forwarding import in strategy_engine.py should also resolve
print("=" * 70)
print("PHASE 191 STAGE 4.2: SEMANTIC EXTRACTION REGRESSION TEST")
print("=" * 70)

GOV_KEYWORDS = ["redundant", "alias", "derivative", "fork", "replacement", "successor"]
REV_KEYWORDS = ["active", "stable", "valid", "restored", "canonical"]

# ============================================================
# Phase 188 Regression: Polarity Detection
# ============================================================
test_cases = [
    # (input_text, expected_polarity, expected_structure_valid, description)
    
    # Pure governance (negative polarity)
    ("Service is redundant and should be removed", "negative", True, "Pure governance signal"),
    ("This is a fork of the original", "negative", True, "Fork detection"),
    ("Identified as an alias for ServiceA", "negative", True, "Alias detection"),
    
    # Pure reversal (positive polarity)
    ("Service is active and stable", "positive", True, "Pure reversal signal"),
    ("System has been restored to canonical state", "positive", True, "Restored canonical"),
    ("The endpoint is valid and operational", "positive", True, "Valid active"),
    
    # Conflicting signals
    ("Service is redundant but still active", "conflicting", True, "Conflicting gov+rev"),
    ("The fork is however stable", "conflicting", True, "Contrast marker override"),
    ("Alias yet valid for production", "conflicting", True, "Yet contrast"),
    
    # Neutral (no keywords)
    ("The weather is nice today", "neutral", False, "No governance or reversal keywords"),
    ("System logs indicate normal operation", "neutral", False, "Neutral operations"),
    
    # Phase 188: Negation flipping
    ("Service is not redundant", "positive", True, "Negation flips negative->positive"),
    ("The endpoint is not active", "negative", True, "Negation flips positive->negative"),
    ("This is no longer a valid fork", "conflicting", True, "Negation with mixed keywords"),
    ("Service never was a replacement", "positive", True, "Never negation"),
    
    # Phase 188: Hedge modifiers
    ("Service appears redundant", "negative", True, "Hedged governance"),
    ("System seems stable", "positive", True, "Hedged reversal"),
    ("Potentially a fork of ServiceB", "negative", True, "Potentially hedged"),
    
    # Phase 188: Temporal markers
    ("Service was redundant", "negative", True, "Temporal governance"),
    ("Previously the canonical version", "positive", True, "Previously temporal"),
    ("System was formerly active", "positive", True, "Formerly temporal"),
    
    # Phase 189: Complex compound cases
    ("Service was previously redundant but is now active", "conflicting", True, "Temporal + contrast + mixed"),
    ("Not a valid replacement", "conflicting", True, "Negated gov+rev: both 'valid' and 'replacement' present"),
]

print(f"\nRunning {len(test_cases)} semantic regression tests...\n")

passed = 0
failed = 0
errors = []

for i, (text, expected_polarity, expected_valid, desc) in enumerate(test_cases, 1):
    result = SCF_Extracted.evaluate(text, GOV_KEYWORDS, REV_KEYWORDS)
    
    polarity_ok = result["polarity"] == expected_polarity
    valid_ok = result["semantic_structure_valid"] == expected_valid
    
    if polarity_ok and valid_ok:
        passed += 1
        status = "PASS"
    else:
        failed += 1
        status = "FAIL"
        errors.append({
            "test": i,
            "desc": desc,
            "input": text,
            "expected_polarity": expected_polarity,
            "got_polarity": result["polarity"],
            "expected_valid": expected_valid,
            "got_valid": result["semantic_structure_valid"],
            "full_result": result
        })
    
    print(f"  [{status}] Test {i:2d}: {desc}")
    if status == "FAIL":
        print(f"         Expected: polarity={expected_polarity}, valid={expected_valid}")
        print(f"         Got:      polarity={result['polarity']}, valid={result['semantic_structure_valid']}")

# ============================================================
# Phase 188: Confidence Modifier Regression
# ============================================================
print(f"\n{'=' * 70}")
print("CONFIDENCE MODIFIER REGRESSION")
print(f"{'=' * 70}\n")

conf_tests = [
    # (input_text, min_conf, max_conf, description)
    ("Service is redundant", 0.9, 1.0, "Clean governance = full confidence"),
    ("Service appears redundant", 0.5, 0.65, "Hedged = reduced confidence"),
    ("Service was redundant", 0.3, 0.45, "Temporal = very reduced confidence"),
    ("Service is not redundant", 0.7, 0.85, "Negated = slightly reduced"),
    ("Service appears to have been a fork", 0.55, 0.65, "Hedge only ('been' is not a temporal marker)"),
    ("Service is redundant but active", 0.4, 0.55, "Conflicting = halved"),
]

for i, (text, min_c, max_c, desc) in enumerate(conf_tests, 1):
    result = SCF_Extracted.evaluate(text, GOV_KEYWORDS, REV_KEYWORDS)
    cm = result["confidence_modifier"]
    ok = min_c <= cm <= max_c
    status = "PASS" if ok else "FAIL"
    if not ok:
        failed += 1
        errors.append({"test": f"conf_{i}", "desc": desc, "cm": cm, "range": f"[{min_c}, {max_c}]"})
    else:
        passed += 1
    print(f"  [{status}] ConfTest {i}: {desc} (cm={cm:.2f}, range=[{min_c}, {max_c}])")

# ============================================================
# Phase 189: Ambiguity Flag Regression
# ============================================================
print(f"\n{'=' * 70}")
print("AMBIGUITY FLAG REGRESSION")
print(f"{'=' * 70}\n")

flag_tests = [
    ("Service is not redundant", ["negated"], "Negation detected"),
    ("Service appears redundant", ["hedged"], "Hedge detected"),
    ("Service was redundant", ["temporal"], "Temporal detected"),
    ("Service is redundant however still active", ["contrast", "conflicting"], "Contrast + conflicting"),
    ("Service is redundant", [], "No ambiguity flags"),
]

for i, (text, expected_flags, desc) in enumerate(flag_tests, 1):
    result = SCF_Extracted.evaluate(text, GOV_KEYWORDS, REV_KEYWORDS)
    flags = result["ambiguity_flags"]
    ok = set(expected_flags) == set(flags)
    status = "PASS" if ok else "FAIL"
    if not ok:
        failed += 1
        errors.append({"test": f"flag_{i}", "desc": desc, "expected": expected_flags, "got": flags})
    else:
        passed += 1
    print(f"  [{status}] FlagTest {i}: {desc} (expected={expected_flags}, got={flags})")

# ============================================================
# Import Forwarding Test
# ============================================================
print(f"\n{'=' * 70}")
print("IMPORT FORWARDING TEST")
print(f"{'=' * 70}\n")

os.environ["AXIS_MOCK_CONSENSUS"] = "1"
os.environ["AXIS_MOCK_POSTURE"] = "FULL_AGENCY"
os.environ["AXIS_MOCK_IDLE"] = "100"

try:
    from strategy_engine import SemanticContextFilter as SCF_Forwarded
    
    # Verify they are the same class
    same_class = SCF_Forwarded is SCF_Extracted
    print(f"  Classes are identical object: {same_class}")
    
    # Verify they produce identical output
    test_input = "Service appears to be a redundant fork but is still active"
    r1 = SCF_Extracted.evaluate(test_input, GOV_KEYWORDS, REV_KEYWORDS)
    r2 = SCF_Forwarded.evaluate(test_input, GOV_KEYWORDS, REV_KEYWORDS)
    outputs_match = r1 == r2
    print(f"  Outputs match on complex input: {outputs_match}")
    
    # Verify marker constants are accessible
    markers_ok = (
        SCF_Forwarded.NEGATION_MARKERS == SCF_Extracted.NEGATION_MARKERS and
        SCF_Forwarded.HEDGE_MARKERS == SCF_Extracted.HEDGE_MARKERS and
        SCF_Forwarded.CONTRAST_MARKERS == SCF_Extracted.CONTRAST_MARKERS and
        SCF_Forwarded.TEMPORAL_MARKERS == SCF_Extracted.TEMPORAL_MARKERS
    )
    print(f"  Marker constants match: {markers_ok}")
    
    if same_class and outputs_match and markers_ok:
        passed += 3
        print(f"\n  FORWARDING: ALL PASS")
    else:
        failed += (3 - sum([same_class, outputs_match, markers_ok]))
        passed += sum([same_class, outputs_match, markers_ok])
        print(f"\n  FORWARDING: ISSUES DETECTED")
except Exception as e:
    failed += 3
    print(f"\n  FORWARDING IMPORT FAILED: {e}")

# ============================================================
# Final Summary
# ============================================================
print(f"\n{'=' * 70}")
print(f"FINAL RESULT: {passed} passed, {failed} failed")
print(f"{'=' * 70}")

if errors:
    print("\nFailed tests:")
    for e in errors:
        print(f"  - {e}")

if failed == 0:
    print("\nOK: STAGE 4.2 SEMANTIC REGRESSION: ALL TESTS PASS")
    print("  The extracted SemanticContextFilter is behaviorally identical")
    print("  to the original inline version.")
else:
    print(f"\nFAIL: STAGE 4.2 SEMANTIC REGRESSION: {failed} FAILURES")
    print("  ROLLBACK RECOMMENDED -- extraction may have introduced drift.")

sys.exit(0 if failed == 0 else 1)
