# Axis Kernel

> **Deterministic governance for probabilistic planning.**

Axis Kernel is an experimental framework for separating probabilistic reasoning from deterministic execution.

Rather than allowing an LLM to directly execute actions, proposed actions are converted into structured proposals, validated against explicit policy, recorded with replayable receipts, and evaluated before execution.

The project explores one question:

> **How can autonomous planning become more auditable, reproducible, and falsifiable?**

```text
       LLM
        │
        ▼
Proposal Gateway
        │
        ▼
     Planner
        │
        ▼
 Strategy Engine
        │
        ▼
    Execution
```

---

## Core Components

### Proposal Gateway
Converts proposed actions into canonical, schema-validated proposals.
Responsibilities:
* validation
* normalization
* provenance
* canonical hashing
* deterministic receipts

---

### Planner
Ranks valid proposals under explicit policy.
Responsibilities:
* eligibility
* deterministic scoring
* agenda construction
* replayability

---

### Strategy Engine
Coordinates execution modes:
* LEGACY
* PLANNER_SHADOW
* PLANNER_CANARY
* PLANNER_LIVE

---

### Laboratory
Experimental framework for:
* preregistered hypotheses
* replay
* evaluation
* evidence collection

---

## Philosophy

Axis is not attempting to prove that language models are always correct.

Instead it assumes that probabilistic reasoning requires deterministic governance.

The objective is to reduce the probability that plausible-looking ideas quietly become accepted as truth.

---

## Current Status

Current work includes:
* Proposal Gateway
* Planner integration
* Shadow Mode evaluation
* replayable receipts
* deterministic governance

---

## Getting Started

Clone the repository:
`ash
git clone https://github.com/Derklem/axis-kernel.git
`

Create a virtual environment and install dependencies:
`ash
python -m venv .venv
# Activate the environment (e.g. .venv\Scripts\activate on Windows)
pip install -r requirements.txt
`

Run the smoke test to verify your environment:
`ash
pytest tests/smoke/test_repository_boot.py
`

Then explore:
* ProposalGateway/
* Planner/
* Strategy/
* Laboratory/

---

## Design Principles

* Explicit policies
* Replayability
* Evidence over intuition
* Provenance
* Recoverability
* Small falsifiable claims
