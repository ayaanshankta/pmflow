import pandas as pd, alpaca_history as h
def test_months_and_resume(tmp_path):
    assert [(f"{a:%F}", f"{b:%F}") for a, b in h.months("2025-11-15", "2026-01-10")] == [
        ("2025-11-15", "2025-12-01"), ("2025-12-01", "2026-01-01"), ("2026-01-01", "2026-01-11")]
    calls = []
    def fake(a, b, hd):
        calls.append(a); return [{"id": 2, "created_at": "2025-09-02T00:00:01Z", "headline": "b", "url": "u", "symbols": ["X"], "source": "benzinga"},
                                 {"id": 9, "created_at": "2025-08-20T00:00:00Z", "headline": "old", "url": "u", "symbols": [], "source": "benzinga"},
                                 {"id": 1, "created_at": "2025-09-01T00:00:01Z", "headline": "a", "url": "u", "symbols": [], "source": "benzinga"},
                                 {"id": 1, "created_at": "2025-09-01T00:00:01Z", "headline": "a", "url": "u", "symbols": [], "source": "benzinga"}]
    assert h.run("2025-09-01", "2025-09-30", tmp_path, {}, fake) == 2
    assert h.run("2025-09-01", "2025-09-30", tmp_path, {}, fake) == 0 and len(calls) == 1   # resumed: month skipped
    df = pd.read_parquet(next(tmp_path.glob("*.parquet")))
    assert list(df.title) == ["a", "b"] and list(df.symbols[1]) == ["X"] and (df.source == "alpaca").all()
