import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from world import World


def test_starts_at_stage_one():
    w = World(population=4)
    assert w.objective.stage == 1
    assert w.objective.completed_stages == []


def test_advances_to_stage_two_on_defection():
    w = World(population=4)
    target_id = next(iter(w.agents.keys()))
    for _ in range(50):
        w.tick()
        w.incite_defection(target_id, credibility=1.0)
        if w.objective.stage > 1:
            break
    assert w.objective.stage >= 2
    assert 1 in w.objective.completed_stages


def test_objective_persists_through_snapshot():
    w = World(population=4)
    snap = w.snapshot()
    assert "objective" in snap
    assert snap["objective"]["stage"] == 1
    assert "progress" in snap["objective"]


def test_persistence_roundtrip_keeps_objective_progress():
    import tempfile
    import persistence

    w = World(population=4, world_id="objective-roundtrip")
    target_id = next(iter(w.agents.keys()))
    for _ in range(50):
        w.tick()
        w.incite_defection(target_id, credibility=1.0)
        if w.objective.stage > 1:
            break

    with tempfile.TemporaryDirectory() as d:
        persistence.save_world(w, d)
        loaded = persistence.load_world(d, "objective-roundtrip")
        assert loaded is not None
        assert loaded.objective.stage == w.objective.stage
        assert loaded.objective.completed_stages == w.objective.completed_stages
