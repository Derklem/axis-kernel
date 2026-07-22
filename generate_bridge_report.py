import os
import json
from datetime import datetime, timezone

METRICS_FILE = r"D:\Infinite\Infinity\Runtime\Decision\Governance_Metrics.json"
BASELINE_METADATA_FILE = r"D:\Infinite\Infinity\Strategy\Proposals\Bridge_Baseline_Metadata.json"
REPORT_OUT = r"D:\Infinite\Infinity\Reports\bridge_status_report.md"

def generate_report():
    metrics = {}
    if os.path.exists(METRICS_FILE):
        try:
            with open(METRICS_FILE, "r", encoding="utf-8") as f:
                metrics = json.load(f)
        except Exception as e:
            print(f"Error reading metrics: {e}")

    baseline_meta = {}
    if os.path.exists(BASELINE_METADATA_FILE):
        try:
            with open(BASELINE_METADATA_FILE, "r", encoding="utf-8") as f:
                baseline_meta = json.load(f)
        except Exception as e:
            print(f"Error reading baseline metadata: {e}")

    now_utc = datetime.now(timezone.utc).isoformat()
    
    # Render Report
    lines = [
        "# Axis Bridge Status Report",
        "",
        "> [!WARNING]",
        "> **Externally generated diagnostic report.**",
        "> Not an Axis-approved execution.",
        "> Not a mutation authorized by the solver.",
        "> Baseline was sealed by operator checkpoint, not by autonomous Axis approval.",
        "",
        f"**Generated:** {now_utc}",
        "**Execution Authority:** LOCKED",
        "",
        "---",
        "",
        "## 1. Oracle Telemetry (Tier 2 Local)",
        f"* **Approval Capable:** `{metrics.get('approval_capable', False)}`",
        f"* **Metrics Health:** `{metrics.get('metrics_health', 'unknown')}`",
        f"* **Stability Index:** `{metrics.get('stability_index', 0.0)}`",
        ""
    ]
    
    # Phase E Verification Metrics
    verif_status = metrics.get('last_execution_verification_status', 'insufficient_samples')
    verif_count = metrics.get('execution_verifications_last_24h', 0)
    verif_failures = metrics.get('execution_verification_failures_last_24h', 0)
    
    lines.extend([
        "### Verification Health (Phase E)",
        f"* **Last Verification Status:** `{verif_status}`",
        f"* **Verifications Last 24h:** `{verif_count}`",
        f"* **Failures Last 24h:** `{verif_failures}`",
        ""
    ])

    lines.extend([
        "### Oracle Observational Limits",
        "The following fields remain constrained by the current oracle tier:",
        "```json",
        json.dumps(metrics.get("oracle_limits", {}), indent=2),
        "```",
        "",
        "## 2. Latest Adjudication Outcome",
        "* **Bridge Verdict:** `REJECTED`",
        "* **Solver Raw Reason:** `insufficient_net_value`",
        "* **Pending Proposals in Queue:** `0`",
        "",
        "## 3. Current Sealed Baseline",
        f"* **Sealed Timestamp (UTC):** `{baseline_meta.get('sealed_timestamp_utc', 'Unknown')}`",
        f"* **Origin:** `{baseline_meta.get('origin', 'Unknown')}`",
        f"* **Operator:** `{baseline_meta.get('operator', 'Unknown')}`",
        f"* **Reason:** `{baseline_meta.get('reason', 'Unknown')}`",
        "",
        "The following hashes represent the sealed structural baseline. ",
        "```json",
        json.dumps(baseline_meta.get("hashes", {}), indent=2),
        "```",
        "",
        "---",
        "*End of Report*"
    ])

    os.makedirs(os.path.dirname(REPORT_OUT), exist_ok=True)
    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
        
    print(f"Bridge status report generated at {REPORT_OUT}")

if __name__ == "__main__":
    generate_report()
