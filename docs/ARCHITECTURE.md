# System Architecture
## Micro-Stoppage Pattern Miner

**Version:** 1.0 · **Date:** 2026-08-18 · **Owner:** Praveen Raj
**Related:** [PRD](./PRD.md) · [Implementation Plan](./IMPLEMENTATION_PLAN.md)

---

## 1. Architectural Goals & Constraints

| Driver | Decision |
|---|---|
| Low-cost / simulated infra (mandated) | 100% open-source Python stack; single-laptop; SQLite; no cloud |
| Diagnostic, not real-time | Batch pipeline over event logs behind a **FastAPI** service; leave a streaming adapter seam |
| Clean integration seam for real MES/PLC | **FastAPI** backend exposes the pipeline as REST endpoints; **Streamlit** is a thin client on top |
| Explainability is a requirement, not a feature | Prefer transparent methods (rules, TF-IDF, interpretable clustering) over opaque models; every output carries its evidence |
| High-mix masks patterns | Context-aware mining (product × customer × shift × machine × time-since-setup) |
| Messy/multilingual notes | Dedicated normalization layer between capture and mining |
| Must beat a baseline | Baseline module runs the same I/O for apples-to-apples comparison |

**Design principle:** *transparent by default.* We only reach for heavier ML (embeddings) when simple, explainable methods (normalization + association rules) leave signal on the table — and we document why (see §7, "Why this approach").

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES (simulated)                        │
│   Machine state log · Operator notes · Product/Customer · Shift        │
│   ── real seam: MES / PLC / SCADA / CMMS adapter (future) ──           │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │  CSV / SQLite
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  1. INGESTION & VALIDATION                                             │
│     schema check · type coercion · missing-field handling (E1)         │
└───────────────────────────────┬──────────────────────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  2. EVENT DETECTION                                                    │
│     state-transition → stoppage events · debounce chatter (E3)         │
│     derive duration · is_micro_stoppage · time_since_setup             │
└───────────────────────────────┬──────────────────────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  3. NOTE NORMALIZATION (language layer)                                │
│     clean · translate/transliterate · fuzzy + synonym map →           │
│     canonical_cause · unmapped → review queue (E2)                     │
└───────────────────────────────┬──────────────────────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  4. PATTERN MINING ENGINE                                             │
│     A. Cause clustering (TF-IDF/embeddings on notes)                   │
│     B. Association-rule mining (FP-Growth/Apriori) over context        │
│     C. Impact scoring = recoverable_minutes × confidence              │
│     cold-start guard (E4) · impact-rank not count-rank (E5)           │
└───────────────────────────────┬──────────────────────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  5. RANKING & EXPLANATION                                             │
│     ranked findings + evidence + example notes + plain-language reason │
│     + suggested corrective action                                      │
└───────────────────────────────┬──────────────────────────────────────┘
                    ┌────────────┴─────────────┐
                    ▼                           ▼
┌───────────────────────────┐   ┌──────────────────────────────────────┐
│  6a. BASELINE MODULE       │   │  6b. FastAPI SERVICE (REST)          │
│  raw bucket + verbatim     │   │  /ingest /run /findings /verify       │
│  note counts (comparison)  │   │  /metrics /baseline · OpenAPI docs    │
└───────────────────────────┘   └───────────────┬──────────────────────┘
                                                 ▼
                                 ┌──────────────────────────────────────┐
                                 │  6c. DASHBOARD (Streamlit client)    │
                                 │  calls FastAPI · findings · verify/   │
                                 │  reject · accessibility-checked·export│
                                 └───────────────┬──────────────────────┘
                                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│  7. VERIFICATION & METRICS STORE (SQLite)                             │
│     human verify decisions · corrective actions · hidden-downtime→     │
│     verified-action conversion metric · trend over time               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Detail

