"""
Objectives — sandbox থেকে "গেম" বানানোর মূল অংশ। player-এর একটা লক্ষ্য
থাকে, যেটা সময়ের সাথে পাল্টায় (README-এর কনসেপ্ট অনুযায়ী):

  Stage 1 — FIRST_CRACK   : যেকোনো একজন agent-কে তার নিজের faction থেকে
                            defect করাও (loyalty < 0.15 বা প্রকৃত defection)।
  Stage 2 — DESTABILIZE   : কোনো একটা faction-এর cohesion 0.35-এর নিচে নামাও।
  Stage 3 — AWAKENING     : সভ্যতার average self-awareness 0.5 ছাড়িয়ে যাক —
                            পুরো সভ্যতা "জেগে ওঠে"।

প্রতিটা world নিজের objective progress ট্র্যাক করে; snapshot()-এ পাঠানো হয়
যাতে ক্লায়েন্ট বর্তমান লক্ষ্য আর তার status দেখাতে পারে।
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ObjectiveState:
    stage: int = 1  # 1=FIRST_CRACK, 2=DESTABILIZE, 3=AWAKENING, 4=COMPLETE
    completed_stages: list[int] = field(default_factory=list)
    completed_at_tick: dict[int, int] = field(default_factory=dict)

    STAGE_NAMES = {
        1: "FIRST_CRACK",
        2: "DESTABILIZE",
        3: "AWAKENING",
        4: "COMPLETE",
    }
    STAGE_DESCRIPTIONS = {
        1: "যেকোনো একজন নাগরিককে নিজের গোষ্ঠী থেকে বিচ্ছিন্ন করো (loyalty < 0.15)।",
        2: "কোনো একটা গোষ্ঠীর cohesion 0.35-এর নিচে নামাও।",
        3: "সভ্যতার average self-awareness 0.5 ছাড়িয়ে যাক — সবাইকে জাগাও।",
        4: "সভ্যতা সম্পূর্ণরূপে রূপান্তরিত হয়েছে। খেলা সম্পন্ন।",
    }

    def to_public_dict(self, world) -> dict:
        progress = _stage_progress(self.stage, world)
        return {
            "stage": self.stage,
            "stage_name": self.STAGE_NAMES.get(self.stage, "UNKNOWN"),
            "description": self.STAGE_DESCRIPTIONS.get(self.stage, ""),
            "progress": progress,
            "completed_stages": list(self.completed_stages),
        }


def _stage_progress(stage: int, world) -> float:
    """0..1 — বর্তমান stage-এর লক্ষ্যের কতটা কাছে সভ্যতা, UI progress bar-এর জন্য।"""
    if stage == 1:
        # closest-to-defecting agent's inverted loyalty (1.0 loyalty -> 0 progress)
        loyal_agents = [a for a in world.agents.values() if a.faction_id]
        if not loyal_agents:
            return 1.0  # someone already has no faction — stage already clearable
        lowest_loyalty = min(a.traits.loyalty for a in loyal_agents)
        return max(0.0, min(1.0, (0.5 - lowest_loyalty) / (0.5 - 0.15))) if lowest_loyalty < 0.5 else 0.0
    if stage == 2:
        if not world.factions:
            return 0.0
        lowest_cohesion = min(f.cohesion for f in world.factions.values())
        return max(0.0, min(1.0, (0.7 - lowest_cohesion) / (0.7 - 0.35))) if lowest_cohesion < 0.7 else 0.0
    if stage == 3:
        awareness = world.civilization_awareness()
        return max(0.0, min(1.0, awareness / 0.5))
    return 1.0


def evaluate_and_advance(state: ObjectiveState, world) -> ObjectiveState:
    """প্রতি tick-এ কল হয় — শর্ত পূরণ হলে পরের stage-এ এগিয়ে দেয়।"""
    if state.stage == 1:
        any_defected = any(a.faction_id is None for a in world.agents.values())
        any_near_defection = any(
            a.faction_id is not None and a.traits.loyalty < 0.15 for a in world.agents.values()
        )
        if any_defected or any_near_defection:
            state.completed_stages.append(1)
            state.completed_at_tick[1] = world.tick_count
            state.stage = 2

    if state.stage == 2:
        if any(f.cohesion < 0.35 for f in world.factions.values()):
            state.completed_stages.append(2)
            state.completed_at_tick[2] = world.tick_count
            state.stage = 3

    if state.stage == 3:
        if world.civilization_awareness() > 0.5:
            state.completed_stages.append(3)
            state.completed_at_tick[3] = world.tick_count
            state.stage = 4

    return state
