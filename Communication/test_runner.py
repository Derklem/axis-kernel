import json
import os
import datetime
import hashlib
import platform
import random
from itertools import permutations
from collections import Counter
from assessment_resolver import resolve_assessment_lineage

def compute_sha256(filepath):
    if not os.path.exists(filepath):
        return None
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest().lower()

def sha256_json(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def canonicalize_resolution(result: dict) -> dict:
    return {
        "current_by_experiment": dict(
            sorted(result.get("current_by_experiment", {}).items())
        ),
        "warnings": sorted(
            result.get("warnings", []),
            key=lambda w: (
                w.get("experiment_id", ""),
                w.get("status", ""),
                w.get("assessment", ""),
                w.get("target", ""),
            ),
        ),
        "fatal_experiments": sorted(result.get("fatal_experiments", [])),
    }

base = 'D:\\Infinite\\Infinity\\Communication\\Tests\\assessment_lineage\\'

# The fixture manifest defined exactly per GPT's specification.
fixture_manifest = {
    'missing_target': {
        'expected_warnings': ['ASSESSMENT_SUPERSEDES_TARGET_MISSING'],
        'expected_current': {}
    },
    'circular_chain': {
        'expected_warnings': ['ASSESSMENT_LINEAGE_CYCLE', 'ASSESSMENT_LINEAGE_CYCLE'],
        'expected_current': {}
    },
    'multiple_branches': {
        'expected_warnings': ['ASSESSMENT_LINEAGE_CONFLICT', 'ASSESSMENT_LINEAGE_CONFLICT'],
        'expected_current': {}
    },
    'self_supersession': {
        'expected_warnings': ['ASSESSMENT_SELF_SUPERSESSION'],
        'expected_current': {}
    },
    'cross_experiment_reference': {
        'expected_warnings': ['ASSESSMENT_EXPERIMENT_MISMATCH', 'ASSESSMENT_EXPERIMENT_MISMATCH'],
        'expected_current': {}
    },
    'duplicate_assessment_ids': {
        'expected_warnings': ['ASSESSMENT_ID_DUPLICATE', 'ASSESSMENT_ID_DUPLICATE'],
        'expected_current': {}
    },
    'duplicate_filepaths': {
        'expected_warnings': ['ASSESSMENT_PATH_DUPLICATE', 'ASSESSMENT_PATH_DUPLICATE'],
        'expected_current': {}
    },
    'missing_experiment_id': {
        'expected_warnings': ['ASSESSMENT_EXPERIMENT_ID_MISSING'],
        'expected_current': {}
    },
    'malformed_supersedes': {
        'expected_warnings': ['ASSESSMENT_SUPERSEDES_INVALID_TYPE'],
        'expected_current': {}
    },
    'merge_attempt': {
        'expected_warnings': ['ASSESSMENT_MERGE_UNSUPPORTED'],
        'expected_current': {}
    },
    'disconnected_historical': {
        'expected_warnings': ['ASSESSMENT_LINEAGE_CONFLICT'],
        'expected_current': {}
    },
    'missing_path': {
        'expected_warnings': ['ASSESSMENT_PATH_MISSING'],
        'expected_current': {}
    },
    'invalid_path_type': {
        'expected_warnings': ['ASSESSMENT_PATH_INVALID_TYPE'],
        'expected_current': {}
    },
    'malformed_supersedes_empty_string': {
        'expected_warnings': ['ASSESSMENT_SUPERSEDES_INVALID_VALUE'],
        'expected_current': {}
    },
    'malformed_supersedes_empty_list': {
        'expected_warnings': ['ASSESSMENT_MERGE_UNSUPPORTED'],
        'expected_current': {}
    },
    'malformed_supersedes_false': {
        'expected_warnings': ['ASSESSMENT_SUPERSEDES_INVALID_TYPE'],
        'expected_current': {}
    },
    'malformed_supersedes_zero': {
        'expected_warnings': ['ASSESSMENT_SUPERSEDES_INVALID_TYPE'],
        'expected_current': {}
    },
    'valid_linear': {
        'expected_warnings': [],
        'expected_current': {'EXP_TEST': 'valid_linear/asm.v3.json'}
    },
    'randomized_order': {
        'expected_warnings': [],
        'expected_current': {'EXP_TEST': 'randomized_order/asm.v3.json'}
    }
}

# Fix manifest for dupes based on fatal status
fixture_manifest['duplicate_assessment_ids']['expected_current'] = {}
fixture_manifest['duplicate_filepaths']['expected_current'] = {}

def read_json_files(directory, fixture_name):
    files = []
    if not os.path.exists(directory):
        return files
    for f in os.listdir(directory):
        if f.endswith('.json'):
            with open(os.path.join(directory, f)) as file:
                record = json.load(file)
                rel_path = f"{fixture_name}/{f}"
                record["_source_fixture_path"] = rel_path
                # Only inject _filepath if the fixture didn't intentionally omit it for testing
                if "_filepath" not in record and fixture_name != "missing_path":
                    record["_filepath"] = rel_path
                files.append(record)
    return files

print('Running Lineage Tests...')
results = []
passed_count = 0
fixture_hashes = {}
permutations_tested = {}
complete_warning_multisets = {}
current_by_experiment = {}
fatal_experiments_res = {}
case_results_list = []

import time
start_time = time.time()

for fixture, expected_state in fixture_manifest.items():
    directory = os.path.join(base, fixture)
    assessments = read_json_files(directory, fixture)
    
    # Hash files
    if os.path.exists(directory):
        for f in os.listdir(directory):
            if f.endswith('.json'):
                path = os.path.join(directory, f)
                fixture_hashes[f"{fixture}/{f}"] = compute_sha256(path)
                
    expected_warnings = Counter(expected_state['expected_warnings'])
    expected_current = expected_state['expected_current']
    
    n = len(assessments)
    perms_to_test = []
    if n <= 6:
        perms_to_test = list(permutations(assessments))
    else:
        random.seed(42)
        for _ in range(720):
            p = assessments.copy()
            random.shuffle(p)
            perms_to_test.append(p)
            
    permutations_tested[fixture] = len(perms_to_test)
    
    baseline_result = None
    order_invariant = True
    
    for p in perms_to_test:
        raw_res = resolve_assessment_lineage(list(p))
        canonical_res = canonicalize_resolution(raw_res)
        
        if baseline_result is None:
            baseline_result = canonical_res
        elif canonical_res != baseline_result:
            order_invariant = False
            break
            
    res = baseline_result
    actual_warnings = Counter([w['status'] for w in res['warnings']])
    actual_current = res['current_by_experiment']
    
    complete_warning_multisets[fixture] = res['warnings']
    current_by_experiment[fixture] = res['current_by_experiment']
    fatal_experiments_res[fixture] = res['fatal_experiments']
    
    passed_warnings = (actual_warnings == expected_warnings)
    passed_current = (actual_current == expected_current)
    passed = passed_warnings and passed_current and order_invariant
    
    if passed:
        passed_count += 1
        
    case_results_list.append({
        "fixture": fixture,
        "passed": passed,
        "expected_warnings": dict(expected_warnings),
        "actual_warnings": dict(actual_warnings),
        "expected_current": expected_current,
        "actual_current": actual_current,
        "order_invariant": order_invariant,
    })
        
    print(f'{fixture}: Expected {dict(expected_warnings)}, Got {dict(actual_warnings)} -> {"PASS" if passed else "FAIL"}')
    if not passed_warnings:
        print(f"  WARNING MISMATCH: Actual={dict(actual_warnings)}")
    if not passed_current:
        print(f"  CURRENT MISMATCH: Expected={expected_current}, Actual={actual_current}")
    if not order_invariant:
        print(f"  ORDER INVARIANCE FAILED")

duration = time.time() - start_time

report = {
    'summary': {
        'total': len(fixture_manifest),
        'passed': passed_count,
        'failed': len(fixture_manifest) - passed_count,
    },
    'cases': case_results_list,
    'expected_manifest': fixture_manifest,
    'expected_manifest_sha256': sha256_json(fixture_manifest),
    'resolver_sha256': compute_sha256(os.path.join(base, '..', '..', 'assessment_resolver.py')),
    'runner_sha256': compute_sha256(__file__),
    'fixture_hashes': fixture_hashes,
    'permutations_tested': permutations_tested,
    'random_seeds': [42],
    'complete_warning_multisets': complete_warning_multisets,
    'current_by_experiment': current_by_experiment,
    'fatal_experiments': fatal_experiments_res,
    'duration_seconds': duration,
    'python_version': platform.python_version(),
    'os': platform.platform()
}

report_path = os.path.join(base, 'lineage_test_report_' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
with open(report_path, 'x', encoding='utf-8') as f:
    json.dump(report, f, indent=2)
    
print(f'Report written to: {report_path}')

if passed_count != len(fixture_manifest):
    print("TEST SUITE FAILED")
    raise SystemExit(1)
