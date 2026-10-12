# C2 result: do sibling markets lag the leader? (Polymarket-v1 trade archive, 2025)

**Verdict: NO. Siblings do catch up after a leader jump, but by about 0.15-0.25 points gross, which is a fraction of the round-trip venue fee; no cell of the test half clears the pre-registered bar.**
At Δ = 30 s with the venue fee on the test half (pooled): mean **−0.506 pts per share, 95 % cluster-bootstrap CI [−0.556, −0.457], 21,482 jumps; median available volume $0** (bar: mean > 0 with CI excluding 0 on ≥ 100 jumps AND median available ≥ $200). Both family kinds fail separately too (exclusive −0.501 [−0.568, −0.439]; ladder −0.516 [−0.596, −0.441]).

Rules: `research/structure-rules.md` Definitions + C2, git blob hash `1582327e1f20…` (full `1582327e1f207b4f6a01f35a80485be306fc5778`), unchanged. Code: `leadlag_fetch.py`, `leadlag_gamma.py`, `leadlag_map.py`, `leadlag.py`, tests `test_leadlag.py`.

## Provenance (order of events)
1. `8814e37` — family map + ladder rule + fetch/Gamma scripts committed. No price measure existed at that point (only fill counts / USDC volume per market were read to bound the Gamma lookup).
2. Development half (2025-01-01..06-30) run twice; second run added the `burst_*` variant (see "Method changes"). Results in `results/leadlag_dev.json`.
3. `df4704d` — final method code + tests + development results committed.
4. Test half (2025-07-01..12-31) run **once** at `df4704d` (the script asserts a clean tree for the code files and records HEAD in `results/leadlag_test.json`). It did not crash; no fix was needed. Raw output `results/leadlag_test.log`.

## Family map (2025; details in `research/leadlag-family-map.md`)
Family = Gamma event id. Exclusive = negRisk event with ≥ 2 archive markets. Ladder = non-negRisk event where ≥ 2 markets share a question template after replacing a deadline ("by <date>") or a threshold (number after above/below/over/reach/hit/>/<…) — rule in `leadlag_map.py` docstring. 'between' brackets, markets varying in both date and threshold, and duplicate-value templates are dropped and counted.
* Gamma still serves closed 2025 events: 99.1 % of 101,432 looked-up markets found; archive `neg_risk_market_id` agrees with Gamma `negRiskMarketID` for 100 % of 47,593 markets with both.
* 8,107 exclusive families (47,046 markets, median 3 members) and 1,558 ladder families (10,251 markets, median 6).
* Share of 2025 USDC volume in the archive layers: exclusive 28.7 %, ladder 11.1 % (**39.8 % covered**); 47.0 % is "single" (no family partner among archive markets); 11.4 % short-horizon up/down markets (not looked up; single-market events by construction); 0.6 % no Gamma record; 1.0 % dropped as ambiguous; 0.2 % under 20 fills. By market count 27.3 % of all markets are placed (56.5 % of those looked up).

## Counts
| | development (H1) | test (H2) |
|---|---|---|
| families with ≥ 2 members traded in window | 2,063 (1,925 excl, 138 ladder) | 7,863 (6,382 excl, 1,481 ladder) |
| leader jumps with ≥ 1 qualifying sibling | 29,520 (24,746 excl, 4,774 ladder) | 75,852 (46,045 excl, 29,807 ladder) |
| (jump, sibling) pairs | 143,035 | 333,170 |
| placebo draws | 2,456,720 | 5,457,344 |
| of which burst-variant jumps | 4,346 | 10,424 |

Entry/exit coverage is low: for Δ = 30 only 23,705 (dev) and 46,920 (test) of the pairs have both a sibling trade in [t0+30 s, t0+12 min) and one in the exit window [12, 18] min. The paper-trade rows are therefore conditional on the sibling trading again; the "moves" tables use all pairs.

## Test half (evaluated once) — paper trade, points per share, Δ = delay after t0
Mean pts after fees; CI = event-cluster bootstrap (cluster = leader jump), 1,000 resamples, seed 0. "real − placebo" = paired-by-jump difference to the 20-random-time placebo.

