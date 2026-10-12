"""24/7 top-of-book recorder, Polymarket YES tokens. WS market channel; REST POST /books fallback.
Rows -> data/tob/polymarket/{market_id}/date=YYYY-MM-DD.parquet {recv_ns, conn_id, bid_px, ask_px, bid_sz, ask_sz}.
Also (2026-10-12, recorder2): data/trades/polymarket/{mkt}/date=*.parquet  last_trade_price events,
  data/depth/polymarket/{mkt}/date=*.parquet  resting size within 1/2/5 c of mid (changes only, rows >= 1 s apart per market),
  data/ticks/polymarket.jsonl  tick_size_change events.  tob schema/semantics unchanged.
Usage: python record_polymarket.py [minutes]   (default: run forever)"""
import asyncio, json, logging, os, sys, time, datetime as dt
import pandas as pd, requests, websockets

WS = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
BOOKS = "https://clob.polymarket.com/books"
OUT, FLUSH_S = "data/tob/polymarket", 60
COLS = ["recv_ns", "conn_id", "bid_px", "ask_px", "bid_sz", "ask_sz"]
TRADES, DEPTH, TICKS = "data/trades/polymarket", "data/depth/polymarket", "data/ticks/polymarket.jsonl"
TCOLS = ["recv_ns", "conn_id", "price", "size", "side", "exch_ts_ms", "fee_rate_bps", "tx_hash"]
BANDS = (0.01, 0.02, 0.05)  # cents from mid
DCOLS = ["recv_ns", "conn_id"] + [f"{s}_{int(b * 100)}c" for b in BANDS for s in ("bid", "ask")] + ["state_ns"]  # state_ns: when the state arrived (<= recv_ns)
DEPTH_MIN_NS = 10**9        # at most one depth row per market per second
NAN = float("nan")

class Recorder:
    def __init__(self, tok2mkt, out=OUT, conn_file="data/conn_id.txt", resolved="data/resolved.jsonl",
                 trades=TRADES, depth=DEPTH, ticks=TICKS):
        self.t2m, self.out, self.conn_file, self.resolved = tok2mkt, out, conn_file, resolved
        self.trades, self.depth, self.ticks = trades, depth, ticks
        self.tbuf, self.dbuf = {}, {}                    # market -> [trade rows] / [depth rows]
        self.dlast, self.dpend, self.dsent = {}, {}, {}  # token -> last written state / pending (ns, state) / ns of last write
        self.n_trades = self.n_depth = 0
        self.books = {t: ({}, {}) for t in tok2mkt}      # token -> (bids{px:sz}, asks{px:sz})
        self.last, self.buf = {}, {}                     # token -> last tob tuple; market -> [rows]
        self.rows_min = 0
        try: self.conn_id = int(open(conn_file).read())
        except Exception: self.conn_id = 0

    def new_conn(self):
        """Call on every (re)connect; books are rebuilt from the fresh snapshot."""
        self.drain(force=True)                           # pending depth rows belong to the old conn_id
        self.conn_id += 1
        os.makedirs(os.path.dirname(self.conn_file) or ".", exist_ok=True)
        open(self.conn_file, "w").write(str(self.conn_id))
        self.books = {t: ({}, {}) for t in self.t2m}; self.last = {}
        self.dlast, self.dpend, self.dsent = {}, {}, {}
        return self.conn_id

    def _depth(self, tok, recv_ns):
        """Resting size within 1/2/5 c of mid per side; queue a row if the six values changed (emitted by drain())."""
        bids, asks = self.books[tok]
        if bids and asks:
            bp, ap = max(map(float, bids)), min(map(float, asks)); mid = (bp + ap) / 2; e = 1e-9
            st = tuple(round(sum(sz for px, sz in side.items() if ok(float(px))), 6)
                       for b in BANDS for side, ok in ((bids, lambda p, b=b: p >= mid - b - e), (asks, lambda p, b=b: p <= mid + b + e)))
        else: st = (NAN,) * 6                            # one-sided/empty book: no mid, no band
        key = lambda t: None if t is None else tuple(None if v != v else v for v in t)
        last = self.dlast.get(tok)
        if key(st) == key(last): self.dpend.pop(tok, None); return          # back to the last written state
        if tok in self.dpend and key(self.dpend[tok][1]) == key(st): return  # already pending (keep its earlier time)
        if last is None and key(st) == key((NAN,) * 6): return              # nothing to say about an empty book yet
        self.dpend[tok] = (recv_ns, st, self.conn_id)

    def drain(self, now_ns=None, force=False):
        """Emit pending depth rows whose market last wrote >= 1 s ago (or all, if force). recv_ns = emit time (so rows are >= 1 s apart); state_ns = when the state arrived."""
        now_ns = now_ns if now_ns is not None else time.time_ns()
        for tok in list(self.dpend):
            ns, st, cid = self.dpend[tok]
            if not force and now_ns - self.dsent.get(tok, -DEPTH_MIN_NS) < DEPTH_MIN_NS: continue
            del self.dpend[tok]; self.dlast[tok] = st; self.dsent[tok] = now_ns
            self.dbuf.setdefault(self.t2m[tok], []).append((now_ns, cid, *st, ns)); self.n_depth += 1

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
            elif et == "last_trade_price" and m.get("asset_id") in self.t2m:
                try:
                    ts = m.get("timestamp")
                    self.tbuf.setdefault(self.t2m[m["asset_id"]], []).append((
                        recv_ns, self.conn_id, float(m["price"]), float(m["size"]), m.get("side") or "",
                        int(ts) if ts not in (None, "") else None, float(m.get("fee_rate_bps") or NAN), m.get("transaction_hash") or ""))
                    self.n_trades += 1
                except Exception as e: logging.warning("bad trade msg %r: %r", m, e)
            elif et == "tick_size_change" and m.get("asset_id") in self.t2m:
                os.makedirs(os.path.dirname(self.ticks) or ".", exist_ok=True)
                with open(self.ticks, "a") as f: f.write(json.dumps({**m, "recv_ns": recv_ns, "conn_id": self.conn_id}) + "\n")
            elif et == "market_resolved" and any(a in self.t2m for a in m.get("assets_ids", [])):
                with open(self.resolved, "a") as f: f.write(json.dumps({**m, "recv_ns": recv_ns}) + "\n")
            for t in touched:
                self._emit(t, recv_ns)
                try: self._depth(t, recv_ns)             # never let the new streams disturb top-of-book
                except Exception as e: logging.warning("depth error %r", e)
        self.drain(recv_ns)

    @staticmethod
    def _write(buf, cols, out, dtypes):
        """Per market/day: merge buffered rows into the day's parquet (atomic rename). Returns rows written."""
        n = 0
        for mkt, rows in buf.items():
            df = pd.DataFrame(rows, columns=cols); n += len(df)
            for day, g in df.groupby(pd.to_datetime(df.recv_ns, unit="ns", utc=True).dt.strftime("%Y-%m-%d")):
                d = f"{out}/{mkt}"; os.makedirs(d, exist_ok=True)
                p = f"{d}/date={day}.parquet"
                if os.path.exists(p): g = pd.concat([pd.read_parquet(p), g], ignore_index=True)
                g.astype(dtypes).to_parquet(p + ".tmp", index=False)
                os.replace(p + ".tmp", p)
        return n

    def flush(self):
        """Write all streams. Returns top-of-book rows written (as before); trades/depth are in self.n_trades/n_depth."""
        buf, self.buf = self.buf, {}
        tb, self.tbuf = self.tbuf, {}
        db, self.dbuf = self.dbuf, {}
        i64 = {"recv_ns": "int64", "conn_id": "int64"}
        try:
            self._write(tb, TCOLS, self.trades, {**i64, "exch_ts_ms": "Int64"})
            self._write(db, DCOLS, self.depth, {**i64, "state_ns": "int64"})
        except Exception as e:  # a failed side stream must not lose the top-of-book rows
            logging.warning("side-stream flush failed %r", e)
        return self._write(buf, COLS, self.out, i64)

