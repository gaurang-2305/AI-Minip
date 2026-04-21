"""
ai/inference_engine.py
======================
FORWARD CHAINING — Rule-Based Inference Engine.

In Forward Chaining (data-driven reasoning), the system:
  1. Starts with FACTS from the Knowledge Base.
  2. Applies IF-THEN rules in priority order.
  3. Fires the FIRST rule whose conditions are met.
  4. The fired rule's action modifies the working memory or triggers an action.

This is contrasted with Backward Chaining (goal-driven), which is implemented
in the Planner (ai/planner.py) — the planner starts with the goal (reach food)
and works backward to determine which search algorithm to invoke.

Rule Hierarchy (highest priority first)
----------------------------------------
  RULE 1  IMMEDIATE_DEATH_AHEAD  — all forward directions lead to death
  RULE 2  FOOD_ADJACENT          — food is 1 step away, move directly to it
  RULE 3  LOW_OPEN_SPACE         — very little reachable space → trigger fallback
  RULE 4  DANGER_AHEAD           — current direction leads to collision
  RULE 5  DEFAULT                — no reactive condition fired → use planner

Rules 1-4 override the planner entirely and return an immediate direction.
Rule 5 signals the planner to run a full search.
"""

from .knowledge_base import KnowledgeBase
from engine.grid import wrap, manhattan_wrap, best_flood_direction
from engine.constants import DIRS


class InferenceResult:
    """
    Output of one inference cycle.

    rule_fired  : name of the rule that matched (str)
    direction   : (dx, dy) to move, or None if planner should decide
    use_planner : True → hand off to the Planner for full search
    """
    __slots__ = ("rule_fired", "direction", "use_planner")

    def __init__(self, rule_fired: str, direction=None, use_planner: bool = False):
        self.rule_fired  = rule_fired
        self.direction   = direction
        self.use_planner = use_planner

    def __repr__(self):
        return f"InferenceResult(rule={self.rule_fired}, dir={self.direction}, planner={self.use_planner})"


# ── Threshold constants ───────────────────────────────────────────────────────
LOW_SPACE_THRESHOLD = 8   # open_space below this → immediate survival mode


class ForwardChainingEngine:
    """
    Stateless rule engine — receives a KnowledgeBase, returns an InferenceResult.
    """

    def infer(self, kb: KnowledgeBase) -> InferenceResult:
        """
        Evaluate rules in priority order and return the first match.
        """

        # ── RULE 1: Immediate death in ALL directions ─────────────────────
        safe = kb.safe_neighbours()
        if not safe:
            return InferenceResult(
                rule_fired="NO_SAFE_MOVE",
                direction=kb.direction,   # can't help — let it die gracefully
                use_planner=False,
            )

        # ── RULE 2: Food is adjacent — eat it directly ────────────────────
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

        # ── RULE 3: Open space critically low → pure flood-fill survival ──
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

        # ── RULE 4: Danger directly ahead — avoid but defer to planner ────
        # We note the danger but still run the planner (it will route around).
        if kb.danger_ahead:
            return InferenceResult(
                rule_fired="DANGER_AHEAD_USE_PLANNER",
                direction=None,
                use_planner=True,
            )

        # ── RULE 5: Default — full search via planner ─────────────────────
        return InferenceResult(
            rule_fired="DEFAULT_PLANNER",
            direction=None,
            use_planner=True,
        )
