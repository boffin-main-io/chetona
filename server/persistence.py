"""
Persistence — world state ডিস্কে save/load।

crash-safe লেখার জন্য: প্রথমে .tmp ফাইলে লেখা হয়, তারপর atomic rename —
মাঝপথে সার্ভার ক্র্যাশ করলেও পুরোনো valid save ফাইলটা নষ্ট হয় না।
"""

from __future__ import annotations

import json
import logging
import os

from world import World

log = logging.getLogger("chetona.persistence")


def _path_for(persistence_dir: str, world_id: str) -> str:
    os.makedirs(persistence_dir, exist_ok=True)
    return os.path.join(persistence_dir, f"world_{world_id}.json")


def save_world(world: World, persistence_dir: str) -> None:
    path = _path_for(persistence_dir, world.world_id)
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(world.to_state_dict(), f, ensure_ascii=False)
        os.replace(tmp_path, path)  # atomic on POSIX and Windows
        log.info("saved world '%s' at tick %d", world.world_id, world.tick_count)
    except OSError as e:
        log.error("failed to save world '%s': %s", world.world_id, e)


def load_world(persistence_dir: str, world_id: str, reflection_fn=None) -> World | None:
    path = _path_for(persistence_dir, world_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        world = World.from_state_dict(data, reflection_fn=reflection_fn)
        log.info("loaded world '%s' from tick %d", world.world_id, world.tick_count)
        return world
    except (json.JSONDecodeError, OSError, KeyError) as e:
        log.error("failed to load world '%s' (%s) — starting fresh instead", world_id, e)
        return None
