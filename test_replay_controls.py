"""Run: /opt/anaconda3/bin/python3 -m pytest -q test_replay_controls.py"""
import numpy as np
import replay_controls as C

DAY = 86400

def test_wrong_post_draw():
    ev_t0 = np.arange(0, 60 * DAY, 2 * DAY)          # 30 events, 2 days apart
    pairs = [0, 0, 5, 29, 14, 14]                    # includes repeated pair events
    w = C.draw_wrong(pairs, ev_t0, seed=0)
    assert w == C.draw_wrong(pairs, ev_t0, seed=0)   # seeded: reproducible
    assert w != C.draw_wrong(pairs, ev_t0, seed=1)   # and seed matters
    for e, x in zip(pairs, w):
        assert x != e                                # never the pair's own event
        assert abs(ev_t0[x] - ev_t0[e]) >= 7 * DAY   # at least 7 days away

def test_wrong_post_boundary_and_no_candidate():
    ev_t0 = np.array([0, 7 * DAY - 1, 7 * DAY, 100 * DAY])
    assert set(C.draw_wrong([0] * 200, ev_t0, seed=0)) == {2, 3}   # exactly 7 d is allowed, 7 d - 1 s is not
    try: C.draw_wrong([0], np.array([0, 3 * DAY]))
    except ValueError: pass
    else: raise AssertionError("expected ValueError")

def test_control1_prompt_has_no_post_or_slots(monkeypatch):
    for a in ("CACHE", "PROMPT_MD", "SYSTEM", "user_message"): monkeypatch.setattr(C.L, a, getattr(C.L, a))   # restored after the test
    C.set_prompt("c1")
    msg = C.L.user_message("SECRET POST", "will-china-tariff-hit-60")
    assert msg == "Market: will china tariff hit 60\nAnswer (up, down or none):" and "SECRET" not in msg
    assert "{" not in C.L.SYSTEM and "none" in C.L.SYSTEM and C.L.CACHE.endswith("controls_c1_dirs.jsonl")

def test_forced_choice_never_coerces_to_direction(monkeypatch):
    for a in ("CACHE", "PROMPT_MD", "SYSTEM", "user_message", "parse_dir"): monkeypatch.setattr(C.L, a, getattr(C.L, a))
    assert C.parse_updown("Up.") == 1 and C.parse_updown(" DOWN\n") == -1
    for bad in ["none", "None.", "", None, "up or down", "upward", "I think up", "up\ndown", "neither"]:
        assert C.parse_updown(bad) is None
    C.set_prompt("c3")
    assert C.L.parse_dir("none") is None and C.L.parse_dir("up") == 1   # the patched parser is the one get_dirs uses
    assert "none" not in C.L.SYSTEM.lower().replace("up or down", "") and C.L.CACHE.endswith("controls_c3_dirs.jsonl")
    assert C.L.user_message("SECRET", "will-x-happen") == "Market: will x happen\nAnswer (up or down):"
