"""E1: missing / empty operator notes must not crash; structured mining still runs."""
from helpers import frame, stoppage

from src.config import load_config
from src.detect import detect_stoppages
from src.ingest import load_events
from src.normalize import UNLABELLED, normalize_stoppages


def test_missing_note_column_is_tolerated():
    cfg = load_config()
    rows = []
    for i in range(8):
        rows += stoppage("CNC-01", 1000 + i * 500, 40, note="")  # all empty notes
    df = frame(rows).drop(columns=["operator_note"])  # column entirely absent

    events = load_events(df)                 # must not raise
    assert "operator_note" in events.columns  # backfilled

    stops = detect_stoppages(events, cfg)
    stops = normalize_stoppages(stops, cfg)
    assert len(stops) == 8
    # empty notes -> UNLABELLED, not an error
    assert (stops["canonical_cause"] == UNLABELLED).all()


def test_pipeline_runs_with_all_empty_notes():
    from src.pipeline import run_pipeline
    cfg = load_config()
    rows = []
    for i in range(10):
        rows += stoppage("CNC-01", 1000 + i * 400, 45, note="")
    result = run_pipeline(frame(rows), cfg)
    # No cause findings possible, but metrics still computed and micro counted.
    assert result["metrics"]["micro_minutes_total"] > 0
    assert result["metrics"]["unlabelled_events"] == 10
    assert result["findings"] == []
