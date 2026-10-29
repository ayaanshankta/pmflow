"""B3 anchoring in CPI markets (research/behavioral-rules.md).

For each BLS CPI release in the archive window, find the CPI ladder markets for the reference month (slug rules below,
committed before any price was read), compute the market-implied expected value at t0 - 24 h and t0 - 1 h, the actual
print (the winning bracket) and the prior print (the previous release's actual), separately for m/m and y/y.
Then fit (implied - actual) = w * (prior - actual) through the origin; w > 0 means the market leans toward the prior print.

Run:  python behav_cpi.py      Out: data/behav/cpi_releases.parquet + printed table and fit
"""
import datetime as dt
import os
import re
import tempfile
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from huggingface_hub import hf_hub_download

REPO = "TimeSeventeen/Polymarket-v1"
ET = ZoneInfo("America/New_York")
MON = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
       "december"]
# BLS archived CPI releases (bls.gov/bls/news-release/cpi.htm, fetched 2026-10-29), all at 08:30 ET.
RELEASES = ["2022-11-10", "2022-12-13", "2023-01-12", "2023-02-14", "2023-03-14", "2023-04-12", "2023-05-10",
            "2023-06-13", "2023-07-12", "2023-08-10", "2023-09-13", "2023-10-12", "2023-11-14", "2023-12-12",
            "2024-01-11", "2024-02-13", "2024-03-12", "2024-04-10", "2024-05-15", "2024-06-12", "2024-07-11",
            "2024-08-14", "2024-09-11", "2024-10-10", "2024-11-13", "2024-12-11", "2025-01-15", "2025-02-12",
            "2025-03-12", "2025-04-10", "2025-05-13", "2025-06-11", "2025-07-15", "2025-08-12", "2025-09-11",
            "2025-10-24", "2025-12-18", "2026-01-13", "2026-02-13", "2026-03-11", "2026-04-10"]
# Reference month = the month the release reports on. Normally the previous month; the shutdown-delayed 2025-10-24
# release reported September and 2025-12-18 reported November (no October 2025 CPI).
REF_OVERRIDE = {"2025-10-24": (2025, 9), "2025-12-18": (2025, 11)}

NUM = r"(negative-)?(\d+)pt(\d+)"
TAIL = r"(-or-(?:more|less|higher|lower|above|below))?"
SUFFIX = r"(?:-[\d-]+)?$"


def rules(ref_y, ref_m):
    """Slug patterns -> (kind, measure). kind: 'bracket' (mutually exclusive) or 'gt' (P(value > x))."""
    m, pm = MON[ref_m - 1], MON[(ref_m - 2) % 12]
    return [
        (re.compile(rf"^will-annual-inflation-increase-by-{NUM}{TAIL}-in-{m}{SUFFIX}"), "bracket", "yoy"),
        (re.compile(rf"^will-monthly-inflation-increase-by-{NUM}{TAIL}-in-{m}{SUFFIX}"), "bracket", "mom"),
        (re.compile(rf"^us-inflation-{NUM}{TAIL}-from-{pm}-to-{m}-{ref_y}{SUFFIX}"), "bracket", "mom"),
        (re.compile(rf"^will-us-inflation-be-greater-than-{NUM}-from-{pm}-to-{m}-{ref_y}{SUFFIX}"), "gt", "mom"),
    ]


def parse(slug, ref_y, ref_m):
    for rx, kind, measure in rules(ref_y, ref_m):
        g = rx.match(slug)
        if g:
            neg, a, b = g.group(1), g.group(2), g.group(3)
            val = (-1 if neg else 1) * float(f"{a}.{b}")
            tail = (g.group(4) or "") if kind == "bracket" else ""
            side = "hi" if re.search("more|higher|above", tail) else "lo" if tail else ""
            return kind, measure, val, side
    return None


def load(days, tmp):
    out = []
    for d in days:
        for layer in ("daily_aligned", "daily_aligned_multi"):
            try:
                p = hf_hub_download(REPO, f"{layer}/{d:%Y_%m_%d}.parquet", repo_type="dataset", local_dir=tmp)
            except Exception:
                continue
            f = pd.read_parquet(p, columns=["block_timestamp", "market_slug", "condition_id", "p_event", "usdc_amount",
                                            "outcome_seq", "outcome_label", "winning_outcome_label"])
            out.append(f[f.market_slug.str.contains("inflation", na=False)])
            os.remove(p)
    return pd.concat(out) if out else pd.DataFrame()


def price_at(g, tau, max_age=48 * 3600):
    pre = g[(g.block_timestamp <= tau) & (g.block_timestamp > tau - max_age)]
    return pre.p_event.iloc[-1] if len(pre) else np.nan


