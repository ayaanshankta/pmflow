"""C2 lead-lag test on the Polymarket-v1 trade archive. Rules: research/structure-rules.md section C2 (blob 1582327e1f20...).
Run: /opt/anaconda3/bin/python3 leadlag.py dev|test      (test refuses to run with uncommitted changes to leadlag*.py)
Inputs: research/leadlag-family-map.csv.gz (leadlag_map.py), data/leadlag/fills_2025_MM.parquet (leadlag_fetch.py).

Implementation choices where C2 is silent (all fixed BEFORE any development number was looked at):
 * "last-trade price changes by >= 3 points within 60 s": trade i is a jump candidate if |p_i - p(last trade at or before t_i - 60 s)| >= 0.03,
   on the p_event axis. A candidate is a JUMP (first of an episode) if the same market had no candidate in the previous 1800 s (rolling,
   so ignored second jumps keep the quiet period running). t0 = ts of trade i.
 * Leader at t0 = member with the most fills in [t0-24h, t0); ties -> smaller condition id. Only the leader's jumps count.
 * Sibling = another member with >= 20 fills in [t0-24h, t0). Needs a last trade before t0 (strictly < t0) as the 'pre' price.
 * Moves: sibling last-trade price at t0+h (last trade <= t0+h; no trade -> unchanged) minus pre, in points, x implied direction.
 * Paper trade: entry = first sibling trade with ts >= t0+delta AND ts < t0+720 (must precede the exit window); exit = last trade with
   ts in [t0+720, t0+1080]. Buy YES if direction +1 else buy NO. Points per share = 100*d*(p_out-p_in); fee = 0.04*p*(1-p) per side per share.
   Missing entry or exit -> pair dropped for that delta (counted).
 * Available volume = USDC traded on that sibling with ts in (entry_ts, entry_ts+10 s] and |p - p_in| <= 0.02 (entry fill excluded; the
   variant including it is reported as avail_incl). Primary = excluded (literal "following 10 s").
 * Catch-up share = signed(first sibling trade at >= t0 minus pre) / signed(15-min move); pooled as ratio of sums over pairs with a trade in
   [t0, t0+900], plus per-pair median over pairs with |15-min move| >= 2 points.
 * Placebo: per (jump, sibling) 20 uniform-random seconds on the same UTC day as t0, >= 7200 s from every leader jump of that family,
   sibling with >= 20 fills in prior 24 h and a pre price; same direction as the real pair; same measure(). RandomState(0), families sorted.
 * Bar (test): Delta = 30 s, venue fee, mean > 0 and cluster-bootstrap 95 % lower bound > 0 on >= 100 jumps (clusters with >= 1 trade) AND
   median available volume >= $200. Evaluated for the pooled set (primary) and for each family kind (reported)."""
import json, subprocess, sys
import numpy as np, pandas as pd
from replay_truth import boot, B, SEED

DELTAS, RATE, JUMP, QUIET, LIQ, EXIT_LO, EXIT_HI, HORIZ = (5, 30, 120), 0.04, 0.03, 1800, 20, 720, 1080, (60, 300, 900)
PERIODS = {"dev": ("2025-01-01", "2025-07-01"), "test": ("2025-07-01", "2026-01-01")}
NPLACEBO, PLACEBO_GAP, TRIES = 20, 7200, 400

def jumps_of(ts, p):
    """indices of first-of-episode jump trades in one market (arrays sorted by ts)."""
    ref = np.searchsorted(ts, ts - 60, "right") - 1
    ok = ref >= 0
    cond = np.zeros(len(ts), bool)
    cond[ok] = np.abs(p[ok] - p[ref[ok]]) >= JUMP - 1e-6
    ci = np.flatnonzero(cond)
    if not len(ci): return ci, ref
    gap = np.diff(ts[ci], prepend=-10**12)
    return ci[gap > QUIET], ref

