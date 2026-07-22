import json
import os

STATE_DIR = os.path.join(os.path.dirname(__file__), "State")
LEDGER_FILE = os.path.join(STATE_DIR, "gateway_receipts.jsonl")

def append_gateway_receipt(receipt: dict):
    """
    Appends a gateway receipt to the local ledger (side effect).
    """
    if not os.path.exists(STATE_DIR):
        os.makedirs(STATE_DIR)
        
    with open(LEDGER_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(receipt) + "\n")
