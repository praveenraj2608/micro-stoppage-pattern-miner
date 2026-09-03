# Implementation Plan
## Micro-Stoppage Pattern Miner — 30-Hour Industry Challenge

**Version:** 1.0 · **Date:** 2026-08-18 · **Owner:** Praveen Raj
**Related:** [PRD](./PRD.md) · [System Architecture](./ARCHITECTURE.md)

---

## 1. Strategy for 30 Hours

Build **thin end-to-end first**, then deepen. A working (if simple) full pipeline — data → detect → normalize → mine → dashboard → verify → metric — is worth more than one perfect component. Every mandated deliverable maps to a phase below, and each phase leaves a demonstrable artifact.

**Definition of Done (whole project):** one command produces the synthetic data, runs baseline + prototype, passes the E1–E5 test suite, launches the dashboard, and prints the experiment table (baseline / target / measured / error analysis).

---

## 2. Repository Layout

```
micro-stoppage-miner/
├─ README.md                      # setup, run, results, screenshots
├─ requirements.txt
├─ run.py                         # one-command: data + pipeline + tests + launch
├─ config.yaml                    # thresholds (micro band, debounce, support)
├─ data/
│  ├─ synthetic/                  # generated CSV/SQLite
│  └─ data_dictionary.md
├─ src/                           # pure business logic (web-framework-agnostic)
│  ├─ generate_data.py            # synthetic generator (seeded, ground truth)
│  ├─ ingest.py                   # load + validate (E1)
│  ├─ detect.py                   # stoppage detection + debounce (E3)
│  ├─ normalize.py                # note normalization + review queue (E2)
│  ├─ mine.py                     # clustering + association rules (E4, E5)
│  ├─ rank.py                     # impact scoring + explanations
│  ├─ baseline.py                 # simple baseline
│  ├─ evaluate.py                 # experiment: baseline/target/measured/errors
│  └─ store.py                    # SQLite persistence + metrics
├─ api/                           # FastAPI backend (thin transport over src/)
│  ├─ main.py                     # app + routes: /ingest /run /findings /verify …
│  ├─ schemas.py                  # Pydantic request/response models (Finding, …)
│  └─ deps.py                     # store/config wiring
├─ app/
│  └─ dashboard.py                # Streamlit client (calls the FastAPI endpoints)
├─ tests/
│  ├─ test_e1_missing_notes.py
│  ├─ test_e2_messy_multilingual.py
│  ├─ test_e3_sensor_flapping.py
│  ├─ test_e4_cold_start.py
│  └─ test_e5_rare_costly.py
└─ docs/                          # PRD, ARCHITECTURE, this plan, validation
```

---

## 3. Phased Plan

### Phase 0 — Setup & Scaffolding  *(~1.5 h)*
- Repo, `requirements.txt`, `config.yaml`, empty modules, `run.py` skeleton.
- **Deliverable:** repo runs end-to-end with stubs (prints "ok" per stage).

### Phase 1 — Synthetic Dataset + Data Dictionary  *(~3.5 h)*
- `generate_data.py`: realistic state timelines across machines/products/customers/shifts. **Inject known recurring causes as ground truth** (e.g., P-4471 jams post-setup on Shift A).
- Bake in the edge conditions: missing notes, multilingual/shorthand variants, sensor flapping, a brand-new customer.
- Write `data_dictionary.md`.
- **Deliverable (mandated):** cleaned/synthetic dataset + schema. **Milestone M1.**

### Phase 2 — Ingestion, Detection, Normalization  *(~5 h)*
- `ingest.py` (schema validation, E1-safe).
- `detect.py` (stoppage extraction, duration, `is_micro`, `time_since_setup`, E3 debounce).
- `normalize.py` (clean → language → canonical cause → review queue for E2).
- **Deliverable:** structured stoppage table with canonical causes.

### Phase 3 — Baseline  *(~1.5 h)*
- `baseline.py`: lumped downtime total + verbatim note counts (no unification, no context).
- **Deliverable (mandated):** baseline for comparison. **Milestone M2.**

### Phase 4 — Pattern Mining + Ranking  *(~5 h)*
- `mine.py`: TF-IDF cause clustering + FP-Growth/Apriori context rules (support/confidence/lift); E4 cold-start guard.
- `rank.py`: impact = recoverable_minutes × confidence (E5); build explainable Finding objects with example notes + plain-language reason + suggested action.
- **Deliverable:** ranked, explainable recurring-cause report. **Milestone M3 (core value).**

