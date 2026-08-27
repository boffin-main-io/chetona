"""
Config — config.json লোড করে, না পেলে sane defaults ব্যবহার করে।
কখনো crash করবে না, শুধু warning log করে।
"""

from __future__ import annotations

import json
import logging
import os

log = logging.getLogger("chetona.config")

DEFAULTS = {
    "host": "0.0.0.0",
    "port": 8765,
    "tick_interval_seconds": 5,
    "autosave_every_ticks": 10,
    "persistence_dir": "./data",
    "default_population": 8,
    "llama": {
        "enabled": False,
        "endpoint": "http://127.0.0.1:8080/completion",
        "timeout_seconds": 3,
    },
    "log_file": "./chetona.log",
    "rate_limit": {"capacity": 5, "refill_per_second": 0.5},
}


def load_config(path: str = "config.json") -> dict:
    if not os.path.exists(path):
        log.warning("config file %s not found, using defaults", path)
        return dict(DEFAULTS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("failed to read config file %s (%s), using defaults", path, e)
        return dict(DEFAULTS)

    merged = dict(DEFAULTS)
    merged.update(user_cfg)
    if "llama" in user_cfg:
        merged["llama"] = {**DEFAULTS["llama"], **user_cfg["llama"]}
    if "rate_limit" in user_cfg:
        merged["rate_limit"] = {**DEFAULTS["rate_limit"], **user_cfg["rate_limit"]}
    return merged
