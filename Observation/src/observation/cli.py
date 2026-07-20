import argparse
import json
import sys
from observation.extractor import extract_feed

def main():
    parser = argparse.ArgumentParser(description="Observation Engine Extractor")
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--artifact-path", required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--verification-artifact", required=True)
    parser.add_argument("--output", required=True)
    
    args = parser.parse_args()
    
    try:
        with open(args.receipt, "r", encoding="utf-8") as f:
            receipt = json.load(f)
        with open(args.artifact, "r", encoding="utf-8") as f:
            artifact = json.load(f)
            
        import hashlib
        def hash_file(filepath: str) -> str:
            digest = hashlib.sha256()
            with open(filepath, "rb") as fh:
                while chunk := fh.read(8192):
                    digest.update(chunk)
            return digest.hexdigest()
    
        with open(args.verification_artifact, "r", encoding="utf-8") as f:
            ver_art = json.load(f)
    except FileNotFoundError as e:
        print(f"Verification artifact or input file not found: {e}", file=sys.stderr)
        sys.exit(2)
        
    actual_hash = hash_file(args.artifact)
    
    try:
        feed = extract_feed(receipt, ver_art, args.artifact_path, artifact, actual_hash)
    except Exception as e:
        print(f"Extraction failed: {e}", file=sys.stderr)
        sys.exit(1)
        
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(feed, f, indent=2)

if __name__ == "__main__":
    main()
