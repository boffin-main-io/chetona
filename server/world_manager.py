"""
WorldManager — একাধিক named World চালায় (multiplayer-এর ভিত্তি)।

প্রতিটা player নিজের world_id দিয়ে কানেক্ট করবে (?world=alice)। manager
প্রয়োজনে ডিস্ক থেকে load করে, না থাকলে নতুন বানায়, আর প্রতি N tick-এ
autosave করে।
"""

from __future__ import annotations

import logging

import persistence
from world import World

log = logging.getLogger("chetona.world_manager")


class WorldManager:
    def __init__(self, config: dict, reflection_fn=None):
        self.config = config
        self.reflection_fn = reflection_fn
        self.worlds: dict[str, World] = {}
        self._ticks_since_save: dict[str, int] = {}

    def get_or_create(self, world_id: str) -> tuple[World, bool]:
        """Returns (world, is_newly_created). is_newly_created is True only the
        very first time this world is created in this server process — used to
        reveal the owner_token once to whoever claims it first."""
        if world_id in self.worlds:
            return self.worlds[world_id], False

        loaded = persistence.load_world(
            self.config["persistence_dir"], world_id, reflection_fn=self.reflection_fn
        )
        is_new = loaded is None
        world = loaded or World(
            population=self.config["default_population"],
            world_id=world_id,
            reflection_fn=self.reflection_fn,
        )
        self.worlds[world_id] = world
        self._ticks_since_save[world_id] = 0
        return world, is_new

    def tick_all(self) -> None:
        autosave_every = self.config["autosave_every_ticks"]
        for world_id, world in self.worlds.items():
            world.tick()
            self._ticks_since_save[world_id] = self._ticks_since_save.get(world_id, 0) + 1
            if self._ticks_since_save[world_id] >= autosave_every:
                persistence.save_world(world, self.config["persistence_dir"])
                self._ticks_since_save[world_id] = 0

    def save_all(self) -> None:
        for world in self.worlds.values():
            persistence.save_world(world, self.config["persistence_dir"])
