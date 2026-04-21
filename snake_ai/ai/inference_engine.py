"""
ai/inference_engine.py  — Forward Chaining Rule Engine
"""

from .knowledge_base import KnowledgeBase
from engine.grid import wrap, manhattan_wrap, best_flood_direction
from engine.constants import DIRS


class InferenceResult:
    __slots__ = ("rule_fired", "direction", "use_planner")

    def __init__(self, rule_fired: str, direction=None, use_planner: bool = False):
        self.rule_fired  = rule_fired
        self.direction   = direction
        self.use_planner = use_planner

    def __repr__(self):
        return f"InferenceResult(rule={self.rule_fired}, dir={self.direction}, planner={self.use_planner})"


LOW_SPACE_THRESHOLD = 8


class ForwardChainingEngine:

    def infer(self, kb: KnowledgeBase) -> InferenceResult:
        safe = kb.safe_neighbours()
        if not safe:
            return InferenceResult(
                rule_fired="NO_SAFE_MOVE",
                direction=kb.direction,
                use_planner=False,
            )

        if kb.food_adjacent:
            hx, hy = kb.head
            for dx, dy in DIRS:
                nb = wrap(hx + dx, hy + dy)
                if nb == kb.food and nb not in kb.obstacles:
                    return InferenceResult(
                        rule_fired="FOOD_ADJACENT",
                        direction=(dx, dy),
                        use_planner=False,
                    )

        if kb.open_space < LOW_SPACE_THRESHOLD:
            nb = best_flood_direction(kb.head, kb.obstacles, kb.direction)
            if nb:
                dx = nb[0] - kb.head[0]
                dy = nb[1] - kb.head[1]
                if dx >  1: dx = -1
                if dx < -1: dx =  1
                if dy >  1: dy = -1
                if dy < -1: dy =  1
                return InferenceResult(
                    rule_fired="LOW_SPACE_SURVIVAL",
                    direction=(dx, dy),
                    use_planner=False,
                )

        if kb.danger_ahead:
            return InferenceResult(
                rule_fired="DANGER_AHEAD_USE_PLANNER",
                direction=None,
                use_planner=True,
            )

        return InferenceResult(
            rule_fired="DEFAULT_PLANNER",
            direction=None,
            use_planner=True,
        )