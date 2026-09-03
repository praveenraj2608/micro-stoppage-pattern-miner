# Product Requirements Document (PRD)
## Micro-Stoppage Pattern Miner — Linking Short Interruptions to Recurring Causes

**Document owner:** Praveen Raj
**Version:** 1.0
**Date:** 2026-08-18
**Status:** Draft for 30-hour industry challenge
**Related docs:** [System Architecture](./ARCHITECTURE.md) · [Implementation Plan](./IMPLEMENTATION_PLAN.md)

---

## 1. Problem Analysis

### 1.1 Context
A **contract manufacturer** runs a high-mix, low-to-medium volume shop floor. It changes machine setups **frequently** to serve **different customers** and product families. Each changeover shifts materials, tooling, feed rates, and operators, so the shop's operating conditions are rarely stable for long.

### 1.2 The unresolved issue
**Micro-stoppages** — short interruptions to a running machine (typically a few seconds up to ~5 minutes: a jam, a misfeed, a sensor trip, a quick manual adjustment) — are **recorded as downtime, but their recurring causes are not visible.**

Why they stay invisible:

| Cause of invisibility | Consequence |
|---|---|
| Too short to formally root-cause | Operators don't log detailed reasons; events collapse into a generic "downtime" bucket |
| High-mix setups | The *same* root cause appears under different products/customers/shifts, so it never looks like a pattern |
| Free-text, shorthand, multilingual operator notes | "jam", "jamd", "material stuck", "atasco" all describe one cause but never aggregate |
| Individually trivial | A 40-second stop is ignored; 300 of them per week is a full shift of lost capacity |

This is the textbook **"minor stoppages / idling"** loss among the Six Big Losses in OEE — the loss category that is hardest to see and therefore most often left unaddressed.

### 1.3 Why this matters (business framing)
- Micro-stoppages erode **Availability** and **Performance** in OEE without ever showing up as a single visible failure.
- In a contract shop, unattributed downtime is **unquoted cost** — it silently eats into margins on fixed-price jobs and distorts future quoting.
- The organisation cannot act on what it cannot see: **no visible cause → no corrective action → recurring loss.**

### 1.4 What "solving it" means
Convert **hidden downtime** (unattributed micro-stoppage minutes) into **verified corrective actions** — i.e., ranked, evidence-backed recurring-cause findings that a human expert confirms as real and actionable. This exact conversion is the challenge's judging metric.

---

## 2. Goals & Non-Goals

### 2.1 Goals
1. Ingest **machine states, operator notes, product, shift, and stoppage duration** and detect micro-stoppage events.
2. **Link** short interruptions to **recurring causes** by unifying inconsistent operator notes and mining context (product/customer/shift/machine/time-since-setup).
3. Produce a **ranked, explainable recurring-cause report** with evidence, impact (minutes recovered if fixed), and a suggested corrective action.
4. Beat a **simple baseline** on a measurable experiment.
5. Run on **low-cost / simulated infrastructure** (a laptop, open-source only).
6. Pass **accessibility, language, and explainability** checks with representative users.
7. Close the loop: track **hidden downtime → verified corrective action**.

### 2.2 Non-Goals (for the pilot)
- Real-time PLC/SCADA integration (we simulate the data feed; the design leaves a clear adapter seam).
- Predicting *future* stoppages (this is diagnostic pattern mining, not forecasting).
- Replacing the MES/CMMS; we augment it with cause visibility.
- Automatically executing corrective actions; a human verifies and owns the action.

---

## 3. Users & Workflow Map

### 3.1 Personas

| Persona | Goal | Pain today | What the product gives them |
|---|---|---|---|
| **Machine Operator** | Keep the line running; log what happened fast | No time to write detailed reasons; notes are terse/multilingual | One-tap suggested cause tags; notes get *used*, not ignored |
| **Shift Supervisor / Line Lead** | Hit shift targets | Sees "downtime" total, not *why* | Daily top recurring micro-stoppage causes for their shift |
| **CI / Lean / Six-Sigma Engineer** | Drive corrective actions | Can't isolate high-mix patterns manually | Ranked cause clusters with lift, impact minutes, and evidence to verify |
| **Plant / Ops Manager** | Improve OEE, quote accurately | Hidden loss distorts costing | Trend of hidden downtime converted to verified actions |

### 3.2 Workflow (current vs. proposed)

