$path = "D:\Infinite\Infinity\Runtime\Decision\T08_Executor.ps1"
$code = Get-Content $path -Raw
$errors = @()
[System.Management.Automation.PSParser]::Tokenize($code, [ref]$errors) | Out-Null
if ($errors.Count -gt 0) {
    echo "SYNTAX ERRORS FOUND:"
    foreach ($e in $errors) {
        echo "Line $($e.StartLine): $($e.Message)"
    }
} else {
    echo "NO SYNTAX ERRORS"
}
