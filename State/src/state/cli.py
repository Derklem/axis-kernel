import argparse
import json
import sys
from pathlib import Path
from importlib.resources import files
from state.transition import transition

def load_schema(package, name):
    schema_text = files(f"{package}.schemas").joinpath(name).read_text(encoding="utf-8")
    return json.loads(schema_text)

def main():
    parser = argparse.ArgumentParser(description="State Engine Evaluator")
    parser.add_argument("--prior-state", required=True)
    parser.add_argument("--feed", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--output", required=True)
    
    args = parser.parse_args()
    
    with open(args.prior_state, "r", encoding="utf-8") as f:
        prior_state = json.load(f)
    with open(args.feed, "r", encoding="utf-8") as f:
        feed = json.load(f)
    with open(args.spec, "r", encoding="utf-8") as f:
        spec = json.load(f)
        
    try:
        result = transition(prior_state, feed, spec)
    except Exception as e:
        print(f"State transition failed: {e}", file=sys.stderr)
        sys.exit(1)
        
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

if __name__ == "__main__":
    main()
