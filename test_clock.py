import struct
from clock import parse, NTP_EPOCH

def test_parse_known_offset():
    # server clock is 1.5 s ahead of local; 0.2 s each way on the wire, 0.1 s server processing
    t1 = 1_000_000.0; t2 = t1 + 0.2 + 1.5; t3 = t2 + 0.1; t4 = t1 + 0.5
    f = lambda t: (int(t) + NTP_EPOCH, int((t % 1) * 2**32))
    pkt = struct.pack("!12I", 0, 0, 0, 0, 0, 0, 0, 0, *f(t2), *f(t3))
    off, rt = parse(pkt, t1, t4)
    assert abs(off - 1.5) < 1e-6 and abs(rt - 0.4) < 1e-6
