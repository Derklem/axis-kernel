# Truth Map: Axis Truth Engine State

**Status**: DISCONNECTED COMPONENTS
Thinking: The Code exists, but the Pipeline is dead.

## 1. File Reality
| Component | Path | Status | Note |
| :--- | :--- | :--- | :--- |
| **Entrypoint** | `D:\Infinite\Infinity\Truth_Engine\Axis_Truth_Service.ps1` | **Alive** | Only handles `ACTION=CONSULT`. Missing `INGEST`. |
| **Strategy T01** | `...\Truth_Engine\Strategies\T01_LogObservation.ps1` | **Broken** | Calls non-existent `D:\Infinite\Axis_Truth_Engine.ps1`. |
| **Strategy T02** | `...\Truth_Engine\Strategies\T02_ResolveOrigins.ps1` | **Alive** | Implemented logic for origin resolution. |
| **Store (Nodes)** | `...\Truth_Engine\Content\TE_Content_Nodes.jsonl` | **Alive** | Contains real data (`origin_method` fields present). |
| **Store (Origin)** | `...\Truth_Engine\Content\TE_Origin_Map.jsonl` | **Alive** | Contains real edges (`ORIGIN-5c...`). |

## 2. Pipeline Truth Table
| Stage | Called By | Action | Result |
| :--- | :--- | :--- | :--- |
| **Service (Entry)** | Router/User | `CONSULT` | **OK** (Calls Triad). |
| **Service (Entry)** | Router/User | `INGEST` | **FAIL** (Action not handled). |
| **T01 (Log)** | *Nothing* | `INGEST` | **Dead Code**. |
| **T02 (Origins)** | *Nothing* | `RESOLVE` | **Dead Code**. |

## 3. Disconnect Diagnosis
The `Axis_Truth_Service.ps1` is the "Service Wrapper", but the `Strategies` (T01/T02) expect a central `Axis_Truth_Engine.ps1` orchestrator that **does not exist**.
They are calling a ghost.

## 4. Fix Plan (Recommendation)
1.  **Refactor `Axis_Truth_Service.ps1`** to become the Engine (or proxy to it).
    - Add `INGEST` action handler.
    - Implementing the pipeline logic: `T01 -> T02`.
2.  **Fix T01**: Point it to the correct parent/orchestrator or remove the recursive call.
3.  **Fix T02**: Ensure it is called after T01.
