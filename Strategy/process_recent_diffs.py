import os
import subprocess

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except Exception as e:
        print(f"Command failed: {cmd} - {e}")
        return ""

def process_recent_diffs(count=10):
    log_output = run_cmd(f"git -C .. log -n {count} --oneline --name-only -- '*.py'")
    if not log_output:
        return
        
    lines = log_output.splitlines()
    commits_to_process = []
    
    current_commit = None
    for line in lines:
        if " " in line and len(line.split()[0]) >= 7 and not line.endswith(".py"):
            current_commit = line.split()[0]
        elif line.endswith(".py") and current_commit:
            commits_to_process.append((current_commit, line.strip()))
            
    unique_commits = []
    seen = set()
    for commit, fpath in commits_to_process:
        if commit not in seen:
            seen.add(commit)
            unique_commits.append((commit, fpath))
    unique_commits = unique_commits[:count]
    
    for commit, file_path in unique_commits:
        print(f"\n======================================")
        print(f"Processing Commit {commit} -> {file_path}")
        print(f"======================================")
        
        # We need to run receptor_pipeline.py which expects local paths if we are in Strategy/
        # but the git paths are relative to root if we use git -C ..
        # Actually, let's just use `file_path` from root and `target` from root.
        # But wait, receptor_pipeline.py assumes target is inside Strategy.
        # Let's just pass `os.path.basename(file_path)` and let receptor_pipeline find it.
        # But `git diff {commit}~1 {commit} -- {file_path}` must be run from ROOT!
        # And `git show {commit}~1:{file_path}` must use the ROOT relative path!
        # receptor_pipeline.py runs `git diff` using whatever path we give it.
        # If we pass `Strategy/...`, `receptor_pipeline.py` is in `Strategy/`!
        # Let's just modify `process_recent_diffs.py` to change directory to ROOT temporarily?
        # Or just run `receptor_pipeline.py` from root?
        local_file = os.path.basename(file_path)
        print(f"Running: python receptor_pipeline.py --git-diff-historical {commit} {file_path}")
        # Note: We pass file_path (e.g. Strategy/abc.py or core/def.py) but receptor_pipeline is in Strategy/
        # Wait, if we pass Strategy/abc.py to receptor_pipeline.py, it will do `git diff {commit}~1 {commit} -- Strategy/abc.py` 
        # But `subprocess.check_output(["git", "diff", ...])` inside `Strategy/` directory will fail because `Strategy/Strategy/abc.py` doesn't exist!
        # Oh, `git diff` takes paths relative to current working directory!
        # So we MUST pass the path relative to `Strategy/`!
        # If file_path is `Strategy/abc.py`, relpath is `abc.py`.
        # If file_path is `core/abc.py`, relpath is `../core/abc.py`.
        
        rel_path = os.path.relpath(os.path.join("..", file_path), ".")
        
        ret = subprocess.call(["python", "receptor_pipeline.py", "--git-diff-historical", commit, rel_path])
        print(f"Pipeline exit code: {ret}")
            
    print("\nBatch processing complete.")

if __name__ == "__main__":
    process_recent_diffs(10)
