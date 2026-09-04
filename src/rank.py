"""Ranking & explanation.

Turns mined rules into ranked, explainable Finding dicts. Ranking uses
impact = recoverable_minutes * confidence so a rare-but-costly cause (E5) is not
buried under many trivial ones. Each finding carries its evidence, example notes,
a plain-language explanation, and a suggested corrective action.
"""
from __future__ import annotations

import pandas as pd

# Cause -> a sensible default corrective-action hint.
ACTION_HINTS = {
    "material_jam": "Review fixture/feed setup sheet and material presentation for this product.",
    "misfeed": "Check feeder alignment and infeed settings during setup validation.",
    "sensor_fault": "Clean/realign the photoeye and add it to the changeover checklist.",
    "tool_change": "Review tool life for this product; pre-stage tooling before the run.",
    "material_out": "Adjust material replenishment timing / hopper level alerts.",
    "operator_adjust": "Standardise the first-off adjustment into the setup procedure.",
    "temperature": "Verify cooling / warm-up step in the setup for this product.",
    "quality_check": "Move the quality check off the critical path or automate the gate.",
}

CAUSE_LABEL = {
    "material_jam": "material jam",
    "misfeed": "misfeed",
    "sensor_fault": "sensor fault",
    "tool_change": "tool change / wear",
    "material_out": "material runout",
    "operator_adjust": "manual adjustment",
    "temperature": "temperature issue",
    "quality_check": "quality check stop",
}


def _pretty_context(context_items: list[str]) -> str:
    parts = []
    labels = {"machine": "machine", "product": "product", "customer": "customer",
              "shift": "shift", "tss": "within"}
    for item in context_items:
        key, val = item.split("=", 1)
        if key == "tss":
            parts.append(f"{val} of setup" if val != "unknown" else "unknown time-since-setup")
        else:
            parts.append(f"{labels.get(key, key)} {val}")
    return ", ".join(parts)


def build_findings(rules: pd.DataFrame, cfg: dict) -> list[dict]:
    """Return ranked findings (list of dicts)."""
    if rules is None or rules.empty:
        return []

    findings = []
    for _, r in rules.iterrows():
        impact = round(float(r["recoverable_min"]) * float(r["confidence"]), 1)
        cause_label = CAUSE_LABEL.get(r["cause"], r["cause"])
        ctx = _pretty_context(r["context_items"])
        plain = (
            f"{cause_label.capitalize()} recurs for {ctx} — "
            f"{r['events']} micro-stoppages, ~{r['recoverable_min']} min lost "
            f"(confidence {int(r['confidence']*100)}%, {r['lift']}x more likely than baseline)."
        )
        findings.append({
            "cause": r["cause"],
            "cause_label": cause_label,
            "context": r["context"],
            "events": int(r["events"]),
            "recoverable_min": float(r["recoverable_min"]),
            "support": float(r["support"]),
            "confidence": float(r["confidence"]),
            "lift": float(r["lift"]),
            "impact": impact,
            "example_notes": list(r.get("example_notes", []) or []),
            "plain_language": plain,
            "suggested_action": ACTION_HINTS.get(r["cause"], "Investigate and root-cause."),
        })

    findings.sort(key=lambda f: f["impact"], reverse=True)
    for i, f in enumerate(findings, 1):
        f["rank"] = i
    return findings
