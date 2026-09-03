"""Seeded synthetic data generator for the micro-stoppage pilot.

Produces a realistic machine-state event log for a high-mix contract manufacturer
and injects KNOWN recurring causes as ground truth so the miner can be scored.

Deliberately bakes in the edge conditions the miner must survive:
  * missing / empty operator notes            (E1)
  * messy / shorthand / multilingual notes     (E2)
  * sub-second sensor flapping                 (E3)
  * a brand-new customer with no history       (E4)
  * a rare-but-costly cause vs frequent-trivial (E5)
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

# --- Static shop-floor definitions -------------------------------------------

MACHINES = ["CNC-01", "CNC-02", "PRESS-01", "PACK-01"]
SHIFTS = ["A", "B", "C"]

# Each machine usually runs a primary product (so recurring patterns can form),
# but occasionally runs something else (high-mix reality + background noise).
PRIMARY_PRODUCT = {
    "CNC-01": "P-4472",
    "CNC-02": "P-4471",
    "PRESS-01": "P-8810",
    "PACK-01": "P-2200",
}

# customer -> products they order
CUSTOMER_PRODUCTS = {
    "CustA": ["P-4471", "P-4472"],
    "CustB": ["P-8810"],
    "CustC": ["P-2200", "P-2201"],
    # CustD is deliberately introduced only at the very end -> cold start (E4)
    "CustD": ["P-9000"],
}

# Canonical cause -> pool of messy, real-world note variants (incl. other languages).
# Empty string "" represents a missing note (operator too busy) -> E1/E2.
NOTE_VARIANTS = {
    "material_jam": ["matl jam again", "material stuck", "jam", "jamd", "atasco", "jaam", ""],
    "misfeed": ["misfeed", "feed problem", "no feed", "feeder stuck", "mis feed", "alimentacion mala"],
    "sensor_fault": ["sensor trip", "photoeye dirty", "sensor err", "detector fault", "sensore"],
    "tool_change": ["tool worn", "changed insert", "blade dull", "tool chg", "tooling"],
    "material_out": ["out of material", "refill", "empty hopper", "reload matl", "agotado"],
    "operator_adjust": ["manual adj", "quick tweak", "adjust", "op correction", "ajuste"],
    "temperature": ["temp high", "overheat", "cooling issue", "too hot"],
    "quality_check": ["quality check", "inspect part", "reject", "scrap check", "defect"],
}


@dataclass
class InjectedPattern:
    """A recurring cause deliberately planted in the data (= ground truth)."""
    machine: str
    product: str
    shift: str
    cause: str
    only_after_setup_min: int | None  # if set, cause fires only within N min of a setup
    events_per_day: float
    duration_range_s: tuple[int, int]
    label: str


# --- The ground-truth recurring patterns we plant ----------------------------

def _injected_patterns() -> list[InjectedPattern]:
    return [
        # Frequent, setup-driven jam on CustA's flagship product (the headline finding).
        InjectedPattern("CNC-02", "P-4471", "A", "material_jam", 30, 4.0, (25, 90),
                        "P-4471 jams on CNC-02 shortly after setup, shift A"),
        # A misfeed pattern on the press, shift B.
        InjectedPattern("PRESS-01", "P-8810", "B", "misfeed", None, 3.0, (35, 95),
                        "P-8810 misfeeds on PRESS-01, shift B"),
        # Sensor faults on packing, shift C.
        InjectedPattern("PACK-01", "P-2200", "C", "sensor_fault", None, 3.0, (25, 75),
                        "P-2200 sensor faults on PACK-01, shift C"),
        # RARE but COSTLY: only ~1.5/day but long (E5) — must not be buried.
        InjectedPattern("CNC-01", "P-4472", "A", "tool_change", None, 1.5, (200, 290),
                        "P-4472 long tool-change stoppages on CNC-01, shift A"),
    ]


def generate(
    days: int = 21,
    seed: int = 42,
    noise_events_per_day: float = 3.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate (events_df, ground_truth_df).

    events_df columns: ts, machine_id, machine_state, product_id, customer_id,
                       shift, operator_note
    """
    rng = random.Random(seed)
    patterns = _injected_patterns()
    start = datetime(2026, 7, 1, 6, 0, 0)

    rows: list[dict] = []

    # Reverse lookup: product -> customer
    product_customer = {
        p: cust for cust, prods in CUSTOMER_PRODUCTS.items() for p in prods
    }

    def emit(ts, machine, state, product, shift, note=""):
        rows.append({
            "ts": ts,
            "machine_id": machine,
            "machine_state": state,
            "product_id": product,
            "customer_id": product_customer[product],
            "shift": shift,
            "operator_note": note,
        })

    def shift_for_hour(hour: int) -> str:
        if 6 <= hour < 14:
            return "A"
        if 14 <= hour < 22:
            return "B"
        return "C"

    def ts_in_shift(day_base: datetime, shift: str) -> datetime:
        """A timestamp landing inside the given shift on this day."""
        if shift == "A":
            hour = rng.randint(6, 13)
        elif shift == "B":
            hour = rng.randint(14, 21)
        else:  # C spans midnight; use early-morning hours of the same day
            hour = rng.choice([22, 23, 0, 1, 2, 3, 4, 5])
        midnight = day_base.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight + timedelta(hours=hour, minutes=rng.randint(0, 59),
                                    seconds=rng.randint(0, 59))

    def choose_product(machine: str, day: int) -> str:
        # CustD (cold start, E4) only appears in the final 2 days.
        primary = PRIMARY_PRODUCT[machine]
        others = [p for p in product_customer
                  if p != primary and (product_customer[p] != "CustD" or day >= days - 2)]
        # 75% primary product, 25% something else (high-mix changeovers).
        return primary if rng.random() < 0.75 else rng.choice(others)

    for day in range(days):
        day_base = start + timedelta(days=day)

        # --- Daily setup per machine (start of shift A) ---
        machine_product_today: dict[str, str] = {}
        setup_ts_today: dict[str, datetime] = {}
        for machine in MACHINES:
            product = choose_product(machine, day)
            machine_product_today[machine] = product
            setup_ts = day_base.replace(hour=6, minute=0) + timedelta(minutes=rng.randint(0, 20))
            setup_ts_today[machine] = setup_ts
            emit(setup_ts, machine, "SETUP", product, "A", "setup / changeover")
            emit(setup_ts + timedelta(minutes=rng.randint(8, 20)), machine, "RUNNING",
                 product, "A", "")

        # --- Injected recurring patterns ---
        for pat in patterns:
            if machine_product_today.get(pat.machine) != pat.product:
                continue  # this machine isn't running the pattern's product today
            n = int(rng.random() < (pat.events_per_day % 1)) + int(pat.events_per_day)
            for _ in range(n):
                if pat.only_after_setup_min is not None:
                    # fire shortly after setup (drives the time-since-setup signal)
                    ts = setup_ts_today[pat.machine] + timedelta(
                        minutes=rng.randint(20, 20 + pat.only_after_setup_min))
                else:
                    ts = ts_in_shift(day_base, pat.shift)
                dur = rng.randint(*pat.duration_range_s)
                note = rng.choice(NOTE_VARIANTS[pat.cause])
                emit(ts, pat.machine, "STOPPED", pat.product, pat.shift, note)
                emit(ts + timedelta(seconds=dur), pat.machine, "RUNNING", pat.product,
                     pat.shift, "")

        # --- Random background noise stoppages (varied causes, spread thin) ---
        n_noise = int(rng.gauss(noise_events_per_day, 1.5))
        for _ in range(max(0, n_noise)):
            machine = rng.choice(MACHINES)
            product = machine_product_today[machine]
            shift = rng.choice(SHIFTS)
            ts = ts_in_shift(day_base, shift)
            cause = rng.choice(list(NOTE_VARIANTS.keys()))
            dur = rng.randint(15, 120)
            note = rng.choice(NOTE_VARIANTS[cause])
            emit(ts, machine, "STOPPED", product, shift, note)
            emit(ts + timedelta(seconds=dur), machine, "RUNNING", product, shift, "")

        # --- Sensor flapping / chatter (E3): sub-second STOPPED->RUNNING blips ---
        for _ in range(rng.randint(1, 3)):
            machine = rng.choice(MACHINES)
            product = machine_product_today[machine]
            shift = rng.choice(SHIFTS)
            ts = ts_in_shift(day_base, shift)
            emit(ts, machine, "STOPPED", product, shift, "")
            emit(ts + timedelta(seconds=1), machine, "RUNNING", product, shift, "")

    events = pd.DataFrame(rows).sort_values(["machine_id", "ts"]).reset_index(drop=True)

    # Ground-truth table: one row per planted pattern.
    gt = pd.DataFrame([{
        "machine_id": p.machine,
        "product_id": p.product,
        "shift": p.shift,
        "cause": p.cause,
        "after_setup_min": p.only_after_setup_min,
        "label": p.label,
    } for p in patterns])

    return events, gt


def main() -> None:
    from .config import load_config, resolve_path

    cfg = load_config()
    events, gt = generate()
    events_path = resolve_path(cfg["paths"]["events_csv"])
    gt_path = resolve_path(cfg["paths"]["ground_truth_csv"])
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events.to_csv(events_path, index=False)
    gt.to_csv(gt_path, index=False)
    print(f"Wrote {len(events)} events -> {events_path}")
    print(f"Wrote {len(gt)} ground-truth patterns -> {gt_path}")


if __name__ == "__main__":
    main()
