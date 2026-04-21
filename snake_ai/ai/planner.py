"""
ai/planner.py
=============
BACKWARD CHAINING — Goal-Driven Planner.

In Backward Chaining (goal-driven reasoning), the system:
  1. Starts with the GOAL: "reach food".
  2. Asks: "what conditions must be met to achieve this goal?"
  3. Works backwards to find which search algorithm can satisfy those conditions.
  4. If the primary algorithm fails, falls back to survival (flood fill).

The Planner receives a KnowledgeBase and an InferenceResult from the
ForwardChainingEngine.  It is only invoked when the inference engine signals
use_planner=True (i.e. no reactive rule fired).

Algorithm Selection
-------------------
  Static mode    : always use the algorithm from config.
  Hybrid mode    : use config.hybrid_early until score ≥ config.hybrid_threshold,
                   then switch to config.hybrid_late.
                   Example: Greedy early-game (fast) → A* late-game (optimal).

Backward Chaining Sub-goals
----------------------------
  GOAL        : head position == food position
  SUB-GOAL 1  : find a path from head to food (search algorithm)
  SUB-GOAL 2  : if no path exists → survive as long as possible (flood fill)
  SUB-GOAL 3  : if no survival move → accept death

"""

import time

from .knowledge_base import KnowledgeBase
from .inference_engine import InferenceResult
from strategies import get_strategy
from strategies.base import SearchResult
from engine.grid import wrap, best_flood_direction
from engine.constants import DIRS
from config import get_config


class PlannerResult:
    """
    The Planner's decision for one tick.

    direction   : (dx, dy) to move this frame
    search      : SearchResult from the algorithm (or None if inference handled it)
    used_fallback : True if flood-fill survival was used
    algorithm   : name of the algorithm that ran
    """
    __slots__ = ("direction", "search", "used_fallback", "algorithm")

    def __init__(self, direction, search: SearchResult | None,
                 used_fallback: bool, algorithm: str):
        self.direction     = direction
        self.search        = search
        self.used_fallback = used_fallback
        self.algorithm     = algorithm


class Planner:
    """
    Stateless planner — called every tick the inference engine defers to it.
    """

    def plan(
        self,
        kb:      KnowledgeBase,
        score:   int,
    ) -> PlannerResult:
        """
        BACKWARD CHAINING entry point.
        Goal: reach food.
        Returns the direction to move and supporting metadata.
        """
        cfg = get_config()

        # ── Algorithm selection (hybrid or static) ───────────────────────
        if cfg.hybrid_mode and score >= cfg.hybrid_threshold:
            alg_name = cfg.hybrid_late
        elif cfg.hybrid_mode:
            alg_name = cfg.hybrid_early
        else:
            alg_name = cfg.algorithm

        strategy = get_strategy(alg_name)

        # ── Sub-goal 1: find path to food ────────────────────────────────
        result: SearchResult = strategy.find_path(kb.head, kb.food, kb.obstacles)

        if len(result.path) >= 2:
            next_cell = result.path[1]
            direction = _cell_to_direction(kb.head, next_cell)
            return PlannerResult(
                direction=direction,
                search=result,
                used_fallback=False,
                algorithm=alg_name,
            )

        # ── Sub-goal 2: no path → flood-fill survival ────────────────────
        nb = best_flood_direction(kb.head, kb.obstacles, kb.direction)
        if nb:
            direction = _cell_to_direction(kb.head, nb)
            return PlannerResult(
                direction=direction,
                search=result,     # result has empty path, but stats are valid
                used_fallback=True,
                algorithm=alg_name,
            )

        # ── Sub-goal 3: no move at all (accept death) ────────────────────
        return PlannerResult(
            direction=kb.direction,
            search=result,
            used_fallback=True,
            algorithm=alg_name,
        )


# ── Helper ───────────────────────────────────────────────────────────────────

def _cell_to_direction(frm: tuple, to: tuple) -> tuple[int, int]:
    dx = to[0] - frm[0]
    dy = to[1] - frm[1]
    if dx >  1: dx = -1
    if dx < -1: dx =  1
    if dy >  1: dy = -1
    if dy < -1: dy =  1
    return (dx, dy)
