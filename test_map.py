import json, os, tempfile
import pandas as pd
import map as M

U = pd.DataFrame({"market_id": ["a", "b", "c", "d", "e", "f"], "volume24hr": [6, 5, 4, 3, 2, 1], "question": [
    "Will the Fed decrease interest rates by 25 bps after the October 2026 meeting?",
    "Will the Fed increase interest rates by 50+ bps after the October 2026 meeting?",
    "Will there be no change in Fed interest rates after the October 2026 meeting?",
    "Will the price of Bitcoin be above $86,000 on October 10?",
    "Will Bitcoin dip to $65,000 in October?",
    "Will Marine Le Pen win the 2027 French presidential election?"]})


def dirs(title, kind="article"):
    th, c = M.candidates(title, U)
    return {m: M.keyword_dir(title, kind, th, q) for m, q in zip(c.market_id, c.question)}


def test_lexicon():
    assert dirs("Consumer Price Index", "scheduled") == {"a": "none", "b": "none", "c": "none"}  # no surprise word
    assert dirs("CPI comes in higher than expected") == {"a": "down", "b": "up", "c": "none"}
    assert dirs("US inflation misses forecasts") == {"a": "up", "b": "down", "c": "none"}
    assert dirs("Federal Reserve issues FOMC statement") == {"a": "none", "b": "none", "c": "none"}
    assert dirs("Fed cuts rate by 25 basis points")["a"] == "up"
    assert dirs("Bitcoin surges after ETF approval") == {"d": "up", "e": "down"}
    assert dirs("Bitcoin plunges as exchange hack drains funds") == {"d": "down", "e": "up"}
    assert dirs("Marine Le Pen appeals verdict") == {"f": "none"}
    assert dirs("8-K - AUTOZONE INC (0000866787) (Filer)", "filing") == {}


def test_parse():
    ids = {"m1": "a", "m2": "b"}
    ok = '```json\n[{"market_id":"m2","direction":"up","confidence":0.8}]\n```'
    assert M.parse_reply(ok, ids) == ([{"market_id": "b", "direction": "up", "confidence": 0.8}], None)
    assert M.parse_reply("[]", ids) == ([], None)
    for bad in ['[{"market_id":"m9","direction":"up","confidence":0.8}]', '[{"market_id":"m1","direction":"sideways","confidence":0.8}]',
                '[{"market_id":"m1","direction":"up","confidence":1.5}]', "no idea", '{"market_id":"m1"}',
                '[{"market_id":"m1","direction":"up","confidence":0.5},{"market_id":"m1","direction":"down","confidence":0.5}]']:
        assert M.parse_reply(bad, ids)[0] is None, bad


def test_rerun_skips():
    ev = pd.DataFrame({"event_id": ["e1", "e2", "e3"], "source": "x", "kind": "article", "url": "",
                       "title": ["Bitcoin surges", "Fed cuts rates", "8-K - FOO INC"],
                       "t0_utc": pd.to_datetime(["2026-10-01", "2026-10-02", "2026-10-03"], utc=True)})
    out = os.path.join(tempfile.mkdtemp(), "mapping.parquet")
    r1 = M.run(True, 0, out, U, ev)
    assert set(r1.event_id) == {"e1", "e2", "e3"} and r1[r1.event_id == "e3"].market_id.isna().all()
    n = len(pd.read_parquet(out))
    assert len(M.run(True, 0, out, U, ev)) == 0 and len(pd.read_parquet(out)) == n  # nothing remapped


def test_llm_path_with_fake_model(monkeypatch=None):
    reply = json.dumps([{"market_id": "m1", "direction": "up", "confidence": 0.7}])
    M.call_llm = lambda msg: (reply, 0.01, None)
    ev = pd.DataFrame({"event_id": ["e1"], "source": "x", "kind": "article", "url": "", "title": ["Bitcoin surges"],
                       "t0_utc": pd.to_datetime(["2026-10-01"], utc=True)})
    out = os.path.join(tempfile.mkdtemp(), "mapping.parquet")
    r = M.run(False, 5, out, U, ev)
    assert list(r.market_id) == ["d"] and list(r.method) == ["llm"] and list(r.direction) == ["up"]


if __name__ == "__main__":
    for f in (test_lexicon, test_parse, test_rerun_skips, test_llm_path_with_fake_model):
        f(); print("ok", f.__name__)