def implied(ladder, col):
    """Expected value from a ladder at one time. Brackets: normalised probabilities (tails at their boundary value)."""
    l = ladder.dropna(subset=[col])
    if l.kind.iloc[0] == "bracket":
        if len(l) < 3:
            return np.nan, np.nan
        s = l[col].sum()
        return float((l.val * l[col]).sum() / s), float(s)
    # 'gt' ladder: P(X > x) at sorted thresholds -> mass between thresholds, mass outside at the end thresholds
    l = l.sort_values("val")
    if len(l) < 3:
        return np.nan, np.nan
    x, q = l.val.to_numpy(), np.minimum.accumulate(l[col].clip(0, 1).to_numpy())  # enforce monotone
    mass = np.r_[1 - q[0], q[:-1] - q[1:], q[-1]]
    pts = np.r_[x[0], (x[:-1] + x[1:]) / 2 + 0.05, x[-1] + 0.1]  # values in (x_i, x_{i+1}] on a 0.1 grid
    return float((mass * pts).sum()), 1.0


def actual_from(ladder):
    """The resolved value: winning bracket's value, or for 'gt' the largest threshold that resolved Yes (+0.1)."""
    if ladder.kind.iloc[0] == "bracket":
        w = ladder[ladder.win]
        return (float(w.val.iloc[0]), w.side.iloc[0]) if len(w) == 1 else (np.nan, f"winners={len(w)}")
    yes = ladder[ladder.win].val
    return (round(float(yes.max()) + 0.1, 1) if len(yes) else round(float(ladder.val.min()), 1)), ""


def main():
    tmp, rows = tempfile.mkdtemp(), []
    for date in RELEASES:
        t0 = int(dt.datetime.fromisoformat(date).replace(hour=8, minute=30, tzinfo=ET).timestamp())
        ref_y, ref_m = REF_OVERRIDE.get(date, ((int(date[:4]) - (date[5:7] == "01")), (int(date[5:7]) - 2) % 12 + 1))
        d0 = dt.date.fromisoformat(date)
        f = load([d0 - dt.timedelta(days=k) for k in (2, 1, 0)], tmp)
        f = f[f.block_timestamp < t0] if len(f) else f
        unmatched = set()
        mk = []
        for cid, g in (f.groupby("condition_id") if len(f) else []):
            slug = g.market_slug.iloc[0]
            p = parse(slug, ref_y, ref_m)
            if p is None:
                unmatched.add(slug)
                continue
            g = g.sort_values("block_timestamp")
            seq1 = g[g.outcome_seq == 1].outcome_label
            win = (g.winning_outcome_label.iloc[0] == (seq1.iloc[0] if len(seq1) else "Yes"))
            mk.append(dict(cid=cid, slug=slug, kind=p[0], measure=p[1], val=p[2], side=p[3], win=win,
                           p24=price_at(g, t0 - 24 * 3600), p1=price_at(g, t0 - 3600)))
        mk = pd.DataFrame(mk)
        for measure in ("mom", "yoy"):
            l = mk[mk.measure == measure] if len(mk) else mk
            if len(l) == 0:
                continue
            l = l.drop_duplicates("val") if l.kind.iloc[0] == "gt" else l.sort_values("p24", na_position="first").drop_duplicates(["val", "side"], keep="last")
            act, flag = actual_from(l)
            i24, s24 = implied(l, "p24")
            i1, s1 = implied(l, "p1")
            rows.append(dict(release=date, ref=f"{ref_y}-{ref_m:02d}", measure=measure, kind=l.kind.iloc[0],
                             n_mkts=len(l), actual=act, actual_flag=flag, implied_24h=i24, psum_24h=s24,
                             implied_1h=i1, psum_1h=s1))
        print(date, f"ref {ref_y}-{ref_m:02d}", "matched", len(mk), "unmatched-inflation", len(unmatched),
              sorted(u for u in unmatched if "powell" not in u)[:3], flush=True)
    r = pd.DataFrame(rows).sort_values(["measure", "release"])
    r["prior"] = r.groupby("measure").actual.shift(1)
    r.to_parquet("data/behav/cpi_releases.parquet")
    pd.set_option("display.width", 200)
    print(r.round(3).to_string(index=False))
    for measure in ("mom", "yoy"):
        for h in ("24h", "1h"):
            d = r[(r.measure == measure)].dropna(subset=[f"implied_{h}", "actual", "prior"])
            d = d[(d[f"psum_{h}"] > 0.8) & (d[f"psum_{h}"] < 1.25) & (d.actual_flag == "")]
            x, y = (d.prior - d.actual).to_numpy(), (d[f"implied_{h}"] - d.actual).to_numpy()
            if len(d) < 5 or (x ** 2).sum() == 0:
                print(measure, h, "n", len(d), "too few")
                continue
            w = (x * y).sum() / (x ** 2).sum()
            rng = np.random.default_rng(0)
            bs = [(x[i] * y[i]).sum() / max((x[i] ** 2).sum(), 1e-12) for i in (rng.integers(0, len(d), len(d)) for _ in range(2000))]
            print(f"{measure} {h}: w = {w:.3f}  95% CI [{np.percentile(bs, 2.5):.3f}, {np.percentile(bs, 97.5):.3f}]  n = {len(d)}")


if __name__ == "__main__":
    main()
