import os
import json
import uuid
import datetime

RECEIPTS_DIR = r"D:\Infinite\Infinity\Communication\receipts"
OBSERVATIONS_DIR = r"D:\Infinite\Infinity\Communication\observations"

def process_receipts():
    if not os.path.exists(RECEIPTS_DIR) or not os.path.exists(OBSERVATIONS_DIR):
        print("Directories not found. Run setup first.")
        return

    receipt_files = [f for f in os.listdir(RECEIPTS_DIR) if f.endswith('.json')]
    
    if not receipt_files:
        print("No receipts pending observation.")
        return

    for filename in receipt_files:
        filepath = os.path.join(RECEIPTS_DIR, filename)
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            receipt = json.load(f)
            
        print("==================================================")
        print("              OBSERVATION LOOP (MANUAL)           ")
        print("==================================================")
        print(f"EXPERIMENT:  {receipt.get('experiment_id')}")
        reference = receipt.get("platform_reference") or receipt.get("post_url", "N/A")
        print(f"POST REF:    {reference}")
        print(f"DEPLOYED AT: {receipt.get('deployed_at')}")
        print("--------------------------------------------------")
        
        print("Go to the URL above and check for replies/engagement.")
        choice = input("[O]bserve   [S]kip   [C]lose receipt without observation: ").strip().upper()
        
        if choice == "O":
            summary = input("Enter a summary of the outcome/replies: ")
            print("\nExecution Quality:")
            print("[1] SUCCESS")
            print("[2] PARTIAL")
            print("[3] FAILED")
            eq_choice = input("Select [1/2/3]: ").strip()
            execution_quality = "SUCCESS" if eq_choice == "1" else ("PARTIAL" if eq_choice == "2" else "FAILED")
            
            print("\nHypothesis Result:")
            print("[1] SUPPORTS")
            print("[2] CONTRADICTS")
            print("[3] INCONCLUSIVE")
            hr_choice = input("Select [1/2/3]: ").strip()
            hypothesis_result = "SUPPORTS" if hr_choice == "1" else ("CONTRADICTS" if hr_choice == "2" else "INCONCLUSIVE")
            
            next_exp = input("\nNext Smallest Experiment: ")
            
            obs_id = f"obs_{uuid.uuid4().hex[:8]}"
            observation = {
                "id": obs_id,
                "receipt_id": receipt.get("id"),
                "experiment_id": receipt.get("experiment_id"),
                "summary": summary,
                "execution_quality": execution_quality,
                "hypothesis_result": hypothesis_result,
                "next_smallest_experiment": next_exp,
                "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            
            obs_path = os.path.join(OBSERVATIONS_DIR, f"{obs_id}.json")
            with open(obs_path, 'w', encoding='utf-8') as obs_f:
                json.dump(observation, obs_f, indent=2)
                
            print(f"Observation logged: {obs_path}")
            
            # Move the receipt to an archive folder or rename it to mark it as observed
            # For simplicity in v0, we will just leave it or rename it.
            os.rename(filepath, filepath + ".observed")
            print("Receipt marked as observed.")
            
        elif choice == "C":
            os.rename(filepath, filepath + ".closed")
            print("Receipt closed.")
        else:
            print("Skipping...")

if __name__ == "__main__":
    process_receipts()
