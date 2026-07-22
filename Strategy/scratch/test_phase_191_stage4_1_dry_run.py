"""Phase 191 Stage 4.1: Dry-Run Extraction Test
Tests the _dry_run_extraction method on small, known targets.
No file writes. No mutations. Pure analysis.
"""
import sys
import os
import json

sys.path.append(r"D:\infinite\Infinity\Strategy")

# Mock environment for clean test
os.environ["AXIS_MOCK_CONSENSUS"] = "1"
os.environ["AXIS_MOCK_POSTURE"] = "FULL_AGENCY"
os.environ["AXIS_MOCK_IDLE"] = "100"

from strategy_engine import StrategyEngine

engine = StrategyEngine()

# ============================================================
# Test 1: Small pure function — _get_cluster_density
# ============================================================
print("\n" + "=" * 70)
print("TEST 1: Dry-run extraction of _get_cluster_density (small, pure-ish)")
print("=" * 70)

proposal_1 = {
    "intent_id": "DRY_RUN_TEST_001",
    "origin_layer": "self_improvement",
    "proposed_change": {
        "artifact_type": "structural_revision",
        "action": "extract_method",
        "target_path": "strategy_engine.py",
        "delta": {
            "source_function": "_get_cluster_density",
            "rationale": "Test extraction of a small helper method"
        }
    },
    "evaluation": {"meta_mutation_eligible": True}
}

report_1 = engine._dry_run_extraction(proposal_1)
print(f"\nStatus: {report_1['status']}")
print(f"Source slice: {report_1.get('source_slice')}")
print(f"Parameters: {report_1['parameters']}")
print(f"Return values: {len(report_1['return_values'])} found")
print(f"Side effects: {report_1['side_effects']}")
print(f"Is pure: {report_1['is_pure']}")
print(f"Extracted valid: {report_1['extracted_source_valid']}")
print(f"Modified valid: {report_1['modified_source_valid']}")
print(f"Diff summary: {report_1.get('diff_summary')}")
print(f"Errors: {report_1['errors']}")
if report_1.get("receipt_id"):
    print(f"Receipt: {report_1['receipt_id'][:24]}...")

# ============================================================
# Test 2: Pure static method — SemanticContextFilter.evaluate
# ============================================================
print("\n" + "=" * 70)
print("TEST 2: Dry-run extraction of 'evaluate' (SemanticContextFilter)")
print("=" * 70)

proposal_2 = {
    "intent_id": "DRY_RUN_TEST_002",
    "origin_layer": "self_improvement",
    "proposed_change": {
        "artifact_type": "structural_revision",
        "action": "extract_method",
        "target_path": "strategy_engine.py",
        "delta": {
            "source_function": "evaluate",
            "rationale": "Test extraction of static method from SemanticContextFilter"
        }
    },
    "evaluation": {"meta_mutation_eligible": True}
}

report_2 = engine._dry_run_extraction(proposal_2)
print(f"\nStatus: {report_2['status']}")
print(f"Source slice: {report_2.get('source_slice')}")
print(f"Parameters: {report_2['parameters']}")
print(f"Side effects count: {len(report_2.get('side_effects', []))}")
print(f"Is pure: {report_2['is_pure']}")
print(f"Extracted valid: {report_2['extracted_source_valid']}")
print(f"Modified valid: {report_2['modified_source_valid']}")
print(f"Errors: {report_2['errors']}")

# ============================================================
# Test 3: Large impure function — _calc_multi_model_instability
# ============================================================
print("\n" + "=" * 70)
print("TEST 3: Dry-run extraction of _calc_multi_model_instability (medium, impure)")
print("=" * 70)

proposal_3 = {
    "intent_id": "DRY_RUN_TEST_003",
    "origin_layer": "self_improvement",
    "proposed_change": {
        "artifact_type": "structural_revision",
        "action": "extract_method",
        "target_path": "strategy_engine.py",
        "delta": {
            "source_function": "_calc_multi_model_instability",
            "rationale": "Test analysis of medium-sized impure method"
        }
    },
    "evaluation": {"meta_mutation_eligible": True}
}

report_3 = engine._dry_run_extraction(proposal_3)
print(f"\nStatus: {report_3['status']}")
print(f"Source slice: {report_3.get('source_slice')}")
print(f"Parameters: {report_3['parameters']}")
print(f"Side effects count: {len(report_3.get('side_effects', []))}")
for se in report_3.get('side_effects', [])[:10]:
    print(f"  -> {se}")
print(f"Is pure: {report_3['is_pure']}")
print(f"Extracted valid: {report_3['extracted_source_valid']}")
print(f"Modified valid: {report_3['modified_source_valid']}")
print(f"Diff summary: {report_3.get('diff_summary')}")

# ============================================================
# Test 4: Nonexistent function (should fail gracefully)
# ============================================================
print("\n" + "=" * 70)
print("TEST 4: Dry-run extraction of nonexistent function (error case)")
print("=" * 70)

proposal_4 = {
    "intent_id": "DRY_RUN_TEST_004",
    "origin_layer": "self_improvement",
    "proposed_change": {
        "artifact_type": "structural_revision",
        "action": "extract_method",
        "target_path": "strategy_engine.py",
        "delta": {
            "source_function": "this_function_does_not_exist",
            "rationale": "Test error handling for missing function"
        }
    },
    "evaluation": {"meta_mutation_eligible": True}
}

report_4 = engine._dry_run_extraction(proposal_4)
print(f"\nStatus: {report_4['status']}")
print(f"Errors: {report_4['errors']}")

# ============================================================
# Final Summary
# ============================================================
print("\n" + "=" * 70)
print("FINAL SUMMARY")
print("=" * 70)
for i, r in enumerate([report_1, report_2, report_3, report_4], 1):
    slice_info = r.get("source_slice", {})
    lines = slice_info.get("line_count", 0) if slice_info else 0
    purity = "PURE" if r["is_pure"] else "IMPURE"
    print(f"  Test {i}: {r['source_function']:40s} | {r['status']:20s} | {lines:4d} lines | {purity}")

print("\nAll tests completed. No files were modified.")