**Current (broken loop):**
```
Machine stops briefly → operator maybe scribbles a note → logged as "downtime"
   → aggregated into a single number → cause never surfaces → recurs forever
```

**Proposed (closed loop):**
```
1. CAPTURE    machine state log + operator note + product + shift + duration
2. DETECT     identify micro-stoppage events (debounce sensor noise)
3. NORMALIZE  map messy/multilingual notes → canonical cause vocabulary
4. MINE       cluster + association-rule mining across context
5. RANK       recurring causes by impact (minutes) × confidence
6. EXPLAIN    show evidence, example notes, plain-language reason
7. VERIFY     CI engineer / operator confirms cause is real  ✅
8. ACT        corrective action assigned + tracked
9. MEASURE    downtime reduction fed back → loop closes
```

The product owns steps 2–6 and 9; humans own 1, 7, 8. Step 7 (**verify**) is the gate that turns "hidden downtime" into a "verified corrective action."

---

## 4. Data Requirements

### 4.1 Input signals (as mandated by the challenge)
| Field | Type | Example | Role |
|---|---|---|---|
| `timestamp` | datetime | 2026-08-18 07:41:12 | event time / sequencing |
| `machine_id` | categorical | CNC-02 | which asset |
| `machine_state` | categorical | RUNNING / STOPPED / IDLE / SETUP | detect start/end of stoppage |
| `product_id` / `customer_id` | categorical | P-4471 / CustA | high-mix context |
| `shift` | categorical | A / B / C | shift context (incl. changeover effects) |
| `stoppage_duration_s` | numeric | 47 | derived; micro-stoppage filter |
| `operator_note` | free text | "matl jam again" | unstructured cause signal |

### 4.2 Derived features
- `is_micro_stoppage` (duration ≤ configurable threshold, default ≤ 300s and ≥ debounce floor).
- `time_since_setup` (minutes since last SETUP state — tests the "frequent setup" hypothesis).
- `canonical_cause` (output of note normalization).
- `stoppage_rate` per (machine × product × shift) window.

### 4.3 Dataset for the pilot
A **synthetic dataset generator** (documented, seeded, reproducible) that injects *known* recurring causes (ground truth) so we can measure precision/recall of the miner. Includes deliberately messy notes, missing notes, multilingual notes, and sensor flapping — mirroring reality and feeding the edge cases (§6). A cleaned schema and a data dictionary ship with it.

---

## 5. Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Ingest CSV/SQLite of machine state + notes and derive stoppage events | Must |
| FR-2 | Classify events as micro-stoppage with a configurable duration band + debounce | Must |
| FR-3 | Normalize operator notes to a canonical cause vocabulary (typo/shorthand/multilingual tolerant) | Must |
| FR-4 | Mine recurring cause patterns across context (product/shift/machine/time-since-setup) with support, confidence, lift | Must |
| FR-5 | Rank findings by **impact = recoverable minutes × confidence** | Must |
| FR-6 | For each finding, show evidence + example raw notes + plain-language explanation | Must |
| FR-7 | Dashboard with a verify/reject control that records the human decision | Must |
| FR-8 | Track "hidden downtime → verified corrective action" metric over time | Must |
| FR-9 | Baseline mode for side-by-side comparison | Must |
| FR-10 | Graceful degradation when notes are missing (structured-only mining) | Should |
| FR-11 | Export the recurring-cause report (CSV/PDF) for shop-floor review | Should |

---

## 6. Edge & Failure Cases (≥3, mandated)

| # | Case | Realistic trigger | Required behaviour |
|---|---|---|---|
| E1 | **Missing / empty operator notes** | Operator too busy to log | Fall back to structured-only pattern mining; flag "cause unlabelled" without crashing; still surface context patterns |
| E2 | **Messy / multilingual / shorthand notes** | "jamd", "atasco", "स्टक", "matl stuck" | Normalization unifies variants to one canonical cause; unmapped notes routed to a review queue, not dropped |
| E3 | **Sensor flapping / chatter** | State toggles RUNNING↔STOPPED in <2s | Debounce filter merges/ignores sub-floor blips so noise isn't mined as a "cause" |
| E4 | **Cold start — new product/customer** | First job for CustD, no history | Miner reports "insufficient history"; does not fabricate a false pattern; uses cross-product priors cautiously |
| E5 | **Rare-but-costly vs frequent-trivial** | One 4-min recurring jam vs many 20s idles | Ranking by *impact minutes*, not raw count, so costly-rare causes aren't buried |

