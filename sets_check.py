"""C1 (research/structure-rules.md, blob 1582327e1f20): are complete sets ever mispriced on live top-of-book quotes?

  python sets_check.py --tob data/tob/polymarket --raw data/sets_gamma_events_raw.json --out data/sets_out [--fetch]

Reads data/tob/{market}/date=*.parquet (recv_ns, conn_id, bid_px, ask_px, bid_sz, ask_sz; YES token), the family map from
families.py, writes episodes.json + tables.md into --out. Pure function core: analyse_family(fam, frames, timeline).

Method
 - A quote is the last row of a market at or before time t. It is UNKNOWN unless its conn_id equals the current connection
   (the latest conn_id that started anywhere in the folder): after a reconnect each market's book is re-sent, so a market
   not yet re-sent is not known. It is also unknown if the book is crossed or that side is empty.
 - Time is cut into segments at every quote update, every update+60 s (stale transition), every connection start, and
   every recording gap (no row from any market for > GAP_S): nothing is carried across a gap.
 - A candidate violation is evaluated in each segment (zero cost and after fee c = sum rate*p*(1-p) over legs, p = leg price).
     exclusive complete: A = sum asks < 1-c (buy all, needs every ask live), B = sum of live bids > 1+c (a leg with no bid
       contributes 0 and is not sold; selling a subset of exclusive YES owes at most $1).
     exclusive partial (SUPPLEMENTARY, not in the bar): B only, same subset form.
     ladder: bid(stronger) - ask(weaker) > c for every recorded pair (weaker = superset claim).
 - Segment is "fresh" if no leg of the candidate is older than 60 s, else "stale"; stale episodes are reported separately
   and never count. Episodes = consecutive segments of the same class.
 - Size = min displayed size over the legs at the best quote (shares); dollars = shares * set price (A, B or ask of the weaker).
"""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

S = 1_000_000_000
STALE_NS = 60 * S
GAP_S = 60
BAR = dict(min_episodes=20, min_dur_s=2.0, min_dollars=100.0, min_families=3)


# ---------------------------------------------------------------- data
def load_frames(tob_root):
    """{market_id: DataFrame sorted by recv_ns} over every date file."""
    out = {}
    for d in sorted(Path(tob_root).iterdir()):
        fs = sorted(d.glob("date=*.parquet"))
        if d.is_dir() and fs:
            out[d.name] = pd.concat([pd.read_parquet(f) for f in fs]).sort_values("recv_ns", kind="stable", ignore_index=True)
    return out


def make_timeline(frames, gap_s=GAP_S):
    """Recording windows (no row from any market for > gap_s ends a window) and the connection start times."""
    ns = np.sort(np.concatenate([f.recv_ns.to_numpy() for f in frames.values()]))
    cut = np.flatnonzero(np.diff(ns) > gap_s * S)
    starts = np.r_[ns[0], ns[cut + 1]]
    ends = np.r_[ns[cut], ns[-1]]
    cs = {}
    for f in frames.values():
        for c, t in f.groupby("conn_id").recv_ns.min().items():
            cs[c] = min(cs.get(c, t), t)
    order = sorted(cs.items(), key=lambda kv: kv[1])
    return dict(win_start=starts, win_end=ends, conn_t=np.array([t for _, t in order], dtype=np.int64),
                conn_id=np.array([c for c, _ in order], dtype=np.int64))


# ---------------------------------------------------------------- core
def _state(f, T, cur_conn):
    ns = f.recv_ns.to_numpy()
    i = np.searchsorted(ns, T, side="right") - 1
    ok = i >= 0
    ic = np.clip(i, 0, None)
    bid, ask = f.bid_px.to_numpy(float)[ic], f.ask_px.to_numpy(float)[ic]
    bsz, asz = f.bid_sz.to_numpy(float)[ic], f.ask_sz.to_numpy(float)[ic]
    live = ok & (f.conn_id.to_numpy()[ic] == cur_conn) & ~(bid > ask)  # crossed book = mid-update artefact
    return dict(bid=bid, ask=ask, bsz=bsz, asz=asz, stale=(T - ns[ic]) > STALE_NS,
                kb=live & ~np.isnan(bid) & (bsz > 0), ka=live & ~np.isnan(ask) & (asz > 0))


