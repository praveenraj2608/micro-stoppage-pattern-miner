"""E4: a brand-new product/customer with too little history must NOT produce a
fabricated pattern — the miner abstains below the min-events threshold."""
from helpers import frame, stoppage

from src.config import load_config
from src.pipeline import run_pipeline


def test_cold_start_abstains():
    cfg = load_config()
    # Only 3 events for a brand-new product -> below min_events_for_cause (5).
    rows = []
    for i in range(3):
        rows += stoppage("CNC-09", 1000 + i * 400, 40, note="jam",
                         product="P-NEW", shift="A")
    result = run_pipeline(frame(rows), cfg)
    assert result["findings"] == []  # no fabricated cause


def test_enough_history_does_surface():
    cfg = load_config()
    rows = []
    # A strong, recurring jam pattern on CNC-02 / P-4471 / shift A.
    for i in range(20):
        rows += stoppage("CNC-02", 1000 + i * 300, 50, note="material jam",
                         product="P-4471", shift="A")
    # Background variety on other assets/causes so the pattern has contrast
    # (association lift is only meaningful relative to a base rate).
    for i in range(20):
        rows += stoppage("PRESS-01", 2000 + i * 300, 30,
                         note=["sensor trip", "tool worn", "misfeed", "quality check"][i % 4],
                         product="P-8810", shift="B")
    result = run_pipeline(frame(rows), cfg)
    assert any(f["cause"] == "material_jam" for f in result["findings"])