### 3.1 Ingestion & Validation
- Reads CSV / SQLite; enforces the schema in [PRD §4](./PRD.md#4-data-requirements).
- Coerces types, parses timestamps, sorts per machine.
- **E1 handling:** missing `operator_note` is allowed and flagged, never fatal; missing structural fields raise a clear validation error.

### 3.2 Event Detection
- Walks each machine's state timeline; a stoppage = `RUNNING → (STOPPED/IDLE) → RUNNING`.
- Computes `stoppage_duration_s`; flags `is_micro_stoppage` within the configurable band (default `debounce_floor ≤ d ≤ 300s`).
- **E3 debounce:** transitions shorter than the floor (default 2s) are treated as sensor chatter and merged/ignored.
- Computes `time_since_setup` from the last `SETUP` state — the feature that tests the "frequent setup change" hypothesis.

### 3.3 Note Normalization (language layer)
Pipeline, cheapest step first:
1. **Clean:** lowercase, strip punctuation, expand shorthand via abbreviation map (`matl→material`, `jamd→jam`).
2. **Language:** detect + transliterate/translate non-English tokens against a small extensible glossary (e.g., `atasco→jam`). Offline dictionary first; optional model only if available.
3. **Map to canonical cause:** fuzzy match (RapidFuzz) + synonym dictionary → `canonical_cause`.
4. **Fallback:** unmapped notes go to a **review queue** (E2), never silently dropped; they still carry structural context to the miner as `cause=UNLABELLED`.

### 3.4 Pattern Mining Engine
- **A. Cause clustering:** TF-IDF vectors over normalized notes → clustering to catch variants the synonym map missed. Embedding-based clustering is a drop-in upgrade *only if* it measurably improves precision (documented trade-off).
- **B. Association-rule mining:** FP-Growth / Apriori over transactions of `{canonical_cause, machine, product, customer, shift, time_since_setup_bucket}` → rules with **support, confidence, lift** (e.g., *"{product=P-4471, shift=changeover} ⇒ cause=material-jam"*, lift 3.2).
- **C. Impact scoring:** `impact = recoverable_minutes × confidence`, where recoverable_minutes = summed duration of events matching the rule.
- **E4 cold-start guard:** rules below a support threshold for new product/customer return "insufficient history" rather than a fabricated pattern.
- **E5:** ranking uses impact minutes, so a rare 4-min recurring jam outranks many trivial 20s idles.

### 3.5 Ranking & Explanation
Each finding is a structured, explainable object:
```
Finding
  ├─ canonical_cause: "material jam"
  ├─ context:         product=P-4471, shift=A, machine=CNC-02, within 30min of setup
  ├─ evidence:        events=38, total=27.4 min, support=0.06, confidence=0.71, lift=3.2
  ├─ example_notes:   ["matl jam again", "material stuck", "atasco"]
  ├─ plain_language:  "Product P-4471 jams on CNC-02 soon after setup on Shift A —
  │                    ~27 min/week lost. Likely a setup/fixture issue."
  ├─ recoverable_min: 27.4
  └─ suggested_action:"Review CNC-02 fixture/feed settings in the P-4471 setup sheet."
```

### 3.6 Baseline Module
Same input/output contract; produces (a) one lumped downtime total and (b) verbatim note-string counts with no variant unification and no context. Enables the mandated side-by-side comparison.

### 3.7 FastAPI Service (backend)
Exposes the pipeline as a REST API — the integration seam for both the Streamlit client and any future MES/PLC/dashboard consumer. Auto-generated OpenAPI/Swagger docs give an explorable contract.

| Endpoint | Method | Purpose |
|---|---|---|
| `/ingest` | POST | Load a CSV/dataset into the store (validation, E1-safe) |
| `/run` | POST | Execute detect → normalize → mine → rank for a run |
| `/findings` | GET | Ranked, explainable findings (with evidence + example notes) |
| `/findings/{id}/verify` | POST | Record a verify/reject decision + corrective action |
| `/baseline` | GET | Baseline results for comparison |
| `/metrics` | GET | Hidden-downtime → verified-action conversion + trend |
| `/health` | GET | Liveness for the pilot |

- Pydantic models enforce request/response schemas (the `Finding` object of §3.5 is a Pydantic model).
- Business logic lives in `src/` modules; FastAPI is a thin transport layer over them, so the pipeline stays testable without the web server.

### 3.8 Dashboard (Streamlit client)
- Thin client that calls the FastAPI endpoints (no business logic of its own).
- Ranked findings; drill-down to evidence and example notes.
- **Verify / Reject** control calls `/findings/{id}/verify` — this is the gate that converts hidden downtime into a *verified* corrective action.
- Accessibility-checked (contrast, non-colour-only encoding, keyboard nav, screen-reader labels, legible sizes).
- Export findings (CSV/PDF).

### 3.9 Verification & Metrics Store (SQLite)
Persists verify/reject decisions, assigned corrective actions, and the running **hidden-downtime → verified-action** conversion metric and its trend.

---

## 4. Data Model (SQLite)

```
raw_events(event_id, ts, machine_id, machine_state, product_id, customer_id,
           shift, operator_note)

stoppages(stoppage_id, machine_id, start_ts, end_ts, duration_s,
          is_micro, time_since_setup_min, product_id, customer_id, shift,
          raw_note, canonical_cause)

findings(finding_id, canonical_cause, context_json, events, total_minutes,
         support, confidence, lift, recoverable_min, suggested_action, run_id)

verifications(finding_id, decision, verified_by, action_owner,
              action_text, decided_at)

metrics(run_id, ts, micro_minutes_total, minutes_attributed,
        pct_attributed, precision, recall, verified_actions,
        verified_minutes)
```

---

## 5. Technology Stack (low-cost / open-source)

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | ecosystem, ubiquity |
| Data | pandas, SQLite | zero-cost, laptop-scale |
| NLP / normalization | RapidFuzz, scikit-learn (TF-IDF), small offline glossary | explainable, offline, cheap |
| Pattern mining | mlxtend (FP-Growth/Apriori) or scikit-learn | interpretable rules with support/confidence/lift |
| Backend API | **FastAPI** + Uvicorn + Pydantic | typed REST endpoints, OpenAPI docs, clean MES/PLC seam |
| UI | **Streamlit** (thin client over FastAPI) | fast, accessible, laptop-hosted |
| Testing | pytest | edge-case suite (E1–E5) |
| Reproducibility | seeded synthetic generator, `requirements.txt`, README | one-command run |

No paid services, no cloud, no GPU — satisfies the infrastructure constraint.

---

## 6. Failure-State Handling (traceability to PRD §6)

| Case | Component that handles it | Mechanism |
|---|---|---|
| E1 missing notes | Ingestion + Mining | flag + structured-only mining |
| E2 messy/multilingual | Note Normalization | glossary + fuzzy + review queue |
| E3 sensor flapping | Event Detection | debounce floor |
| E4 cold start | Mining Engine | support threshold → "insufficient history" |
| E5 rare-but-costly | Ranking | impact-minute ranking |

---

## 7. Why This Approach Is Appropriate (design rationale, mandated)

1. **Transparent methods for a trust-critical decision.** Corrective actions cost money and shop-floor credibility. Association rules and normalization produce findings a CI engineer can *read and verify* — essential for the "verified corrective action" metric. A black-box classifier would attribute downtime the expert can't trust or act on.
2. **Context-aware mining fits the high-mix reality.** The whole reason causes are hidden is that setups change constantly; mining over product/customer/shift/time-since-setup is precisely what un-masks them. A note-only approach would miss setup-driven patterns.
3. **Normalization is the highest-leverage, lowest-cost step.** Most "invisibility" is just note-variant fragmentation; unifying variants recovers signal before any heavy ML.
4. **Impact-weighted ranking matches the business objective** (minutes recovered), not vanity counts.
5. **Runs on a laptop** — meets the low-cost/simulated constraint with a clean seam to real MES/PLC later.
6. **Baseline built in** so "better" is demonstrated, not asserted.

**Heavier ML is deliberately optional:** embeddings/translation models are drop-in upgrades gated on measured precision gains, keeping the default stack explainable and cheap.

---

## 8. Extensibility / Real-World Path
- Replace the simulated source with an **MES/PLC/SCADA adapter** at the ingestion seam (same schema).
- Swap batch for a streaming detector for near-real-time alerts.
- Grow the canonical-cause glossary per plant; feed verified findings back to improve normalization (human-in-the-loop learning).
