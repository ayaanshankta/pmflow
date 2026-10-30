# F1 forward paper test runner for the "pmflow-f1-daily" (scan) and "pmflow-f1-settle" (weekly settle) tasks.
# Runs forward_no.py (scan), or forward_no.py settle then forward_no.py f2 (settle), and appends each output, or the error, to
# data\forward\f1.log. Read-only on Gamma; never retries, so a Gamma error is logged and the run simply ends (the next scheduled run
# tries again). f2 runs even if settle failed; the exit code is the first non-zero one.
param([ValidateSet("scan", "settle")][string]$mode = "scan")
$root = Split-Path -Parent $PSScriptRoot
$log = Join-Path $root "data\forward\f1.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
Set-Location $root
$steps = if ($mode -eq "settle") { @("settle", "f2") } else { @("scan") }
$rc = 0
foreach ($step in $steps) {
    $pyArgs = @("-W", "ignore", "forward_no.py") + $(if ($step -ne "scan") { @($step) } else { @() })
    $out = & (Join-Path $root ".venv\Scripts\python.exe") @pyArgs 2>&1 | ForEach-Object { "$_" }
    $code = $LASTEXITCODE
    $stamp = "{0:yyyy-MM-ddTHH:mm:ssZ}" -f (Get-Date).ToUniversalTime()
    if ($code -eq 0) {
        Add-Content -Encoding utf8 $log ("{0} {1} {2}" -f $stamp, $step, ($out -join " | "))
    } else {
        Add-Content -Encoding utf8 $log ("{0} {1} ERROR exit {2}: {3}" -f $stamp, $step, $code, (($out | Select-Object -Last 3) -join " | "))
        if (-not $rc) { $rc = $code }
    }
}
exit $rc
