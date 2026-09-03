"""Shared test helpers: build small event logs by hand."""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

BASE = datetime(2026, 7, 1, 7, 0, 0)


def ev(offset_s, machine, state, product="P-1", customer="CustA", shift="A", note=""):
    return {
        "ts": BASE + timedelta(seconds=offset_s),
        "machine_id": machine,
        "machine_state": state,
        "product_id": product,
        "customer_id": customer,
        "shift": shift,
        "operator_note": note,
    }


def stoppage(machine, at_s, dur_s, note="", product="P-1", shift="A", setup_before=None):
    """Return the event rows for one stoppage (optionally preceded by a SETUP)."""
    rows = []
    if setup_before is not None:
        rows.append(ev(at_s - setup_before, machine, "SETUP", product, shift=shift))
        rows.append(ev(at_s - setup_before + 60, machine, "RUNNING", product, shift=shift))
    else:
        rows.append(ev(at_s - 5, machine, "RUNNING", product, shift=shift))
    rows.append(ev(at_s, machine, "STOPPED", product, shift=shift, note=note))
    rows.append(ev(at_s + dur_s, machine, "RUNNING", product, shift=shift))
    return rows


def frame(rows):
    return pd.DataFrame(rows)