def segments(frames_m, tl):
    T = np.unique(np.concatenate([*(f.recv_ns.to_numpy() for f in frames_m), *(f.recv_ns.to_numpy() + STALE_NS + 1 for f in frames_m),
                                  tl["conn_t"], tl["win_start"], tl["win_end"]]))
    w = np.searchsorted(tl["win_start"], T, side="right") - 1
    keep = (w >= 0) & (T < tl["win_end"][np.clip(w, 0, None)])
    T, w = T[keep], w[keep]
    if not len(T):
        return T, T
    end = np.minimum(np.r_[T[1:], T[-1] + 1], tl["win_end"][w])
    end = np.where(np.r_[w[1:] != w[:-1], True], tl["win_end"][w], end)
    m = end > T
    return T[m], end[m]


def analyse_family(fam, frames, tl, fee_variant=True):
    """-> dict(evaluable_s, episodes=[...]) for one family from families.build(). Episodes carry variant 'c0'/'fee' and class 'fresh'/'stale'."""
    mem = [m for m in fam["members"] if m["recorded"] and m["market_id"] in frames]
    if len(mem) < 2:
        return dict(evaluable_s=0.0, episodes=[], observed_s=0.0)
    fr = [frames[m["market_id"]] for m in mem]
    T, E = segments(fr, tl)
    if not len(T):
        return dict(evaluable_s=0.0, episodes=[], observed_s=0.0)
    cur = tl["conn_id"][np.clip(np.searchsorted(tl["conn_t"], T, side="right") - 1, 0, None)]
    st = [_state(f, T, cur) for f in fr]
    rate = np.array([m["fee_rate"] for m in mem])
    fee = lambda p, j: rate[j] * p * (1 - p)
    cands = []  # each: name, legs [(member idx, 'a'|'b')], ok, gross, fee, shares, notional
    n = len(mem)
    if fam["kind"] == "exclusive":
        if fam["complete"] and len(mem) == fam["n_members"]:
            ka = np.all([s["ka"] for s in st], axis=0)
            A = np.sum([s["ask"] for s in st], axis=0)
            cands.append(dict(name="A: buy all YES", legs=[(j, "a") for j in range(n)], ok=ka, gross=1 - A,
                              fee=np.sum([fee(s["ask"], j) for j, s in enumerate(st)], axis=0),
                              shares=np.min([s["asz"] for s in st], axis=0), notional=A))
        # B side, complete or partial: sell YES on every recorded leg that has a live bid. A leg with no bid contributes 0 and is
        # not sold; selling any subset of mutually exclusive YES still owes at most $1, so B > 1 + c is riskless.
        kb = np.array([s["kb"] for s in st])
        B = np.sum(np.where(kb, [s["bid"] for s in st], 0.0), axis=0)
        cands.append(dict(name="B: sell YES on legs with a bid", legs=[(j, "b") for j in range(n)], ok=kb.sum(0) >= 2, gross=B - 1,
                          fee=np.sum(np.where(kb, [fee(s["bid"], j) for j, s in enumerate(st)], 0.0), axis=0),
                          shares=np.min(np.where(kb, [s["bsz"] for s in st], np.inf), axis=0), notional=B, subset=kb))
    else:
        rk = [m["rank"] for m in mem]
        for w in range(n):
            for s_ in range(n):
                if w == s_ or rk[w] > rk[s_]:
                    continue  # weaker claim = lower rank; equal ranks are tested both ways
                a, b = st[w], st[s_]
                cands.append(dict(name=f"L: buy {mem[w]['title'] or w} / sell {mem[s_]['title'] or s_}", legs=[(w, "a"), (s_, "b")],
                                  ok=a["ka"] & b["kb"], gross=b["bid"] - a["ask"], fee=fee(a["ask"], w) + fee(b["bid"], s_),
                                  shares=np.minimum(a["asz"], b["bsz"]), notional=a["ask"]))
    if not cands:
        return dict(evaluable_s=0.0, episodes=[], observed_s=0.0)
    ok = np.array([c["ok"] for c in cands])
    # staleness per candidate: any (known) leg older than 60 s
    stale = np.array([np.any([st[j]["stale"] & (c["subset"][j] if c.get("subset") is not None else True) for j, _ in c["legs"]], axis=0)
                      for c in cands])
    dur = (E - T) / S
    res = dict(evaluable_s=float(dur[ok.any(0)].sum()), observed_s=float(dur.sum()), episodes=[])
    for variant in ("c0", "fee"):
        net = np.array([np.where(c["ok"], c["gross"] - (c["fee"] if variant == "fee" else 0.0), -np.inf) for c in cands])
        viol = net > 1e-9
        vf, vs = viol & ~stale, viol & stale
        nf, ns_ = np.where(vf, net, -np.inf), np.where(vs, net, -np.inf)
        isf, iss = vf.any(0), vs.any(0)
        cls = np.where(isf, 1, np.where(iss, 2, 0))
        pick = np.where(isf, nf.argmax(0), ns_.argmax(0))
        contig = np.r_[False, T[1:] == E[:-1]]
        i = 0
        while i < len(T):
            if cls[i] == 0:
                i += 1
                continue
            j = i
            while j + 1 < len(T) and cls[j + 1] == cls[i] and contig[j + 1]:
                j += 1
            seg = np.arange(i, j + 1)
            k = seg[np.argmax(net[pick[seg], seg])]  # peak-gap segment
            c = cands[pick[k]]
            legs = [dict(market=mem[l]["market_id"], title=mem[l]["title"], side="ask" if sd == "a" else "bid",
                         px=float(st[l]["ask" if sd == "a" else "bid"][k]), sz=float(st[l]["asz" if sd == "a" else "bsz"][k]),
                         age_s=float((T[k] - fr[l].recv_ns.to_numpy()[np.searchsorted(fr[l].recv_ns.to_numpy(), T[k], side="right") - 1]) / S))
                    for l, sd in c["legs"] if not (c.get("subset") is not None and not c["subset"][l][k])]
            sh = np.array([cands[pick[x]]["shares"][x] for x in seg])
            nt = np.array([cands[pick[x]]["notional"][x] for x in seg])
            res["episodes"].append(dict(
                variant=variant, cls="fresh" if cls[i] == 1 else "stale", start_ns=int(T[i]), end_ns=int(E[j]), dur_s=float((E[j] - T[i]) / S),
                cand=c["name"], gross_pts=float(c["gross"][k] * 100), net_pts=float(net[pick[k], k] * 100),
                shares=float(c["shares"][k]), dollars=float(c["shares"][k] * c["notional"][k]),
                max_shares=float(sh.max()), max_dollars=float((sh * nt).max()),
                profit_usd=float(c["shares"][k] * net[pick[k], k]), legs=legs))
            i = j + 1
    return res