| kind      |   Δ s | fee   |   trades |   jumps | mean pts [95% CI]       |   hit |   placebo mean | real − placebo          | med $avail (excl/incl entry)   |   pairs w/o entry or exit |
|:----------|------:|:------|---------:|--------:|:------------------------|------:|---------------:|:------------------------|:-------------------------------|--------------------------:|
| all       |     5 | 0     |    48003 |   21930 | +0.227 [+0.179, +0.276] |  0.39 |         -0.003 | +0.178 [+0.126, +0.232] | 0 / 5.8                        |                    285167 |
| all       |     5 | venue |    48003 |   21930 | -0.470 [-0.518, -0.420] |  0.29 |         -0.612 | +0.094 [+0.045, +0.149] | 0 / 5.8                        |                    285167 |
| all       |    30 | 0     |    46920 |   21482 | +0.190 [+0.141, +0.239] |  0.38 |         -0.002 | +0.149 [+0.098, +0.197] | 0 / 5.8                        |                    286250 |
| all       |    30 | venue |    46920 |   21482 | -0.506 [-0.556, -0.457] |  0.28 |         -0.611 | +0.065 [+0.014, +0.113] | 0 / 5.8                        |                    286250 |
| all       |   120 | 0     |    44104 |   20446 | +0.146 [+0.096, +0.196] |  0.38 |         -0.002 | +0.105 [+0.054, +0.152] | 0 / 5.7                        |                    289066 |
| all       |   120 | venue |    44104 |   20446 | -0.552 [-0.602, -0.502] |  0.28 |         -0.612 | +0.021 [-0.031, +0.070] | 0 / 5.7                        |                    289066 |
| exclusive |     5 | 0     |    33805 |   14020 | +0.206 [+0.145, +0.268] |  0.37 |         -0.002 | +0.146 [+0.088, +0.206] | 0 / 4.6                        |                    197675 |
| exclusive |     5 | venue |    33805 |   14020 | -0.460 [-0.522, -0.400] |  0.28 |         -0.545 | +0.046 [-0.011, +0.105] | 0 / 4.6                        |                    197675 |
| exclusive |    30 | 0     |    33022 |   13732 | +0.165 [+0.101, +0.226] |  0.37 |         -0.001 | +0.115 [+0.052, +0.174] | 0 / 4.6                        |                    198458 |
| exclusive |    30 | venue |    33022 |   13732 | -0.501 [-0.568, -0.439] |  0.28 |         -0.545 | +0.015 [-0.047, +0.072] | 0 / 4.6                        |                    198458 |
| exclusive |   120 | 0     |    31018 |   13079 | +0.121 [+0.063, +0.183] |  0.37 |         -0.002 | +0.076 [+0.020, +0.132] | 0 / 4.6                        |                    200462 |
| exclusive |   120 | venue |    31018 |   13079 | -0.550 [-0.610, -0.487] |  0.27 |         -0.548 | -0.024 [-0.080, +0.035] | 0 / 4.6                        |                    200462 |
| ladder    |     5 | 0     |    14198 |    7910 | +0.277 [+0.197, +0.353] |  0.41 |         -0.006 | +0.258 [+0.172, +0.348] | 0 / 10.8                       |                     87492 |
| ladder    |     5 | venue |    14198 |    7910 | -0.491 [-0.571, -0.413] |  0.3  |         -0.747 | +0.201 [+0.115, +0.288] | 0 / 10.8                       |                     87492 |
| ladder    |    30 | 0     |    13898 |    7750 | +0.249 [+0.171, +0.322] |  0.41 |         -0.003 | +0.233 [+0.143, +0.316] | 0 / 10.6                       |                     87792 |
| ladder    |    30 | venue |    13898 |    7750 | -0.516 [-0.596, -0.441] |  0.3  |         -0.744 | +0.178 [+0.086, +0.262] | 0 / 10.6                       |                     87792 |
| ladder    |   120 | 0     |    13086 |    7367 | +0.208 [+0.133, +0.285] |  0.41 |         -0.002 | +0.176 [+0.097, +0.266] | 0 / 10.2                       |                     88604 |
| ladder    |   120 | venue |    13086 |    7367 | -0.556 [-0.630, -0.480] |  0.29 |         -0.744 | +0.122 [+0.041, +0.216] | 0 / 10.2                       |                     88604 |

Siblings' last-trade price move after a jump (points, signed by implied direction; all pairs; no trade = unchanged):