def measure(m, t0, d):
    """m = (ts, p, usd) of the sibling, d = implied direction (+1/-1). -> dict or None if no pre price."""
    ts, p, usd = m
    i0 = int(np.searchsorted(ts, t0, "left"))
    if i0 == 0: return None
    pre = float(p[i0 - 1]); r = dict(pre=pre)
    for h in HORIZ:
        j = int(np.searchsorted(ts, t0 + h, "right")) - 1
        r[f"m{h}"] = 100 * d * (float(p[j]) - pre) if j >= i0 else 0.0
    r["first"] = 100 * d * (float(p[i0]) - pre) if i0 < len(ts) and ts[i0] <= t0 + HORIZ[-1] else np.nan
    lo, hi = int(np.searchsorted(ts, t0 + EXIT_LO, "left")), int(np.searchsorted(ts, t0 + EXIT_HI, "right"))
    for dl in DELTAS:
        i = int(np.searchsorted(ts, t0 + dl, "left"))
        if i >= len(ts) or ts[i] >= t0 + EXIT_LO or hi <= lo:
            r[f"ok{dl}"] = False; continue
        pi, po = float(p[i]), float(p[hi - 1])
        g = 100 * d * (po - pi)
        k = int(np.searchsorted(ts, ts[i] + 10, "right"))
        near = np.abs(p[i:k] - pi) <= 0.02 + 1e-6
        v = usd[i:k] * near
        r.update({f"ok{dl}": True, f"p_in{dl}": pi, f"p_out{dl}": po, f"pts0_{dl}": g,
                  f"ptsF_{dl}": g - 100 * RATE * (pi * (1 - pi) + po * (1 - po)),
                  f"avail{dl}": float(v[1:].sum()), f"avail_incl{dl}": float(v.sum())})
    return r

def n24(ts, t0): return int(np.searchsorted(ts, t0, "left") - np.searchsorted(ts, t0 - 86400, "left"))

def analyse_family(fam, kind, members, t_lo, t_hi, rng):
    """members: cid -> (ts, p, usd). Returns (pairs list, placebo list); t_lo/t_hi epoch bounds for t0."""
    cids = sorted(members)
    allj = {}
    for c in cids:
        ts, p, _ = members[c]
        ji, _ = jumps_of(ts, p)
        allj[c] = ji
    leader_jumps = []   # (t0, leader cid, idx)
    for c in cids:
        ts = members[c][0]
        for i in allj[c]:
            t0 = int(ts[i]); cnt = {x: n24(members[x][0], t0) for x in cids}
            if max(cnt, key=lambda x: (cnt[x], -cids.index(x))) == c: leader_jumps.append((t0, c, int(i)))
    ljt = np.array(sorted(t for t, _, _ in leader_jumps))
    pairs, plac = [], []
    for t0, c, i in leader_jumps:
        if not (t_lo <= t0 < t_hi): continue
        ts, p, _ = members[c]
        ref = int(np.searchsorted(ts, t0 - 60, "right")) - 1
        sL = int(np.sign(p[i] - p[ref]))
        j0 = int(np.searchsorted(ts, t0 - 60, "left"))
        burst = bool((np.abs(p[j0:i] - p[i]) >= JUMP - 1e-6).any())   # variant: a trade INSIDE the 60 s window already differs by >= 3 pts
        d = -sL if kind == "exclusive" else sL
        for s in cids:
            if s == c or n24(members[s][0], t0) < LIQ: continue
            m = measure(members[s], t0, d)
            if m is None: continue
            pid = f"{fam}@{t0}:{s}"
            pairs.append(dict(pid=pid, family=fam, kind=kind, t0=t0, leader=c, sib=s, d=d, p_ref=float(p[ref]), p_jump=float(p[i]), burst=burst,
                              n24_leader=n24(ts, t0), n24_sib=n24(members[s][0], t0), **m))
            day0 = t0 - t0 % 86400; got = 0
            for _ in range(TRIES):
                if got >= NPLACEBO: break
                tp = int(day0 + rng.randint(0, 86400 - EXIT_HI))
                if len(ljt) and np.abs(ljt - tp).min() < PLACEBO_GAP: continue
                if n24(members[s][0], tp) < LIQ: continue
                mp = measure(members[s], tp, d)
                if mp is None: continue
                plac.append(dict(pid=pid, family=fam, kind=kind, t0=tp, sib=s, d=d, **mp)); got += 1
    return pairs, plac

def stat(tr, col, extra=None):
    """tr: rows with pid/jump cluster; mean and cluster bootstrap CI of col. cluster = leader jump (family@t0)."""
    if not len(tr): return dict(n=0, jumps=0, mean=np.nan, lo=np.nan, hi=np.nan)
    g = tr.assign(_v=tr[col]).groupby("jump")["_v"].agg(["sum", "count"])
    lo, hi = boot(g["sum"].values, g["count"].values, np.random.RandomState(SEED))
    return dict(n=len(tr), jumps=len(g), mean=float(tr[col].mean()), lo=lo, hi=hi)

