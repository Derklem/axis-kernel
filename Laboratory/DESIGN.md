# Design & Architecture Motivations

Why is the Laboratory architected the way it is? This document explains the core design decisions.

## Why an append-only JSONL ledger instead of a Database?
A SQLite or Postgres database would be faster and easier to query, but it fundamentally obscures the concept of *time* and *immutability*. A JSONL file is universally readable, inherently append-only, and extremely easy to hash block-by-block. It removes the need for a database server, allowing the Laboratory to run entirely locally in a user's repository without daemon dependencies.

## Why Canonical JSON instead of Binary Serialization?
Protobuf, MessagePack, or BSON are more efficient, but they sacrifice human legibility. Evidence should be inspectable by a human using standard Unix tools (`cat`, `jq`, `grep`). Canonical JSON strikes the perfect balance: it is strict enough to produce deterministic hashes, but simple enough to be read in any text editor.

## Why separate Receipts from the Ledger?
The ledger is the immutable anchor of time, but the receipt contains the heavy details of a specific run (hashes of all inputs, outputs, and artifacts). 
By keeping the receipt alongside the artifact files in the `runs/` directory, the evidence payload is highly portable. You can zip a specific `RUN_...` directory and send it to a colleague. As long as they have a copy of the ledger containing the corresponding hash anchor, they can independently verify the portable evidence.

## Why "Ruthless Verification"?
Verification is a binary state. We explicitly chose not to implement "partial verification" or "auto-repair" features. If an artifact is missing, the run fails. If a timestamp is altered, the run fails. This ruthlessness is necessary to build trust in the protocol. If the verifier was lenient, it would no longer be an evidence engine; it would just be a compatibility layer.
