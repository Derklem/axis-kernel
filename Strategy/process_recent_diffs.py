import os
import subprocess

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except Exception as e:
        print(f"Command failed: {cmd} - {e}")
        return ""

def process_recent_diffs(count=10):
    log_output = run_cmd(f'git -C .. log -n {count} --oneline --name-only -- "*.py"')
    if not log_output:
        print("Git log failed to produce output.")
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
            unique_commits.append(commit)
    unique_commits = unique_commits[:count]
    
    for commit in unique_commits:
        print(f"\n======================================")
        print(f"Processing Commit {commit}")
        print(f"======================================")
        
        print(f"Running: python receptor_pipeline.py --git-commit {commit}")
        ret = subprocess.call(["python", "receptor_pipeline.py", "--git-commit", commit])
        print(f"Pipeline exit code: {ret}")
            
    print("\nBatch processing complete.")

if __name__ == "__main__":
    process_recent_diffs(10)
