import datetime as dt, importlib, sys

def test_recent_filters_by_date(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path); monkeypatch.setattr(sys, "argv", ["gaps.py"])
    import pandas as pd, os
    os.makedirs("data/tob/polymarket/m/"); pd.DataFrame(dict(recv_ns=[1, 2])).to_parquet("data/tob/polymarket/m/date=2026-10-12.parquet")
    g = importlib.import_module("gaps")
    fs = ["a/date=2026-10-10.parquet", "a/date=2026-10-11.parquet", "a/date=2026-10-12/part-1.parquet", "a/nodate.parquet"]
    today = dt.date(2026, 10, 12)
    assert g.recent(fs, None) == fs
    assert g.recent(fs, 2, today) == fs[1:3] and g.recent(fs, 1, today) == fs[2:3]