# ---------------------------------------------------------------- report
def _q(x, p):
    return float(np.percentile(x, p)) if len(x) else float("nan")


def summarise(fam, res):
    row = dict(kind=fam["kind"], scope="bar" if fam["complete"] else "supplementary", event=fam["event_id"], title=(fam["title"] or "")[:44],
               legs=f'{fam["n_recorded"]}/{fam["n_members"]}', evaluable_h=res["evaluable_s"] / 3600)
    ev = res["episodes"]
    for v in ("c0", "fee"):
        for cl in ("fresh", "stale"):
            e = [x for x in ev if x["variant"] == v and x["cls"] == cl]
            d = np.array([x["dur_s"] for x in e])
            p = f"{v}_{cl}_"
            row[p + "share"] = d.sum() / res["evaluable_s"] if res["evaluable_s"] else float("nan")
            row[p + "n"], row[p + "n2s"] = len(e), int((d >= BAR["min_dur_s"]).sum())
            row[p + "med_s"], row[p + "p90_s"] = _q(d, 50), _q(d, 90)
            row[p + "gap_med"], row[p + "gap_max"] = _q([x["net_pts"] for x in e], 50), max([x["net_pts"] for x in e], default=float("nan"))
            row[p + "sh_med"], row[p + "sh_max"] = _q([x["shares"] for x in e], 50), max([x["shares"] for x in e], default=float("nan"))
            row[p + "usd_med"], row[p + "usd_max"] = _q([x["dollars"] for x in e], 50), max([x["dollars"] for x in e], default=float("nan"))
    return row


