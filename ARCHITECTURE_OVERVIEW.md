# Axis Architecture Overview

## The Motivation
The Axis Kernel exists to address a fundamental friction point in autonomous systems: **probabilistic reasoning vs. deterministic execution.**

Large Language Models (LLMs) are incredibly powerful reasoning engines, but they are inherently probabilistic. They hallucinate, they lose context, and their outputs can drift over time. In contrast, physical systems, production environments, and secure workflows demand deterministic, predictable, and safe execution.

When you connect a probabilistic engine directly to an execution layer, you inherit the probability of failure at the system level.

## The Axis Hypothesis
Axis is not attempting to prove that language models are always correct. Instead, it assumes that **probabilistic reasoning requires deterministic governance.** 

Our objective is to reduce the probability that plausible-looking but subtly flawed ideas quietly become accepted as truth and executed by the system.

## Key Architectural Principles

### 1. The Proposal Gateway
Instead of allowing the LLM to directly invoke tools or APIs, the Planner must formulate its intent into a **Proposal**. This proposal is passed to the **Proposal Gateway**—a purely deterministic, mathematically rigid boundary.

The Gateway ensures that every proposed action:
- Matches a predefined, strict schema.
- Adheres to explicit governance policies.
- Has an auditable provenance trail.

If a proposal violates any invariant, the execution is halted and the proposal is rejected. The LLM never touches the execution layer directly.

### 2. Evidence Over Intuition (Shadow Mode)
Before trusting an autonomous agent to execute, we must measure what it *would* have done. 
Axis introduces **Shadow Mode**: the Planner generates full action proposals against live tasks, but the execution is purely simulated. The Gateway records these proposals into replayable receipts. 

Shadow mode exists to measure behavior before changing behavior, allowing us to build an empirical dataset to prove safety before transitioning to Canary or Live execution.

### 3. Replayability & Falsifiability
Every action that passes through the Gateway is hashed and recorded as a **Receipt**. Because the Gateway is deterministic, a receipt can be replayed at any time to guarantee that the system state was exactly as recorded. 

By enforcing small, falsifiable claims, we ensure that the system's behavior can always be audited, verified, and challenged.

## Conclusion
The Axis Kernel is a framework for building verifiable trust. By enforcing a rigid, deterministic boundary between the "brain" and the "hands," we allow the probabilistic reasoning of LLMs to safely scale in environments that demand absolute reliability.
