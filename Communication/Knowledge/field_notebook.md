# Field Notebook

**Purpose:** A chronological, narrative record of observations, intuitions, and qualitative field data that precedes formal Knowledge Ledger ingestion. 

---

## 2026-07-14

### Observation: Discord interaction (`EXP_018_DISCORD`) escalated into deep technical exposition.
- **Context:** The initial observation window closed with zero inquiries. Two days later, a highly substantive technical inquiry arrived.
- **Action:** Operator provided a targeted diagnosis (AI IDE context collapse).
- **Result:** The user (Vermeses) not only accepted the diagnosis but replied with a multi-paragraph, deep-dive exposition on their exact workflow.
- **Key Engineering Data Extracted:**
  - Frontier model context limits (1M tokens) degrade significantly at ~60% capacity in AI IDEs.
  - Operators are manually forcing "handoff prompts" to migrate state to new sessions.
  - Explicit state files (`CLAUDE.md`, `README.md`) are required for "rehydration."
  - Operators are relying on external memory systems (`claudemem`, `open-viking`) to augment built-in IDE memory.
  - Logging is critical because "logging is the way AIs see the world."

### Unexpected Finding
- **Asynchronous Latency:** The latency for high-value technical engagement on a general network (Discord) was far longer than anticipated (48+ hours). Prematurely closing the observation window almost caused this data to be lost as a false negative.

### Next Questions to Track
- Is this 48+ hour latency common across all non-specialized asynchronous platforms?
- Will the Reddit deployment (`EXP_019`) exhibit a faster response rate because it is a specialized technical subreddit, or will it also require days to mature?

### Next Thing to Watch
- Reddit timing (`EXP_019`).
- X scheduled payload deployment (`EXP_020`).
