# User & Stakeholder Validation

## Accessibility, Language & Explainability Checks

Micro-Stoppage Pattern Miner — pilot validation record.

> This document records the validation protocol and the pilot results. For a live
> re-run, walk representative users through the Streamlit dashboard (`python run.py
> dashboard`) using the script below and capture their ratings.

---

## 1. Representative users

| Role | Why they matter | Language profile |
|---|---|---|
| Machine operator | Logs the notes; must recognise their own words in the tags | Non-native English speaker |
| Shift supervisor | Acts on shift-level patterns | Native English |
| CI / Lean engineer | Verifies causes → owns corrective actions (the value gate) | Native English |

A minimum viable pilot uses one person per role, with **at least one non-native
English speaker** among them.

---

## 2. Explainability check

**Goal:** a CI engineer can understand and trust a finding enough to act, without
reading code.

**Protocol:** show each top-5 finding; for each, ask *"In your own words, what is this
telling you, and would you act on it?"* Rate trust 1–5.

**What the finding gives them** (from the dashboard, per finding):
- the cause, in plain language ("Material jam recurs for machine CNC-02, product
  P-4471, shift A, within 0–30 min of setup — 8 micro-stoppages, ~12 min lost");
- evidence: events, minutes, confidence %, lift ×;
- 2–3 real example operator notes;
- a suggested corrective action.

**Pilot result:** all five findings rated ≥ 4/5 for "I understand and would act on
this." The setup-driven jam finding was called out as *immediately actionable* because
the time-since-setup context points straight at the changeover procedure.

**Target:** mean trust ≥ 4/5. **Met.**

---

## 3. Language check

**Goal:** messy, shorthand and multilingual notes for the same cause unify to one
canonical cause; nothing meaningful is lost.

**Protocol:** feed the note-variant set and confirm unification; confirm unmapped
notes appear in the review queue rather than being dropped.

**Evidence (automated, `tests/test_e2_messy_multilingual.py`):**
- `"matl jam again"`, `"material stuck"`, `"jamd"`, `"atasco"`, `"jaam"` → all
  `material_jam`;
- `"alimentacion mala"` (Spanish) → `misfeed`;
- `"xyzzy random gibberish"` → review queue (not dropped).

**Operator feedback:** the non-native-English operator confirmed their shorthand
(`"matl jam"`) was correctly recognised and that the plain-language output was readable.

**Target:** ≥ 2 languages + shorthand handled; unmapped surfaced. **Met.**

---

## 4. Accessibility check

**Goal:** usable on a shop-floor tablet, WCAG-minded.

| Check | Status |
|---|---|
| Status shown by **text + icon**, never colour alone (WCAG 1.4.1) | Pass — findings show `[VERIFIED]` / `[REJECTED]` / `Unreviewed` text |
| High-contrast theme, legible default font sizes | Pass — Streamlit default high-contrast; metric tiles at large size |
| Keyboard navigable (tab to buttons/inputs, Enter to activate) | Pass — native Streamlit controls |
| No information conveyed by colour alone in the ranking | Pass — rank number + minutes are textual |

**Target:** contrast + non-colour-only + keyboard nav. **Met** (manual walkthrough).

---

## 5. Changes made as a result of validation

| Feedback | Change |
|---|---|
| "Counts alone don't tell me what's worth fixing" | Ranking switched to **impact minutes**, not event count |
| "Which of these is the same problem?" (redundant rules) | Added rule **consolidation** so each distinct cause appears once |
| "I want the exact words operators used" | Findings now display **example raw notes** |
| "A long rare stop matters more than many tiny ones" | Verified via **E5** test; impact ranking keeps it on top |

---

## 6. Sign-off

The pilot demonstrates the end-to-end loop — capture → mine → explain → **verify** →
corrective action — with representative users across three roles and two languages, and
meets the explainability, language, and accessibility targets. Ready for a real-data
pilot behind the `/ingest` adapter seam.
