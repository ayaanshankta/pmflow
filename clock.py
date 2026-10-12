"""Log this machine's clock error against NTP, without changing the clock (no admin needed).
offset_s = true time - local time, so corrected recv_ns = recv_ns + offset_s * 1e9. Appends to data/clock_offset.jsonl.
Run: python clock.py --once   |   python clock.py --loop 60"""
import json, os, socket, struct, sys, time

NTP_EPOCH = 2208988800  # seconds between 1900 and 1970
SERVERS = ("time.cloudflare.com", "pool.ntp.org", "time.windows.com")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "clock_offset.jsonl")


def parse(data, t1, t4):
    """SNTP reply + local send/receive times -> (offset_s, round_trip_s). Standard formulas."""
    u = struct.unpack("!12I", data[:48])
    t2, t3 = u[8] - NTP_EPOCH + u[9] / 2**32, u[10] - NTP_EPOCH + u[11] / 2**32
    return ((t2 - t1) + (t3 - t4)) / 2, (t4 - t1) - (t3 - t2)


def query(server, timeout=3.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(timeout)
    try:
        t1 = time.time(); s.sendto(b"\x1b" + 47 * b"\0", (server, 123)); data, _ = s.recvfrom(48); t4 = time.time()
    finally: s.close()
    return parse(data, t1, t4)


def once():
    rows = []
    for srv in SERVERS:
        try: off, rt = query(srv); rows.append({"utc": time.time(), "server": srv, "offset_s": round(off, 4), "round_trip_s": round(rt, 4)})
        except Exception as e: rows.append({"utc": time.time(), "server": srv, "error": type(e).__name__})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "a") as f:
        for r in rows: f.write(json.dumps(r) + "\n")
    return rows


if __name__ == "__main__":
    if "--loop" in sys.argv:
        n = float(sys.argv[sys.argv.index("--loop") + 1])
        while True: once(); time.sleep(n)
    else:
        for r in once(): print(r)
