"""Load the YAML config once and expose it as a plain dict."""
from __future__ import annotations

import functools
from pathlib import Path

import yaml

# Project root = parent of the src/ package directory.
ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"


@functools.lru_cache(maxsize=1)
def load_config(path: str | Path | None = None) -> dict:
    """Return the config dict, cached. Pass a path to override (used in tests)."""
    cfg_path = Path(path) if path else CONFIG_PATH
    with open(cfg_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def resolve_path(rel: str) -> Path:
    """Resolve a config-relative path against the project root."""
    return ROOT / rel