| kind            |   horizon_s |   pairs |   jumps | mean pts [95% CI]       |   placebo mean | real − placebo          |
|:----------------|------------:|--------:|--------:|:------------------------|---------------:|:------------------------|
| all             |          60 |  333170 |   75852 | +0.120 [+0.114, +0.127] |          0     | +0.123 [+0.115, +0.130] |
| all             |         300 |  333170 |   75852 | +0.180 [+0.171, +0.189] |          0     | +0.182 [+0.172, +0.191] |
| all             |         900 |  333170 |   75852 | +0.235 [+0.223, +0.246] |          0.001 | +0.235 [+0.223, +0.249] |
| exclusive       |          60 |  231480 |   46045 | +0.131 [+0.121, +0.139] |          0     | +0.133 [+0.123, +0.143] |
| exclusive       |         300 |  231480 |   46045 | +0.173 [+0.161, +0.184] |          0     | +0.176 [+0.163, +0.188] |
| exclusive       |         900 |  231480 |   46045 | +0.204 [+0.191, +0.219] |          0.001 | +0.207 [+0.191, +0.223] |
| ladder          |          60 |  101690 |   29807 | +0.097 [+0.089, +0.106] |         -0     | +0.098 [+0.089, +0.107] |
| ladder          |         300 |  101690 |   29807 | +0.195 [+0.183, +0.208] |          0.001 | +0.196 [+0.182, +0.210] |
| ladder          |         900 |  101690 |   29807 | +0.303 [+0.284, +0.323] |          0.002 | +0.303 [+0.282, +0.323] |
| burst_all       |          60 |   51959 |   10424 | +0.202 [+0.182, +0.223] |          0.001 | +0.209 [+0.187, +0.233] |
| burst_all       |         300 |   51959 |   10424 | +0.260 [+0.235, +0.285] |         -0.001 | +0.268 [+0.241, +0.297] |
| burst_all       |         900 |   51959 |   10424 | +0.298 [+0.264, +0.331] |         -0.002 | +0.305 [+0.269, +0.342] |
| burst_exclusive |          60 |   40646 |    7131 | +0.237 [+0.212, +0.262] |          0.001 | +0.244 [+0.219, +0.271] |
| burst_exclusive |         300 |   40646 |    7131 | +0.285 [+0.255, +0.316] |         -0.003 | +0.295 [+0.263, +0.330] |
| burst_exclusive |         900 |   40646 |    7131 | +0.311 [+0.274, +0.349] |         -0.004 | +0.318 [+0.279, +0.361] |
| burst_ladder    |          60 |   11313 |    3293 | +0.076 [+0.047, +0.109] |          0     | +0.078 [+0.046, +0.111] |
| burst_ladder    |         300 |   11313 |    3293 | +0.170 [+0.132, +0.211] |          0.003 | +0.168 [+0.123, +0.211] |
| burst_ladder    |         900 |   11313 |    3293 | +0.250 [+0.184, +0.324] |          0.003 | +0.254 [+0.185, +0.327] |

