"""24/7 top-of-book recorder, Polymarket YES tokens. WS market channel; REST POST /books fallback.
Rows -> data/tob/polymarket/{market_id}/date=YYYY-MM-DD.parquet {recv_ns, conn_id, bid_px, ask_px, bid_sz, ask_sz}.
Usage: python record_polymarket.py [minutes]   (default: run forever)"""
import asyncio, json, logging, os, sys, time, datetime as dt
import pandas as pd, requests, websockets

WS = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
BOOKS = "https://clob.polymarket.com/books"
OUT, FLUSH_S = "data/tob/polymarket", 60
COLS = ["recv_ns", "conn_id", "bid_px", "ask_px", "bid_sz", "ask_sz"]
NAN = float("nan")

class Recorder:
    def __init__(self, tok2mkt, out=OUT, conn_file="data/conn_id.txt", resolved="data/resolved.jsonl"):
        self.t2m, self.out, self.conn_file, self.resolved = tok2mkt, out, conn_file, resolved
        self.books = {t: ({}, {}) for t in tok2mkt}      # token -> (bids{px:sz}, asks{px:sz})
        self.last, self.buf = {}, {}                     # token -> last tob tuple; market -> [rows]
        self.rows_min = 0
        try: self.conn_id = int(open(conn_file).read())
        except Exception: self.conn_id = 0

    def new_conn(self):
        """Call on every (re)connect; books are rebuilt from the fresh snapshot."""
        self.conn_id += 1
        os.makedirs(os.path.dirname(self.conn_file) or ".", exist_ok=True)
        open(self.conn_file, "w").write(str(self.conn_id))
        self.books = {t: ({}, {}) for t in self.t2m}; self.last = {}
        return self.conn_id

    def _emit(self, tok, recv_ns):
        bids, asks = self.books[tok]
        bp, ap = max(bids, default=None), min(asks, default=None)
        row = (float(bp) if bp is not None else NAN, float(ap) if ap is not None else NAN,
               bids[bp] if bp is not None else NAN, asks[ap] if ap is not None else NAN)
        if self.last.get(tok) == row or (row[0] != row[0] and row[1] != row[1] and tok not in self.last):
            return
        self.last[tok] = row
        self.buf.setdefault(self.t2m[tok], []).append((recv_ns, self.conn_id, *row))
        self.rows_min += 1

    def on_msg(self, msg, recv_ns):
        for m in msg if isinstance(msg, list) else [msg]:
            if not isinstance(m, dict): continue
            et, touched = m.get("event_type"), set()
            if et == "book" and m.get("asset_id") in self.t2m:
                t = m["asset_id"]
                self.books[t] = ({l["price"]: float(l["size"]) for l in m.get("bids", []) if float(l["size"]) > 0},
                                 {l["price"]: float(l["size"]) for l in m.get("asks", []) if float(l["size"]) > 0})
                touched.add(t)
            elif et == "price_change":
                for c in m.get("price_changes", []):
                    t = c.get("asset_id")
                    if t not in self.t2m: continue
                    side = self.books[t][0 if c["side"] == "BUY" else 1]
                    if float(c["size"]) > 0: side[c["price"]] = float(c["size"])
                    else: side.pop(c["price"], None)
                    touched.add(t)
            elif et == "market_resolved" and any(a in self.t2m for a in m.get("assets_ids", [])):
                with open(self.resolved, "a") as f: f.write(json.dumps({**m, "recv_ns": recv_ns}) + "\n")
            for t in touched: self._emit(t, recv_ns)

    def flush(self):
        """Per market/day: merge buffered rows into the day's parquet (atomic rename). Returns rows written."""
        n, buf, self.buf = 0, self.buf, {}
        for mkt, rows in buf.items():
            df = pd.DataFrame(rows, columns=COLS); n += len(df)
            for day, g in df.groupby(pd.to_datetime(df.recv_ns, unit="ns", utc=True).dt.strftime("%Y-%m-%d")):
                d = f"{self.out}/{mkt}"; os.makedirs(d, exist_ok=True)
                p = f"{d}/date={day}.parquet"
                if os.path.exists(p): g = pd.concat([pd.read_parquet(p), g], ignore_index=True)
                g.astype({"recv_ns": "int64", "conn_id": "int64"}).to_parquet(p + ".tmp", index=False)
                os.replace(p + ".tmp", p)
        return n

async def ws_session(rec, tokens, deadline):
    async with websockets.connect(WS, ping_interval=None, max_size=None) as ws:
        cid = rec.new_conn()
        await ws.send(json.dumps({"assets_ids": tokens, "type": "market", "custom_feature_enabled": True}))
        logging.info("ws connected conn_id=%d tokens=%d", cid, len(tokens))
        async def pinger():
            while True: await asyncio.sleep(10); await ws.send("PING")
        pt = asyncio.create_task(pinger())
        try:
            async for raw in ws:
                ns = time.time_ns()
                if raw == "PONG": continue
                rec.on_msg(json.loads(raw), ns)
                if time.time() > deadline: return
        finally: pt.cancel()

def poll_once(rec, tokens):
    """REST fallback: POST /books in batches; same Recorder path via synthetic book messages."""
    for i in range(0, len(tokens), 100):
        r = requests.post(BOOKS, json=[{"token_id": t} for t in tokens[i:i + 100]], timeout=10); r.raise_for_status()
        ns = time.time_ns()
        for b in r.json(): rec.on_msg({**b, "event_type": "book"}, ns)

async def flusher(rec, deadline):
    while time.time() < deadline:
        await asyncio.sleep(FLUSH_S)
        t0 = time.time(); r = rec.rows_min; rec.rows_min = 0
        await asyncio.to_thread(rec.flush)
        logging.info("rows/min=%d conn_id=%d flush_s=%.2f", r, rec.conn_id, time.time() - t0)

async def main(minutes=None):
    u = pd.read_parquet("data/universe_polymarket.parquet")
    tok2mkt = dict(zip(u.token_id_yes, u.market_id)); tokens = list(tok2mkt)
    rec = Recorder(tok2mkt)
    deadline = time.time() + minutes * 60 if minutes else float("inf")
    ft = asyncio.create_task(flusher(rec, deadline))
    fails, backoff = 0, 1
    while time.time() < deadline:
        try:
            await ws_session(rec, tokens, deadline); fails, backoff = 0, 1
        except Exception as e:
            fails += 1; logging.warning("ws error (%s) fail#%d reconnect in %ds", repr(e)[:120], fails, backoff)
            if fails >= 3:  # ponytail: fallback cycles ~1 request/100 tokens; fine at 200 markets
                logging.warning("ws unavailable -> REST polling /books for 60s then retry ws")
                rec.new_conn()
                end = time.time() + 60
                while time.time() < min(end, deadline):
                    t0 = time.time()
                    try: await asyncio.to_thread(poll_once, rec, tokens)
                    except Exception as e2: logging.warning("poll error %r", e2)
                    await asyncio.sleep(max(0, 1 - (time.time() - t0)))
            await asyncio.sleep(backoff); backoff = min(backoff * 2, 60)
    ft.cancel(); rec.flush()

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    logging.basicConfig(filename="data/recorder.log", level=logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger().addHandler(logging.StreamHandler())
    asyncio.run(main(float(sys.argv[1]) if len(sys.argv) > 1 else None))
