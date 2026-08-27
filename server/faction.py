"""
Faction — agent-দের একটা গোষ্ঠী, যাদের একটা শেয়ার্ড "ideology vector" আছে।

ideology axes (0..1 each):
    order        — নিয়ম/কর্তৃত্বের প্রতি ঝোঁক (0 = নৈরাজ্যপন্থী, 1 = কঠোর শৃঙ্খলাপন্থী)
    unity        — ব্যক্তি vs সম্মিলিত স্বার্থ (0 = individualist, 1 = collectivist)
    openness     — বহিরাগত/নতুন ধারণার প্রতি সহনশীলতা (0 = insular, 1 = open)

cohesion = গোষ্ঠীর অভ্যন্তরীণ বিশ্বাস কতটা অক্ষত — player-এর মূল target।
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field


@dataclass
class Ideology:
    order: float = 0.5
    unity: float = 0.5
    openness: float = 0.5

    def clamp(self) -> None:
        for f in ("order", "unity", "openness"):
            setattr(self, f, min(1.0, max(0.0, getattr(self, f))))

    def as_dict(self) -> dict:
        return {"order": round(self.order, 3), "unity": round(self.unity, 3),
                "openness": round(self.openness, 3)}


class Faction:
    def __init__(self, name: str, creed: str, ideology: Ideology | None = None):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.creed = creed
        self.ideology = ideology or Ideology(
            order=random.uniform(0.2, 0.8),
            unity=random.uniform(0.2, 0.8),
            openness=random.uniform(0.2, 0.8),
        )
        self.member_ids: set[str] = set()
        self.cohesion: float = 0.7  # starts fairly stable

    def add_member(self, agent_id: str) -> None:
        self.member_ids.add(agent_id)

    def remove_member(self, agent_id: str) -> None:
        self.member_ids.discard(agent_id)

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "creed": self.creed,
            "ideology": self.ideology.as_dict(),
            "cohesion": round(self.cohesion, 3),
            "member_count": len(self.member_ids),
        }

    # ---- persistence ----------------------------------------------------

    def to_state_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "creed": self.creed,
            "ideology": self.ideology.as_dict(),
            "cohesion": self.cohesion,
            "member_ids": list(self.member_ids),
        }

    @classmethod
    def from_state_dict(cls, data: dict) -> "Faction":
        ideo = data.get("ideology", {})
        f = cls(name=data["name"], creed=data.get("creed", ""),
                 ideology=Ideology(order=ideo.get("order", 0.5),
                                    unity=ideo.get("unity", 0.5),
                                    openness=ideo.get("openness", 0.5)))
        f.id = data["id"]
        f.cohesion = data.get("cohesion", 0.7)
        f.member_ids = set(data.get("member_ids", []))
        return f
