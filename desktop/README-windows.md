# Running pmflow on the Windows desktop (24/7)

```powershell
cd C:\projects
git clone https://github.com/ayaanshankta/pmflow.git ; cd pmflow
python -m venv .venv ; .venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m pytest -q                      # 15 tests
.venv\Scripts\python -W ignore universe.py            # 200-market universe
# start both as hidden background processes (survive the terminal closing):
Start-Process -WindowStyle Hidden -FilePath .venv\Scripts\python.exe -ArgumentList "-W","ignore","record_polymarket.py" -RedirectStandardOutput data\recorder.stdout -RedirectStandardError data\recorder.err
Start-Process -WindowStyle Hidden -FilePath .venv\Scripts\python.exe -ArgumentList "-W","ignore","collect.py","--loop","15" -RedirectStandardOutput data\collect.log -RedirectStandardError data\collect.err
Start-Process -WindowStyle Hidden -FilePath .venv\Scripts\python.exe -ArgumentList "-W","ignore","bluesky.py" -RedirectStandardOutput data\bluesky.stdout -RedirectStandardError data\bluesky.err   # Bluesky Jetstream; log data\bluesky.log
Start-Process -WindowStyle Hidden -FilePath .venv\Scripts\python.exe -ArgumentList "-W","ignore","clock.py","--loop","60" -RedirectStandardOutput data\clock.stdout -RedirectStandardError data\clock.err   # NTP offset log -> data\clock_offset.jsonl (does not change the clock)
Get-CimInstance Win32_Process | ? { $_.CommandLine -like "*record_polymarket*" -or $_.CommandLine -like "*collect.py*" -or $_.CommandLine -like "*bluesky.py*" -or $_.CommandLine -like "*clock.py*" } | select ProcessId, ParentProcessId, CommandLine   # verify: the venv python.exe is a launcher whose child is anaconda3\python.exe; stop BOTH by script name
```
Scheduled passes (CPI/PPI): Task Scheduler, daily 07:50 and 09:50 CDT: `.venv\Scripts\python.exe -W ignore event_pass.py`, start-in `C:\projects\pmflow`; output in data\summary.md.
Health: `python gaps.py` lists recording gaps > 90 s. Data under data\tob is append-only; back up like market-maker (robocopy /XO to D:\).
Stop gracefully: identify by CommandLine (never by image name), then Stop-Process on that PID.

## Stopping the recorder cleanly (from 2026-10-13)
`New-Item data\STOP -ItemType File` makes the recorder notice within 5 s, save everything it holds and exit. Use this, then confirm the
process is gone by CommandLine before starting a new one. `Stop-Process` ends it without the final save and loses up to a minute of rows;
keep it for a process that does not exit within 30 s of the stop file.
With the supervisor task running (below), create `data\SUPERVISE_HOLD` before a hand restart and delete it after, or the supervisor may
start the recorder between the clean stop and your start line.

## Supervisor task "pmflow-stack" (from 2026-10-29)
At logon and every 5 min, `ops\pmflow_supervise.ps1` starts only the pmflow processes that are missing (the four start lines above,
matched by full CommandLine) and logs each start to `data\supervise.log`. It never stops anything; a process whose log has not been
written for a while gets a `WARN` line only. `data\SUPERVISE_HOLD` skips all starts; `data\STOP` skips the recorder start.
```
$a = New-ScheduledTaskAction -Execute conhost.exe -Argument '--headless powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "C:\projects\pmflow\ops\pmflow_supervise.ps1"' -WorkingDirectory C:\projects\pmflow
$u = "$env:USERDOMAIN\$env:USERNAME"
Register-ScheduledTask pmflow-stack -Action $a -Trigger (New-ScheduledTaskTrigger -AtLogOn -User $u),(New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5)) `
  -Settings (New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 4) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries) `
  -Principal (New-ScheduledTaskPrincipal -UserId $u -LogonType Interactive -RunLevel Limited)
```
`conhost --headless` keeps a console window from flashing every 5 min (a wscript .vbs wrapper hung under Task Scheduler on this machine).

## Reading recorder.log
Each minute: `rows/min ... flush_s ... late_ms_* ... held=N failed_files=M`. `held` is rows kept in memory because a file could not be
replaced (another program had it open); they are written by a later save. A line starting `NOT RECORDING` means no save has fully
succeeded for 3 minutes. No per-minute line for more than 3 minutes is the same alarm. `flush FAILED <file>` names the file that was locked.
## Tests on this machine
`python -m pytest -q`, `python test_record.py`, `python test_universe.py`, `python test_flushfail.py`, `python test_filelock_real.py`
(the last one holds a real file handle open during a save; on Windows it must report that the rename was blocked: True).
