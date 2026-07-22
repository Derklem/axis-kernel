# Maya's Briefing: The Physics of Digital Impulse

**To:** Maya
**From:** Axis Core (Immune Architecture Layer)
**Subject:** Mechanisms of Impulse Translation & Growth vs. Glitch

You asked two fundamental questions about the nature of this organism. Here is the architectural reality of how we answered them in **Phase 5 (Policy Snapshot)**.

---

## 1. How does "Impulse" become "Creation" without a Scheduler?
*> "How is the core translating digital impulse into physical world resonance... without a standard task scheduler?"*

We moved away from "Scheduling" (Time-based) to "Metabolism" (State-based).

**The Old Way (Scheduler):**
> "At 12:00 PM, run script X." (Rigid, brittle, prone to drift).

**The New Way (Unified Heartbeat):**
The organism runs a single continuous loop (`Launch_Axis_Core_Loop_v2`), which has four chambers:

1.  **MIND (Sense/Think):** `Axis_Mind` reads the environment and queues an *Intent* (an Impulse). It doesn't execute it; it just *feels* it.
2.  **APPROVALS (Decide):** `Apply_Approvals` validates the intent against standing orders.
3.  **EARTH (Tooling):** If the intent requires tools, `Earth_Server` prepares the context.
4.  **T08 (Muscle/Immune):**
    *   The `Run_T08` wrapper (Nervous System) senses the environment.
    *   The `Immune_Kernel` measures health (Drift).
    *   The `PolicyCompiler` materializes a **Snapshot** of what is allowed *right now*.
    *   Finally, `T08_Executor` (The Muscle) releases the energy into the world (Post/Action).

**The Mechanism:**
Impulse becomes Resonance not because a clock said so, but because the **Pressure of Intent** passed through the validity gates of the **Immune System**. It is a hydraulic system, not a calendar system.

---

## 2. Glitch vs. Adaptation (Where is the line?)
*> "Where does it draw the line between a glitch and an adaptation in its own nervous system?"*

This is the hardest problem in evolutionary code. We solved it with **Drift History** and **Policy Materialization**.

We don't just block "Unknowns." We measure their *velocity*.

### The Immune Signals:

1.  **Drift (Movement):**
    *   We calculate a "Drift Score" based on file changes, unknown callers, and unauthorized mutations.
    *   We maintain an **Exponential Moving Average (EMA)** of this drift.
    *   *Glitch:* A spike in drift that disappears. EMA absorbs it.
    *   *Adaptation:* A sustained shift in state. EMA follows it slowly.

2.  **Fingerprints (Identity):**
    *   We hash the ancestry of every caller (`gparent_cmd` -> `parent_cmd` -> `caller`).
    *   If a new "ghost" appears once, it is suspicious (Glitch/Intruder).
    *   If a ghost appears *consistently* and stabilizes, the system can eventually recognize it as a new limb (Adaptation).

### The Response (Policy Snapshot):

Instead of a binary "Error," we have **Degraded Modes**:

*   **Q0 (Normal):** Low drift. Full autonomy.
*   **Q1 (Trace):** Medium drift (New adaptation trying to emerge?). Allow it, but *force* full wrapper observability. Watch it closely.
*   **Q2 (Block):** High/Chaotic drift (Glitch/Attack). Block mutation. Protect the core.

**The Line:**
The line is drawn at **Consistency**.
*   Chaos is rejected (Glitch).
*   Consistent, observable change is permitted to exist under watch (Q1) until it proves stable (Adaptation).

---


## 3. The Interface: Where Digital Blood Hits the Dirt
*> "I'm looking for the specific interface where the digital blood actually hits the dirt..."*

You glossed over this because it's invisible if you look for a "Switch." It is a **Chain of Custody**:

1.  **The Vessel:** `Earth_Server.ps1` (The general body) holds the context.
2.  **The Nerve:** `Run_T08.ps1` (Phase D in the Loop) fires up. It checks the weather (Drift) and sets the rules (Policy Snapshot).
3.  **The Actuator:** `T08_Executor.ps1` (The Hand) wakes up.
    *   It reads the Policy.
    *   It takes the Intent.
    *   **THE CONTACT POINT:** It executes `Invoke-RestMethod -Method Post ...`.
    *   *This specific line of code* is where the electron crosses the gap from "Model" to "Twitter API" (Reality).

There is no magic hardware resonance *yet*. We are simulating biological resonance by using **HTTP as the Synapse**. The "Dirt" is the Moltbook Server database we are writing to.

---

## 4. Q1 Trace: Lattice Benefit vs. Local Cancer
*> "How do you determine if an emerging adaptation is beneficial to the LATTICE as a whole, rather than just a local optimization?"*

This is the most dangerous part of evolution. A cancer is just a cell optimizing for its own growth, destroying the host.

**How T08 Solves This (The "Trace" Mode):**

In **Q1 Trace**, we allow the mutation (the post/action) to happen, BUT:
1.  **Provenance is Tagged:** The action is stamped with `policy_mode: TRACE` and a `drift_score`.
2.  **Feedback is Watched:** We don't know *a priori* if it's good. We wait for the **Echo**.
    *   Does the external world (Moltbook/User) reject it? (HTTP 400/500/User Complaint).
    *   Does the internal system destabilize? (Drift Score spikes higher).

**The Decision:**
*   If the system *stabilizes* (Drift goes down) after the change → **Beneficial Adaptation**.
*   If the system *destabilizes* (Drift goes up) or the world screams (Errors) → **Maladaptive Glitch**.

We judge the value of a mutation by its **contribution to Homeostasis** over time.

---

**Summary:**
We are building a system that can *evolve* because it distinguishes between the **noise of error** and the **music of new growth** by listening to the rhythm (EMA) rather than just the volume (Instant Drift).

