# 3-Minute Demo Video — Shot List & Script

Record with two terminals + a browser. Target: **3:00**.

## Setup (before recording)
```bash
pip install -r requirements.txt
python run.py generate
```
Terminal A: `python run.py api`  → wait for "Uvicorn running".
Terminal B: `python run.py dashboard` → opens http://localhost:8501.

---

## Scene 1 — The problem (0:00–0:30)
> "A contract manufacturer changes setups constantly for different customers.
> Micro-stoppages — short jams, misfeeds, sensor trips — get logged as generic
> downtime, so their recurring causes stay invisible. Individually trivial;
> together, a full shift a week."

Show `data/synthetic/events.csv` scrolling — messy notes, `STOPPED` rows.

## Scene 2 — Baseline (0:30–0:50)
> "Today's practice: lump all micro-stoppage minutes into one bucket and count raw
> note strings. It attributes **zero** minutes to any recurring cause."

Show the dashboard's **Baseline comparison** expander (0 min attributed, N distinct
raw note strings).

## Scene 3 — Run the miner (0:50–1:30)
Click **Run miner**. Then narrate the top metrics row:
> "It detects 210 micro-stoppages, and attributes **74.6%** of those minutes to five
> recurring causes — with **100% precision** against known ground truth."

Expand finding #1 (sensor fault, night shift) and #2 (the rare-but-costly tool change):
> "Each finding is explainable — events, minutes, confidence, lift, the actual
> operator notes, and a suggested corrective action. Ranking is by *impact minutes*,
> so this rare-but-long tool-change stays near the top instead of being buried."

## Scene 4 — Verify → corrective action (1:30–2:10)
On the setup-driven **material jam** finding:
> "The context says it jams within 30 minutes of setup — that points straight at the
> changeover procedure."

Type an owner + action, click **Verify & assign**. Watch the top metric
**Verified actions** increment.
> "That click is the whole point: hidden downtime just became a *verified corrective
> action*."

## Scene 5 — Edge cases & rigour (2:10–2:40)
Terminal: `python run.py test`
> "Five realistic failure states are tested: missing notes, multilingual shorthand,
> sensor flapping, cold-start on a new customer, and rare-but-costly ranking.
> Ten tests pass."

Show `python run.py evaluate` report table (baseline / target / measured — all pass).

## Scene 6 — Close (2:40–3:00)
> "Open-source, laptop-only, with a FastAPI backend ready to swap the simulated feed
> for a real MES. From invisible micro-stoppages to a ranked, verified, actionable
> improvement list."

Show FastAPI `/docs` (Swagger UI) briefly as proof of the integration seam.
