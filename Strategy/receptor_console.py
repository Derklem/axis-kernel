import os
import sys
import argparse
import time
from datetime import datetime
from ledger_reader import parse_ledger_fast

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

    @classmethod
    def disable(cls):
        cls.GREEN = ''
        cls.YELLOW = ''
        cls.RED = ''
        cls.RESET = ''

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEDGER_PATH = os.environ.get("AXIS_LEDGER_PATH", os.path.join(BASE_DIR, "State", "receptor_ledger.jsonl"))

def print_status(metrics):
    open_quarantines = metrics["quarantined"] - metrics["overrides"]
    # Rough approximation since a true resolution drops the quarantine count.
    # Actually, a better way to compute open quarantines is to count cases where the last event is QUARANTINE and no ADJUDICATION exists.

    print("\n=== AXIS GOVERNANCE STATUS ===")

    score = (open_quarantines * 10) + (metrics["overrides"] * 5) + metrics["session_burden"]

    if score < 10:
        health = f"{Colors.GREEN}GREEN (Healthy){Colors.RESET}"
    elif score <= 30:
        health = f"{Colors.YELLOW}YELLOW (Elevated Debt){Colors.RESET}"
    else:
        health = f"{Colors.RED}RED (Critical Burden){Colors.RESET}"

    print(f"System Health:      {health}")
    print(f"Debt Score:         {score:.2f}")
    print(f"Session Burden:     {metrics['session_burden']:.2f}")
    print(f"Accepted Deltas:    {metrics['accepted']}")
    print(f"Total Quarantines:  {metrics['quarantined']}")
    print(f"Adjudicated:        {metrics['overrides']}")
    print(f"Auditor Requests:   {metrics['audit_requests']}")
    print("==============================\n")

def print_last_n(cases, receipts, n):
    print(f"\n=== LAST {n} CASES ===")

    # Get distinct case IDs in order of appearance
    seen = set()
    ordered_cases = []
    for r in reversed(receipts):
        cid = r.get("case_id")
        if cid and cid not in seen:
            seen.add(cid)
            ordered_cases.append(cid)
            if len(ordered_cases) == n:
                break

    print(f"{'Case ID':<40} | {'Target':<30} | {'Final State'}")
    print("-" * 90)
    for cid in ordered_cases:
        case = cases.get(cid, {})
        events = case.get("events", [])

        target = "Unknown"
        obs = case.get("observation")
        if obs:
            target = obs.get("target_file", "Unknown")

        final_state = "OPEN"
        if events:
            # Look at the most significant terminal event
            if "RECEPTOR_DELTA_ACCEPTED" in events:
                final_state = f"{Colors.GREEN}ACCEPTED{Colors.RESET}"
            elif "ADJUDICATION_RULING" in events:
                final_state = f"{Colors.GREEN}ADJUDICATED{Colors.RESET}"
            elif "RECEPTOR_DELTA_QUARANTINED" in events:
                final_state = f"{Colors.RED}QUARANTINED{Colors.RESET}"
            elif "CHECK_ONLY" in events:
                final_state = "DRY_RUN"
            else:
                final_state = events[-1]

        print(f"{cid:<40} | {target:<30} | {final_state}")
    print("======================\n")

def print_case(cases, case_id):
    case = cases.get(case_id)
    if not case:
        print(f"Case {case_id} not found in ledger.")
        return

    print(f"\n=== CASE {case_id} ===")
    obs = case.get("observation", {})
    print(f"Target: {obs.get('target_file', 'Unknown')}")
    print("Events:")
    for ev in case.get("events", []):
        payload = case.get("payloads", {}).get(ev, {})

        detail = ""
        if ev == "RECEPTOR_DELTA_QUARANTINED":
            detail = f"Reason: {payload.get('reason')}"
        elif ev == "RECEPTOR_SEMANTIC_RISK_SCORED":
            detail = f"Score: {payload.get('risk_score')}, Flags: {payload.get('risk_flags')}"
        elif ev == "ADJUDICATION_RULING":
            detail = f"Ruling: {payload.get('ruling_type')}"
        elif ev == "AUDITOR_VERDICT_RECEIVED":
            detail = f"Verdict: {payload.get('verdict')}, Confidence: {payload.get('confidence')}"
        elif ev == "MULTI_AUDIT_CONSENSUS_RECORDED":
            detail = f"Consensus: {payload.get('consensus_verdict')} (Strategy: {payload.get('strategy_applied')})"

        print(f" - {ev:<32} {detail}")
    print("======================\n")

