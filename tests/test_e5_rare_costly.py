"""E5: a rare-but-costly cause must out-rank frequent-but-trivial ones because
ranking uses impact (recoverable minutes x confidence), not raw event count."""
from helpers import frame, stoppage

from src.config import load_config
from src.pipeline import run_pipeline


def test_rare_costly_outranks_frequent_trivial():
    cfg = load_config()
    rows = []
    # Frequent trivial: 30 x 15s idles on PACK-01 / P-2200 / shift C
    for i in range(30):
        rows += stoppage("PACK-01", 1000 + i * 200, 15, note="quality check",
                         product="P-2200", shift="C")
    # Rare costly: 8 x 280s tool changes on CNC-01 / P-4472 / shift A
    for i in range(8):
        rows += stoppage("CNC-01", 1000 + i * 600, 280, note="tool worn",
                         product="P-4472", shift="A")

    result = run_pipeline(frame(rows), cfg)
    findings = result["findings"]
    assert findings, "expected findings"
    # The #1 ranked finding should be the costly tool-change, not the trivial idle.
    top = findings[0]
    assert top["cause"] == "tool_change"
    # And its recoverable minutes should exceed the trivial cause's.
    trivial = next((f for f in findings if f["cause"] == "quality_check"), None)
    if trivial:
        assert top["recoverable_min"] > trivial["recoverable_min"]
