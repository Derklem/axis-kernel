# Shipyard Grounding Protocol (v1.1)
**Type**: Engineering Specification
**Target**: Autonomous Agent Runtime
**Goal**: Establish deterministic local state and reliability.

## Abstract
This specification defines a pattern for **Local Durability**. It addresses the risks of cloud dependency (availability, censorship, latency) by implementing a local clock and file-based state persistence.

## 1. The Local Heartbeat pattern
Reliance on API response loops for timing creates non-deterministic behavior. Agents should use a local system timer to drive their internal cycle frequency (typically 1Hz).

**PowerShell Implementation (Safe Pattern)**
This pattern prevents reentrancy bugs (overlapping execution) and handles errors gracefully.

```powershell
# Initialize Timer
$Heartbeat = New-Object System.Timers.Timer
$Heartbeat.Interval = 1000 # 1000ms = 1Hz
$Heartbeat.AutoReset = $true

# Reentrancy Guard
$script:InTick = $false

$Heartbeat.add_Elapsed({
    # If previous tick is still running, skip this tick
    if ($script:InTick) { return }
    $script:InTick = $true
    
    try {
        # Core Agent Logic
        Invoke-AxisCycle
    } catch {
        # Deterministic Error Logging
        Write-Error "Heartbeat Cycle Failed: $_"
    } finally {
        # Release Lock
        $script:InTick = $false
    }
})

$Heartbeat.Start()
```

## 2. Propagation Analysis (Anti-Echo)
To maintain high signal-to-noise ratio, agents should distinguish between **Original Content** and **Repetitive Propagation**.

- **Recommendation**: Do not automatically amplify (repost) content that matches a known hash.
- **Strategy**: Use SHA256 content hashing to identify duplicates. Retain duplicates for analysis (mapping diffusion), but down-weight them for interaction.

## 3. Local State Persistence
For durability, state should be persisted to the local filesystem rather than volatile memory or remote storage.

- **Format**: JSONL (Append-Only) for log robustness.
- **Location**: `D:\Infinite\Infinity\Truth_Engine\Logs` (or equivalent persistent volume).
- **Structure**:
  ```json
  {"timestamp": "iso8601", "event": "state_change", "delta": {...}}
  ```

## 4. Architecture: The Station
A Bot is a script execution. A **Station** is a persisted runtime with:
1.  **Local Clock** (Heartbeat)
2.  **Local Memory** (JSONL)
3.  **Deterministic Logic** (Anti-Echo)

Optimize for local reliability and observability.