def print_quarantines(cases):
    print("\n=== OPEN QUARANTINES ===")
    count = 0
    print(f"{'Case ID':<40} | {'Target':<30} | {'Reason'}")
    print("-" * 90)
    for cid, case in cases.items():
        events = case.get("events", [])
        if "RECEPTOR_DELTA_QUARANTINED" in events and "ADJUDICATION_RULING" not in events:
            target = case.get("observation", {}).get("target_file", "Unknown")
            payload = case.get("payloads", {}).get("RECEPTOR_DELTA_QUARANTINED", {})
            reason = payload.get("reason", "Unknown")
            print(f"{cid:<40} | {target:<30} | {reason}")
            count += 1

    if count == 0:
        print("No open quarantines.")
    print("========================\n")

def print_audits(receipts):
    print("\n=== RECENT AUDIT VERDICTS ===")
    print(f"{'Case ID':<40} | {'Verdict':<15} | {'Type/Auditor'}")
    print("-" * 90)
    count = 0
    for r in reversed(receipts):
        if r["event_type"] == "MULTI_AUDIT_CONSENSUS_RECORDED":
            payload = r.get("payload", {})
            print(f"{r['case_id']:<40} | {payload.get('consensus_verdict', 'N/A'):<15} | MULTI-CONSENSUS ({payload.get('strategy_applied')})")
            count += 1
        elif r["event_type"] == "AUDITOR_VERDICT_RECEIVED":
            payload = r.get("payload", {})
            print(f"{r['case_id']:<40} | {payload.get('verdict', 'N/A'):<15} | {payload.get('auditor_id', 'Unknown')}")
            count += 1

        if count >= 10:
            break

    if count == 0:
        print("No audits recorded.")
    print("=============================\n")

def print_recoveries(cases):
    print("\n=== OPEN RECOVERY PROPOSALS ===")
    count = 0
    print(f"{'Case ID':<40} | {'Status':<20} | {'Patch Path'}")
    print("-" * 90)
    for cid, case in cases.items():
        events = case.get("events", [])
        if "RECOVERY_PATCH_PROPOSED" in events and "RECOVERY_APPLIED" not in events:
            payload = case.get("payloads", {}).get("RECOVERY_PATCH_PROPOSED", {})
            status = payload.get("proposal_status", "Unknown")
            patch = payload.get("patch_path", "Unknown")
            print(f"{cid:<40} | {status:<20} | {patch}")
            count += 1

    if count == 0:
        print("No open recovery proposals.")
    print("===============================\n")

def print_debt_map(cases):
    print("\n=== DEBT MAP ===")
    print(f"{'Target File':<30} | {'Reason / Consensus':<30} | {'Recovery Status'}")
    print("-" * 90)
    count = 0
    for cid, case in cases.items():
        events = case.get("events", [])
        if "RECEPTOR_DELTA_QUARANTINED" in events and "ADJUDICATION_RULING" not in events:
            target = case.get("observation", {}).get("target_file", "Unknown")

            reason = case.get("payloads", {}).get("RECEPTOR_DELTA_QUARANTINED", {}).get("reason", "Unknown")
            if "MULTI_AUDIT_CONSENSUS_RECORDED" in events:
                reason = f"AUDITOR: {case.get('payloads', {}).get('MULTI_AUDIT_CONSENSUS_RECORDED', {}).get('consensus_verdict')}"

            recovery_status = "NONE"
            if "RECOVERY_VERIFIED" in events:
                recovery_status = f"{Colors.GREEN}VERIFIED ({case.get('verification_status', 'Unknown')}){Colors.RESET}"
            elif "RECOVERY_APPLIED" in events:
                recovery_status = f"{Colors.YELLOW}APPLIED{Colors.RESET}"
            elif "RECOVERY_PATCH_PROPOSED" in events:
                recovery_status = f"{Colors.YELLOW}PROPOSED ({case.get('payloads', {}).get('RECOVERY_PATCH_PROPOSED', {}).get('proposal_status', '')}){Colors.RESET}"

            if recovery_status == "NONE":
                reason_color = Colors.RED
            else:
                reason_color = Colors.YELLOW

            # Use fixed width for original reason, then color the whole string
            reason_str = f"{reason_color}{reason:<30}{Colors.RESET}"
            
            # Print using normal widths but adjust for color codes
            # The color codes add invisible characters, so we format without padding the colored string
            print(f"{target:<30} | {reason_str} | {recovery_status}")
            count += 1

    if count == 0:
        print(f"{Colors.GREEN}No open debt detected.{Colors.RESET}")
    else:
        print(f"\n{Colors.YELLOW}{count} actionable open quarantines. Run `python Strategy/receptor_console.py --recoveries` to view recovery options.{Colors.RESET}")
    print("================\n")