def diff_ci(a, b, col):
    """paired-by-jump cluster bootstrap of mean(real) - mean(placebo)."""
    ja = a.groupby("jump")[col].agg(["sum", "count"]); jb = b.groupby("jump")[col].agg(["sum", "count"])
    j = ja.index.intersection(jb.index)
    if not len(j): return np.nan, np.nan, np.nan
    sa, na, sb, nb = ja.loc[j, "sum"].values, ja.loc[j, "count"].values, jb.loc[j, "sum"].values, jb.loc[j, "count"].values
    idx = np.random.RandomState(SEED).randint(0, len(j), (B, len(j)))
    m = sa[idx].sum(1) / na[idx].sum(1) - sb[idx].sum(1) / nb[idx].sum(1)
    return float(sa.sum() / na.sum() - sb.sum() / nb.sum()), *np.percentile(m, [2.5, 97.5])

def tables(P, Q):
    """P pairs, Q placebo (both with 'jump' column). Returns dict of DataFrames."""
    kinds = [("all", None), ("exclusive", "exclusive"), ("ladder", "ladder"), ("burst_all", "burst"), ("burst_exclusive", "burst_exclusive"), ("burst_ladder", "burst_ladder")]
    sel = lambda k: P if k is None else P[P.burst] if k == "burst" else P[P.burst & (P.kind == k[6:])] if k.startswith("burst_") else P[P.kind == k]
    tr, mv = [], []
    for name, k in kinds:
        p = sel(k); q = Q[Q.jump.isin(p.jump)]
        for dl in DELTAS:
            a, b = p[p[f"ok{dl}"]], q[q[f"ok{dl}"]]
            for fee, col in (("0", f"pts0_{dl}"), ("0.04", f"ptsF_{dl}")):
                s, sp = stat(a, col), stat(b, col)
                dm, dlo, dhi = diff_ci(a, b, col) if len(a) and len(b) else (np.nan,) * 3
                tr.append(dict(kind=name, delta=dl, fee=fee, **s, hit=float((a[col] > 0).mean()) if len(a) else np.nan,
                               med_avail=float(a[f"avail{dl}"].median()) if len(a) else np.nan,
                               med_avail_incl=float(a[f"avail_incl{dl}"].median()) if len(a) else np.nan,
                               plc_n=sp["n"], plc_mean=sp["mean"], plc_lo=sp["lo"], plc_hi=sp["hi"], diff=dm, diff_lo=dlo, diff_hi=dhi,
                               dropped=int(len(p) - len(a))))
        for h in HORIZ:
            s, sp = stat(p, f"m{h}"), stat(q, f"m{h}")
            dm, dlo, dhi = diff_ci(p, q, f"m{h}") if len(p) and len(q) else (np.nan,) * 3
            mv.append(dict(kind=name, horizon_s=h, **s, plc_n=sp["n"], plc_mean=sp["mean"], plc_lo=sp["lo"], plc_hi=sp["hi"], diff=dm, diff_lo=dlo, diff_hi=dhi))
    cu = []
    for name, k in kinds:
        p = sel(k)
        x = p[p["first"].notna()]
        big = x[x.m900.abs() >= 2]
        cu.append(dict(kind=name, pairs=len(x), ratio_of_sums=float(x["first"].sum() / x.m900.sum()) if len(x) and x.m900.sum() != 0 else np.nan,
                       pairs_big=len(big), median_share_big=float((big["first"] / big.m900).median()) if len(big) else np.nan))
    return dict(trades=pd.DataFrame(tr), moves=pd.DataFrame(mv), catchup=pd.DataFrame(cu))

def verdict(T):
    out = {}
    for name in ("all", "exclusive", "ladder", "burst_all", "burst_exclusive", "burst_ladder"):
        r = T[(T.kind == name) & (T.delta == 30) & (T.fee == "0.04")]
        if r.empty: out[name] = False; continue
        r = r.iloc[0]
        out[name] = bool(r["mean"] > 0 and r.lo > 0 and r.jumps >= 100 and r.med_avail >= 200)
    return out