Each case ships with an automated test asserting the required behaviour.

---

## 7. Success Metrics & Experiment

### 7.1 Primary metric (challenge-defined)
**Hidden downtime converted into verified corrective actions**, expressed as:
- **% of micro-stoppage minutes attributed** to an identified recurring cause, and
- **# of verified corrective actions** (human-confirmed) with recoverable-minutes estimate.

### 7.2 Measurable experiment structure

| Element | Definition |
|---|---|
| **Baseline** | Current practice proxy: total micro-stoppage minutes reported as one bucket + naive verbatim-note counting (no variant unification, no context). |
| **Target** | Attribute **≥ 70%** of micro-stoppage minutes to recurring causes; surface **≥ 5** ranked causes; achieve **≥ 0.80 precision** of cause assignment vs. synthetic ground truth. |
| **Measured result** | Reported from the pilot run: attributed %, clusters found, precision/recall, minutes recoverable, and how many an expert verified. |
| **Error analysis** | False clusters, misattributed events, unmapped notes, cold-start abstentions — categorized with counts and root cause. |

### 7.3 Baseline vs. prototype comparison (what "better" means)
The prototype must show it **unifies note variants + adds context** to attribute materially more downtime, with higher precision, than the baseline — and that the extra attributions survive human verification.

---

## 8. Non-Functional Requirements

- **Cost:** open-source only (Python, pandas, scikit-learn, FastAPI, Streamlit, SQLite); runs on a single laptop; no cloud dependency. FastAPI backend + Streamlit frontend; simulated data feed with a documented REST/adapter seam for real MES/PLC later.
- **Explainability:** every finding is evidence-backed and stated in plain language; no unexplained black-box score. (Detailed in §9.)
- **Accessibility & language:** see §9.
- **Reproducibility:** seeded synthetic data; one-command run; README.

---

## 9. Accessibility, Language & Explainability Checks

These are **first-class acceptance criteria**, validated with representative users (operators, a supervisor, a CI engineer — including at least one non-native-English speaker).

| Dimension | Requirement | How we check it |
|---|---|---|
| **Explainability** | Each finding shows: event count, total minutes, contexts, confidence/lift, 2–3 example raw notes, and a one-sentence plain-language cause statement | Ask a CI engineer: "Do you understand and trust this finding enough to act?" — target ≥ 4/5 |
| **Language** | Note normalization handles at least 2 languages + shorthand/typos; UI output uses plain, jargon-light wording | Feed multilingual note set; confirm unification; readability review |
| **Accessibility** | WCAG-minded dashboard: sufficient colour contrast, non-colour-only encodings, keyboard navigable, screen-reader labels, legible font sizes for shop-floor tablets | Contrast checker + keyboard-only walkthrough + one representative-user test |

A short **user/stakeholder validation** write-up records who tested it, what they said, and what changed as a result.

---

## 10. Deliverables Checklist (challenge-mandated)

- [ ] Problem analysis (this PRD §1) + user/workflow map (§3)
- [ ] Cleaned or synthetic dataset (+ generator, schema, data dictionary)
- [ ] End-to-end **working prototype** (not a concept deck or isolated notebook)
- [ ] Simple **baseline** + prototype comparison
- [ ] **≥ 3 edge/failure cases** with tests (§6)
- [ ] **Measurable experiment**: baseline, target, measured result, error analysis (§7)
- [ ] Accessibility / language / explainability checks with representative users (§9)
- [ ] Short user/stakeholder validation
- [ ] **3-minute demo video**
- [ ] **Source code + README**

---

## 11. Assumptions, Risks & Open Questions

| Type | Item | Mitigation |
|---|---|---|
| Assumption | Machine state logs exist or can be simulated at event granularity | Synthetic generator models realistic state transitions |
| Assumption | Operator notes, however messy, carry cause signal for most events | E1 fallback handles the note-less remainder |
| Risk | Synthetic data flatters the miner | Inject realistic noise + hold out ground truth; report error analysis honestly |
| Risk | Over-fitting clusters to spurious high-mix coincidences | Require support + lift thresholds; human verification gate |
| Open | Exact micro-stoppage duration band per shop | Make threshold configurable; default ≤ 300s |
| Open | Which languages appear in real notes | Design normalization as an extensible mapping/embedding layer |
