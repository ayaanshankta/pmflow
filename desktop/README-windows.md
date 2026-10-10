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
Get-CimInstance Win32_Process | ? { $_.CommandLine -like "*pmflow*" } | select ProcessId, CommandLine   # verify
```
Scheduled passes (CPI/PPI): Task Scheduler, daily 07:50 and 09:50 CDT: `.venv\Scripts\python.exe -W ignore event_pass.py`, start-in `C:\projects\pmflow`; output in data\summary.md.
Health: `python gaps.py` lists recording gaps > 90 s. Data under data\tob is append-only; back up like market-maker (robocopy /XO to D:\).
Stop gracefully: identify by CommandLine (never by image name), then Stop-Process on that PID.
