"""Pattern mining engine.

Mines recurring cause patterns from micro-stoppages using association-rule mining
over context (machine, product, customer, shift, time-since-setup bucket) -> cause.
Produces rules with support / confidence / lift. Enforces the cold-start guard (E4).
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import association_rules, fpgrowth
from mlxtend.preprocessing import TransactionEncoder

# mlxtend's optional 'certainty' metric divides by zero on degenerate rules; benign.
warnings.filterwarnings("ignore", message="invalid value encountered in divide")

from .normalize import UNLABELLED, UNMAPPED


def _tss_bucket(minutes, edges) -> str:
    if minutes is None or (isinstance(minutes, float) and np.isnan(minutes)):
        return "tss=unknown"
    for i in range(len(edges) - 1):
        if edges[i] <= minutes < edges[i + 1]:
            return f"tss={edges[i]}-{edges[i+1]}min"
    return f"tss={edges[-1]}min+"


def _to_transactions(micro: pd.DataFrame, edges) -> list[list[str]]:
    txns = []
    for _, r in micro.iterrows():
        items = [
            f"cause={r['canonical_cause']}",
            f"machine={r['machine_id']}",
            f"product={r['product_id']}",
            f"customer={r['customer_id']}",
            f"shift={r['shift']}",
            _tss_bucket(r["time_since_setup_min"], edges),
        ]
        txns.append(items)
    return txns


def mine_patterns(stoppages: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Return candidate rules: context -> cause, with support/confidence/lift/impact.

    Only micro-stoppages with a real (mapped) cause feed the miner; UNLABELLED /
    UNMAPPED events are excluded from cause rules but their minutes are still counted
    elsewhere for attribution accounting.
    """
    mcfg = cfg["mining"]
    edges = mcfg["time_since_setup_buckets_min"]
    empty = pd.DataFrame(columns=[
        "cause", "context", "events", "recoverable_min", "support",
        "confidence", "lift",
    ])
    if stoppages.empty:
        return empty

    micro = stoppages[stoppages["is_micro"]].copy()
    micro = micro[~micro["canonical_cause"].isin([UNLABELLED, UNMAPPED])]
    if len(micro) < mcfg["min_events_for_cause"]:
        return empty

    txns = _to_transactions(micro, edges)
    te = TransactionEncoder()
    arr = te.fit_transform(txns)
    onehot = pd.DataFrame(arr, columns=te.columns_)

    try:
        freq = fpgrowth(onehot, min_support=mcfg["min_support"], use_colnames=True)
    except Exception:
        return empty
    if freq.empty:
        return empty

    rules = association_rules(freq, metric="confidence",
                             min_threshold=mcfg["min_confidence"])
    if rules.empty:
        return empty

    def only_cause(items) -> bool:
        items = list(items)
        return len(items) == 1 and items[0].startswith("cause=")

    def no_cause(items) -> bool:
        return all(not i.startswith("cause=") for i in items)

    mask = (
        rules["consequents"].apply(only_cause)
        & rules["antecedents"].apply(no_cause)
        & (rules["lift"] >= mcfg["min_lift"])
    )
    rules = rules[mask].copy()
    if rules.empty:
        return empty

    # Build a candidate per rule, capturing the exact set of events it matches.
    candidates = []
    for _, r in rules.iterrows():
        cause = list(r["consequents"])[0].split("=", 1)[1]
        context_items = sorted(r["antecedents"])
        # Filter the micro data to events matching this rule to sum real minutes.
        sub = micro[micro["canonical_cause"] == cause]
        for item in context_items:
            key, val = item.split("=", 1)
            colmap = {"machine": "machine_id", "product": "product_id",
                      "customer": "customer_id", "shift": "shift"}
            if key in colmap:
                sub = sub[sub[colmap[key]].astype(str) == val]
            elif key == "tss":
                sub = sub[sub["time_since_setup_min"].apply(
                    lambda m: _tss_bucket(m, edges) == item)]
        idx_set = frozenset(sub.index.tolist())
        if not idx_set:
            continue
        candidates.append({
            "cause": cause,
            "context": ", ".join(context_items),
            "context_items": context_items,
            "idx_set": idx_set,
            "events": int(len(sub)),
            "recoverable_min": round(float(sub["duration_s"].sum()) / 60.0, 1),
            "support": round(float(r["support"]), 4),
            "confidence": round(float(r["confidence"]), 3),
            "lift": round(float(r["lift"]), 2),
            "specificity": len(context_items),
            "example_notes": sub["raw_note"].replace("", np.nan).dropna().unique()[:3].tolist(),
        })

    consolidated = _consolidate(candidates, cfg)
    if not consolidated:
        return empty
    result = pd.DataFrame(consolidated).drop(columns=["idx_set", "specificity"])
    return result.reset_index(drop=True)


def _consolidate(candidates: list[dict], cfg: dict) -> list[dict]:
    """Collapse redundant association rules into distinct, high-quality findings.

    Association-rule mining emits every context subset, so one real pattern appears
    as many overlapping rules. We keep, per cause, the tightest/highest-confidence
    representative of each largely-distinct event cluster and drop the rest.
    """
    mcfg = cfg["mining"]
    overlap_max = mcfg.get("consolidation_overlap", 0.3)
    min_report_events = mcfg.get("min_report_events", 5)

    # Prefer specific, high-confidence, high-lift, high-impact rules first.
    candidates.sort(
        key=lambda c: (c["confidence"], c["lift"], c["specificity"],
                       c["recoverable_min"]),
        reverse=True,
    )

    accepted: list[dict] = []
    covered_by_cause: dict[str, set] = {}
    for c in candidates:
        if c["events"] < min_report_events:
            continue
        cov = covered_by_cause.setdefault(c["cause"], set())
        overlap = len(c["idx_set"] & cov) / len(c["idx_set"])
        if overlap < overlap_max:
            accepted.append(c)
            cov |= set(c["idx_set"])
    return accepted
