"""Historical Alpaca (Benzinga) news -> data/archive/alpaca_news_<start>_<end>.parquet (one file per month; resumable).
  python3 alpaca_history.py [--start 2022-11-01] [--end 2026-04-30]
Columns: event_id, source('alpaca'), t0_utc, first_seen_utc(=t0), title, url, kind, symbols(list), publisher.
Needs APCA_API_KEY_ID / APCA_API_SECRET_KEY. Read-only news endpoint; ~1 req/0.5 s (limit 200/min)."""
import argparse, sys, time
from pathlib import Path
import pandas as pd, requests
import collect as c

ARCH = Path(__file__).parent / "data" / "archive"
PAUSE = 0.5

def fetch_month(a, b, headers, sess=requests, pause=PAUSE):
    """All news with created_at in [a, b) (Timestamps, UTC), paged by page_token (sort asc)."""
    items, tok = [], None
    while True:
        p = dict(limit=50, sort="asc", include_content="false", start=a.strftime("%Y-%m-%dT%H:%M:%SZ"), end=b.strftime("%Y-%m-%dT%H:%M:%SZ"))
        if tok: p["page_token"] = tok
        for att in range(6):
            r = sess.get(c.ALPACA_URL, headers={**c.UA, **headers}, params=p, timeout=30)
            if r.status_code == 429 or r.status_code >= 500: time.sleep(5 * (att + 1)); continue
            r.raise_for_status(); break
        else: r.raise_for_status()
        d = r.json(); items += d.get("news", []); tok = d.get("next_page_token")
        if not tok: return items
        time.sleep(pause)

def to_df(items):
    rows = c.parse_alpaca(items)
    for r, n in zip(rows, items): r.update(first_seen_utc=r["t0_utc"], symbols=list(n.get("symbols") or []), publisher=n.get("source"))
    df = pd.DataFrame(rows, columns=c.COLS + ["symbols", "publisher"]).drop_duplicates("event_id")
    return df.sort_values("t0_utc", kind="stable").reset_index(drop=True)

def months(start, end):
    """[(month_start, next_month_start)] clipped to [start, end+1 day)."""
    s, e, out = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1), []
    m = s.replace(day=1)
    while m < e:
        n = m + pd.offsets.MonthBegin(1); out.append((max(m, s), min(n, e))); m = n
    return out

def run(start, end, arch=ARCH, headers=None, fetch=fetch_month):
    arch.mkdir(parents=True, exist_ok=True); tot = 0
    for a, b in months(start, end):
        f = arch / f"alpaca_news_{a:%Y-%m-%d}_{(b - pd.Timedelta(days=1)):%Y-%m-%d}.parquet"
        if f.exists(): print(f"{a:%Y-%m} exists, skip", flush=True); continue
        df = to_df(fetch(a, b, headers))
        df = df[(df.t0_utc >= a) & (df.t0_utc < b)]  # API start/end filter on updated_at: drop items created before the month
        tmp = f.with_suffix(".tmp"); df.to_parquet(tmp, index=False); tmp.replace(f)
        tot += len(df); print(f"{a:%Y-%m} rows={len(df)} -> {f.name}", flush=True)
    return tot

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--start", default="2022-11-01"); ap.add_argument("--end", default="2026-04-30")
    a = ap.parse_args(); h = c.alpaca_headers()
    if not h: sys.exit("APCA_API_KEY_ID / APCA_API_SECRET_KEY not set")
    print("total rows", run(a.start, a.end, headers=h))
