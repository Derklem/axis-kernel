import argparse
import json
import sys
from strategy.evaluator import evaluate

def main():
    parser = argparse.ArgumentParser(description="Strategy Engine Evaluator")
    parser.add_argument("--state", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--observations", required=True)
    parser.add_argument("--output", required=True)
    
    args = parser.parse_args()
    
    with open(args.state, "r", encoding="utf-8") as f:
        state = json.load(f)
    with open(args.spec, "r", encoding="utf-8") as f:
        spec = json.load(f)
    with open(args.observations, "r", encoding="utf-8") as f:
        observations = json.load(f)
        
    try:
        decision = evaluate(state, spec, observations)
    except Exception as e:
        print(f"Evaluation failed: {e}", file=sys.stderr)
        sys.exit(1)
        
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(decision, f, indent=2)
        
if __name__ == "__main__":
    main()
