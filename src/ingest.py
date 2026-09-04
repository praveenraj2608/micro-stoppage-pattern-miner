"""Ingestion & validation. E1-safe: missing operator notes are allowed."""
from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = [
    "ts", "machine_id", "machine_state", "product_id",
    "customer_id", "shift",
]
# operator_note is optional (E1) — filled with "" if absent.


class SchemaError(ValueError):
    """Raised when a structurally required column is missing."""


def load_events(source) -> pd.DataFrame:
    """Load events from a CSV path or an existing DataFrame; validate & clean.

    - Enforces required structural columns (raises SchemaError otherwise).
    - Tolerates a missing/empty operator_note column (E1).
    - Parses timestamps and sorts per machine.
    """
    if isinstance(source, pd.DataFrame):
        df = source.copy()
    else:
        df = pd.read_csv(source)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SchemaError(f"Missing required columns: {missing}")

    if "operator_note" not in df.columns:
        df["operator_note"] = ""
    df["operator_note"] = df["operator_note"].fillna("").astype(str)

    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    bad_ts = df["ts"].isna().sum()
    if bad_ts:
        df = df.dropna(subset=["ts"])
    for col in ["machine_id", "machine_state", "product_id", "customer_id", "shift"]:
        df[col] = df[col].astype(str)

    df = df.sort_values(["machine_id", "ts"]).reset_index(drop=True)
    df.attrs["dropped_bad_timestamps"] = int(bad_ts)
    return df
