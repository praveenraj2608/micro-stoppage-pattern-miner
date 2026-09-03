"""E2: messy / shorthand / multilingual note variants unify to one canonical cause;
truly unmappable notes go to the review queue, not silently dropped."""
from helpers import frame, stoppage

from src.config import load_config
from src.detect import detect_stoppages
from src.normalize import (UNMAPPED, classify_note, normalize_stoppages,
                           review_queue)


def test_variants_unify_to_material_jam():
    cfg = load_config()
    for note in ["matl jam again", "material stuck", "jamd", "atasco", "jaam"]:
        assert classify_note(note, cfg) == "material_jam", note


def test_multilingual_misfeed():
    cfg = load_config()
    assert classify_note("alimentacion mala", cfg) == "misfeed"


def test_unmappable_note_goes_to_review_queue():
    cfg = load_config()
    rows = []
    # a note with no cause signal at all
    for i in range(6):
        rows += stoppage("CNC-01", 1000 + i * 400, 40, note="xyzzy random gibberish")
    stops = normalize_stoppages(detect_stoppages(frame(rows), cfg), cfg)
    assert (stops["canonical_cause"] == UNMAPPED).all()
    q = review_queue(stops)
    assert len(q) == 6  # surfaced for humans, not dropped
