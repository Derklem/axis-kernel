
FATAL_LINEAGE_CODES = {
    'ASSESSMENT_PATH_MISSING',
    'ASSESSMENT_PATH_INVALID_TYPE',
    'ASSESSMENT_PATH_DUPLICATE',
    'ASSESSMENT_ID_DUPLICATE',
    'ASSESSMENT_EXPERIMENT_ID_MISSING',
    'ASSESSMENT_SUPERSEDES_INVALID_TYPE',
    'ASSESSMENT_SUPERSEDES_TARGET_MISSING',
    'ASSESSMENT_SELF_SUPERSESSION',
    'ASSESSMENT_EXPERIMENT_MISMATCH',
    'ASSESSMENT_LINEAGE_CONFLICT',
    'ASSESSMENT_LINEAGE_CYCLE',
    'ASSESSMENT_MERGE_UNSUPPORTED',
    'ASSESSMENT_SUPERSEDES_INVALID_VALUE',
}

def resolve_assessment_lineage(assessments: list[dict]) -> dict:
    warnings = []
    
    # Sort assessments to guarantee order invariance
    assessments_sorted = sorted(assessments, key=lambda a: (str(a.get('_filepath', '')), str(a.get('assessment_id', ''))))
    
    assessment_by_path = {}
    path_counts = {}
    assessment_ids = {}
    
    # First pass: Track all paths and IDs to identify duplicates bilaterally
    for a in assessments_sorted:
        path = a.get('_filepath')
        if path is not None and isinstance(path, str) and path.strip():
            path_counts.setdefault(path, []).append(a)
            aid = a.get('assessment_id')
            if aid:
                assessment_ids.setdefault(aid, []).append(a)

    for path, records in path_counts.items():
        if len(records) > 1:
            for a in records:
                warnings.append({
                    'experiment_id': a.get('experiment_id', 'UNKNOWN'),
                    'field': 'assessments',
                    'status': 'ASSESSMENT_PATH_DUPLICATE',
                    'assessment': path,
                    'target': '',
                    'source_record': a.get('_source_fixture_path')
                })

    for aid, records in assessment_ids.items():
        if len(records) > 1:
            for a in records:
                warnings.append({
                    'experiment_id': a.get('experiment_id', 'UNKNOWN'),
                    'field': 'assessments',
                    'status': 'ASSESSMENT_ID_DUPLICATE',
                    'assessment': a.get('_filepath'),
                    'target': aid,
                    'source_record': a.get('_source_fixture_path')
                })

    # Second pass: Index validly structured nodes
    for a in assessments_sorted:
        path = a.get('_filepath')
        exp_id = a.get('experiment_id', 'UNKNOWN')
        src = a.get('_source_fixture_path')
        
        if path is None:
            warnings.append({'experiment_id': exp_id, 'field': 'assessments', 'status': 'ASSESSMENT_PATH_MISSING', 'assessment': 'UNKNOWN', 'target': '', 'source_record': src})
            continue
            
        if not isinstance(path, str) or not path.strip():
            warnings.append({'experiment_id': exp_id, 'field': 'assessments', 'status': 'ASSESSMENT_PATH_INVALID_TYPE', 'assessment': str(path), 'target': '', 'source_record': src})
            continue
            
        if not a.get('experiment_id'):
            warnings.append({'experiment_id': 'UNKNOWN', 'field': 'assessments', 'status': 'ASSESSMENT_EXPERIMENT_ID_MISSING', 'assessment': path, 'target': '', 'source_record': src})
            
        # We only keep the first one in the index for subsequent graph logic, but both are already fatal
        if path not in assessment_by_path:
            assessment_by_path[path] = a

    # 2. Global edge validation
    superseded_by = {}
    invalid_nodes = set()
    
    for path, a in assessment_by_path.items():
        if 'supersedes' not in a or a['supersedes'] is None:
            continue
            
        target = a['supersedes']
        exp_id = a.get('experiment_id', 'UNKNOWN')
        src = a.get('_source_fixture_path')
            
        if isinstance(target, list):
            warnings.append({'experiment_id': exp_id, 'field': 'assessments', 'status': 'ASSESSMENT_MERGE_UNSUPPORTED', 'assessment': path, 'target': str(target), 'source_record': src})
            invalid_nodes.add(path)
            continue
            
        if not isinstance(target, str):
            warnings.append({'experiment_id': exp_id, 'field': 'assessments', 'status': 'ASSESSMENT_SUPERSEDES_INVALID_TYPE', 'assessment': path, 'target': str(target), 'source_record': src})
            invalid_nodes.add(path)
            continue
            
        if not target.strip():
            warnings.append({'experiment_id': exp_id, 'field': 'assessments', 'status': 'ASSESSMENT_SUPERSEDES_INVALID_VALUE', 'assessment': path, 'target': str(target), 'source_record': src})
            invalid_nodes.add(path)
            continue
            
        target_a = assessment_by_path.get(target)
        if not target_a:
            warnings.append({'experiment_id': exp_id, 'field': 'assessments', 'status': 'ASSESSMENT_SUPERSEDES_TARGET_MISSING', 'assessment': path, 'target': target, 'source_record': src})
            invalid_nodes.add(path)
            continue
            
        if target == path:
            warnings.append({'experiment_id': exp_id, 'field': 'assessments', 'status': 'ASSESSMENT_SELF_SUPERSESSION', 'assessment': path, 'target': target, 'source_record': src})
            invalid_nodes.add(path)
            continue
            
        if target_a.get('experiment_id') != a.get('experiment_id'):
            warnings.append({'experiment_id': exp_id, 'field': 'assessments', 'status': 'ASSESSMENT_EXPERIMENT_MISMATCH', 'assessment': path, 'target': target, 'source_record': src})
            warnings.append({'experiment_id': target_a.get('experiment_id'), 'field': 'assessments', 'status': 'ASSESSMENT_EXPERIMENT_MISMATCH', 'assessment': target, 'target': path, 'source_record': target_a.get('_source_fixture_path')})
            invalid_nodes.add(path)
            invalid_nodes.add(target)
            continue
            
        if target in superseded_by:
            warnings.append({'experiment_id': exp_id, 'field': 'assessments', 'status': 'ASSESSMENT_LINEAGE_CONFLICT', 'assessment': path, 'target': target, 'source_record': src})
            warnings.append({'experiment_id': assessment_by_path[superseded_by[target]].get('experiment_id'), 'field': 'assessments', 'status': 'ASSESSMENT_LINEAGE_CONFLICT', 'assessment': superseded_by[target], 'target': target, 'source_record': assessment_by_path[superseded_by[target]].get('_source_fixture_path')})
            invalid_nodes.add(path)
            invalid_nodes.add(superseded_by[target])
        else:
            superseded_by[target] = path

    # 3. Cycle detection
    for path in sorted(assessment_by_path.keys()):
        if path in invalid_nodes: continue
        visited = set()
        curr = path
        while curr in superseded_by:
            if curr in visited:
                exp_id = assessment_by_path[path].get('experiment_id', 'UNKNOWN')
                src = assessment_by_path[path].get('_source_fixture_path')
                warnings.append({'experiment_id': exp_id, 'field': 'assessments', 'status': 'ASSESSMENT_LINEAGE_CYCLE', 'assessment': path, 'target': curr, 'source_record': src})
                invalid_nodes.add(path)
                break
            visited.add(curr)
            curr = superseded_by[curr]

    # 4. Resolve current per experiment
    experiments = {}
    for path, a in assessment_by_path.items():
        exp_id = a.get('experiment_id')
        if not exp_id: continue
        if exp_id not in experiments:
            experiments[exp_id] = []
        experiments[exp_id].append(path)
        
    current_by_experiment = {}
    fatal_experiments = set()
    
    for w in warnings:
        if w['status'] in FATAL_LINEAGE_CODES:
            fatal_experiments.add(w.get('experiment_id'))
            
    for exp_id, paths in experiments.items():
        if exp_id in fatal_experiments:
            continue
            
        active_paths = [p for p in paths if p not in superseded_by and p not in invalid_nodes]
        
        if len(active_paths) > 1:
            warnings.append({'experiment_id': exp_id, 'field': 'assessments', 'status': 'ASSESSMENT_LINEAGE_CONFLICT', 'assessment': 'MULTIPLE_ROOTS', 'target': '', 'source_record': None})
            fatal_experiments.add(exp_id)
        elif len(active_paths) == 1:
            current_by_experiment[exp_id] = active_paths[0]
            
    return {
        'current_by_experiment': current_by_experiment,
        'warnings': warnings,
        'fatal_experiments': list(fatal_experiments)
    }

