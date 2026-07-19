import subprocess
import os
from typing import Dict, Any, List

def run_experiment(command: List[str], stdout_path: str, stderr_path: str, cwd: str, env: Dict[str, str], timeout_seconds: int = 300) -> Dict[str, Any]:
    """
    Dumb runner that executes a command and streams output to files.
    Returns the execution result status and exit code.
    """
    try:
        run_env = os.environ.copy()
        run_env.update(env)
        
        timeout = None if timeout_seconds == 0 else timeout_seconds
        
        with open(stdout_path, "w", encoding="utf-8") as out_f, \
             open(stderr_path, "w", encoding="utf-8") as err_f:
            
            process = subprocess.Popen(
                command, 
                shell=False, 
                stdout=out_f, 
                stderr=err_f,
                cwd=cwd,
                env=run_env,
                text=True
            )
            
            try:
                exit_code = process.wait(timeout=timeout)
                return {
                    "status": "COMPLETED",
                    "exit_code": exit_code
                }
            except subprocess.TimeoutExpired:
                process.kill()
                return {
                    "status": "FAILED",
                    "exit_code": None,
                    "error": "Timeout expired"
                }
    except Exception as e:
        return {
            "status": "ABORTED",
            "exit_code": None,
            "error": str(e)
        }
