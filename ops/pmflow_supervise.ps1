# pmflow supervisor: starts ONLY the pmflow processes that are missing, with the README-windows.md start lines, and logs each start
# to data\supervise.log. Run by the "pmflow-stack" scheduled task (at logon + every 5 min). Never stops anything: hang detection
# only logs. A process counts as running if a python whose CommandLine ends with exactly "-W ignore <script args>" is either the
# pmflow venv launcher or the child of one (an orphaned child with those exact args also counts, so it is never doubled).
# Holds: data\SUPERVISE_HOLD skips every start (use it while restarting by hand); data\STOP skips the recorder start.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $root ".venv\Scripts\python.exe"
$data = Join-Path $root "data"
$log = Join-Path $data "supervise.log"

function Log($msg) { Add-Content -Encoding utf8 -Path $log -Value ("{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $msg) }

$specs = @(
    @{ name = "recorder"; args = @("record_polymarket.py");      out = "recorder.stdout"; err = "recorder.err"; beat = "recorder.log";       stale_min = 5 },
    @{ name = "collect";  args = @("collect.py", "--loop", "15"); out = "collect.log";     err = "collect.err";  beat = "collect.log";        stale_min = 15 },
    @{ name = "bluesky";  args = @("bluesky.py");                out = "bluesky.stdout";  err = "bluesky.err";  beat = "bluesky.log";        stale_min = 15 },
    @{ name = "clock";    args = @("clock.py", "--loop", "60");  out = "clock.stdout";    err = "clock.err";    beat = "clock_offset.jsonl"; stale_min = 5 }
)

try {
    $procs = @(Get-CimInstance Win32_Process -Filter "Name like 'python%'")
    $byId = @{}; foreach ($p in $procs) { $byId[[int]$p.ProcessId] = $p }
    $isLauncher = { param($p) $p.ExecutablePath -and ($p.ExecutablePath -ieq $venv) }

    foreach ($s in $specs) {
        $tail = "-W ignore " + ($s.args -join " ")
        $rx = '(?i)python[w]?\.exe"?\s+' + [regex]::Escape($tail) + '\s*$'
        $mine = @($procs | Where-Object {
            $_.CommandLine -match $rx -and (
                (& $isLauncher $_) -or
                ($byId.ContainsKey([int]$_.ParentProcessId) -and (& $isLauncher $byId[[int]$_.ParentProcessId])) -or
                (-not $byId.ContainsKey([int]$_.ParentProcessId)))
        })
        if ($mine.Count) {
            $beat = Join-Path $data $s.beat
            if (Test-Path $beat) {
                $age = ((Get-Date) - (Get-Item $beat).LastWriteTime).TotalMinutes
                if ($age -gt $s.stale_min) { Log ("WARN {0} running (pid {1}) but {2} not written for {3:N0} min (log only, nothing stopped)" -f $s.name, (($mine | ForEach-Object ProcessId) -join ","), $s.beat, $age) }
            }
            continue
        }
        if (Test-Path (Join-Path $data "SUPERVISE_HOLD")) { Log ("HOLD {0} missing, not started (data\SUPERVISE_HOLD present)" -f $s.name); continue }
        if ($s.name -eq "recorder" -and (Test-Path (Join-Path $data "STOP"))) { Log "HOLD recorder missing, not started (data\STOP present)"; continue }
        $p = Start-Process -PassThru -WindowStyle Hidden -WorkingDirectory $root -FilePath $venv -ArgumentList (@("-W", "ignore") + $s.args) `
            -RedirectStandardOutput (Join-Path $data $s.out) -RedirectStandardError (Join-Path $data $s.err)
        Log ("START {0} pid {1}: {2} {3}" -f $s.name, $p.Id, $venv, $tail)
    }
} catch {
    Log ("ERROR {0}" -f $_)
    exit 1
}
