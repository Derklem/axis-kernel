import os
import sys
import json
import uuid
import datetime
import hashlib
import re
import unicodedata
from pathlib import Path
import psutil

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright is not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

COMM_DIR = r"D:\Infinite\Infinity\Communication"
APPROVED_DIR = os.path.join(COMM_DIR, "approved")
ARCHIVED_DIR = os.path.join(COMM_DIR, "archived")
RECEIPTS_DIR = os.path.join(COMM_DIR, "receipts")
RECOVERY_DIR = os.path.join(COMM_DIR, "recovery")
BROWSER_PROFILE = os.path.join(COMM_DIR, "BrowserProfile")
LOCK_FILE = os.path.join(COMM_DIR, ".actuating")

X_URL_REGEX = re.compile(r"^https?://(www\.)?(x|twitter)\.com/[a-zA-Z0-9_]+/status/[0-9]+")
ADAPTER_VERSION = "v0.2.3"
ADAPTER_NAME = "attended_x_adapter"

for d in [APPROVED_DIR, ARCHIVED_DIR, RECEIPTS_DIR, RECOVERY_DIR, BROWSER_PROFILE]:
    os.makedirs(d, exist_ok=True)

def normalize_text_for_hash(text: str) -> str:
    # Normalize unicode to NFC, normalize newlines, and strip leading/trailing whitespace
    text = unicodedata.normalize('NFC', text)
    return text.replace('\r\n', '\n').strip()

def compute_content_sha256(content: str) -> str:
    normalized = normalize_text_for_hash(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest().lower()

def compute_file_sha256(filepath: str) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest().lower()

def handle_lock(draft_id: str, draft_hash: str, exp_id: str):
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, "r") as f:
            try:
                lock_data = json.load(f)
            except:
                lock_data = {}
        
        pid = lock_data.get("process_id")
        if pid and psutil.pid_exists(pid):
            print(f"[FATAL] System is currently ACTUATING draft {lock_data.get('draft_id')} in PID {pid}.")
            sys.exit(1)
        else:
            print(f"[FATAL] Stale ACTUATING lock detected from PID {pid}. System crashed during deployment.")
            print("Never clear a stale lock silently. You must run recover_lock.py to reconcile state.")
            sys.exit(1)

    # Acquire lock
    lock_data = {
        "draft_id": draft_id,
        "experiment_id": exp_id,
        "process_id": os.getpid(),
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "draft_sha256": draft_hash,
        "adapter": ADAPTER_NAME,
        "adapter_version": ADAPTER_VERSION
    }
    with open(LOCK_FILE, "w") as f:
        json.dump(lock_data, f, indent=2)

