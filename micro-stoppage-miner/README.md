# Micro-Stoppage Pattern Miner

**Linking short interruptions to recurring causes for a contract manufacturer.**

Micro-stoppages (short interruptions — a jam, a misfeed, a sensor trip) are recorded
as downtime, but their *recurring causes* stay invisible: they're too short to
root-cause, high-mix setups mask them, and operator notes are terse/multilingual.
Individually trivial, collectively they cost a full shift a week.

This project mines those micro-stoppages, **links them to recurring causes**, and
converts **hidden downtime into verified corrective actions** — the judged value.

> Planning docs: [`../docs/PRD.md`](../docs/PRD.md) ·
> [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) ·
> [`../docs/IMPLEMENTATION_PLAN.md`](../docs/IMPLEMENTATION_PLAN.md)

---

## What it does

1. **Ingests** machine states, operator notes, product, customer, shift, duration.
2. **Detects** stoppages from state transitions; debounces sensor chatter.
3. **Normalizes** messy/shorthand/multilingual notes to a canonical cause vocabulary.
4. **Mines** recurring patterns with association rules (support / confidence / lift)
   over context (machine × product × shift × time-since-setup).
5. **Ranks** findings by *impact = recoverable minutes × confidence* (so rare-but-costly
   causes aren't buried) and explains each in plain language.
6. **Verifies**: a human confirms/rejects each finding in the dashboard — this is the
   gate that turns hidden downtime into a *verified corrective action*.

Architecture: **pure logic in `src/`**, a **FastAPI** backend (`api/`) exposing it as
REST, and a thin **Streamlit** dashboard (`app/`) as the client. Everything runs on a
laptop with open-source tools and SQLite — no cloud.

---

## Quick start

```bash
pip install -r requirements.txt
python run.py all          # generate data + evaluate + run the E1-E5 test suite
```

`run.py all` prints the experiment report (baseline / target / measured / error
analysis). To explore interactively, run the backend and dashboard in two terminals:

```bash
python run.py api          # FastAPI at http://127.0.0.1:8000  (docs at /docs)
```

```bash
python run.py dashboard    # Streamlit at http://localhost:8501
```

Then click **Run miner**, review the ranked causes, and **Verify** the real ones.

### Other commands
```bash
python run.py generate     # (re)create the seeded synthetic dataset
python run.py evaluate     # run pipeline + baseline, print the report
python run.py test         # run the edge-case suite only
```

---

## Results (seeded run)

| Metric | Baseline | Target | Measured |
|---|---|---|---|
| % micro-stoppage minutes attributed to a recurring cause | 0% | ≥ 70% | **74.6%** |
| Recurring causes surfaced | 0 | ≥ 5 | **5** |
| Cause-assignment precision | — | ≥ 0.80 | **1.00** |
| Recall of planted patterns | — | — | **1.00 (4/4)** |
| Verified corrective actions | 0 | ≥ 3 | **5** |

The **baseline** (current practice) lumps all micro-stoppage minutes into one bucket
and counts raw note strings without unification — it attributes **0 minutes** to any
recurring cause. That gap is the hidden downtime this tool surfaces.

Numbers regenerate exactly via `python run.py evaluate` (seed = 42).

---

## Edge & failure cases (tested)

| # | Case | Behaviour | Test |
|---|---|---|---|
| E1 | Missing/empty operator notes | Structured-only mining; no crash | `tests/test_e1_missing_notes.py` |
| E2 | Messy/shorthand/multilingual notes | Variants unify; unmapped → review queue | `tests/test_e2_messy_multilingual.py` |
| E3 | Sub-second sensor flapping | Debounced, not mined as a cause | `tests/test_e3_sensor_flapping.py` |
| E4 | Cold start (new product/customer) | Abstains below support; no fabricated pattern | `tests/test_e4_cold_start.py` |
| E5 | Rare-but-costly vs frequent-trivial | Impact ranking keeps costly cause on top | `tests/test_e5_rare_costly.py` |

```bash
python run.py test    # 10 passed
```

---

## Why this approach

The value metric is *verified* corrective actions, so findings must be **trusted and
acted on by a CI engineer**. We deliberately use transparent methods — note
normalization + association-rule mining — over a black-box classifier: every finding
carries its evidence (events, minutes, confidence, lift, example notes) and a
plain-language explanation. Context-aware mining is what un-masks causes hidden by
high-mix setups. See [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) §7.

---

## Project layout

```
src/       pure business logic (ingest, detect, normalize, mine, rank, baseline, evaluate, store)
api/       FastAPI backend (thin REST transport over src/)
app/       Streamlit dashboard (client of the API)
tests/     E1-E5 edge-case suite
data/      seeded synthetic dataset + data dictionary
run.py     one-command entrypoint
config.yaml  all thresholds (micro band, debounce, support/confidence/lift)
```

## Accessibility, language & explainability

- **Explainability:** every finding is evidence-backed with a plain-language sentence.
- **Language:** normalization handles shorthand, typos and multiple languages; unmapped
  notes are surfaced for review, never dropped.
- **Accessibility:** status shown by text + icon (never colour alone), high-contrast
  Streamlit theme, keyboard-navigable controls.

See the stakeholder validation notes in
[`../docs/VALIDATION.md`](../docs/VALIDATION.md).

## Real-world path

Replace the synthetic feed with an MES/PLC/SCADA adapter at the `/ingest` seam (same
schema). The `src/` logic is unchanged; only the data source differs.
