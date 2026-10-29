# F1 forward paper test runner for the "pmflow-f1-daily" (scan) and "pmflow-f1-settle" (weekly settle) tasks.
# Runs forward_no.py [settle] and appends its output, or the error, to data\forward\f1.log. Read-only on Gamma; never retries,
# so a Gamma error is logged and the run simply ends (the next scheduled run tries again).
param([ValidateSet("scan", "settle")][string]$mode = "scan")
$root = Split-Path -Parent $PSScriptRoot
$log = Join-Path $root "data\forward\f1.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
Set-Location $root
$pyArgs = @("-W", "ignore", "forward_no.py") + $(if ($mode -eq "settle") { @("settle") } else { @() })
$out = & (Join-Path $root ".venv\Scripts\python.exe") @pyArgs 2>&1 | ForEach-Object { "$_" }
$code = $LASTEXITCODE
$stamp = "{0:yyyy-MM-ddTHH:mm:ssZ}" -f (Get-Date).ToUniversalTime()
if ($code -eq 0) {
    Add-Content -Encoding utf8 $log ("{0} {1} {2}" -f $stamp, $mode, ($out -join " | "))
} else {
    Add-Content -Encoding utf8 $log ("{0} {1} ERROR exit {2}: {3}" -f $stamp, $mode, $code, (($out | Select-Object -Last 3) -join " | "))
}
exit $code