def bar(rows, episodes_by_fam, complete_only=True):
    """Fee-clearing, fresh, >= 2 s, >= $100 (max dollars during the episode, the generous reading) episodes."""
    tot, fams = 0, 0
    for r in rows:
        if complete_only and r["scope"] != "bar":
            continue
        n = sum(1 for x in episodes_by_fam[r["key"]] if x["variant"] == "fee" and x["cls"] == "fresh"
                and x["dur_s"] >= BAR["min_dur_s"] and x["max_dollars"] >= BAR["min_dollars"])
        tot += n
        fams += n > 0
    return tot, fams


def run(tob, raw, out):
    import families
    frames = load_frames(tob)
    tl = make_timeline(frames)
    fam_map = families.build(json.loads(Path(raw).read_text()))
    rows, eps = [], {}
    for fam in fam_map["families"]:
        if fam["n_recorded"] < 2:
            continue
        res = analyse_family(fam, frames, tl)
        r = summarise(fam, res)
        r["key"] = fam["key"]
        rows.append(r)
        eps[fam["key"]] = res["episodes"]
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / "episodes.json").write_text(json.dumps(dict(families=rows, episodes=eps, windows=[
        [int(a), int(b)] for a, b in zip(tl["win_start"], tl["win_end"])]), indent=1))
    return fam_map, rows, eps, tl


