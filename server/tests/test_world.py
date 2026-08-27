"""
Core invariant টেস্ট — যাতে future পরিবর্তন সিমুলেশনের মূল আচরণ না ভাঙে।
চালানো: cd server && pytest
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import persistence
from world import World


def test_world_creates_expected_population():
    w = World(population=6)
    assert len(w.agents) == 6
    assert len(w.factions) == 2
    # every agent should belong to exactly one of the seeded factions
    for agent in w.agents.values():
        assert agent.faction_id in w.factions


def test_tick_advances_and_grows_awareness():
    w = World(population=4)
    for _ in range(30):
        w.tick()
    assert w.tick_count == 30
    assert w.civilization_awareness() >= 0.0


def test_incite_defection_lowers_loyalty():
    w = World(population=4)
    target_id = next(iter(w.agents.keys()))
    before = w.agents[target_id].traits.loyalty
    w.incite_defection(target_id, credibility=1.0)
    after = w.agents[target_id].traits.loyalty
    assert after < before


def test_whisper_rumor_raises_paranoia():
    w = World(population=4)
    target_id = next(iter(w.agents.keys()))
    before = w.agents[target_id].traits.paranoia
    w.whisper_rumor(target_id, "কেউ একজন সবাইকে দেখছে।", credibility=0.9)
    after = w.agents[target_id].traits.paranoia
    assert after > before


def test_infiltration_respects_openness():
    a = World(population=3, world_id="attacker")
    b = World(population=3, world_id="defender")
    target_id = next(iter(b.agents.keys()))
    b.agents[target_id].ideology.openness = 0.0  # fully insular
    result = b.infiltrate_from(a, target_id, "বহিরাগত বার্তা", credibility=1.0)
    assert result["ok"] is True
    # low openness should heavily dampen effective credibility
    assert result["effective_credibility"] < 0.5


def test_persistence_roundtrip(tmp_path):
    w = World(population=5, world_id="roundtrip")
    for _ in range(15):
        w.tick()
    persistence.save_world(w, str(tmp_path))

    loaded = persistence.load_world(str(tmp_path), "roundtrip")
    assert loaded is not None
    assert loaded.tick_count == w.tick_count
    assert len(loaded.agents) == len(w.agents)
    assert len(loaded.factions) == len(w.factions)


def test_load_missing_world_returns_none(tmp_path):
    assert persistence.load_world(str(tmp_path), "nonexistent") is None
