"""24/7 top-of-book recorder, Polymarket YES tokens. WS market channel; REST POST /books fallback.
Rows -> data/tob/polymarket/{market_id}/date=YYYY-MM-DD.parquet {recv_ns, conn_id, bid_px, ask_px, bid_sz, ask_sz}.
Also (2026-10-12, recorder2): data/trades/polymarket/date=*/part-HHMMSS.parquet  last_trade_price events (market_id column; one part file per flush),
  data/depth/polymarket/date=*/part-HHMMSS.parquet  resting size within 1/2/5 c of mid (changes only, rows >= 1 s apart per market),
  data/ticks/polymarket.jsonl  tick_size_change events.  tob schema/semantics unchanged.
Depth is computed in drain() (ticker, 0.1 s), not per message; heartbeat() reports event-loop lateness in the per-minute log line.
Usage: python record_polymarket.py [minutes]   (default: run forever)"""
import asyncio, collections, json, logging, math, os, signal, statistics, sys, threading, time, datetime as dt
import pandas as pd, requests, websockets
from streams import write_part, replace_retry

WS = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
BOOKS = "https://clob.polymarket.com/books"
OUT, FLUSH_S = "data/tob/polymarket", 60
COLS = ["recv_ns", "conn_id", "bid_px", "ask_px", "bid_sz", "ask_sz"]
TRADES, DEPTH, TICKS = "data/trades/polymarket", "data/depth/polymarket", "data/ticks/polymarket.jsonl"
TCOLS = ["recv_ns", "conn_id", "price", "size", "side", "exch_ts_ms", "fee_rate_bps", "tx_hash"]
BANDS = (0.01, 0.02, 0.05)  # cents from mid
DCOLS = ["recv_ns", "conn_id"] + [f"{s}_{int(b * 100)}c" for b in BANDS for s in ("bid", "ask")] + ["state_ns"]  # state_ns: when the state arrived (<= recv_ns)
DEPTH_MIN_NS = 10**9        # at most one depth row per market per second
WS_QUEUE = (4096, 1024)     # websockets max_queue (high, low) in frames; library default is 16. See ws_session.
WS_IDLE_S = 60              # the server answers our PING every 10 s; silence this long = dead connection -> reconnect
STOP_FILE = "data/STOP"     # create this file to make the recorder flush and exit (the only way to stop it cleanly from PowerShell)
LIVE_AGE_S = 180            # no successful flush for this long -> error line every minute
NAN = float("nan")

