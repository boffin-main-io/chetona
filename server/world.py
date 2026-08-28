"""
World — পুরো civilization-এর tick engine।

- background-এ প্রতি TICK_INTERVAL_SECONDS পর পর tick() চালায়, app বন্ধ
  থাকলেও সার্ভার চললে সভ্যতা এগোতে থাকে।
- player-এর "whisper" action (rumor/implant/nudge) world-এ inject হয়।
"""

from __future__ import annotations

import asyncio
import random
import secrets
import time

from agent import Agent, Traits
from faction import Faction, Ideology
from objectives import ObjectiveState, evaluate_and_advance

TICK_INTERVAL_SECONDS = 5  # ডেমোর জন্য ছোট রাখা হলো; আসল খেলায় মিনিট/ঘণ্টা হতে পারে

DEFAULT_NAMES = [
    "Amara", "Beno", "Cira", "Dax", "Ely", "Feru", "Goa", "Hiro",
    "Ira", "Juno", "Kael", "Lira",
]

DEFAULT_FACTIONS = [
    ("The Ember Circle", "শৃঙ্খলা আর ঐক্যই টিকে থাকার একমাত্র পথ।",
     Ideology(order=0.75, unity=0.7, openness=0.3)),
    ("Wandering Loom", "প্রতিটা মন স্বাধীন, প্রতিটা প্রশ্ন মূল্যবান।",
     Ideology(order=0.25, unity=0.35, openness=0.8)),
]


