"""E3: sub-floor sensor chatter must be debounced (not mined as a stoppage)."""
from helpers import ev, frame

from src.config import load_config
from src.detect import detect_stoppages


def test_subsecond_flap_is_ignored():
    cfg = load_config()  # debounce_floor_s default = 2
    rows = [
        ev(0, "CNC-01", "RUNNING"),
        ev(100, "CNC-01", "STOPPED", note="blip"),
        ev(101, "CNC-01", "RUNNING"),   # 1s flap -> below floor -> ignored
        ev(200, "CNC-01", "STOPPED", note="real jam"),
        ev(240, "CNC-01", "RUNNING"),   # 40s real stoppage -> kept
    ]
    stops = detect_stoppages(frame(rows), cfg)
    assert len(stops) == 1
    assert stops.iloc[0]["duration_s"] == 40


def test_many_flaps_do_not_inflate_counts():
    cfg = load_config()
    rows = [ev(0, "CNC-01", "RUNNING")]
    t = 50
    for _ in range(20):
        rows.append(ev(t, "CNC-01", "STOPPED", note=""))
        rows.append(ev(t + 1, "CNC-01", "RUNNING"))  # all 1s flaps
        t += 30
    stops = detect_stoppages(frame(rows), cfg)
    assert len(stops) == 0
