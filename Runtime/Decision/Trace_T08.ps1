Set-PSDebug -Trace 1
& "D:\Infinite\Infinity\Runtime\Decision\T08_Executor.ps1" 2>&1 | Out-File "D:\Infinite\Infinity\Runtime\Decision\t08_trace.txt" -Encoding UTF8
Set-PSDebug -Trace 0
