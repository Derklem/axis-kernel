import os
import sys
import argparse
from gemma_bridge import query_gemma

def run_experiment(experiment_id, experiments_dir=r"D:\Mind\Laboratory\Experiments", attempt=1):
    exp_path = os.path.join(experiments_dir, experiment_id)
    attempt_dir = os.path.join(exp_path, f"attempt_{attempt}")
    
    if not os.path.isdir(exp_path):
        print(f"Error: Experiment directory not found at {exp_path}")
        sys.exit(1)
        
    os.makedirs(attempt_dir, exist_ok=True)
        
    prompt_file = os.path.join(attempt_dir, "prompt.md")
    output_file = os.path.join(attempt_dir, "output.md")
    
    if not os.path.isfile(prompt_file):
        print(f"Error: prompt.md not found in {attempt_dir}")
        sys.exit(1)
        
    print(f"Reading prompt from {prompt_file}...")
    with open(prompt_file, 'r', encoding='utf-8') as f:
        prompt = f.read()
        
    print(f"Running experiment {experiment_id} (attempt {attempt}) against Gemma...")
    response = query_gemma(prompt)
    
    print(f"Writing output to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(response)
        
    print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a laboratory experiment against Gemma.")
    parser.add_argument("experiment_id", help="The ID of the experiment (e.g., RL_001)")
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    
    run_experiment(args.experiment_id, attempt=args.attempt)
