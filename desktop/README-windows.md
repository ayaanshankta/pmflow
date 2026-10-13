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
## Reading recorder.log
Each minute: `rows/min ... flush_s ... late_ms_* ... held=N failed_files=M`. `held` is rows kept in memory because a file could not be
replaced (another program had it open); they are written by a later save. A line starting `NOT RECORDING` means no save has fully
succeeded for 3 minutes. No per-minute line for more than 3 minutes is the same alarm. `flush FAILED <file>` names the file that was locked.
## Tests on this machine
`python -m pytest -q`, `python test_record.py`, `python test_universe.py`, `python test_flushfail.py`, `python test_filelock_real.py`
(the last one holds a real file handle open during a save; on Windows it must report that the rename was blocked: True).
