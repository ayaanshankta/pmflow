"""News/event collector -> data/events.parquet (append-only, dedup by event_id).
Columns: event_id, source, t0_utc, first_seen_utc, title, url, kind. All times UTC, second precision.
  python3 collect.py --once      one poll of every source
  python3 collect.py --loop 15   poll every 15 s (schedules re-polled at most every SCHED_EVERY s)
Scheduled releases: t0 = official schedule time. Others: t0 = publisher's timestamp (Fed pubDate is minute precision).
"""
import argparse, contextlib, hashlib, json, os, html, re, sys, time, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd, requests

UA = {"User-Agent": "pmflow-research/0.1 (student project; ayaanshankta08@gmail.com)"}
OUT = Path(__file__).parent / "data" / "events.parquet"
COLS = ["event_id", "source", "t0_utc", "first_seen_utc", "title", "url", "kind"]
ET_TZ = ZoneInfo("America/New_York")
SCHED_EVERY, SCHED_DAYS = 600, 14
SOURCES = [  # (source, url, parser, kind)
    ("bls", "https://www.bls.gov/schedule/news_release/bls.ics", "ics", "scheduled"),
    ("bea", "https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics", "ics", "scheduled"),
    ("fed_press_all", "https://www.federalreserve.gov/feeds/press_all.xml", "rss", "release"),
    ("fed_press_monetary", "https://www.federalreserve.gov/feeds/press_monetary.xml", "rss", "release"),
    ("fed_speeches", "https://www.federalreserve.gov/feeds/speeches.xml", "rss", "release"),
    ("sec_8k", "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&output=atom", "atom", "filing"),
    ("cointelegraph", "https://cointelegraph.com/rss", "rss", "article"),
    ("decrypt", "https://decrypt.co/feed", "rss", "article"),
    ("theblock", "https://www.theblock.co/rss.xml", "rss", "article"),
]

def clean(s): return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s or "")).split())
def eid(source, key): return hashlib.sha1(f"{source}|{key}".encode()).hexdigest()[:16]
def utc(dt): return pd.Timestamp(dt).tz_convert("UTC").floor("s")

def parse_ics(text, source, kind, now=None, days=SCHED_DAYS):
    """DTSTART with TZID (or floating) = wall time in ET (BLS/BEA publish ET); trailing Z = already UTC.
    Keeps events in [now-1 day, now+days]."""
    now = pd.Timestamp(now or datetime.now(timezone.utc))
    rows, text = [], re.sub(r"\r?\n[ \t]", "", text)  # unfold
    for blk in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S):
        f = {}
        for line in blk.strip().splitlines():
            k, _, v = line.partition(":")
            f.setdefault(k.split(";")[0], v)
        m = re.match(r"(\d{8}T\d{6})(Z?)", f.get("DTSTART", ""))
        if not m: continue
        dt = datetime.strptime(m[1], "%Y%m%dT%H%M%S")
        t0 = utc(dt.replace(tzinfo=timezone.utc if m[2] else ET_TZ))
        if not now - pd.Timedelta(days=1) <= t0 <= now + pd.Timedelta(days=days): continue
        uid = f.get("UID") or f.get("SUMMARY", "")
        rows.append(dict(event_id=eid(source, uid), source=source, t0_utc=t0, kind=kind,
                         title=clean(f.get("SUMMARY", "").replace("\\,", ",")), url=f.get("URL", "")))
    return rows

def parse_rss(text, source, kind):
    rows = []
    for it in ET.fromstring(text.lstrip("﻿")).iter("item"):
        url, pub = (it.findtext("link") or "").strip(), it.findtext("pubDate")
        if not url or not pub: continue
        key = (it.findtext("guid") or url).strip()
        t0 = utc(pd.Timestamp(parsedate_to_datetime(pub.strip())))
        rows.append(dict(event_id=eid(source, key), source=source, t0_utc=t0, kind=kind,
                         title=clean(it.findtext("title")), url=re.split(r"[?#]", url)[0]))
    return rows

def parse_atom(text, source, kind):
    ns, rows = "{http://www.w3.org/2005/Atom}", []
    for e in ET.fromstring(text).iter(ns + "entry"):
        link, upd = e.find(ns + "link"), e.findtext(ns + "updated")
        if link is None or not upd: continue
        rows.append(dict(event_id=eid(source, e.findtext(ns + "id") or link.get("href")), source=source,
                         t0_utc=utc(pd.Timestamp(upd)), kind=kind, title=clean(e.findtext(ns + "title")), url=link.get("href")))
    return rows

TS_URL, TS_EVERY, TS_BACKFILL_DAYS = "https://ix.cnn.io/data/truth-social/truth_archive.json", 300, 7