def main():
    print(f"--- Attended X Adapter ({ADAPTER_VERSION}) ---")
    
    # 1. Select Approved Draft
    approved_files = [f for f in os.listdir(APPROVED_DIR) if f.endswith(".json")]
    if not approved_files:
        print("No approved drafts found in approved/")
        sys.exit(0)
        
    print("Available Approved Drafts:")
    for i, f in enumerate(approved_files):
        print(f"[{i}] {f}")
        
    choice = input("Select draft index to post (or 'q' to quit): ").strip()
    if choice.lower() == 'q':
        sys.exit(0)
        
    try:
        draft_fname = approved_files[int(choice)]
    except:
        print("Invalid selection.")
        sys.exit(1)
        
    draft_path = os.path.join(APPROVED_DIR, draft_fname)
    
    with open(draft_path, "r", encoding="utf-8-sig") as f:
        draft = json.load(f)
        
    if draft.get("platform", "").strip().lower() != "x":
        raise RuntimeError(f"Draft platform is not X (found '{draft.get('platform')}'). Refusing actuation.")
            
    content = draft["content"]
    exp_id = draft.get("experiment_id", "UNKNOWN")
    draft_id = draft.get("id", "UNKNOWN")
    draft_hash = compute_file_sha256(draft_path)
    content_hash = compute_content_sha256(content)
    
    # 2. Acquire ACTUATING lock
    handle_lock(draft_id, draft_hash, exp_id)
    
    print(f"\n[LOCK ACQUIRED] Processing {exp_id} / {draft_id}")
    
    url_captured = False
    captured_url = None
    
    try:
        with sync_playwright() as p:
            print(f"[BROWSER] Launching isolated Chromium profile...")
            context = p.chromium.launch_persistent_context(
                user_data_dir=BROWSER_PROFILE,
                headless=False,
                executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                args=["--disable-blink-features=AutomationControlled"],
                ignore_default_args=["--enable-automation"]
            )
            
            page = context.new_page()
            print("[BROWSER] Navigating to X Composer...")
            page.goto("https://x.com/compose/post", timeout=60000)
            
            locator = page.locator("[data-testid='tweetTextarea_0']").first
            try:
                locator.wait_for(state="visible", timeout=30000)
            except Exception as e:
                print("\n[WARNING] Composer not found automatically.")
                print("If you are logging in for the first time, complete login, navigate to https://x.com/compose/post manually.")
                input("Press ENTER here in the terminal once the composer is visible...")
                locator = page.locator("[data-testid='tweetTextarea_0']").first
                locator.wait_for(state="visible", timeout=30000)
                
            print("\n[BROWSER] Injecting draft content...")
            locator.focus()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.keyboard.insert_text(content)
            
            # Hash verification of INJECTED text
            print("[VERIFICATION] Checking composed text hash...")
            browser_text = locator.inner_text()
            browser_hash = compute_content_sha256(browser_text)
            
            if browser_hash != content_hash:
                raise RuntimeError(
                    f"Composed text hash mismatch. expected={content_hash}, actual={browser_hash}\n"
                    f"Check if X altered formatting or if characters were dropped."
                )
            
            print(f"[VERIFIED] Browser content hash exactly matches draft: {browser_hash}")
            
            print("\n=============================================")
            print(">>> DRAFT INJECTED AND VERIFIED.")
            print(">>> THE ADAPTER WILL NEVER CLICK POST FOR YOU.")
            print("=============================================\n")
            print("If you are running Stage A (non-posting test), type 'ABORT'.")
            print("If this is a real deployment, click 'Post' in the browser.")
            
            if draft.get("deployment_mode") == "DRY_RUN":
                user_input = input("Type ABORT to complete Stage A: ").strip()
                if user_input.upper() != "ABORT":
                    raise RuntimeError("Dry-run artifact cannot be deployed.")
            else:
                user_input = input("Enter Deployed Post URL (or 'ABORT'): ").strip()
            
            if user_input.upper() == 'ABORT':
                print("[ABORT] Releasing lock and exiting.")
                context.close()
                os.remove(LOCK_FILE)
                sys.exit(0)
                
            if not X_URL_REGEX.match(user_input):
                raise Exception("Invalid Platform Reference URL")
                
            url_captured = True
            captured_url = user_input
            
            # 3. Post-Deployment URL Verification
            print(f"\n[VERIFICATION] Re-verifying published URL: {captured_url}")
            verif_page = context.new_page()
            verif_page.goto(captured_url, wait_until="domcontentloaded", timeout=60000)
            
            posted_text_locator = verif_page.locator("article [data-testid='tweetText']").first
            posted_text_locator.wait_for(state="visible", timeout=30000)
            
            posted_text = posted_text_locator.inner_text()
            posted_hash = compute_content_sha256(posted_text)
            
            if posted_hash != content_hash:
                raise RuntimeError(
                    f"Published post content does not match approved draft!\n"
                    f"Expected hash: {content_hash}\nActual hash: {posted_hash}"
                )
            print("[VERIFIED] Published post content is a perfect hash match.")
            context.close()
            
        # 4. Transactional Commit
        timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archived_fname = f"{exp_id}__draft_{draft_id.replace('draft_', '')}__{timestamp_str}.json"
        archived_path = os.path.join(ARCHIVED_DIR, archived_fname)
        
        receipt_id = f"receipt_{uuid.uuid4().hex[:8]}"
        receipt = {
            "id": receipt_id,
            "experiment_id": exp_id,
            "draft_id": draft_id,
            "adapter": ADAPTER_NAME,
            "adapter_version": ADAPTER_VERSION,
            "platform": "X",
            "platform_reference": captured_url,
            "deployed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "deployment_state": "SUCCESS",
            "status": "deployed",
            "observation_window": "72h",
            "archive_path": f"archived/{archived_fname}",
            "draft_sha256": draft_hash,
            "content_sha256": content_hash
        }
        
        tmp_receipt_path = os.path.join(RECEIPTS_DIR, f"{receipt_id}.tmp.json")
        final_receipt_path = os.path.join(RECEIPTS_DIR, f"{receipt_id}.json")
        
        with open(tmp_receipt_path, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)
            
        print("[COMMIT] Moving approved draft to archive...")
        os.rename(draft_path, archived_path)
        
        actual_archived_hash = compute_file_sha256(archived_path)
        if actual_archived_hash != draft_hash:
            raise Exception("Archived draft hash mismatch! File corruption during move.")
            
        print("[COMMIT] Renaming receipt to final...")
        os.rename(tmp_receipt_path, final_receipt_path)
        
        print("[COMMIT] Success. Releasing ACTUATING lock.")
        os.remove(LOCK_FILE)
        
        print(f"\nDeployment complete for {exp_id}.")
        print(f"Receipt: {final_receipt_path}")
        
    except Exception as e:
        print(f"\n[FATAL ERROR] {str(e)}")
        if url_captured:
            print("[RECONCILIATION] Failure occurred after external deployment.")
            rec_fname = f"PENDING_DEPLOYMENT_RECONCILIATION_{exp_id}_{int(datetime.datetime.now().timestamp())}.json"
            rec_path = os.path.join(RECOVERY_DIR, rec_fname)
            with open(rec_path, "w") as f:
                json.dump({
                    "experiment_id": exp_id,
                    "draft_id": draft_id,
                    "captured_url": captured_url,
                    "draft_hash": draft_hash,
                    "error": str(e)
                }, f, indent=2)
            print(f"Wrote recovery artifact to {rec_path}")
            print("You must run recover_lock.py to reconcile the ledger.")
        else:
            print("[SAFE] Failure occurred before URL capture. You may abort or retry.")
            
        print("Leaving .actuating lock in place for forensic investigation.")
        sys.exit(1)

if __name__ == "__main__":
    main()
