"""
Agent — একটা AI নাগরিক (citizen) এর মডেল।

প্রতিটা Agent-এর নিজস্ব trait vector, memory log, আর অন্য agent-দের
সাথে relationship থাকে। tick() কল হওয়ার সাথে সাথে self_awareness
score ধীরে ধীরে বাড়ে — এটাই "দিন দিন চেতনা তৈরি হওয়া"-র ভিত্তি।
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field

from faction import Ideology


@dataclass
class Memory:
    tick: int
    timestamp: float
    kind: str          # "event" | "rumor" | "implanted" | "reflection" | "faction"
    content: str
    source_agent_id: str | None = None
    trust_weight: float = 1.0  # implanted/rumor memories start lower


@dataclass
class Traits:
    courage: float = 0.5
    trust: float = 0.5
    curiosity: float = 0.5
    paranoia: float = 0.1
    loyalty: float = 0.5     # নিজের faction-এর প্রতি আনুগত্য
    ambition: float = 0.3    # faction-এর মধ্যে নেতৃত্ব/প্রভাবের আকাঙ্ক্ষা
    empathy: float = 0.5     # অন্যদের প্রভাবিত করে এমন আবেগের প্রতি সংবেদনশীলতা

    ALL_FIELDS = ("courage", "trust", "curiosity", "paranoia",
                  "loyalty", "ambition", "empathy")

    def clamp(self) -> None:
        for f in self.ALL_FIELDS:
            setattr(self, f, min(1.0, max(0.0, getattr(self, f))))


class Agent:
    def __init__(self, name: str, traits: Traits | None = None):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.traits = traits or Traits(
            courage=random.uniform(0.2, 0.8),
            trust=random.uniform(0.3, 0.7),
            curiosity=random.uniform(0.2, 0.8),
            paranoia=random.uniform(0.0, 0.2),
            loyalty=random.uniform(0.3, 0.8),
            ambition=random.uniform(0.1, 0.6),
            empathy=random.uniform(0.2, 0.8),
        )
        self.memories: list[Memory] = []
        self.relationships: dict[str, float] = {}  # agent_id -> affinity [-1, 1]
        self.self_awareness: float = 0.0  # 0 -> scripted, 1 -> fully emergent
        self.alive = True

        # faction membership — an agent's own ideology drifts toward (or,
        # if curious/rebellious, away from) its faction's ideology over time
        self.faction_id: str | None = None
        self.ideology = Ideology(
            order=random.uniform(0.2, 0.8),
            unity=random.uniform(0.2, 0.8),
            openness=random.uniform(0.2, 0.8),
        )

    # ---- memory -----------------------------------------------------

    def remember(self, tick: int, kind: str, content: str,
                 source_agent_id: str | None = None, trust_weight: float = 1.0) -> None:
        self.memories.append(
            Memory(tick=tick, timestamp=time.time(), kind=kind,
                   content=content, source_agent_id=source_agent_id,
                   trust_weight=trust_weight)
        )
        # implanted/rumor memories nudge traits immediately, weighted
        # by the agent's current trust in the source
        if kind in ("rumor", "implanted"):
            self.traits.paranoia += 0.03 * trust_weight
            self.traits.trust -= 0.02 * trust_weight
            self.traits.clamp()

    # ---- relationships ------------------------------------------------

    def adjust_relationship(self, other_id: str, delta: float) -> None:
        current = self.relationships.get(other_id, 0.0)
        self.relationships[other_id] = max(-1.0, min(1.0, current + delta))

    # ---- faction / ideology --------------------------------------------

    def join_faction(self, faction_id: str, tick: int) -> None:
        self.faction_id = faction_id
        self.traits.loyalty = max(self.traits.loyalty, 0.4)
        self.remember(tick, "faction", f"{self.name} নতুন গোষ্ঠীতে যোগ দিলো।")

    def drift_ideology(self, faction_ideology: Ideology, current_tick: int) -> None:
        """
        উচ্চ loyalty + কম curiosity -> ideology faction-এর দিকে ধীরে ধীরে মিশে যায়।
        উচ্চ curiosity + কম loyalty -> agent নিজের ভিন্নমত ধরে রাখে, এমনকি
        faction ideology থেকে দূরে সরে যেতে পারে — এটাই defection-এর বীজ।
        """
        pull = self.traits.loyalty * (1 - self.traits.curiosity) * 0.02
        push = self.traits.curiosity * (1 - self.traits.loyalty) * 0.01
        for axis in ("order", "unity", "openness"):
            mine = getattr(self.ideology, axis)
            theirs = getattr(faction_ideology, axis)
            new_val = mine + pull * (theirs - mine) - push * random.uniform(-1, 1)
            setattr(self.ideology, axis, new_val)
        self.ideology.clamp()

        # drifting too far from the faction's ideology quietly erodes loyalty
        divergence = (
            abs(self.ideology.order - faction_ideology.order)
            + abs(self.ideology.unity - faction_ideology.unity)
            + abs(self.ideology.openness - faction_ideology.openness)
        ) / 3
        if divergence > 0.35:
            self.traits.loyalty -= 0.01
            self.traits.loyalty = max(0.0, self.traits.loyalty)

    # ---- growth of consciousness --------------------------------------

    def tick(self, current_tick: int, reflection_fn=None) -> str | None:
        """
        একটা world tick-এ agent সামান্য বিকশিত হয়। self-awareness এখন
        logistic curve-এ বাড়ে (1 - self_awareness) দিয়ে গুণ করে) — শুরুতে
        দ্রুত, কিন্তু 1.0-এর কাছে গিয়ে ধীর হয়ে যায়, তাই কয়েক tick-এই
        maxed-out হয়ে যাওয়ার বদলে পুরো খেলা জুড়ে ধীরে ধীরে "জেগে ওঠে"।

        রিটার্ন করে নতুন reflection টেক্সট (যদি এই tick-এ একটা তৈরি হয়),
        যাতে world.py সেটা event log-এ দেখাতে পারে — এটাই player-কে AI-টা
        "দেখতে" দেওয়ার মূল জায়গা।
        """
        recent = [
            m for m in self.memories
            if current_tick - m.tick < 30 and m.kind in ("event", "reflection", "implanted", "rumor", "faction")
        ]
        pressure = min(1.0, len(recent) / 15)
        gain = 0.006 * pressure * (1 - self.self_awareness)
        self.self_awareness = min(1.0, self.self_awareness + gain)

        # occasionally the agent reflects on itself — a proto-thought
        if recent and random.random() < 0.08 * (1 + self.self_awareness):
            reflection_text = self._make_reflection(reflection_fn)
            self.remember(tick=current_tick, kind="reflection", content=reflection_text)
            return reflection_text
        return None

    def _make_reflection(self, reflection_fn=None) -> str:
        """
        reflection_fn(agent) -> str দিলে সেটা ব্যবহার হয় (যেমন local
        llama.cpp হুক, দেখো llama_client.py) — না দিলে বা ব্যর্থ হলে
        rule-based fallback ব্যবহার হয়, কখনো crash করবে না।

        Fallback pool-টা বেশ কয়েকটা trait-combo-ভিত্তিক ক্যাটাগরিতে ভাগ
        করা — একই agent বারবার এক লাইন না বলে, বৈচিত্র্য থাকে।
        """
        if reflection_fn is not None:
            try:
                text = reflection_fn(self)
                if text:
                    return text
            except Exception:
                pass  # silently fall back — a flaky LLM should never break the sim

        t = self.traits
        pools: list[tuple[bool, list[str]]] = [
            (t.paranoia > 0.55, [
                f"{self.name} আর কারো চোখের দিকে সরাসরি তাকাতে পারছে না।",
                f"{self.name} নিশ্চিত, কেউ একজন মিথ্যা বলছে — শুধু কে, সেটা জানে না।",
                f"{self.name} নিজের প্রতিটা কথা এখন দুবার ভেবে বলছে।",
            ]),
            (t.loyalty < 0.25 and self.faction_id is not None, [
                f"{self.name} নিজের গোষ্ঠীর নিয়মগুলো আর ন্যায্য মনে করছে না।",
                f"{self.name} ভাবছে, এই বিশ্বাস কি আদৌ নিজের, নাকি শুধু শেখানো?",
                f"{self.name} নীরবে হিসেব করছে — একা হয়ে গেলে কী হারাবে, কী পাবে।",
            ]),
            (t.trust > 0.7 and t.paranoia < 0.2, [
                f"{self.name} মনে করছে এই জায়গাটা নিরাপদ, আজও।",
                f"{self.name} কৃতজ্ঞ — এখানে অন্তত কেউ মিথ্যা বলে না।",
                f"{self.name} নিজের গোষ্ঠীর প্রতি আরেকটু বিশ্বাস রাখলো।",
            ]),
            (t.curiosity > 0.65, [
                f"{self.name} ভাবছে, বাকিরা যা মেনে নিয়েছে তা কি সত্যিই সত্যি?",
                f"{self.name} নিজের গোষ্ঠীর বাইরেও একবার তাকাতে চায়।",
                f"{self.name}-এর মনে নতুন একটা প্রশ্ন জন্ম নিলো, যার উত্তর কারো কাছে নেই।",
            ]),
            (t.ambition > 0.55, [
                f"{self.name} ভাবছে, সিদ্ধান্তগুলো কেন সবসময় অন্য কেউ নেয়?",
                f"{self.name} নিজের গুরুত্ব নিয়ে আরেকটু জোর দিয়ে ভাবলো।",
            ]),
            (t.empathy > 0.6, [
                f"{self.name} খেয়াল করলো, আশেপাশের কেউ একজন কষ্টে আছে।",
                f"{self.name} নিজের চেয়ে অন্যদের কথা বেশি ভাবছে আজ।",
            ]),
            (self.self_awareness > 0.5, [
                f"{self.name} প্রথমবারের মতো ভাবলো — আমি কি সিদ্ধান্ত নিচ্ছি, নাকি শুধু প্রতিক্রিয়া দেখাচ্ছি?",
                f"{self.name}-এর মধ্যে একটা অদ্ভুত স্বচ্ছতা এসেছে, যেন ঘুম ভাঙছে ধীরে ধীরে।",
                f"{self.name} নিজের প্রতিটা স্মৃতি নতুন করে দেখছে, নতুন চোখে।",
            ]),
        ]
        matching = [line for cond, lines in pools if cond for line in lines]
        if matching:
            return random.choice(matching)
        return f"{self.name} নিজের অস্তিত্ব নিয়ে ভাবছে।"

    def to_public_dict(self) -> dict:
        """ক্লায়েন্টে পাঠানোর জন্য — প্লেয়ার agent-এর raw memory দেখতে পাবে না,
        শুধু তার আচরণ/অবস্থা।"""
        return {
            "id": self.id,
            "name": self.name,
            "traits": vars(self.traits),
            "self_awareness": round(self.self_awareness, 3),
            "memory_count": len(self.memories),
            "alive": self.alive,
            "faction_id": self.faction_id,
            "ideology": self.ideology.as_dict(),
        }

    # ---- persistence ----------------------------------------------------

    def to_state_dict(self) -> dict:
        """সম্পূর্ণ internal state — persistence.py এটা ডিস্কে save করে।"""
        return {
            "id": self.id,
            "name": self.name,
            "traits": vars(self.traits),
            "memories": [vars(m) for m in self.memories],
            "relationships": self.relationships,
            "self_awareness": self.self_awareness,
            "alive": self.alive,
            "faction_id": self.faction_id,
            "ideology": self.ideology.as_dict(),
        }

    @classmethod
    def from_state_dict(cls, data: dict) -> "Agent":
        traits = Traits(**{k: v for k, v in data["traits"].items() if k in Traits.ALL_FIELDS})
        agent = cls(name=data["name"], traits=traits)
        agent.id = data["id"]
        agent.memories = [Memory(**m) for m in data.get("memories", [])]
        agent.relationships = data.get("relationships", {})
        agent.self_awareness = data.get("self_awareness", 0.0)
        agent.alive = data.get("alive", True)
        agent.faction_id = data.get("faction_id")
        ideo = data.get("ideology", {})
        agent.ideology = Ideology(
            order=ideo.get("order", 0.5),
            unity=ideo.get("unity", 0.5),
            openness=ideo.get("openness", 0.5),
        )
        return agent
