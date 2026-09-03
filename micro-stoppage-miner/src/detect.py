"""Stoppage detection from machine-state transitions.

Turns a RUNNING -> STOPPED/IDLE -> RUNNING sequence into a stoppage event with a
duration. Applies a debounce floor so sensor chatter (E3) is not mined as a cause,
and derives time_since_setup (tests the 'frequent setup change' hypothesis).
"""
from __future__ import annotations

import pandas as pd


def detect_stoppages(events: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Return one row per detected stoppage.

    Columns: machine_id, start_ts, end_ts, duration_s, is_micro,
             time_since_setup_min, product_id, customer_id, shift, raw_note
    """
    dcfg = cfg["detection"]
    stopped_states = set(dcfg["stopped_states"])
    running = dcfg["running_state"]
    setup = dcfg["setup_state"]
    floor = dcfg["debounce_floor_s"]
    micro_max = dcfg["micro_max_s"]

    stoppages: list[dict] = []

    for machine, grp in events.groupby("machine_id", sort=False):
        grp = grp.sort_values("ts").reset_index(drop=True)
        last_setup_ts = None
        open_stop = None  # dict describing an in-progress stoppage

        for _, row in grp.iterrows():
            state = row["machine_state"]
            ts = row["ts"]

            if state == setup:
                last_setup_ts = ts
                # A setup implicitly ends any open stoppage without recording it.
                open_stop = None
                continue

            if state in stopped_states:
                if open_stop is None:
                    open_stop = {
                        "machine_id": machine,
                        "start_ts": ts,
                        "product_id": row["product_id"],
                        "customer_id": row["customer_id"],
                        "shift": row["shift"],
                        "raw_note": row["operator_note"],
                        "last_setup_ts": last_setup_ts,
                    }
                # consecutive stopped rows: keep the earliest start, first note
            elif state == running:
                if open_stop is not None:
                    duration = (ts - open_stop["start_ts"]).total_seconds()
                    # E3: ignore sub-floor chatter entirely.
                    if duration >= floor:
                        tss = None
                        if open_stop["last_setup_ts"] is not None:
                            tss = (open_stop["start_ts"]
                                   - open_stop["last_setup_ts"]).total_seconds() / 60.0
                        stoppages.append({
                            "machine_id": open_stop["machine_id"],
                            "start_ts": open_stop["start_ts"],
                            "end_ts": ts,
                            "duration_s": duration,
                            "is_micro": bool(floor <= duration <= micro_max),
                            "time_since_setup_min": tss,
                            "product_id": open_stop["product_id"],
                            "customer_id": open_stop["customer_id"],
                            "shift": open_stop["shift"],
                            "raw_note": open_stop["raw_note"],
                        })
                    open_stop = None
            # other states (e.g. IDLE end-of-shift) close nothing special here

    return pd.DataFrame(stoppages)