def load(half, fam_kinds=("exclusive", "ladder")):
    fm = pd.read_csv("research/leadlag-family-map.csv.gz")
    fm = fm[fm.kind.isin(fam_kinds)]
    lo, hi = (pd.Timestamp(x, tz="UTC").timestamp() for x in PERIODS[half])
    months = {"dev": range(1, 8), "test": range(6, 13)}[half]
    cid_set = set(fm.cid)
    parts = []
    for m in months:
        f = pd.read_parquet(f"data/leadlag/fills_2025_{m:02d}.parquet")
        f["cid"] = f.cid.astype(str); f = f[f.cid.isin(cid_set)]
        f = f[(f.ts >= lo - 86400) & (f.ts < hi + EXIT_HI + 60)]
        parts.append(f)
    f = pd.concat(parts).sort_values(["cid", "ts"], kind="stable")
    fam_of = dict(zip(fm.cid, fm.family)); kind_of = dict(zip(fm.cid, fm.kind))
    fams = {}
    for c, g in f.groupby("cid", sort=True):
        fams.setdefault(fam_of[c], (kind_of[c], {}))[1][c] = (g.ts.values, g.p.values.astype("float64"), g.usd.values.astype("float64"))
    return fams, lo, hi, fm

def main(half):
    if half == "test":
        dirty = subprocess.run("git status --porcelain leadlag.py leadlag_map.py leadlag_fetch.py", shell=True, capture_output=True, text=True).stdout.strip()
        assert not dirty, "test half refuses to run with uncommitted code changes:\n" + dirty
    head = subprocess.run("git rev-parse HEAD", shell=True, capture_output=True, text=True).stdout.strip()
    fams, lo, hi, fm = load(half)
    rng = np.random.RandomState(0); P, Q = [], []
    for fam in sorted(fams):
        kind, mem = fams[fam]
        if len(mem) < 2: continue
        a, b = analyse_family(fam, kind, mem, lo, hi, rng); P += a; Q += b
    P, Q = pd.DataFrame(P), pd.DataFrame(Q)
    P["jump"] = P.family + "@" + P.t0.astype(str)
    Q["jump"] = Q.pid.str.rsplit(":", n=1).str[0]
    names = fm.drop_duplicates("cid").set_index("cid")
    top = []
    for c in ("leader", "sib"): P[c + "_slug"] = P[c].map(names.slug)
    P.to_parquet(f"data/leadlag/{half}_pairs.parquet"); Q.to_parquet(f"data/leadlag/{half}_placebo.parquet")
    T = tables(P, Q); V = verdict(T["trades"])
    cnt = dict(half=half, head=head, families=int(len(fams)), families_by_kind=fm[fm.cid.isin([c for f in fams.values() for c in f[1]])].groupby("kind").family.nunique().to_dict(),
               jumps_with_sibling=int(P.jump.nunique()) if len(P) else 0, pairs=int(len(P)), placebo_rows=int(len(Q)),
               jumps_by_kind=P.groupby("kind").jump.nunique().to_dict() if len(P) else {})
    ok = P[P.ok30]
    if len(ok):
        g = ok.groupby("jump").agg(sum_ptsF=("ptsF_30", "sum"), n=("ptsF_30", "size"), t0=("t0", "first"), leader=("leader_slug", "first"), p_ref=("p_ref", "first"),
                                   p_jump=("p_jump", "first"), sibs=("sib_slug", lambda x: "; ".join(x)), p_in=("p_in30", lambda x: ", ".join(f"{v:.3f}" for v in x)),
                                   avail=("avail30", lambda x: ", ".join(f"{v:.0f}" for v in x)), avail_incl=("avail_incl30", lambda x: ", ".join(f"{v:.0f}" for v in x)))
        top = g.sort_values("sum_ptsF", ascending=False).head(5).reset_index()
        top["t0_utc"] = pd.to_datetime(top.t0, unit="s", utc=True).astype(str); top = top.to_dict("records")
    out = dict(counts=cnt, verdict=V, top_jumps=top, **{k: v.to_dict("records") for k, v in T.items()})
    json.dump(out, open(f"results/leadlag_{half}.json", "w"), indent=1, default=float)
    pd.set_option("display.width", 250, "display.max_columns", 40)
    print(json.dumps(cnt, indent=1)); [print(k, "\n", v.round(3).to_string()) for k, v in T.items()]; print("verdict", V)

if __name__ == "__main__":
    main(sys.argv[1])
