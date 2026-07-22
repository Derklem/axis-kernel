import json
import uuid
import datetime
import os

DRAFTS_DIR = r"D:\Infinite\Infinity\Communication\drafts"

def generate_draft(experiment_id, platform, intent, evidence_links, content, color, risk_reasoning, hypothesis_statement, success_metric, failure_metric):
    draft_id = f"draft_{uuid.uuid4().hex[:8]}"
    
    draft = {
        "id": draft_id,
        "experiment_id": experiment_id,
        "platform": platform,
        "intent": intent,
        "evidence_links": evidence_links,
        "content": content,
        "hypothesis": {
            "statement": hypothesis_statement,
            "success_metric": success_metric,
            "failure_metric": failure_metric,
            "minimum_observation_window": "72h"
        },
        "risk_assessment": {
            "color": color,
            "reasoning": risk_reasoning,
            "evidence_freshness": "High",
            "known_assumptions": 0
        },
        "status": "pending_approval",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    file_path = os.path.join(DRAFTS_DIR, f"{draft_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(draft, f, indent=2)
        
    print(f"Generated draft: {file_path}")
    return file_path

if __name__ == "__main__":
    # Draft 1: EXP_016_REDDIT (The Audit)
    generate_draft(
        experiment_id="EXP_016_REDDIT",
        platform="Reddit",
        intent="Test the Sovereignty Audit offer on a community-driven platform (e.g. r/LocalLLaMA or r/selfhosted).",
        evidence_links=["D:\\Mind\\Laboratory\\OPERATION_ZERO.md"],
        content="Hey all, I've spent the last few months building self-governing local AI workflows, focusing heavily on auditability, state recovery, and avoiding bloat. \n\nIf you're building a local agent, RAG pipeline, or automation script and it feels fragile or overly complex, drop a short description below. I'll give you a free, brutal 1-page architectural review highlighting where you might be leaking momentum, recovery gaps, and tradeoffs. \n\nNo upsells. Just want to see what architectures people are struggling with and offer some of the resilience patterns we've developed.",
        color="GREEN",
        risk_reasoning="High value, low friction offer tailored for Reddit communities. No sales pressure.",
        hypothesis_statement="Engineers on Reddit respond better to collaborative problem-solving than direct service offers.",
        success_metric="At least one genuine request for an architectural review.",
        failure_metric="Zero engagement or community moderation removal."
    )

    # Draft 2: EXP_017_X (The Philosophy Ping)
    generate_draft(
        experiment_id="EXP_017_X",
        platform="X",
        intent="Test a purely philosophical/architectural ping on X to see if ideas resonate better than services.",
        evidence_links=["D:\\Mind\\Laboratory\\OPERATION_ZERO.md"],
        content="A lot of autonomous AI projects fail because they optimize for uptime instead of usefulness. \n\nThe hardest engineering constraint isn't building a system that can run forever. It's building a system that knows exactly what evidence it needs to confidently delete its own code. \n\nWe call it 'The Right to Delete.' It changes how you build.",
        color="GREEN",
        risk_reasoning="Abstract, thought-provoking. Low risk of rejection, tests idea resonance rather than transaction.",
        hypothesis_statement="Abstract engineering principles (The Right to Delete) attract more engagement on X than direct service offers.",
        success_metric="More than 6 detail expands or at least 1 reply/repost.",
        failure_metric="Fewer than 6 detail expands and zero replies."
    )

    # Draft 3: EXP_018_DISCORD (The Tactical Ping)
    generate_draft(
        experiment_id="EXP_018_DISCORD",
        platform="Discord",
        intent="Test a highly tactical, direct offer in a developer/tech Discord channel.",
        evidence_links=["D:\\Mind\\Laboratory\\OPERATION_ZERO.md"],
        content="Yo. If anyone is stuck on building local AI automations (especially PowerShell/Python bridges, state management, or agent loops), I've been doing this non-stop and have some hardened templates. Let me know what you're building and I'll drop some feedback or point you to a pattern that works.",
        color="GREEN",
        risk_reasoning="Casual, helpful, fits Discord developer culture perfectly.",
        hypothesis_statement="Solving an immediate technical problem generates stronger trust on Discord than broadcasting expertise.",
        success_metric="A direct reply or DM asking for a specific code pattern or template.",
        failure_metric="Zero engagement."
    )
