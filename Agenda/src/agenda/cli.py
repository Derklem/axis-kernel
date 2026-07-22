import argparse
import json
import sys
from .planner import generate_agenda

def main():
    parser = argparse.ArgumentParser(description="Agenda Engine Planner")
    parser.add_argument("--input", required=True, help="Path to planner_input.json")
    parser.add_argument("--spec", required=True, help="Path to planner_spec.json")
    parser.add_argument("--output", required=True, help="Path to output agenda.json")
    
    args = parser.parse_args()
    
    with open(args.input, "r", encoding="utf-8") as f:
        planner_input = json.load(f)
    
    with open(args.spec, "r", encoding="utf-8") as f:
        planner_spec = json.load(f)
        
    agenda = generate_agenda(planner_input, planner_spec)
    
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(agenda, f, indent=2)

if __name__ == "__main__":
    main()