Catch-up (ratio of sums = share of the sibling's 15-min move already present at its first trade ≥ t0; "big" = |15-min move| ≥ 2 pts, per-pair median):

| kind            |   pairs |   ratio_of_sums |   pairs_big |   median_share_big |
|:----------------|--------:|----------------:|------------:|-------------------:|
| all             |  147011 |           0.709 |       32413 |              0.75  |
| exclusive       |  106914 |           0.634 |       22034 |              0.69  |
| ladder          |   40097 |           0.824 |       10379 |              0.913 |
| burst_all       |   28315 |           0.565 |        5671 |              0.389 |
| burst_exclusive |   22936 |           0.561 |        4439 |              0.333 |
| burst_ladder    |    5379 |           0.583 |        1232 |              0.5   |

## Development half (for reference)

| kind      |   Δ s | fee   |   trades |   jumps | mean pts [95% CI]       |   hit |   placebo mean | real − placebo          | med $avail (excl/incl entry)   |   pairs w/o entry or exit |
|:----------|------:|:------|---------:|--------:|:------------------------|------:|---------------:|:------------------------|:-------------------------------|--------------------------:|
| all       |     5 | 0     |    24350 |    9687 | +0.117 [+0.061, +0.172] |  0.35 |          0.008 | +0.120 [+0.058, +0.175] | 0 / 4.7                        |                    118685 |
| all       |     5 | venue |    24350 |    9687 | -0.512 [-0.572, -0.459] |  0.25 |         -0.556 | +0.043 [-0.020, +0.099] | 0 / 4.7                        |                    118685 |
| all       |    30 | 0     |    23705 |    9467 | +0.110 [+0.062, +0.162] |  0.35 |          0.009 | +0.118 [+0.064, +0.171] | 0 / 4.7                        |                    119330 |
| all       |    30 | venue |    23705 |    9467 | -0.520 [-0.568, -0.469] |  0.25 |         -0.555 | +0.041 [-0.014, +0.094] | 0 / 4.7                        |                    119330 |
| all       |   120 | 0     |    22352 |    9001 | +0.070 [+0.018, +0.124] |  0.34 |          0.006 | +0.079 [+0.030, +0.133] | 0 / 4.7                        |                    120683 |
| all       |   120 | venue |    22352 |    9001 | -0.561 [-0.612, -0.506] |  0.24 |         -0.561 | +0.002 [-0.050, +0.057] | 0 / 4.7                        |                    120683 |
| exclusive |     5 | 0     |    22025 |    8202 | +0.095 [+0.035, +0.149] |  0.34 |          0.01  | +0.096 [+0.039, +0.161] | 0 / 4.2                        |                    107720 |
| exclusive |     5 | venue |    22025 |    8202 | -0.526 [-0.586, -0.470] |  0.25 |         -0.549 | +0.028 [-0.031, +0.092] | 0 / 4.2                        |                    107720 |
| exclusive |    30 | 0     |    21422 |    8002 | +0.089 [+0.032, +0.140] |  0.34 |          0.011 | +0.096 [+0.039, +0.153] | 0 / 4.3                        |                    108323 |
| exclusive |    30 | venue |    21422 |    8002 | -0.533 [-0.589, -0.482] |  0.24 |         -0.548 | +0.028 [-0.031, +0.086] | 0 / 4.3                        |                    108323 |
| exclusive |   120 | 0     |    20197 |    7607 | +0.049 [-0.011, +0.104] |  0.33 |          0.008 | +0.056 [-0.003, +0.115] | 0 / 4.2                        |                    109548 |
| exclusive |   120 | venue |    20197 |    7607 | -0.574 [-0.636, -0.517] |  0.24 |         -0.554 | -0.011 [-0.071, +0.051] | 0 / 4.2                        |                    109548 |
| ladder    |     5 | 0     |     2325 |    1485 | +0.332 [+0.217, +0.447] |  0.42 |         -0.008 | +0.343 [+0.216, +0.489] | 0 / 12.1                       |                     10965 |
| ladder    |     5 | venue |     2325 |    1485 | -0.376 [-0.490, -0.265] |  0.26 |         -0.614 | +0.183 [+0.053, +0.324] | 0 / 12.1                       |                     10965 |
| ladder    |    30 | 0     |     2283 |    1465 | +0.309 [+0.204, +0.419] |  0.42 |         -0.007 | +0.324 [+0.208, +0.445] | 0 / 10.0                       |                     11007 |
| ladder    |    30 | venue |     2283 |    1465 | -0.396 [-0.498, -0.284] |  0.25 |         -0.613 | +0.163 [+0.047, +0.287] | 0 / 10.0                       |                     11007 |
| ladder    |   120 | 0     |     2155 |    1394 | +0.265 [+0.164, +0.376] |  0.41 |         -0.01  | +0.291 [+0.177, +0.422] | 0 / 9.7                        |                     11135 |
| ladder    |   120 | venue |     2155 |    1394 | -0.439 [-0.540, -0.328] |  0.24 |         -0.611 | +0.124 [+0.009, +0.254] | 0 / 9.7                        |                     11135 |

| kind            |   horizon_s |   pairs |   jumps | mean pts [95% CI]       |   placebo mean | real − placebo          |
|:----------------|------------:|--------:|--------:|:------------------------|---------------:|:------------------------|
| all             |          60 |  143035 |   29520 | +0.116 [+0.105, +0.126] |          0     | +0.115 [+0.103, +0.125] |
| all             |         300 |  143035 |   29520 | +0.158 [+0.145, +0.170] |          0.001 | +0.155 [+0.140, +0.169] |
| all             |         900 |  143035 |   29520 | +0.185 [+0.167, +0.203] |          0.001 | +0.181 [+0.163, +0.199] |
| exclusive       |          60 |  129745 |   24746 | +0.120 [+0.108, +0.132] |          0     | +0.118 [+0.106, +0.130] |
| exclusive       |         300 |  129745 |   24746 | +0.156 [+0.141, +0.171] |          0.001 | +0.153 [+0.138, +0.168] |
| exclusive       |         900 |  129745 |   24746 | +0.179 [+0.162, +0.196] |          0.002 | +0.173 [+0.153, +0.190] |
| ladder          |          60 |   13290 |    4774 | +0.077 [+0.066, +0.090] |         -0.001 | +0.078 [+0.066, +0.091] |
| ladder          |         300 |   13290 |    4774 | +0.171 [+0.150, +0.193] |         -0.002 | +0.172 [+0.149, +0.196] |
| ladder          |         900 |   13290 |    4774 | +0.247 [+0.216, +0.282] |         -0.002 | +0.257 [+0.225, +0.291] |
| burst_all       |          60 |   24605 |    4346 | +0.179 [+0.153, +0.206] |         -0.001 | +0.182 [+0.156, +0.210] |
| burst_all       |         300 |   24605 |    4346 | +0.237 [+0.205, +0.272] |          0.002 | +0.237 [+0.200, +0.273] |
| burst_all       |         900 |   24605 |    4346 | +0.258 [+0.219, +0.301] |          0.002 | +0.255 [+0.214, +0.296] |
| burst_exclusive |          60 |   22962 |    3777 | +0.183 [+0.153, +0.209] |         -0.001 | +0.186 [+0.158, +0.216] |
| burst_exclusive |         300 |   22962 |    3777 | +0.236 [+0.201, +0.274] |          0.003 | +0.235 [+0.199, +0.272] |
| burst_exclusive |         900 |   22962 |    3777 | +0.256 [+0.214, +0.299] |          0.004 | +0.251 [+0.208, +0.293] |
| burst_ladder    |          60 |    1643 |     569 | +0.133 [+0.082, +0.192] |          0.001 | +0.134 [+0.082, +0.197] |
| burst_ladder    |         300 |    1643 |     569 | +0.250 [+0.175, +0.342] |         -0.008 | +0.272 [+0.196, +0.363] |
| burst_ladder    |         900 |    1643 |     569 | +0.288 [+0.188, +0.414] |         -0.015 | +0.323 [+0.214, +0.453] |

| kind            |   pairs |   ratio_of_sums |   pairs_big |   median_share_big |
|:----------------|--------:|----------------:|------------:|-------------------:|
| all             |   72338 |           0.743 |       11632 |              0.69  |
| exclusive       |   65900 |           0.753 |       10643 |              0.714 |
| ladder          |    6438 |           0.67  |         989 |              0.667 |
| burst_all       |   15216 |           0.673 |        2166 |              0.468 |
| burst_exclusive |   14305 |           0.686 |        2038 |              0.46  |
| burst_ladder    |     911 |           0.516 |         128 |              0.5   |

## Variant: burst jumps (added after the first development run; reported alongside, not instead)
Restricts to jumps where a trade inside the 60 s window already differs from the jump trade by ≥ 3 pts (a move made of trades, not one trade re-pricing after a quiet gap). Test half:

| kind            |   Δ s | fee   |   trades |   jumps | mean pts [95% CI]       |   hit |   placebo mean | real − placebo          | med $avail (excl/incl entry)   |   pairs w/o entry or exit |
|:----------------|------:|:------|---------:|--------:|:------------------------|------:|---------------:|:------------------------|:-------------------------------|--------------------------:|
| burst_all       |     5 | 0     |    12339 |    4637 | +0.199 [+0.105, +0.308] |  0.39 |         -0.021 | +0.163 [+0.063, +0.267] | 0 / 6.6                        |                     39620 |
| burst_all       |     5 | venue |    12339 |    4637 | -0.472 [-0.570, -0.367] |  0.29 |         -0.603 | +0.083 [-0.016, +0.185] | 0 / 6.6                        |                     39620 |
| burst_all       |    30 | 0     |    12144 |    4568 | +0.144 [+0.041, +0.239] |  0.39 |         -0.019 | +0.127 [+0.024, +0.224] | 0 / 6.3                        |                     39815 |
| burst_all       |    30 | venue |    12144 |    4568 | -0.528 [-0.634, -0.433] |  0.29 |         -0.602 | +0.047 [-0.058, +0.146] | 0 / 6.3                        |                     39815 |
| burst_all       |   120 | 0     |    11529 |    4389 | +0.103 [+0.017, +0.192] |  0.38 |         -0.022 | +0.079 [-0.021, +0.179] | 0 / 6.7                        |                     40430 |
| burst_all       |   120 | venue |    11529 |    4389 | -0.576 [-0.663, -0.486] |  0.27 |         -0.606 | -0.005 [-0.106, +0.095] | 0 / 6.7                        |                     40430 |
| burst_exclusive |     5 | 0     |     9848 |    3395 | +0.165 [+0.053, +0.281] |  0.39 |         -0.023 | +0.115 [+0.004, +0.221] | 0 / 5.0                        |                     30798 |
| burst_exclusive |     5 | venue |     9848 |    3395 | -0.480 [-0.590, -0.364] |  0.29 |         -0.562 | +0.029 [-0.081, +0.137] | 0 / 5.0                        |                     30798 |
| burst_exclusive |    30 | 0     |     9692 |    3346 | +0.104 [+0.006, +0.209] |  0.38 |         -0.021 | +0.079 [-0.028, +0.184] | 0 / 5.0                        |                     30954 |
| burst_exclusive |    30 | venue |     9692 |    3346 | -0.541 [-0.647, -0.435] |  0.29 |         -0.561 | -0.007 [-0.119, +0.096] | 0 / 5.0                        |                     30954 |
| burst_exclusive |   120 | 0     |     9203 |    3220 | +0.079 [-0.026, +0.182] |  0.37 |         -0.024 | +0.047 [-0.058, +0.155] | 0 / 5.1                        |                     31443 |
| burst_exclusive |   120 | venue |     9203 |    3220 | -0.574 [-0.683, -0.472] |  0.27 |         -0.566 | -0.043 [-0.145, +0.070] | 0 / 5.1                        |                     31443 |
| burst_ladder    |     5 | 0     |     2491 |    1242 | +0.337 [+0.148, +0.543] |  0.4  |         -0.011 | +0.356 [+0.127, +0.575] | 0 / 19.6                       |                      8822 |
| burst_ladder    |     5 | venue |     2491 |    1242 | -0.444 [-0.633, -0.241] |  0.29 |         -0.757 | +0.297 [+0.067, +0.511] | 0 / 19.6                       |                      8822 |
| burst_ladder    |    30 | 0     |     2452 |    1222 | +0.302 [+0.105, +0.477] |  0.4  |         -0.012 | +0.318 [+0.118, +0.551] | 0 / 17.9                       |                      8861 |
| burst_ladder    |    30 | venue |     2452 |    1222 | -0.478 [-0.677, -0.297] |  0.29 |         -0.758 | +0.260 [+0.070, +0.498] | 0 / 17.9                       |                      8861 |
| burst_ladder    |   120 | 0     |     2326 |    1169 | +0.197 [+0.027, +0.379] |  0.4  |         -0.014 | +0.210 [-0.001, +0.429] | 0 / 17.5                       |                      8987 |
| burst_ladder    |   120 | venue |     2326 |    1169 | -0.585 [-0.756, -0.401] |  0.28 |         -0.758 | +0.147 [-0.056, +0.361] | 0 / 17.5                       |                      8987 |

Development half:

| kind            |   Δ s | fee   |   trades |   jumps | mean pts [95% CI]       |   hit |   placebo mean | real − placebo          | med $avail (excl/incl entry)   |   pairs w/o entry or exit |
|:----------------|------:|:------|---------:|--------:|:------------------------|------:|---------------:|:------------------------|:-------------------------------|--------------------------:|
| burst_all       |     5 | 0     |     6526 |    2126 | +0.145 [+0.039, +0.245] |  0.35 |          0.006 | +0.139 [+0.018, +0.255] | 0 / 4.2                        |                     18079 |
| burst_all       |     5 | venue |     6526 |    2126 | -0.443 [-0.550, -0.343] |  0.25 |         -0.55  | +0.107 [-0.018, +0.222] | 0 / 4.2                        |                     18079 |
| burst_all       |    30 | 0     |     6393 |    2092 | +0.129 [+0.035, +0.226] |  0.35 |          0.005 | +0.130 [+0.018, +0.236] | 0 / 4.3                        |                     18212 |
| burst_all       |    30 | venue |     6393 |    2092 | -0.462 [-0.560, -0.359] |  0.25 |         -0.552 | +0.093 [-0.021, +0.202] | 0 / 4.3                        |                     18212 |
| burst_all       |   120 | 0     |     6091 |    2004 | +0.065 [-0.033, +0.157] |  0.34 |          0.004 | +0.073 [-0.029, +0.179] | 0 / 4.4                        |                     18514 |
| burst_all       |   120 | venue |     6091 |    2004 | -0.525 [-0.619, -0.432] |  0.24 |         -0.555 | +0.041 [-0.068, +0.150] | 0 / 4.4                        |                     18514 |
| burst_exclusive |     5 | 0     |     6158 |    1913 | +0.130 [+0.017, +0.236] |  0.34 |          0.009 | +0.125 [+0.006, +0.247] | 0 / 3.9                        |                     16804 |
| burst_exclusive |     5 | venue |     6158 |    1913 | -0.456 [-0.574, -0.349] |  0.25 |         -0.55  | +0.099 [-0.024, +0.216] | 0 / 3.9                        |                     16804 |
| burst_exclusive |    30 | 0     |     6030 |    1882 | +0.120 [+0.007, +0.226] |  0.35 |          0.009 | +0.123 [+0.005, +0.236] | 0 / 4.0                        |                     16932 |
| burst_exclusive |    30 | venue |     6030 |    1882 | -0.469 [-0.586, -0.363] |  0.25 |         -0.551 | +0.092 [-0.027, +0.208] | 0 / 4.0                        |                     16932 |
| burst_exclusive |   120 | 0     |     5748 |    1805 | +0.058 [-0.042, +0.153] |  0.34 |          0.007 | +0.065 [-0.035, +0.173] | 0 / 4.3                        |                     17214 |
| burst_exclusive |   120 | venue |     5748 |    1805 | -0.530 [-0.630, -0.430] |  0.24 |         -0.556 | +0.039 [-0.063, +0.147] | 0 / 4.3                        |                     17214 |
| burst_ladder    |     5 | 0     |      368 |     213 | +0.398 [+0.089, +0.858] |  0.45 |         -0.036 | +0.373 [+0.022, +0.868] | 0 / 12.6                       |                      1275 |
| burst_ladder    |     5 | venue |      368 |     213 | -0.225 [-0.525, +0.209] |  0.27 |         -0.555 | +0.237 [-0.117, +0.714] | 0 / 12.6                       |                      1275 |
| burst_ladder    |    30 | 0     |      363 |     210 | +0.274 [+0.006, +0.629] |  0.42 |         -0.039 | +0.258 [-0.047, +0.716] | 0 / 10.0                       |                      1280 |
| burst_ladder    |    30 | venue |      363 |     210 | -0.353 [-0.620, -0.005] |  0.26 |         -0.557 | +0.118 [-0.194, +0.583] | 0 / 10.0                       |                      1280 |
| burst_ladder    |   120 | 0     |      343 |     199 | +0.184 [-0.124, +0.576] |  0.43 |         -0.034 | +0.206 [-0.158, +0.689] | 0 / 8.6                        |                      1300 |
| burst_ladder    |   120 | venue |      343 |     199 | -0.440 [-0.750, -0.062] |  0.25 |         -0.543 | +0.066 [-0.295, +0.541] | 0 / 8.6                        |                      1300 |

## Reading
* The lag is real and small: the median sibling has already made ~70 % of its 15-minute move by its first trade after t0 (pooled ratio of sums 0.71 test, 0.74 dev; lower, 0.57, for burst jumps). The remaining move, relative to placebo, is +0.12/+0.18/+0.24 pts at 1/5/15 min (all pairs), +0.15 pts gross at Δ = 30 s on the traded subset.
* Fees take ~0.7 pts per round trip at these prices; placebo trades lose 0.55-0.75 pts after fees purely from that. Real − placebo after fees is slightly positive for pooled/ladder (e.g. ladder Δ = 30 s: +0.178 [0.086, 0.262]) but the strategy itself is still negative.
* Available volume: median $0 in the 10 s after entry within 2c (excluding the entry fill) in every cell; including the entry fill the median is ~$5-20. The $200 bar is far away.
* Ladders respond more than exclusives (0.30 vs 0.20 pts at 15 min), consistent between halves, but they also fail on fees and volume.
* The five largest contributing jumps (by summed 30 s paper-trade points after fees, test half) are not evidence of a tradeable effect: all are single-leg entries at extreme prices (0.999, 0.001, 0.015…) or near-resolution price flips, i.e. a market that was about to settle: 2025-10-18 04:53 UTC `mex-tig-nec-2025-10-17-tig` 0.85→0.89, sibling entry 0.999, avail $0; 2025-10-01 08:28 `ethereum-above-4100-on-october-1` 0.80→0.84, siblings entered at 0.015/0.300/0.999, avail $0/0/0 ($0/5/40 incl. entry); 2025-11-22 04:42 `will-the-price-of-solana-be-between-120-130-on-november-22` 0.63→0.79, siblings at 0.001/0.001/0.989 with $14,983/$14,997/$0 near-price volume (bracket markets resolving on the day); 2025-11-16 00:12 `will-russia-capture-myrnohard-by-november-30…` 0.53→0.58, siblings at 0.160/0.880, $538/$2,204; 2025-11-30 16:18 `will-the-price-of-solana-be-between-140-150-on-november-30` 0.056→0.095, sibling at 0.908, avail $0. Full rows: `results/leadlag_test.json` → `top_jumps`. Since the bar is failed these are listed for hand-checking only.

## Method changes
* Before any price: ladder cue list extended with `>`, `>=`, `<`, `<=` after looking at the largest unplaced non-negRisk events (e.g. "FDV >$10B"). Committed in `8814e37`.
* After the first development run: added the `burst_*` variant (above) and a `top_jumps` listing. The primary method, the Δ grid, the fee and the bar were not touched; nothing was tuned on a development number. The first development run's numbers for the primary rows are identical to the second's.
* Choices C2 leaves open, fixed before the first development number and written in the `leadlag.py` docstring: jump = |p − p(last trade ≤ t−60 s)| ≥ 3 pts; 30-min quiet period is rolling; entry must precede the exit window; "available volume" excludes the entry fill (incl.-entry variant reported); bar applied to the pooled set as primary (per-kind also shown); placebo requires the same ≥ 20-fills-in-24 h liquidity as the real sibling; placebo days are UTC days.
* No crash fix was needed on the test half.

## Limitations
* The archive is trades only: the bid-ask spread and displayed depth are unmeasured. Entry at "the first sibling trade" is a trade that happened, not a quote that could be hit; the fee-clearing question would need quotes.
* Timestamps are on-chain settlement (block) times, a few seconds after the match; Δ = 5 s is below the timestamp resolution, and the order of the leader jump and sibling trades within ~2 s is not observable. Same-second fills have an arbitrary (file) order.
* A sibling's "late" trade may simply be the first time anyone traded it after a quiet period, not a stale quote that could have been hit; the catch-up share and the lag are measured on trades, so they overstate hittable staleness.
* Entry/exit coverage ~15 % of pairs: the paper-trade rows condition on the sibling trading again within 12-18 min; results do not describe siblings that never trade.
* Many large jumps are resolution-time moves (sports finals, daily price brackets) where siblings resolve within seconds; these were not excluded because the rules did not say to.
* Families only include markets that traded in 2025; a never-traded member is invisible. Up/down markets and markets with < 20 fills were not looked up. Ladder detection is template-based and conservative (date × threshold grids are dropped; sports O/U ladders are not identified).
* Last-trade price on one side of the book includes bid-ask bounce: 3-pt "jumps" in wide-spread leaders can be bounce, which the burst variant does not remove.
* Gamma metadata was fetched on 2026-10-12 for markets that resolved in 2025; event membership is current-state, not point-in-time.
* The test half ran once; the leader/sibling/jump definitions are not tuned, and 6 kinds × 3 Δ × 2 fees are reported without multiplicity correction (none passes, so correction would not change the verdict).
