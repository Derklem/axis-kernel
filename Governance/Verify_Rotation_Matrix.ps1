# Verify_Rotation_Matrix.ps1
Import-Module "D:\Infinite\Infinity\Truth_Engine\T08_LifecycleGate.psm1" -Force

$id = "system:tester"
$matrix = @(
    @{ Case = 'v4 (Current)'; Env = @{identity = $id; key_id = 'k_system_tester_v4' }; Op = 'test.op' },
    @{ Case = 'v3 (Revoked)'; Env = @{identity = $id; key_id = 'k_system_tester_v3' }; Op = 'test.op' },
    @{ Case = 'Missing Key'; Env = @{identity = $id; key_id = '' }; Op = 'test.op' },
    @{ Case = 'Wrong Bound'; Env = @{identity = 'system:promoter'; key_id = 'k_system_tester_v4' }; Op = 'test.op' }
)

$results = foreach ($c in $matrix) {
    $res = Test-AxisKeyLifecycleAllowed -Envelope $c.Env -OpKey $c.Op -NoCache
    [pscustomobject]@{
        Case   = $c.Case
        Result = if ($res.ok) { "PASS" }else { "BLOCK" }
        Reason = $res.reason
    }
}

$results | Format-Table -AutoSize
