import json, pandas as pd, collect as c, bluesky as b
TS = json.dumps([
    {"id": "2", "created_at": "2026-10-11T15:21:27.921Z", "content": "RT: <p>hi &amp; bye</p>", "url": "https://truthsocial.com/@realDonaldTrump/2", "media": []},
    {"id": "1", "created_at": "2026-10-11T15:00:00.100Z", "content": "", "url": "https://truthsocial.com/@realDonaldTrump/1", "media": ["x.jpg"]},
    {"id": "0", "created_at": "2025-01-01T00:00:00.000Z", "content": "old", "url": "u0", "media": []}])
BS = {"did": "did:plc:abc", "time_us": 1760000000000000, "kind": "commit", "commit": {"operation": "create",
      "collection": "app.bsky.feed.post", "rkey": "3k", "record": {"text": "BREAKING:\nFed holds", "createdAt": "2026-10-11T14:00:01.789Z"}}}

def test_truthsocial(tmp_path):
    now = pd.Timestamp("2026-10-12T00:00:00Z")
    r = c.parse_truthsocial(TS, now=now)                       # 7-day backfill drops "old"
    assert [x["title"] for x in r] == ["RT: hi & bye", "[media]"]
    assert r[0]["t0_utc"] == pd.Timestamp("2026-10-11T15:21:27Z") and r[0]["kind"] == "post"
    assert [x["title"] for x in c.parse_truthsocial(TS, since=pd.Timestamp("2026-10-11T15:00:00Z"))] == ["RT: hi & bye"]  # only newer than last seen

def test_bluesky(tmp_path):
    recv = pd.Timestamp("2026-10-11T14:00:03.5Z")
    row = b.parse_msg(BS, {"did:plc:abc": "ap.test"}, recv)
    assert row["t0_utc"] == pd.Timestamp("2026-10-11T14:00:01Z") and row["first_seen_utc"] == pd.Timestamp("2026-10-11T14:00:03Z")
    assert row["title"] == "BREAKING: Fed holds" and row["url"] == "https://bsky.app/profile/ap.test/post/3k" and row["source"] == "bluesky"
    assert b.parse_msg(BS, {}) is None                                          # unwatched DID
    assert b.parse_msg({**BS, "commit": {**BS["commit"], "operation": "delete"}}, {"did:plc:abc": "x"}) is None
    out = tmp_path / "events.parquet"
    assert c.merge([row], out) == 1 and c.merge([row], out) == 0               # shared writer + dedup
    df = pd.read_parquet(out); assert list(df.columns) == c.COLS and df.first_seen_utc[0] == recv.floor("s")
