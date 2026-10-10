import pandas as pd, collect as c
NOW = pd.Timestamp("2026-10-10T08:00:00Z")
ICS = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:a1
DTSTART;TZID=US-Eastern:20261014T083000
SUMMARY:Consumer Price Index (Monthly)
END:VEVENT
BEGIN:VEVENT
UID:a2
DTSTART;TZID=US-Eastern:20261215T083000
SUMMARY:December event beyond 14 days
END:VEVENT
BEGIN:VEVENT
UID:a3
DTSTART;TZID=US-Eastern:20261102T083000
SUMMARY:Post-DST-end but too far
END:VEVENT
BEGIN:VEVENT
UID:b1
DTSTART;VALUE=DATE-TIME:20261015T123000Z
SUMMARY:Gross Domestic Product\\, 3rd Quarter (Adv
 ance Estimate)
END:VEVENT
END:VCALENDAR"""
RSS = """﻿<?xml version="1.0" encoding="utf-8" ?><rss version="2.0"><channel><item><title>FOMC statement</title>
<link><![CDATA[https://x/y.htm]]></link><guid><![CDATA[https://x/y.htm]]></guid><pubDate><![CDATA[Wed, 17 Sep 2025 18:00:00 GMT]]></pubDate></item>
<item><title>Offset &amp; zone</title><link>https://x/z</link><pubDate>Fri, 9 Oct 2026 10:00:07 -0400</pubDate></item></channel></rss>"""
ATOM = """<?xml version="1.0" encoding="ISO-8859-1" ?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>8-K - AUTOZONE INC (0000866787) (Filer)</title>
<link rel="alternate" href="https://sec/idx.htm"/><updated>2026-10-09T17:30:15-04:00</updated><id>urn:tag:sec.gov,2008:accession-number=0001171843-26-006565</id></entry></feed>"""

def test_ics():
    r = {x["event_id"]: x for x in c.parse_ics(ICS, "bls", "scheduled", now=NOW)}
    ts = {x["title"]: x["t0_utc"] for x in r.values()}
    assert len(r) == 2, ts                       # 14-day window drops a2, a3
    assert ts["Consumer Price Index (Monthly)"] == pd.Timestamp("2026-10-14T12:30:00Z")   # EDT = UTC-4
    assert ts["Gross Domestic Product, 3rd Quarter (Advance Estimate)"] == pd.Timestamp("2026-10-15T12:30:00Z")  # Z kept, unfolded

def test_et_dst():
    f = lambda d: c.parse_ics(f"BEGIN:VEVENT\nUID:u\nDTSTART;TZID=US-Eastern:{d}T083000\nSUMMARY:s\nEND:VEVENT", "bls", "scheduled",
                              now=pd.Timestamp(d + "T00:00:00Z"), days=1)[0]["t0_utc"]
    assert f("20261103") == pd.Timestamp("2026-11-03T13:30:00Z")   # after DST end: EST, UTC-5
    assert f("20261031") == pd.Timestamp("2026-10-31T12:30:00Z")   # before: EDT, UTC-4
    assert f("20260310") == pd.Timestamp("2026-03-10T12:30:00Z")   # after DST start (Mar 8)
    assert f("20260305") == pd.Timestamp("2026-03-05T13:30:00Z")

def test_rss_atom():
    r = c.parse_rss(RSS, "fed", "release")
    assert [x["t0_utc"] for x in r] == [pd.Timestamp("2025-09-17T18:00:00Z"), pd.Timestamp("2026-10-09T14:00:07Z")]
    assert r[1]["title"] == "Offset & zone"
    a = c.parse_atom(ATOM, "sec_8k", "filing")[0]
    assert a["t0_utc"] == pd.Timestamp("2026-10-09T21:30:15Z") and a["kind"] == "filing"

def test_dedup_append_only(tmp_path):
    out = tmp_path / "events.parquet"
    rows = c.parse_rss(RSS, "fed", "release")
    assert c.merge(rows, out, now=pd.Timestamp("2026-10-10T01:00:00Z")) == 2
    assert c.merge(rows, out, now=pd.Timestamp("2026-10-10T02:00:00Z")) == 0   # rerun adds nothing
    more = rows + c.parse_atom(ATOM, "sec_8k", "filing")
    assert c.merge(more, out, now=pd.Timestamp("2026-10-10T03:00:00Z")) == 1
    df = pd.read_parquet(out)
    assert len(df) == 3 and df.event_id.is_unique and list(df.columns) == c.COLS
    assert (df.first_seen_utc[:2] == pd.Timestamp("2026-10-10T01:00:00Z")).all()  # first sighting kept
    assert str(df.t0_utc.dt.tz) == "UTC" and df.t0_utc.dt.microsecond.eq(0).all()

if __name__ == "__main__":
    import tempfile, pathlib
    test_ics(); test_et_dst(); test_rss_atom(); test_dedup_append_only(pathlib.Path(tempfile.mkdtemp())); print("ok")
