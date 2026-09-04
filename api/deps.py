"""Shared wiring: config + store singletons for the API."""
from __future__ import annotations

from src.config import load_config, resolve_path
from src.store import Store

_cfg = load_config()
_store: Store | None = None


def get_config() -> dict:
    return _cfg


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store(resolve_path(_cfg["paths"]["db"]))
    return _store