class Recorder:
    def __init__(self, tok2mkt, out=OUT, conn_file="data/conn_id.txt", resolved="data/resolved.jsonl",
                 trades=TRADES, depth=DEPTH, ticks=TICKS):
        self.t2m, self.out, self.conn_file, self.resolved = tok2mkt, out, conn_file, resolved
        self.trades, self.depth, self.ticks = trades, depth, ticks
        self.tbuf, self.dbuf = {}, {}                    # market -> [trade rows] / [depth rows]
        self.dlast, self.dirty, self.dcalc = {}, {}, {}  # token -> last written state / ns of latest change not yet computed / ns of last computation
        self.late = collections.deque(maxlen=6000)       # event-loop lateness samples (ms) from heartbeat(), emptied once a minute
        self.n_trades = self.n_depth = 0
        self.books = {t: ({}, {}) for t in tok2mkt}      # token -> (bids{px:sz}, asks{px:sz})
        self.last, self.buf = {}, {}                     # token -> last tob tuple; market -> [rows]
        self.rows_min = 0
        self.held = ({}, {}, {})                         # tob / trades / depth rows whose file write failed: market -> [rows]; only touched under wlock
        self.held_n = self.fail_n = 0                    # rows held back / files that failed in the latest flush
        self.wlock = threading.Lock()                    # one write at a time (the flush thread may still run when a final flush starts)
        self.last_ok = time.time()                       # end of the last flush that wrote everything
        try: self.conn_id = int(open(conn_file).read())
        except Exception: self.conn_id = 0

    def new_conn(self):
        """Call on every (re)connect; books are rebuilt from the fresh snapshot."""
        self.drain(force=True)                           # pending depth belongs to the old conn_id and the old (not yet cleared) book
        self.conn_id += 1
        try:
            os.makedirs(os.path.dirname(self.conn_file) or ".", exist_ok=True)
            with open(self.conn_file, "w") as f: f.write(str(self.conn_id))
        except Exception as e: logging.error("conn_id file write failed %r (kept in memory)", e)   # must not stop a reconnect
        self.books = {t: ({}, {}) for t in self.t2m}; self.last = {}
        self.dlast, self.dirty, self.dcalc = {}, {}, {}
        return self.conn_id

    def _depth_state(self, tok):
        """Resting size within 1/2/5 c of mid per side as a 6-tuple (NaNs for a one-sided/empty book). Runs only from drain()."""
        bids, asks = self.books[tok]
        if not (bids and asks): return (NAN,) * 6        # no mid, no band
        bp, ap = max(map(float, bids)), min(map(float, asks)); mid = (bp + ap) / 2; e = 1e-9
        acc = [0.0] * (2 * len(BANDS))                   # one pass per side
        for j, side, sgn in ((0, bids, -1.0), (1, asks, 1.0)):
            for px, sz in side.items():
                d = sgn * (float(px) - mid)              # distance from mid, positive away from it
                for i, b in enumerate(BANDS):
                    if d <= b + e: acc[2 * i + j] += sz
        return tuple(round(v, 6) for v in acc)

    def drain(self, now_ns=None, force=False):
        """Depth for tokens marked changed (self.dirty: token -> time of latest change), at most once per second per token
        (force: all, ignoring the throttle; new_conn uses it). A row is written only if the six values differ from the last
        written row. recv_ns = now (rows >= 1 s apart); state_ns = time of the latest change that led to the row; conn_id = current.
        Called from the ticker every 0.1 s, never per message."""
        now_ns = now_ns if now_ns is not None else time.time_ns()
        key = lambda t: None if t is None else tuple(None if v != v else v for v in t)
        for tok in list(self.dirty):
            if not force and now_ns - self.dcalc.get(tok, -DEPTH_MIN_NS) < DEPTH_MIN_NS: continue
            ns = self.dirty.pop(tok, None)               # pop BEFORE computing: a change arriving meanwhile re-marks the token
            if ns is None: continue
            try:
                st = self._depth_state(tok); self.dcalc[tok] = now_ns
                last = self.dlast.get(tok)
                if key(st) == key(last) or (last is None and key(st) == key((NAN,) * 6)): continue   # unchanged / nothing to say yet
                self.dlast[tok] = st
                self.dbuf.setdefault(self.t2m[tok], []).append((now_ns, self.conn_id, *st, ns)); self.n_depth += 1
            except Exception as e: logging.warning("depth error %r", e)   # never let the new streams disturb top-of-book

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
                self.dirty[t] = recv_ns                  # depth is computed later, in drain(); keep the latest change time

    @staticmethod
    def _write(buf, cols, out, dtypes, kept=None, fails=None):
        """Per market/day: merge buffered rows into the day's parquet (atomic rename). Returns rows written.
        kept (dict) given: a failing market/day file does not raise; its rows go into kept (market -> [rows]) for a later call,
        the stray .tmp is removed, one error line is logged and the file name is appended to fails."""
        n = 0
        for mkt, rows in buf.items():
            if not rows: continue
            try: df = pd.DataFrame(rows, columns=cols); days = pd.to_datetime(df.recv_ns, unit="ns", utc=True).dt.strftime("%Y-%m-%d")
            except Exception as e:
                if kept is None: raise
                fails.append(f"{out}/{mkt}"); logging.error("flush FAILED %s/%s: %r -- %d rows kept for retry", out, mkt, e, len(rows))
                kept.setdefault(mkt, []).extend(rows); continue
            for day, g in df.groupby(days):
                d = f"{out}/{mkt}"; p = f"{d}/date={day}.parquet"
                try:
                    os.makedirs(d, exist_ok=True)
                    new = len(g)
                    if os.path.exists(p): g = pd.concat([pd.read_parquet(p), g], ignore_index=True)
                    g.astype(dtypes).to_parquet(p + ".tmp", index=False)
                    replace_retry(p + ".tmp", p, tries=4 if kept is None or len(fails) < 5 else 1)   # after 5 failed files stop waiting: one try each
                    n += new
                except Exception as e:
                    if kept is None: raise
                    try: os.remove(p + ".tmp")
                    except OSError: pass
                    idx = df.index[days == day]
                    fails.append(p); logging.error("flush FAILED %s: %r -- %d rows kept for retry", p, e, len(idx))
                    kept.setdefault(mkt, []).extend(rows[i] for i in idx)
        return n

    def take(self):
        """Swap the three buffers out. Call from the event loop (not the flush thread) so no append can land in a dict
        that is already being written (such a row would be silently lost)."""
        snap = (self.buf, self.tbuf, self.dbuf); self.buf, self.tbuf, self.dbuf = {}, {}, {}
        return snap

    @staticmethod
    def _join(held, new):
        """held rows (older) + new rows per market, in receive-time order. Builds new containers; never touches `new`'s lists."""
        if not held: return new
        out = dict(new)
        for m, rs in held.items(): out[m] = sorted(rs + new.get(m, []), key=lambda r: r[0])  # stable; row[0] is recv_ns
        return out

    def write(self, snap):
        """Top-of-book first (rewrite-per-day files, unchanged), then each side stream as an append-only part file.
        Never raises. A file that cannot be written keeps its rows in self.held; they are joined (in receive-time order) to the
        next call's rows. Returns tob rows written; trades/depth counts are in self.n_trades/n_depth."""
        with self.wlock:
            self.held = tuple(self._join(h, b) for h, b in zip(self.held, snap))   # set first: whatever happens below, no row is dropped
            buf, tb, db = self.held
            kept, fails, n = ({}, {}, {}), [], 0
            i64 = {"recv_ns": "int64", "conn_id": "int64"}
            try: n = self._write(buf, COLS, self.out, i64, kept[0], fails)
            except Exception as e: logging.error("tob flush error %r", e); kept = ({m: list(r) for m, r in buf.items()}, kept[1], kept[2])
            for k, b, cols, root, dt_ in ((1, tb, TCOLS, self.trades, {**i64, "exch_ts_ms": "Int64"}),
                                          (2, db, DCOLS, self.depth, {**i64, "state_ns": "int64"})):
                try: write_part(b, cols, root, dt_, kept=kept[k], fails=fails)
                except Exception as e:                   # raised before anything was written (frame building): keep it all
                    logging.error("side-stream flush failed (%s): %r -- rows kept for retry", root, e)
                    fails.append(root); kept[k].clear(); kept[k].update({m: list(r) for m, r in b.items()})
            self.held = kept
            self.held_n, self.fail_n = sum(len(r) for h in kept for r in h.values()), len(fails)
            if not fails: self.last_ok = time.time()
            return n

    def flush(self): return self.write(self.take())

