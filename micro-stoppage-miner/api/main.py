"""FastAPI service exposing the micro-stoppage miner as REST endpoints.

Endpoints:
  GET  /health                    liveness
  POST /run                       run the pipeline on the configured/synthetic data
  POST /ingest                    load a CSV path into the store and run
  GET  /findings                  ranked, explainable findings (latest run)
  POST /findings/{id}/verify      record a verify/reject decision + action
  GET  /baseline                  baseline results for comparison
  GET  /metrics                   hidden-downtime -> verified-action conversion
"""
from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException

from src.config import resolve_path
from src.pipeline import run_pipeline

from .deps import get_config, get_store
from .schemas import (ConversionMetric, Finding, RunResponse, VerifyRequest)

app = FastAPI(
    title="Micro-Stoppage Pattern Miner",
    description="Links short interruptions to recurring causes for a contract manufacturer.",
    version="1.0.0",
)

# Keep the last run's baseline in memory for the /baseline endpoint.
_last_baseline: dict = {}


@app.get("/health")
def health():
    return {"status": "ok"}


def _run(source) -> RunResponse:
    global _last_baseline
    cfg = get_config()
    store = get_store()
    result = run_pipeline(source, cfg)

    run_id = uuid.uuid4().hex[:8]
    store.reset()  # pilot: one active run at a time for a clean dashboard
    ids = store.save_findings(run_id, result["findings"])
    for f, fid in zip(result["findings"], ids):
        f["finding_id"] = fid
    store.save_metrics(run_id, result["metrics"])
    _last_baseline = result["baseline"]

    return RunResponse(
        run_id=run_id,
        micro_count=result["micro_count"],
        metrics=result["metrics"],
        findings=[Finding(**f) for f in store.get_findings(run_id)],
    )


@app.post("/run", response_model=RunResponse)
def run():
    """Run on the default synthetic events CSV."""
    cfg = get_config()
    path = resolve_path(cfg["paths"]["events_csv"])
    if not path.exists():
        raise HTTPException(404, f"Events file not found: {path}. Generate data first.")
    return _run(str(path))


@app.post("/ingest", response_model=RunResponse)
def ingest(csv_path: str):
    """Ingest an arbitrary CSV path and run the pipeline."""
    from pathlib import Path
    if not Path(csv_path).exists():
        raise HTTPException(404, f"CSV not found: {csv_path}")
    return _run(csv_path)


@app.get("/findings", response_model=list[Finding])
def findings():
    store = get_store()
    run_id = store.latest_run_id()
    if not run_id:
        return []
    return [Finding(**f) for f in store.get_findings(run_id)]


@app.post("/findings/{finding_id}/verify")
def verify(finding_id: int, body: VerifyRequest):
    if body.decision not in ("verified", "rejected"):
        raise HTTPException(400, "decision must be 'verified' or 'rejected'")
    store = get_store()
    store.verify(finding_id, body.decision, body.verified_by,
                 body.action_owner, body.action_text)
    return {"finding_id": finding_id, "decision": body.decision}


@app.get("/baseline")
def baseline():
    return _last_baseline or {"note": "run the pipeline first"}


@app.get("/metrics", response_model=ConversionMetric)
def metrics():
    store = get_store()
    return ConversionMetric(**store.conversion_metric())