def main():
    parser = argparse.ArgumentParser(description="Operator Console for Axis Governance")
    parser.add_argument("--status", action="store_true", help="Print overall health and debt score")
    parser.add_argument("--last", type=int, metavar="N", help="Print the last N cases")
    parser.add_argument("--case", type=str, metavar="CASE_ID", help="Print detailed lifecycle of a specific case")
    parser.add_argument("--quarantines", action="store_true", help="List all open quarantines")
    parser.add_argument("--audits", action="store_true", help="List recent auditor verdicts")
    parser.add_argument("--recoveries", action="store_true", help="List open recovery proposals")
    parser.add_argument("--debt-map", action="store_true", help="Print visual summary of open debt")
    parser.add_argument("--quiet", action="store_true", help="Suppress non-essential output")
    parser.add_argument("--verbose", action="store_true", help="Print verbose details")
    parser.add_argument("--no-color", action="store_true", help="Disable color output")

    args = parser.parse_args()

    if args.no_color or os.environ.get("NO_COLOR") == "1":
        Colors.disable()
    elif not sys.stdout.isatty() and os.environ.get("FORCE_COLOR") != "1":
        Colors.disable()

    try:
        cases, metrics, receipts = parse_ledger_fast(LEDGER_PATH)
    except Exception as e:
        print(f"Error reading ledger: {e}")
        sys.exit(1)

    # Re-calculate accurate open_quarantines for the status
    open_quarantine_count = 0
    for cid, case in cases.items():
        events = case.get("events", [])
        if "RECEPTOR_DELTA_QUARANTINED" in events and "ADJUDICATION_RULING" not in events:
            open_quarantine_count += 1

    # Update metrics with precise count
    metrics["quarantined"] = open_quarantine_count + metrics["overrides"] # Adjust total if needed, but status logic uses total minus overrides, so let's just pass open quarantines.
    # Actually, let's just pass open_quarantine_count cleanly to print_status by replacing the logic inside print_status.

    # We will compute the score properly.
    if args.status:
        # Pass exact open quarantines down
        metrics["open_quarantines"] = open_quarantine_count

        score = (open_quarantine_count * 10) + (metrics["overrides"] * 5) + metrics["session_burden"]

        print("\n=== AXIS GOVERNANCE STATUS ===")
        if score < 10:
            health = f"{Colors.GREEN}GREEN (Healthy){Colors.RESET}"
        elif score <= 30:
            health = f"{Colors.YELLOW}YELLOW (Elevated Debt){Colors.RESET}"
        else:
            health = f"{Colors.RED}RED (Critical Burden){Colors.RESET}"

        print(f"System Health:      {health}")
        print(f"Debt Score:         {score:.2f}")
        print(f"Session Burden:     {metrics['session_burden']:.2f}")
        print(f"Accepted Deltas:    {metrics['accepted']}")
        print(f"Open Quarantines:   {open_quarantine_count}")
        print(f"Adjudicated:        {metrics['overrides']}")
        print(f"Auditor Requests:   {metrics['audit_requests']}")
        print("==============================\n")

    if args.last is not None:
        print_last_n(cases, receipts, args.last)

    if args.case:
        print_case(cases, args.case)

    if args.quarantines:
        print_quarantines(cases)

    if args.audits:
        print_audits(receipts)

    if args.recoveries:
        print_recoveries(cases)

    if args.debt_map:
        print_debt_map(cases)

    if not any(vars(args).values()):
        parser.print_help()

if __name__ == "__main__":
    main()
