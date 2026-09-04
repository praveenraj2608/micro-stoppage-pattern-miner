"""One-command entrypoint for the Micro-Stoppage Pattern Miner.

Usage:
  python run.py generate     # create the seeded synthetic dataset
  python run.py evaluate     # run pipeline + baseline, print the experiment report
  python run.py test         # run the E1-E5 edge-case suite
  python run.py api          # launch the FastAPI backend (uvicorn)
  python run.py dashboard    # launch the Streamlit dashboard
  python run.py all          # generate -> evaluate -> test  (default)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def cmd_generate():
    from src.generate_data import main as gen
    gen()


def cmd_evaluate():
    import pandas as pd

    from src.config import load_config, resolve_path
    from src.evaluate import build_report
    from src.pipeline import run_pipeline

    cfg = load_config()
    events_path = resolve_path(cfg["paths"]["events_csv"])
    gt_path = resolve_path(cfg["paths"]["ground_truth_csv"])
    if not events_path.exists():
        print("No dataset found — generating first...")
        cmd_generate()
    result = run_pipeline(str(events_path), cfg)
    gt = pd.read_csv(gt_path)

    # Simulate verification of the true-positive findings for the metric.
    from src.evaluate import _finding_matches_gt
    verified = 0
    for f in result["findings"]:
        if any(_finding_matches_gt(f, gt.loc[i]) for i in gt.index):
            verified += 1
    report = build_report(result, gt, verified_actions=verified)

    _print_report(result, report)


def _print_report(result, report):
    m = result["metrics"]
    print("\n" + "=" * 72)
    print(" MICRO-STOPPAGE PATTERN MINER — EXPERIMENT REPORT")
    print("=" * 72)
    print(f"\nMicro-stoppages detected: {result['micro_count']}  "
          f"| total {m['micro_minutes_total']} min")
    print(f"Attributed to a recurring cause: {m['pct_attributed']}%  "
          f"({m['minutes_attributed']} min)")
    print(f"Unlabelled (empty notes, E1): {m['unlabelled_events']}  "
          f"| Unmapped (review queue, E2): {m['unmapped_events']}")

    print("\n--- Baseline vs Target vs Measured -------------------------------")
    print(f"{'metric':40} {'base':>7} {'target':>8} {'measured':>9}  pass")
    for row in report["comparison"]:
        p = "PASS" if row["pass"] else "----"
        print(f"{row['metric']:40} {str(row['baseline']):>7} "
              f"{str(row['target']):>8} {str(row['measured']):>9}  {p}")

    print("\n--- Ranked findings ----------------------------------------------")
    for f in result["findings"]:
        print(f"  #{f['rank']} {f['cause_label']:18} "
              f"{f['recoverable_min']:>6} min  conf {int(f['confidence']*100):>3}%  "
              f"lift {f['lift']}x  | {f['context']}")

    print("\n--- Error analysis -----------------------------------------------")
    ea = report["error_analysis"]
    print(f"  False-positive findings: {ea['false_positive_findings']}")
    print(f"  Missed ground-truth patterns: {ea['missed_ground_truth_patterns']}")
    print(f"  Unmapped-note events: {ea['unmapped_notes_events']}  "
          f"| Unlabelled-note events: {ea['unlabelled_notes_events']}")
    sc = report["score"]
    print(f"  Precision: {sc['precision']}  | Recall: {sc['recall']}  "
          f"({sc['matched_patterns']}/{sc['ground_truth_patterns']} patterns)")
    print("=" * 72 + "\n")


def cmd_test():
    raise SystemExit(subprocess.call(
        [sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")]))


def cmd_api():
    subprocess.call([sys.executable, "-m", "uvicorn", "api.main:app",
                     "--reload", "--port", "8000"], cwd=str(ROOT))


def cmd_dashboard():
    subprocess.call([sys.executable, "-m", "streamlit", "run",
                     str(ROOT / "app" / "dashboard.py")], cwd=str(ROOT))


def cmd_all():
    cmd_generate()
    cmd_evaluate()
    print(">>> Running edge-case test suite (E1-E5)...")
    subprocess.call([sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")])


COMMANDS = {
    "generate": cmd_generate,
    "evaluate": cmd_evaluate,
    "test": cmd_test,
    "api": cmd_api,
    "dashboard": cmd_dashboard,
    "all": cmd_all,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd not in COMMANDS:
        print(__doc__)
        raise SystemExit(1)
    COMMANDS[cmd]()