### Phase 5 — FastAPI Backend + Streamlit Dashboard + Verification Loop  *(~5 h)*
- `api/main.py` + `api/schemas.py`: FastAPI endpoints `/ingest`, `/run`, `/findings`, `/findings/{id}/verify`, `/baseline`, `/metrics`, `/health`; Pydantic models; auto OpenAPI docs at `/docs`. Thin transport over `src/` so logic stays testable without the server.
- `app/dashboard.py`: Streamlit **client** that calls the API — ranked findings, drill-down evidence, **verify/reject** control (POSTs to `/findings/{id}/verify`), export.
- Apply accessibility choices (contrast, non-colour-only cues, keyboard nav, labels, legible sizes).
- **Deliverable (mandated):** end-to-end working prototype (API + UI). **Milestone M4.**

### Phase 6 — Edge/Failure Tests  *(~2.5 h)*
- Implement `tests/` for E1–E5; wire into `run.py`.
- **Deliverable (mandated):** ≥3 (we ship 5) edge/failure cases, automated. **Milestone M5.**

### Phase 7 — Measurable Experiment + Error Analysis  *(~3 h)*
- `evaluate.py`: compare prototype vs baseline against ground truth → % minutes attributed, precision/recall, recoverable minutes; **error analysis** (false clusters, misattributions, unmapped notes, cold-start abstentions).
- Emit the **baseline / target / measured / error-analysis** table.
- **Deliverable (mandated):** evaluation report. **Milestone M6.**

### Phase 8 — Accessibility, Language & User Validation  *(~2 h)*
- Run explainability check (CI engineer rates trust ≥4/5), multilingual normalization check, accessibility walkthrough (contrast + keyboard-only).
- Recruit representative users (operator, supervisor, CI engineer, ≥1 non-native English speaker); record feedback + changes made in `docs/validation.md`.
- **Deliverable (mandated):** accessibility/language/explainability checks + stakeholder validation. **Milestone M7.**

### Phase 9 — README, Demo Video, Polish  *(~2 h)*
- README: problem, setup, one-command run, results table, screenshots, limitations.
- Record the **3-minute demo**: problem → dashboard → a verified corrective action → the conversion metric.
- **Deliverable (mandated):** 3-min video + source + README. **Milestone M8 — submission.**

*Total ≈ 31 h; keep the FastAPI layer intentionally thin (transport only) to hold near 30 h. If time-pressed, ship the Streamlit UI calling `src/` directly first, then lift the same calls behind FastAPI — the `src/` logic is identical either way.*

---

## 4. Milestones & Deliverable Traceability

| Milestone | Phase | Mandated deliverable satisfied |
|---|---|---|
| M1 | 1 | Cleaned/synthetic dataset |
| M2 | 3 | Baseline |
| M3 | 4 | Recurring-cause miner (core) |
| M4 | 5 | End-to-end working prototype |
| M5 | 6 | ≥3 edge/failure cases |
| M6 | 7 | Measurable experiment + error analysis |
| M7 | 8 | Accessibility/language/explainability + user validation |
| M8 | 9 | Demo video + source + README |
| — | PRD/ARCH/this | Problem analysis + user/workflow map |

---

## 5. Experiment Protocol (fills PRD §7)

1. Generate synthetic data with hidden ground-truth causes.
2. Run **baseline** → record attributed minutes, note-count "insights".
3. Run **prototype** → record ranked findings.
4. Score both vs ground truth → % minutes attributed, precision, recall.
5. Simulate verification (mark true findings verified) → verified actions + verified minutes.
6. Produce the report table:

| Metric | Baseline | Target | Measured |
|---|---|---|---|
| % micro-stoppage minutes attributed | (lump only) | ≥ 70% | _run_ |
| Recurring causes surfaced | ~0 (no unification) | ≥ 5 | _run_ |
| Cause-assignment precision | — | ≥ 0.80 | _run_ |
| Verified corrective actions | 0 | ≥ 3 | _run_ |
| Recoverable minutes identified | 0 | — | _run_ |

7. **Error analysis:** categorize every miss (false cluster / misattribution / unmapped note / cold-start abstention) with counts and cause.

---

## 6. Risks & Mitigations (execution)

| Risk | Mitigation |
|---|---|
| Time overrun on NLP | Ship glossary+fuzzy first; embeddings only if time and precision demand |
| Synthetic data too easy | Inject realistic noise; report honest error analysis |
| Dashboard eats time | Streamlit defaults; function over polish; accessibility via simple correct choices |
| Scope creep (real-time, forecasting) | Explicit non-goals in PRD; hold the line |
| Demo video slips | Time-box to 2 h; script it from the milestone artifacts |

---

## 7. Immediate Next Actions
1. Confirm doc approval (PRD / Architecture / this plan).
2. Scaffold repo (Phase 0).
3. Build the synthetic generator with ground truth (Phase 1) — it unblocks everything else.
