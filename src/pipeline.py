"""End-to-end pipeline: ingest -> detect -> normalize -> mine -> rank -> attribute.

Framework-agnostic. The FastAPI layer and the CLI both call run_pipeline().
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .baseline import run_baseline
from .config import load_config
from .detect import detect_stoppages
from .ingest import load_events
from .mine import _tss_bucket, mine_patterns
from .normalize import UNLABELLED, UNMAPPED, normalize_stoppages, review_queue
from .rank import build_findings


def _attribution_mask(micro: pd.DataFrame, findings: list[dict]) -> pd.Series:
    """Micro events explained by a surfaced recurring cause.

    A verified recurring cause explains ALL its occurrences on the same asset /
    product, not only those in the finding's tight context window. So we attribute
    an event when a finding shares its cause AND its machine (or its product).
    """
    if micro.empty or not findings:
        return pd.Series(False, index=micro.index)

    mask = pd.Series(False, index=micro.index)
    for f in findings:
        dims = {}
        for item in [c.strip() for c in f["context"].split(",") if c.strip()]:
            k, v = item.split("=", 1)
            dims[k] = v
        cause_mask = micro["canonical_cause"] == f["cause"]
        if "machine" in dims:
            mask |= cause_mask & (micro["machine_id"].astype(str) == dims["machine"])
        if "product" in dims:
            mask |= cause_mask & (micro["product_id"].astype(str) == dims["product"])
    return mask


def run_pipeline(source, cfg: dict | None = None) -> dict:
    """Run the whole pipeline on a CSV path or DataFrame. Returns a result dict."""
    cfg = cfg or load_config()
    edges = cfg["mining"]["time_since_setup_buckets_min"]

    events = load_events(source)
    stoppages = detect_stoppages(events, cfg)
    stoppages = normalize_stoppages(stoppages, cfg)

    rules = mine_patterns(stoppages, cfg)
    findings = build_findings(rules, cfg)
    baseline = run_baseline(stoppages)
    queue = review_queue(stoppages)

    micro = stoppages[stoppages["is_micro"]] if not stoppages.empty else stoppages
    total_micro_min = float(micro["duration_s"].sum()) / 60.0 if not micro.empty else 0.0

    # Attribution: micro events explained by a surfaced recurring cause.
    attributed_mask = _attribution_mask(micro, findings) if not micro.empty else pd.Series(dtype=bool)
    minutes_attributed = (
        float(micro.loc[attributed_mask, "duration_s"].sum()) / 60.0
        if not micro.empty else 0.0
    )
    pct_attributed = (minutes_attributed / total_micro_min * 100.0) if total_micro_min else 0.0

    # Counting of edge conditions for transparency.
    n_unlabelled = int((micro["canonical_cause"] == UNLABELLED).sum()) if not micro.empty else 0
    n_unmapped = int((micro["canonical_cause"] == UNMAPPED).sum()) if not micro.empty else 0

    return {
        "events": events,
        "stoppages": stoppages,
        "micro_count": int(len(micro)),
        "findings": findings,
        "baseline": baseline,
        "review_queue": queue,
        "metrics": {
            "micro_minutes_total": round(total_micro_min, 1),
            "minutes_attributed": round(minutes_attributed, 1),
            "pct_attributed": round(pct_attributed, 1),
            "causes_surfaced": len(findings),
            "unlabelled_events": n_unlabelled,
            "unmapped_events": n_unmapped,
        },
    }