class World:
    def __init__(self, population: int = 8, world_id: str | None = None,
                 reflection_fn=None, _skip_seed: bool = False):
        self.world_id = world_id or "default"
        self.tick_count = 0
        self.started_at = time.time()
        self.agents: dict[str, Agent] = {}
        self.factions: dict[str, Faction] = {}
        self.reflection_fn = reflection_fn  # optional callable(agent) -> str, e.g. llama.cpp hook

        # per-player auth: whoever first creates/claims this world gets the
        # token needed for mutating actions on it (see world_manager.py).
        # Read-only actions (snapshot, graph) never require it — spectating
        # and being infiltrated don't need permission, only acting does.
        self.owner_token: str = secrets.token_urlsafe(16)
        self.objective = ObjectiveState()

        if _skip_seed:
            self._running = False
            return

        for name, creed, ideology in DEFAULT_FACTIONS:
            f = Faction(name=name, creed=creed, ideology=ideology)
            self.factions[f.id] = f

        faction_ids = list(self.factions.keys())
        for i in range(population):
            name = DEFAULT_NAMES[i % len(DEFAULT_NAMES)]
            a = Agent(name=name)
            self.agents[a.id] = a
            faction = self.factions[faction_ids[i % len(faction_ids)]]
            a.join_faction(faction.id, self.tick_count)
            faction.add_member(a.id)

        self._seed_relationships()
        self._running = False

    def _seed_relationships(self) -> None:
        ids = list(self.agents.keys())
        for a_id in ids:
            for b_id in ids:
                if a_id == b_id:
                    continue
                same_faction = self.agents[a_id].faction_id == self.agents[b_id].faction_id
                base = random.uniform(0.0, 0.4) if same_faction else random.uniform(-0.3, 0.1)
                self.agents[a_id].adjust_relationship(b_id, base)

    # ---- simulation loop -----------------------------------------------

    async def run_forever(self) -> None:
        self._running = True
        while self._running:
            self.tick()
            await asyncio.sleep(TICK_INTERVAL_SECONDS)

    def stop(self) -> None:
        self._running = False

    def tick(self) -> None:
        self.tick_count += 1
        agent_ids = list(self.agents.keys())

        # random social interactions — the raw material agents reflect on
        for a_id in agent_ids:
            agent = self.agents[a_id]
            if not agent.alive:
                continue
            if random.random() < 0.3 and len(agent_ids) > 1:
                other_id = random.choice([x for x in agent_ids if x != a_id])
                other = self.agents[other_id]
                affinity = agent.relationships.get(other_id, 0.0)
                if affinity >= 0:
                    agent.remember(self.tick_count, "event",
                                    f"{agent.name} আর {other.name} একসাথে সময় কাটালো।")
                    agent.adjust_relationship(other_id, 0.02)
                else:
                    agent.remember(self.tick_count, "event",
                                    f"{agent.name} {other.name}-কে এড়িয়ে গেলো।")
                    agent.adjust_relationship(other_id, -0.01)

        for agent in self.agents.values():
            if agent.faction_id and agent.faction_id in self.factions:
                faction = self.factions[agent.faction_id]
                agent.drift_ideology(faction.ideology, self.tick_count)
            agent.tick(self.tick_count, reflection_fn=self.reflection_fn)

        self._recompute_faction_cohesion()
        self.objective = evaluate_and_advance(self.objective, self)

    def _recompute_faction_cohesion(self) -> None:
        """cohesion = গোষ্ঠীর মধ্যে গড় সম্পর্ক + গড় loyalty - গড় paranoia।
        এটাই player-এর ultimate scoreboard: cohesion যত কমবে, গোষ্ঠী তত ভাঙনের মুখে।"""
        for faction in self.factions.values():
            members = [self.agents[mid] for mid in faction.member_ids if mid in self.agents]
            if not members:
                continue
            avg_loyalty = sum(m.traits.loyalty for m in members) / len(members)
            avg_paranoia = sum(m.traits.paranoia for m in members) / len(members)

            internal_pairs, internal_sum = 0, 0.0
            for m in members:
                for other_id in faction.member_ids:
                    if other_id != m.id:
                        internal_sum += m.relationships.get(other_id, 0.0)
                        internal_pairs += 1
            avg_internal_affinity = internal_sum / internal_pairs if internal_pairs else 0.0

            target = 0.5 * avg_loyalty + 0.3 * (avg_internal_affinity + 1) / 2 - 0.2 * avg_paranoia
            faction.cohesion += (target - faction.cohesion) * 0.1
            faction.cohesion = max(0.0, min(1.0, faction.cohesion))

    # ---- player actions (the actual "game") -----------------------------

    def whisper_rumor(self, target_id: str, content: str, credibility: float = 0.5) -> dict:
        """একটা agent-এর মধ্যে গুজব/মিথ্যা স্মৃতি বসানো — মূল player action।"""
        agent = self.agents.get(target_id)
        if not agent:
            return {"ok": False, "error": "agent not found"}
        agent.remember(self.tick_count, "implanted", content, trust_weight=credibility)
        return {"ok": True, "agent": agent.to_public_dict()}

    def sow_distrust(self, a_id: str, b_id: str, strength: float = 0.3) -> dict:
        """দুই agent-এর মধ্যে সম্পর্ক নষ্ট করা।"""
        a, b = self.agents.get(a_id), self.agents.get(b_id)
        if not a or not b:
            return {"ok": False, "error": "agent not found"}
        a.adjust_relationship(b_id, -strength)
        b.adjust_relationship(a_id, -strength)
        a.remember(self.tick_count, "implanted", f"{b.name}-কে আর বিশ্বাস করা যায় না।", trust_weight=strength)
        return {"ok": True}

    def incite_defection(self, agent_id: str, credibility: float = 0.5) -> dict:
        """
        মূল faction-বিরোধী action: agent-এর মনে নিজের গোষ্ঠীর প্রতি সন্দেহ
        বপন করা। উচ্চ curiosity/কম loyalty-র agent-দের ওপর এটা বেশি কাজ করে,
        আর বারবার প্রয়োগে ideology faction থেকে সরে গিয়ে defection ঘটতে পারে।
        """
        agent = self.agents.get(agent_id)
        if not agent or not agent.faction_id:
            return {"ok": False, "error": "agent not found or has no faction"}
        faction = self.factions.get(agent.faction_id)
        agent.traits.loyalty -= 0.08 * credibility
        agent.traits.loyalty = max(0.0, agent.traits.loyalty)
        agent.remember(
            self.tick_count, "implanted",
            f"{agent.name} নিজের গোষ্ঠীর সিদ্ধান্ত নিয়ে প্রশ্ন তুলতে শুরু করলো।",
            trust_weight=credibility,
        )
        defected = False
        if agent.traits.loyalty < 0.15 and random.random() < 0.3:
            if faction:
                faction.remove_member(agent.id)
            agent.faction_id = None
            defected = True
            agent.remember(self.tick_count, "faction", f"{agent.name} নিজের গোষ্ঠী ছেড়ে দিলো।")
        return {"ok": True, "defected": defected, "agent": agent.to_public_dict()}

    def civilization_paranoia(self) -> float:
        alive = [a for a in self.agents.values() if a.alive]
        if not alive:
            return 0.0
        return sum(a.traits.paranoia for a in alive) / len(alive)

    def civilization_awareness(self) -> float:
        alive = [a for a in self.agents.values() if a.alive]
        if not alive:
            return 0.0
        return sum(a.self_awareness for a in alive) / len(alive)

    def snapshot(self) -> dict:
        return {
            "world_id": self.world_id,
            "tick": self.tick_count,
            "uptime_seconds": round(time.time() - self.started_at),
            "avg_paranoia": round(self.civilization_paranoia(), 3),
            "avg_self_awareness": round(self.civilization_awareness(), 3),
            "agents": [a.to_public_dict() for a in self.agents.values()],
            "factions": [f.to_public_dict() for f in self.factions.values()],
            "objective": self.objective.to_public_dict(self),
        }

    # ---- multiplayer infiltration (cross-world) --------------------------

    def infiltrate_from(self, other_world: "World", target_agent_id: str,
                         content: str, credibility: float = 0.4) -> dict:
        """
        Multiplayer hook: এই world-এর agent-এর মনে অন্য world (মানে অন্য
        প্লেয়ারের civilization) থেকে পাঠানো একটা গুজব বসানো। যেহেতু এটা
        "বহিরাগত" উৎস থেকে আসছে, ideology-openness যত কম, effect তত কম —
        insular faction-গুলো infiltration-প্রতিরোধী।
        """
        agent = self.agents.get(target_agent_id)
        if not agent:
            return {"ok": False, "error": "agent not found"}
        effective_credibility = credibility * (0.4 + 0.6 * agent.ideology.openness)
        agent.remember(self.tick_count, "implanted",
                        f"[বহিরাগত ফিসফিস] {content}", trust_weight=effective_credibility)
        return {
            "ok": True,
            "from_world": other_world.world_id,
            "effective_credibility": round(effective_credibility, 3),
            "agent": agent.to_public_dict(),
        }

    # ---- relationship graph (for visualization) --------------------------

    def relationship_graph(self) -> dict:
        """
        একটা ছোট, aggregated graph — player-এর নিজের civilization দেখার জন্য।
        raw memory log বা যুক্তি প্রকাশ করে না, শুধু node (agent) আর edge
        (affinity) — visualization (D3/force-graph) খাওয়ানোর জন্য যথেষ্ট।
        """
        nodes = [
            {
                "id": a.id,
                "name": a.name,
                "faction_id": a.faction_id,
                "self_awareness": round(a.self_awareness, 3),
                "paranoia": round(a.traits.paranoia, 3),
                "alive": a.alive,
            }
            for a in self.agents.values()
        ]
        edges = []
        seen_pairs: set[tuple[str, str]] = set()
        for a in self.agents.values():
            for other_id, affinity in a.relationships.items():
                if other_id not in self.agents:
                    continue
                pair = tuple(sorted((a.id, other_id)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                # average both directions if both exist, so the edge is symmetric
                reverse = self.agents[other_id].relationships.get(a.id, affinity)
                edges.append({"a": pair[0], "b": pair[1], "affinity": round((affinity + reverse) / 2, 3)})
        return {"nodes": nodes, "edges": edges, "factions": [f.to_public_dict() for f in self.factions.values()]}

    # ---- persistence ------------------------------------------------------

    def to_state_dict(self) -> dict:
        return {
            "world_id": self.world_id,
            "tick_count": self.tick_count,
            "started_at": self.started_at,
            "owner_token": self.owner_token,
            "agents": [a.to_state_dict() for a in self.agents.values()],
            "factions": [f.to_state_dict() for f in self.factions.values()],
            "objective": {
                "stage": self.objective.stage,
                "completed_stages": self.objective.completed_stages,
                "completed_at_tick": self.objective.completed_at_tick,
            },
        }

    @classmethod
    def from_state_dict(cls, data: dict, reflection_fn=None) -> "World":
        world = cls(world_id=data.get("world_id", "default"),
                     reflection_fn=reflection_fn, _skip_seed=True)
        world.tick_count = data.get("tick_count", 0)
        world.started_at = data.get("started_at", time.time())
        world.owner_token = data.get("owner_token") or world.owner_token
        world.factions = {f["id"]: Faction.from_state_dict(f) for f in data.get("factions", [])}
        world.agents = {a["id"]: Agent.from_state_dict(a) for a in data.get("agents", [])}
        obj_data = data.get("objective")
        if obj_data:
            world.objective = ObjectiveState(
                stage=obj_data.get("stage", 1),
                completed_stages=obj_data.get("completed_stages", []),
                completed_at_tick={int(k): v for k, v in obj_data.get("completed_at_tick", {}).items()},
            )
        return world
