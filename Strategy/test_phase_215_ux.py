import os
import sys
import subprocess

def run_console(args, env=None):
    cmd = [sys.executable, "Strategy/receptor_console.py"] + args
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return result

def main():
    print("--- Testing Phase 215 Console UX ---")
    
    # Test 1: Color Output
    print("Testing default color output...")
    env = os.environ.copy()
    env["FORCE_COLOR"] = "1"
    res = run_console(["--status"], env=env)
    if '\033[9' in res.stdout:
        print("  [PASS] ANSI color codes detected in output.")
    else:
        print("  [FAIL] Missing color codes.")
        sys.exit(1)

    # Test 2: --no-color flag
    print("Testing --no-color flag...")
    res_no_color = run_console(["--status", "--no-color"])
    if '\033[9' not in res_no_color.stdout:
        print("  [PASS] ANSI color codes successfully stripped.")
    else:
        print("  [FAIL] Color codes present despite --no-color.")
        sys.exit(1)

    # Test 3: NO_COLOR environment variable
    print("Testing NO_COLOR=1 environment variable...")
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    res_env_color = run_console(["--status"], env=env)
    if '\033[9' not in res_env_color.stdout:
        print("  [PASS] ANSI color codes successfully stripped via env var.")
    else:
        print("  [FAIL] Color codes present despite NO_COLOR=1.")
        sys.exit(1)
        
    # Test 4: Actionable Debt Map Output
    print("Testing actionable output in --debt-map...")
    res_debt = run_console(["--debt-map", "--no-color"])
    if "actionable open quarantines" in res_debt.stdout or "No open debt detected" in res_debt.stdout:
        print("  [PASS] Actionable summary found in debt map.")
    else:
        print("  [FAIL] Missing actionable summary in debt map.")
        sys.exit(1)

    print("\nPhase 215 UX tests completed successfully.")

if __name__ == "__main__":
    main()