async def ws_session(rec, tokens, deadline):
    async with websockets.connect(WS, ping_interval=None, max_size=None) as ws:
        cid = rec.new_conn()
        await ws.send(json.dumps({"assets_ids": tokens, "type": "market", "custom_feature_enabled": True}))
        logging.info("ws connected conn_id=%d tokens=%d", cid, len(tokens)); rec.connected_ok = True  # a session that connected resets the backoff
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
        t0 = time.time(); r, tr, dp = rec.rows_min, rec.n_trades, rec.n_depth; rec.rows_min = rec.n_trades = rec.n_depth = 0
        await asyncio.to_thread(rec.flush)
        logging.info("rows/min=%d conn_id=%d flush_s=%.2f trades=%d depth=%d", r, rec.conn_id, time.time() - t0, tr, dp)

async def ticker(rec, deadline):
    while time.time() < deadline:
        await asyncio.sleep(0.5); rec.drain()           # emit throttled depth rows even when the stream is quiet

async def main(minutes=None):
    u = pd.read_parquet("data/universe_polymarket.parquet")
    tok2mkt = dict(zip(u.token_id_yes, u.market_id)); tokens = list(tok2mkt)
    rec = Recorder(tok2mkt)
    deadline = time.time() + minutes * 60 if minutes else float("inf")
    ft = asyncio.create_task(flusher(rec, deadline)); tt = asyncio.create_task(ticker(rec, deadline))
    fails, backoff = 0, 1
    while time.time() < deadline:
        try:
            await ws_session(rec, tokens, deadline); fails, backoff = 0, 1
        except Exception as e:
            if getattr(rec, "connected_ok", False): fails, backoff, rec.connected_ok = 0, 1, False  # fix 2026-10-11: counters used to accumulate for the process lifetime
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
    ft.cancel(); tt.cancel(); rec.drain(force=True); rec.flush()

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    logging.basicConfig(filename="data/recorder.log", level=logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger().addHandler(logging.StreamHandler())
    asyncio.run(main(float(sys.argv[1]) if len(sys.argv) > 1 else None))