def report_md(fam_map, rows, eps, tl):
    """Markdown tables for research/sets-result.md (all numbers come from episodes)."""
    f = lambda x, nd=2: "-" if x != x else f"{x:.{nd}f}"
    L = []
    cnt = {}
    for fam in fam_map["families"]:
        k = (fam["kind"], "complete" if fam["complete"] else "partial", "testable" if fam["n_recorded"] >= 2 else "single recorded leg")
        cnt[k] = cnt.get(k, 0) + 1
    L += ["| kind | completeness | recorded legs | families |", "|---|---|---|---|"] + [f"| {k[0]} | {k[1]} | {k[2]} | {v} |" for k, v in sorted(cnt.items())]
    win = ", ".join(f"{pd.Timestamp(a_):%m-%d %H:%M:%S}-{pd.Timestamp(b):%H:%M:%S}" for a_, b in zip(tl["win_start"], tl["win_end"]))
    L += ["", f"Recording windows (UTC, cut where no market updated for > {GAP_S} s): {win}.", ""]
    for v, name in (("fee", "after fee"), ("c0", "zero cost")):
        L += [f"### Per family, {name} (fresh quotes; episodes / of which >= 2 s; duration median / p90 s; net gap points median / max; shares median / max; $ at peak median / max; time share; stale-quote episodes)", "",
              "| scope | kind | event | title | legs | hours | episodes | >=2 s | dur med | dur p90 | gap med | gap max | shares med | shares max | $ med | $ max | share of time | stale eps |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in sorted(rows, key=lambda r: (r["scope"] != "bar", -r[f"{v}_fresh_n"], r["event"])):
            p = f"{v}_fresh_"
            L.append(f"| {r['scope']} | {r['kind']} | {r['event']} | {r['title']} | {r['legs']} | {f(r['evaluable_h'], 1)} | {r[p+'n']} | {r[p+'n2s']} | "
                     f"{f(r[p+'med_s'], 1)} | {f(r[p+'p90_s'], 1)} | {f(r[p+'gap_med'])} | {f(r[p+'gap_max'])} | {f(r[p+'sh_med'], 0)} | {f(r[p+'sh_max'], 0)} | "
                     f"{f(r[p+'usd_med'])} | {f(r[p+'usd_max'])} | {r[p+'share']:.2%} | {r[f'{v}_stale_n']} |")
        L.append("")
    for co in (True, False):
        t, nf = bar(rows, eps, co)
        L.append(f"- Bar ({'complete families only' if co else 'every testable family incl. partial and ladders'}): {t} fee-clearing fresh episodes >= {BAR['min_dur_s']:.0f} s "
                 f"with >= ${BAR['min_dollars']:.0f} in {nf} families (need {BAR['min_episodes']} in {BAR['min_families']}).")
    tot = {}
    for v in ("c0", "fee"):
        for cl in ("fresh", "stale"):
            e = [x for es in eps.values() for x in es if x["variant"] == v and x["cls"] == cl]
            tot[(v, cl)] = (len(e), sum(x["dur_s"] >= 2 for x in e), sum(x["dur_s"] >= 2 and x["max_dollars"] >= 100 for x in e))
    L += ["", "| variant | class | episodes | >= 2 s | >= 2 s and >= $100 |", "|---|---|---|---|---|"] + [f"| {k[0]} | {k[1]} | {v[0]} | {v[1]} | {v[2]} |" for k, v in tot.items()]
    for v in ("fee", "c0"):
        top = sorted([(k, x) for k, es in eps.items() for x in es if x["variant"] == v and x["cls"] == "fresh"], key=lambda kx: -kx[1]["profit_usd"])[:3]
        L += ["", f"### Three largest fresh episodes, {v} (by profit at peak = shares x net gap)", ""]
        for k, x in top:
            L.append(f"- family {k[:40]} start {pd.Timestamp(x['start_ns']):%H:%M:%S.%f}Z dur {x['dur_s']:.3f} s, {x['cand']}, gross {x['gross_pts']:.2f} / net {x['net_pts']:.2f} pts, "
                     f"{x['shares']:.0f} shares, ${x['dollars']:.2f}, profit ${x['profit_usd']:.2f}; legs: " +
                     "; ".join(f"{l['title']} {l['side']} {l['px']:.3f}x{l['sz']:.0f} (age {l['age_s']:.2f}s)" for l in x["legs"]))
    return "\n".join(L)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tob", default="data/tob/polymarket")
    ap.add_argument("--raw", default="data/sets_gamma_events_raw.json")
    ap.add_argument("--out", default="data/sets_out")
    ap.add_argument("--fetch", action="store_true", help="re-fetch Gamma events for the markets under --tob into --raw first")
    a = ap.parse_args()
    if a.fetch:
        import families
        Path(a.raw).write_text(json.dumps(families.fetch(families.recorded_markets(a.tob))))
    fam_map, rows, eps, tl = run(a.tob, a.raw, a.out)
    (Path(a.out) / "tables.md").write_text(report_md(fam_map, rows, eps, tl))
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 250, "display.max_columns", 50, "display.max_rows", 200)
    print("windows (UTC):", [(pd.Timestamp(a_).strftime("%m-%d %H:%M:%S"), pd.Timestamp(b).strftime("%H:%M:%S")) for a_, b in zip(tl["win_start"], tl["win_end"])])
    cols = ["scope", "kind", "event", "title", "legs", "evaluable_h"]
    for v in ("c0", "fee"):
        print(f"\n== {v} ==")
        c = [f"{v}_fresh_{k}" for k in ("share", "n", "n2s", "med_s", "p90_s", "gap_max", "sh_max", "usd_max")] + [f"{v}_stale_n", f"{v}_stale_share"]
        print(df[cols + c].to_string(index=False, float_format=lambda x: f"{x:.4g}"))
    for co in (True, False):
        t, f = bar(rows, eps, co)
        print(f"\nBAR ({'complete families only' if co else 'all testable incl. partial'}): fee-clearing fresh episodes >=2s & >=$100: {t} in {f} families (need {BAR['min_episodes']} in {BAR['min_families']})")