async def ws_session(rec, tokens, deadline):
    # max_queue = (high, low) in FRAMES. Default 16 means the client stops reading the socket once 16 messages are waiting for the
    # handler; on connect the server pushes one book per token at once, our send buffer on their side fills -> close 1013 "slow consumer".
    # 4096 > any snapshot (<= ~1 book per token, caps are a few hundred) plus the live changes that arrive during it, and bounds memory
    # (4096 * a few KB per book = tens of MB, never unbounded). Other params that matter (17.2 source): ping_interval=None (no client-side
    # keepalive that a stalled loop could fail), max_size=None (no 1 MiB limit on a big book), write_limit only affects what we send.
    async with websockets.connect(WS, ping_interval=None, max_size=None, max_queue=WS_QUEUE) as ws:
        cid = rec.new_conn()
        await ws.send(json.dumps({"assets_ids": tokens, "type": "market", "custom_feature_enabled": True}))
        logging.info("ws connected conn_id=%d tokens=%d", cid, len(tokens)); rec.connected_ok = True  # a session that connected resets the backoff
        async def pinger():
            while True: await asyncio.sleep(10); await ws.send("PING")
        pt = asyncio.create_task(pinger())
        try:
            while True:
                try: raw = await asyncio.wait_for(ws.recv(), WS_IDLE_S)   # a half-open socket would otherwise block here forever, silently
                except websockets.ConnectionClosedOK: return
                ns = time.time_ns()
                if raw == "PONG": continue
                try: rec.on_msg(json.loads(raw), ns)
                except Exception as e: logging.warning("bad message dropped %r: %.200r", e, raw)   # one odd message must not cost a reconnect
                if time.time() > deadline: return
        except websockets.ConnectionClosed as e:
            logging.warning("ws closed rcvd=%s sent=%s", getattr(e.rcvd, "code", None), getattr(e.sent, "code", None)); raise
        finally: pt.cancel()

def poll_once(rec, tokens):
    """REST fallback: POST /books in batches; same Recorder path via synthetic book messages."""
    for i in range(0, len(tokens), 100):
        r = requests.post(BOOKS, json=[{"token_id": t} for t in tokens[i:i + 100]], timeout=10); r.raise_for_status()
        ns = time.time_ns()
        for b in r.json(): rec.on_msg({**b, "event_type": "book"}, ns)

def late_stats(samples):
    """(median, p99, max, count > 250 ms) of lateness samples in ms; (nan, nan, nan, 0) if none."""
    if not samples: return (NAN, NAN, NAN, 0)
    s = sorted(samples)
    return (statistics.median(s), s[math.ceil(0.99 * len(s)) - 1], s[-1], sum(v > 250 for v in s))

