"""
strategies/base.py
==================
Abstract base class for all search-algorithm strategies.

AI Concept: the STRATEGY PATTERN makes algorithms hot-swappable.
The Planner (ai/planner.py) depends only on this interface, not on any
specific algorithm implementation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SearchResult:
    """
    Unified return value from any search algorithm.

    path:           List of (col, row) from start (inclusive) to goal (inclusive).
                    Empty list means no path was found.
    nodes_explored: Size of the closed/visited set after search completes.
    nodes_seen:     Total nodes ever placed into the open structure
                    (open + closed, i.e. len(g_scores) for A*).
    time_ms:        Wall-clock time for this search (milliseconds).
    algorithm:      Name tag for the algorithm that produced this result.
    """
    path:           list
    nodes_explored: int
    nodes_seen:     int
    time_ms:        float
    algorithm:      str


class BaseStrategy(ABC):
    """
    Every search algorithm must implement exactly one method: find_path().
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier used in config, UI, and logs."""
        ...

    @abstractmethod
    def find_path(
        self,
        start: tuple[int, int],
        goal:  tuple[int, int],
        obstacles: set,
    ) -> SearchResult:
        """
        Find a path from `start` to `goal` avoiding `obstacles`.

        Parameters
        ----------
        start     : (col, row) of the snake's current head.
        goal      : (col, row) of the food.
        obstacles : set of (col, row) cells the snake cannot enter
                    (usually the snake body minus the tail tip).

        Returns
        -------
        SearchResult — path is [] if no route exists.
        """
        ...
