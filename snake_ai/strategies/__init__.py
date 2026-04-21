"""
strategies/__init__.py
======================
Algorithm registry.
Maps string names (from config) → strategy instances.
"""

from .base          import BaseStrategy, SearchResult
from .astar         import AStarStrategy
from .bfs           import BFSStrategy
from .dfs           import DFSStrategy
from .greedy        import GreedyStrategy
from .hill_climbing import HillClimbingStrategy

# ── Registry ─────────────────────────────────────────────────────────────────
# All strategies are singletons — they hold no mutable state between calls.

_REGISTRY: dict[str, BaseStrategy] = {
    "astar":         AStarStrategy(),
    "bfs":           BFSStrategy(),
    "dfs":           DFSStrategy(),
    "greedy":        GreedyStrategy(),
    "hill_climbing": HillClimbingStrategy(),
}


def get_strategy(name: str) -> BaseStrategy:
    """Return the strategy instance for the given name. Raises KeyError if unknown."""
    if name not in _REGISTRY:
        raise KeyError(
            f"Unknown strategy '{name}'. "
            f"Available: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[name]


def list_strategies() -> list[str]:
    return list(_REGISTRY.keys())
