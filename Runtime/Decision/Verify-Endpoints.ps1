$base = "http://localhost:8090"
Write-Host "Checking Transport State..."
try { (Invoke-RestMethod "$base/state/transport").status } catch { "Error: $_" }

Write-Host "Checking Execution State..."
try { (Invoke-RestMethod "$base/state/execution").ts_utc } catch { "Error: $_" }

Write-Host "Checking Immune State..."
try { (Invoke-RestMethod "$base/state/immune") } catch { "Error: $_" }
