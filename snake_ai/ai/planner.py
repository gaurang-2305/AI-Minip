"""
ai/planner.py  — Backward Chaining Goal-Driven Planner
"""

from .knowledge_base import KnowledgeBase
from .inference_engine import InferenceResult
from strategies import get_strategy
from strategies.base import SearchResult
from engine.grid import wrap, best_flood_direction
from engine.constants import DIRS
from config import get_config


class PlannerResult:
    __slots__ = ("direction", "search", "used_fallback", "algorithm")

    def __init__(self, direction, search: SearchResult | None,
                 used_fallback: bool, algorithm: str):
        self.direction     = direction
        self.search        = search
        self.used_fallback = used_fallback
        self.algorithm     = algorithm


class Planner:

    def plan(self, kb: KnowledgeBase, score: int) -> PlannerResult:
        cfg = get_config()

        if cfg.hybrid_mode and score >= cfg.hybrid_threshold:
            alg_name = cfg.hybrid_late
        elif cfg.hybrid_mode:
            alg_name = cfg.hybrid_early
        else:
            alg_name = cfg.algorithm

        strategy = get_strategy(alg_name)
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

        nb = best_flood_direction(kb.head, kb.obstacles, kb.direction)
        if nb:
            direction = _cell_to_direction(kb.head, nb)
            return PlannerResult(
                direction=direction,
                search=result,
                used_fallback=True,
                algorithm=alg_name,
            )

        return PlannerResult(
            direction=kb.direction,
            search=result,
            used_fallback=True,
            algorithm=alg_name,
        )


def _cell_to_direction(frm: tuple, to: tuple) -> tuple[int, int]:
    dx = to[0] - frm[0]
    dy = to[1] - frm[1]
    if dx >  1: dx = -1
    if dx < -1: dx =  1
    if dy >  1: dy = -1
    if dy < -1: dy =  1
    return (dx, dy)