async def heartbeat(rec, deadline, period=0.1, clock=time.perf_counter, sleep=asyncio.sleep):
    """Event-loop lateness against an absolute schedule: beat k is due at t0 + k*period; lateness (ms) = wake - due, unclamped,
    so early and late wake-ups (15.6 ms timer ticks on Windows) cancel and a real stall is a run of large values.
    A beat more than 2 periods late (still over 1 period behind after advancing) resynchronises the schedule instead of firing the missed beats in a burst.
    Costs 10 wakeups/s; any error is swallowed (cancellation is not an Exception, so it still stops the task)."""
    due = None
    while time.time() < deadline:
        try:
            if due is None: due = clock() + period
            await sleep(max(0.0, due - clock()))
            now = clock(); rec.late.append((now - due) * 1000)
            due += period
            if now - due > period: due = now + period
        except Exception as e: due = None; logging.warning("heartbeat error %r", e); await asyncio.sleep(period)

async def flusher(rec, deadline):
    """Once a minute: swap the buffers out, write them in a thread, log. Nothing can end this task except cancellation."""
    while time.time() < deadline:
        await asyncio.sleep(FLUSH_S)
        try:
            t0 = time.time(); r, tr, dp = rec.rows_min, rec.n_trades, rec.n_depth; rec.rows_min = rec.n_trades = rec.n_depth = 0
            snap = rec.take()                            # swapped here, in the loop; only the writing runs in the thread
            await asyncio.to_thread(rec.write, snap)
            try: med, p99, mx, n250 = late_stats(list(rec.late)); rec.late.clear()
            except Exception: med = p99 = mx = NAN; n250 = -1
            logging.info("rows/min=%d conn_id=%d flush_s=%.2f trades=%d depth=%d late_ms_med=%.1f late_ms_max=%.1f late_ms_p99=%.1f late_ms_gt250=%d held=%d failed_files=%d",
                         r, rec.conn_id, time.time() - t0, tr, dp, med, mx, p99, n250, rec.held_n, rec.fail_n)
        except Exception as e: logging.error("flusher iteration error %r (loop continues)", e)

def rows_in_memory(rec):
    return sum(len(v) for b in (rec.buf, rec.tbuf, rec.dbuf) for v in list(b.values())) + rec.held_n

async def watchdog(rec, deadline, main_task, every=5):
    """Independent of flusher(): (1) error line each minute once no flush has fully succeeded for LIVE_AGE_S, with the age and
    the rows held in memory; (2) data/STOP file -> end main() through cancellation, which runs the final flush."""
    next_log = 0
    while time.time() < deadline:
        await asyncio.sleep(every)
        try:
            if os.path.exists(STOP_FILE):
                logging.warning("stop file found -> clean stop"); os.remove(STOP_FILE); main_task.cancel(); return
            age = time.time() - rec.last_ok
            if age >= LIVE_AGE_S and time.time() >= next_log:
                next_log = time.time() + 60
                logging.error("NOT RECORDING: no successful flush for %ds, rows held in memory=%d (held for retry=%d, failed files=%d)",
                              age, rows_in_memory(rec), rec.held_n, rec.fail_n)
        except Exception as e: logging.error("watchdog error %r", e)

async def ticker(rec, deadline):
    while time.time() < deadline:
        await asyncio.sleep(0.1)                        # depth is computed here, per token at most once per second; 0.1 s keeps each tick small
        try: rec.drain()
        except Exception as e: logging.warning("drain error %r", e)

async def main(minutes=None):
    u = pd.read_parquet("data/universe_polymarket.parquet")
    tok2mkt = dict(zip(u.token_id_yes, u.market_id)); tokens = list(tok2mkt)
    rec = Recorder(tok2mkt)
    deadline = time.time() + minutes * 60 if minutes else float("inf")
    try: os.remove(STOP_FILE)                            # a stale stop file must not stop the next run
    except OSError: pass
    tasks = [asyncio.create_task(c) for c in (flusher(rec, deadline), ticker(rec, deadline), heartbeat(rec, deadline),
                                              watchdog(rec, deadline, asyncio.current_task()))]
    try:
        await run_sessions(rec, tokens, deadline)
    finally:                                             # normal end, cancellation (Ctrl-C, stop file) or error: always try the last flush
        for t in tasks: t.cancel()
        try:
            rec.drain(force=True); rec.flush()
            logging.info("final flush done, held=%d failed_files=%d", rec.held_n, rec.fail_n)
            if rec.held_n: logging.error("EXIT WITH %d ROWS NOT WRITTEN (files unwritable)", rec.held_n)
        except BaseException as e: logging.error("final flush error %r", e)

async def run_sessions(rec, tokens, deadline):
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

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    logging.basicConfig(filename="data/recorder.log", level=logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger().addHandler(logging.StreamHandler())
    if hasattr(signal, "SIGBREAK"):                      # Windows only: Ctrl-Break (and a console close, if the CRT maps it) -> same path as Ctrl-C
        signal.signal(signal.SIGBREAK, signal.default_int_handler)
    try: asyncio.run(main(float(sys.argv[1]) if len(sys.argv) > 1 else None))
    except KeyboardInterrupt: logging.info("stopped by KeyboardInterrupt")
