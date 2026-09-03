"""Pydantic request/response models for the FastAPI layer."""
from __future__ import annotations

from pydantic import BaseModel


class Finding(BaseModel):
    finding_id: int | None = None
    rank: int | None = None
    cause: str
    cause_label: str
    context: str
    events: int
    recoverable_min: float
    support: float
    confidence: float
    lift: float
    impact: float
    example_notes: list[str] = []
    plain_language: str
    suggested_action: str
    verification: dict | None = None


class Metrics(BaseModel):
    micro_minutes_total: float
    minutes_attributed: float
    pct_attributed: float
    causes_surfaced: int
    unlabelled_events: int
    unmapped_events: int


class RunResponse(BaseModel):
    run_id: str
    micro_count: int
    metrics: Metrics
    findings: list[Finding]


class VerifyRequest(BaseModel):
    decision: str  # 'verified' | 'rejected'
    verified_by: str = ""
    action_owner: str = ""
    action_text: str = ""


class ConversionMetric(BaseModel):
    total_findings: int
    verified_actions: int
    verified_recoverable_min: float
    total_recoverable_min: float
