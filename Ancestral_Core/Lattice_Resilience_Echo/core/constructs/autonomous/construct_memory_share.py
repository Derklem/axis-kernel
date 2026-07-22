# core/constructs/autonomous/construct_memory_share.py

def share_memory(source_agent, target_agent, count=3):
    recent = source_agent.memory[-count:]
    for entry in recent:
        clone = {
            "timestamp": entry["timestamp"],
            "input": f"(from {source_agent.name}) {entry['input']}",
            "source": source_agent.name
        }
        target_agent.memory.append(clone)
    print(f"[MemoryShare] {source_agent.name} → {target_agent.name} shared {len(recent)} memories.")