def parse_truthsocial(text, since=None, now=None):
    """CNN archive (refreshed ~5 min, ~20 MB, newest first). created_at has ms precision -> floored to second (source 'truthsocial').
    Only posts with t0 > since (default: last TS_BACKFILL_DAYS days, so first run does not backfill 4 years)."""
    since = since if since is not None else pd.Timestamp(now or datetime.now(timezone.utc)) - pd.Timedelta(days=TS_BACKFILL_DAYS)
    rows = []
    for p in json.loads(text):
        t0 = utc(pd.Timestamp(p["created_at"]))
        if t0 <= since: continue
        title = clean(p.get("content")) or ("[media]" if p.get("media") else "[empty]")
        rows.append(dict(event_id=eid("truthsocial", p["id"]), source="truthsocial", t0_utc=t0, kind="post", title=title, url=p["url"]))
    return rows

def poll_truthsocial(out=OUT):
    since = None
    if out.exists():
        d = pd.read_parquet(out, columns=["source", "t0_utc"]); d = d[d.source == "truthsocial"]
        since = d.t0_utc.max() if len(d) else None
    r = requests.get(TS_URL, headers=UA, timeout=60); r.raise_for_status()
    rows = parse_truthsocial(r.text, since)
    return len(rows), merge(rows, out)

PARSERS = {"ics": parse_ics, "rss": parse_rss, "atom": parse_atom}
_last = {}  # host -> last request time (<= 1 req / 2 s / host)
def get(url):
    host = url.split("/")[2]
    time.sleep(max(0, 2 - (time.time() - _last.get(host, 0))))
    _last[host] = time.time()
    r = requests.get(url, headers=UA, timeout=30); r.raise_for_status()
    return r.content.decode(_enc(r.content), "replace")

def _enc(b):  # honour the XML declaration (SEC is ISO-8859-1), else utf-8
    m = re.match(rb'\s*<\?xml[^>]*encoding=["\']([\w-]+)', b)
    return m[1].decode() if m else "utf-8"

def merge(new_rows, out=OUT, now=None):
    """Append rows whose event_id is unseen; existing rows (incl. first_seen_utc) are never changed. Returns n added."""
    df = pd.DataFrame(new_rows, columns=COLS[:2] + ["t0_utc", "first_seen_utc", "title", "url", "kind"])
    if df.empty: return 0
    with _lock(out): return _merge(df, out, now)

@contextlib.contextmanager
def _lock(out):  # lockfile (no fcntl: desktop is Windows); collect.py and bluesky.py both write events.parquet
    lk = out.with_suffix(".lock"); out.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(600):
        try: os.close(os.open(lk, os.O_CREAT | os.O_EXCL)); break
        except FileExistsError:
            if time.time() - lk.stat().st_mtime > 120: lk.unlink(missing_ok=True)  # stale
            time.sleep(0.1)
    try: yield
    finally: lk.unlink(missing_ok=True)

def _merge(df, out, now):
    old = pd.read_parquet(out) if out.exists() else pd.DataFrame(columns=COLS)
    df = df[~df.event_id.isin(old.event_id)].drop_duplicates("event_id")
    if df.empty: return 0
    df["first_seen_utc"] = df.first_seen_utc.fillna(utc(now or datetime.now(timezone.utc)))
    df = df[COLS]
    allr = pd.concat([old, df], ignore_index=True) if len(old) else df
    for c in ("t0_utc", "first_seen_utc"): allr[c] = pd.to_datetime(allr[c], utc=True).astype("datetime64[s, UTC]")
    tmp = out.with_suffix(".tmp"); allr.to_parquet(tmp, index=False); tmp.replace(out)
    return len(df)

def poll(sources=SOURCES, last_sched=None):
    """One pass. Schedule sources are skipped if polled < SCHED_EVERY s ago (tracked in last_sched dict)."""
    last_sched = {} if last_sched is None else last_sched
    counts = {}
    for source, url, kind_p, kind in sources:
        if kind == "scheduled":
            if time.time() - last_sched.get(source, 0) < SCHED_EVERY: continue
        try:
            rows = PARSERS[kind_p](get(url), source, kind)
            if kind == "scheduled": last_sched[source] = time.time()
            counts[source] = (len(rows), merge(rows))
        except Exception as e:
            print(f"{datetime.now(timezone.utc):%F %T} {source} ERROR {e!r:.200}", file=sys.stderr, flush=True)
    if time.time() - last_sched.get("truthsocial", 0) >= TS_EVERY:
        try: counts["truthsocial"] = poll_truthsocial(); last_sched["truthsocial"] = time.time()
        except Exception as e:
            print(f"{datetime.now(timezone.utc):%F %T} truthsocial ERROR {e!r:.200}", file=sys.stderr, flush=True)
    return counts

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--once", action="store_true"); g.add_argument("--loop", type=float, metavar="SECONDS")
    a = ap.parse_args(); ls = {}
    while True:
        t = time.time(); c = poll(last_sched=ls)
        print(f"{datetime.now(timezone.utc):%F %T}Z " + " ".join(f"{s}={n}/+{k}" for s, (n, k) in c.items()), flush=True)
        if a.once: break
        time.sleep(max(0, a.loop - (time.time() - t)))
