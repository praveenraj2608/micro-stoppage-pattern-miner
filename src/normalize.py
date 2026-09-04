"""Operator-note normalization (the language layer).

Maps messy / shorthand / multilingual free-text notes to a canonical cause
vocabulary. Handles E1 (empty note -> UNLABELLED) and E2 (variants unified;
truly unmappable non-empty notes routed to a review queue, never dropped).
"""
from __future__ import annotations

import re

import pandas as pd
from rapidfuzz import fuzz

UNLABELLED = "UNLABELLED"      # note was empty/missing (E1)
UNMAPPED = "UNMAPPED"          # note present but not matched -> review queue (E2)


def _clean(text: str, abbreviations: dict) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)  # strip punctuation; keep unicode-stripped ascii
    tokens = [abbreviations.get(t, t) for t in text.split()]
    return " ".join(tokens)


def classify_note(note: str, cfg: dict) -> str:
    """Return a canonical cause for a single note."""
    ncfg = cfg["normalize"]
    if note is None or str(note).strip() == "":
        return UNLABELLED

    cleaned = _clean(str(note), ncfg["abbreviations"])
    if not cleaned:
        return UNLABELLED

    threshold = ncfg["fuzzy_threshold"]
    best_cause = None
    best_score = 0

    for cause, keywords in ncfg["cause_keywords"].items():
        for kw in keywords:
            kw_l = kw.lower()
            # direct substring hit is a strong, cheap signal
            if kw_l in cleaned:
                score = 100
            else:
                # token-level fuzzy match against each word
                score = max(
                    (fuzz.ratio(kw_l, tok) for tok in cleaned.split()),
                    default=0,
                )
            if score > best_score:
                best_score, best_cause = score, cause

    if best_cause is not None and best_score >= threshold:
        return best_cause
    return UNMAPPED


def normalize_stoppages(stoppages: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Add a canonical_cause column to the stoppage table."""
    df = stoppages.copy()
    if df.empty:
        df["canonical_cause"] = []
        return df
    df["canonical_cause"] = df["raw_note"].apply(lambda n: classify_note(n, cfg))
    return df


def review_queue(stoppages: pd.DataFrame) -> pd.DataFrame:
    """Notes that were present but could not be mapped (for human review)."""
    if stoppages.empty or "canonical_cause" not in stoppages.columns:
        return stoppages.iloc[0:0]
    return stoppages[stoppages["canonical_cause"] == UNMAPPED].copy()
