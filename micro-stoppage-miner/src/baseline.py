"""Simple baseline = current shop-floor practice.

(1) Micro-stoppage time reported as ONE lumped bucket (no cause visibility).
(2) Verbatim operator-note counts with NO variant unification and NO context.

This is what the prototype must beat: the baseline cannot attribute downtime to a
recurring cause because it neither unifies note variants nor uses context.
"""
from __future__ import annotations

import pandas as pd


def run_baseline(stoppages: pd.DataFrame) -> dict:
    if stoppages.empty:
        return {"total_micro_min": 0.0, "lumped_bucket_min": 0.0,
                "verbatim_note_counts": {}, "attributed_min": 0.0,
                "pct_attributed": 0.0, "causes_surfaced": 0}

    micro = stoppages[stoppages["is_micro"]]
    total_min = float(micro["duration_s"].sum()) / 60.0

    # Verbatim counting: raw note strings, no unification. Empty notes excluded.
    notes = micro["raw_note"].astype(str).str.strip()
    notes = notes[notes != ""]
    counts = notes.value_counts().to_dict()

    # The baseline "attributes" nothing to a *recurring cause*: every distinct raw
    # string is treated as its own one-off. It reports a lump total only.
    return {
        "total_micro_min": round(total_min, 1),
        "lumped_bucket_min": round(total_min, 1),
        "verbatim_note_counts": {k: int(v) for k, v in list(counts.items())[:15]},
        "distinct_raw_notes": int(len(counts)),
        "attributed_min": 0.0,       # no recurring-cause attribution possible
        "pct_attributed": 0.0,
        "causes_surfaced": 0,
    }
