# Laboratory Protocol Specification

This is the normative document defining the Laboratory Evidence Protocol v0.1.0. If you are implementing the protocol in another language, this document defines what "correct" means.

## Protocol Guarantees

1. Evidence accepted by the verifier exactly matches the frozen receipt.
2. Receipt integrity is cryptographically anchored to the ledger.
3. Ledger history is purely append-only and cryptographically chained.
4. Verification never mutates evidence (zero side-effects).
5. Undeclared evidence (added files) or missing evidence invalidates verification.

## 2. Canonical Serialization
Before any JSON payload is hashed, it MUST be serialized into a canonical byte string. 
We rely on a deterministic JSON subset to guarantee cross-language agreement.

### Rules:
1. **No Whitespace:** All structural whitespace (spaces, newlines, tabs) between keys and values MUST be omitted. (In Python: `separators=(',', ':')`).
2. **Lexicographical Key Sorting:** Object keys MUST be sorted lexicographically by their UTF-8 byte values before serialization. (In Python: `sort_keys=True`).
3. **No Floating-Point Numbers:** Canonically hashed Laboratory JSON structures MUST NOT contain floating-point numbers. JSON numbers MUST be integers within the interoperable safe-integer range `-9,007,199,254,740,991` through `9,007,199,254,740,991`. This avoids disagreement among implementations that represent JSON numbers differently (e.g., IEEE-754 doubles by default).

This restriction covers ledger events, receipts, experiment specifications, and any future JSON structure hashed through canonical serialization.

Example Canonical Form:
`{"event_schema_version":"1.0.0","event_type":"RUN_STARTED","payload":{"experiment_hash":"abcd...","run_id":"RUN_123"},"previous_hash":null,"sequence":0,"timestamp":"2026-06-25T14:32:01Z"}`).
3. Strings must be encoded in `UTF-8`.

## Hashing

The protocol exclusively uses **SHA-256**. 
- JSON structures are hashed using the canonical serialization defined above.
- Files (inputs, outputs, artifacts) are hashed purely on their binary byte content, chunked to support files larger than memory.

## Ledger Topology

The ledger is a sequence of JSONL events (`ledger.jsonl`).
- **Genesis Block**: The first event (`sequence: 0`) must have `event_type: "LEDGER_INITIALIZED"` and `previous_hash: null`.
- **Chaining**: Every subsequent event must explicitly declare `previous_hash` equal to the `hash` of the immediately preceding event.
- **Monotonicity**: `sequence` must strictly increase by exactly `1` for each event.

## Verification Semantics

A compliant verifier must return one of three states for a given `run_id`:

- **PASS**: All required evidence is present, intact, and exactly matches the ledger's cryptographic anchors.
- **FAIL**: Evidence exists but has been altered, malformed, contains unauthorized additions/omissions, or contradicts the ledger chain.
- **UNVERIFIABLE**: Required evidence (e.g., the receipt or the ledger file) is unavailable, making it impossible to establish the claim.

A missing receipt is not necessarily proof of tampering, but it MUST NOT pass. It is UNVERIFIABLE.
