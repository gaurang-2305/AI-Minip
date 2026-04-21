"""
strategies/greedy.py
====================
Greedy Best-First Search — always expands the node that LOOKS closest to goal.

AI Concepts
-----------
  Category      : Informed search (uses heuristic)
  Completeness  : Yes on finite graphs (with visited tracking)
  Optimality    : NO — does NOT guarantee shortest path
  Space         : O(b^d)
  Time          : O(b log b) in the best case; O(b^d) worst case

How it differs from A*
-----------------------
  A*   selects nodes by  f(n) = g(n) + h(n)
  Greedy selects nodes by       h(n)  alone  (ignores cost already paid)

  This makes Greedy faster in open environments — it races toward the goal —
  but it can take long, non-optimal detours when the direct path is blocked,
  because it has no memory of how far it has already travelled (no g term).

  In Snake, Greedy tends to work well early-game (sparse grid) but struggles
  in late-game when the body fills the grid and traps form easily.

Wrap-awareness
--------------
  Uses manhattan_wrap() so the heuristic correctly crosses grid edges.
"""

import heapq
import time

from .base import BaseStrategy, SearchResult
from engine.grid import manhattan_wrap, wrap
from engine.constants import DIRS


class GreedyStrategy(BaseStrategy):

    @property
    def name(self) -> str:
        return "greedy"

    def find_path(
        self,
        start:     tuple[int, int],
        goal:      tuple[int, int],
        obstacles: set,
    ) -> SearchResult:
        t0 = time.perf_counter()

        # Heap entries: (h, node) — ordered ONLY by heuristic, no g term
        open_heap  = [(manhattan_wrap(start, goal), start)]
        came_from  : dict[tuple, tuple | None] = {start: None}
        visited    : set                        = {start}

        while open_heap:
            _, current = heapq.heappop(open_heap)

            if current == goal:
                # ── Reconstruct path ────────────────────────────────────────
                path = []
                node = current
                while node is not None:
                    path.append(node)
                    node = came_from[node]
                path.reverse()
                ms = (time.perf_counter() - t0) * 1000
                return SearchResult(
                    path=path,
                    nodes_explored=len(visited),
                    nodes_seen=len(visited),
                    time_ms=ms,
                    algorithm=self.name,
                )

            cx, cy = current
            for dx, dy in DIRS:
                nb = wrap(cx + dx, cy + dy)
                if nb in obstacles or nb in visited:
                    continue
                visited.add(nb)
                came_from[nb] = current
                h = manhattan_wrap(nb, goal)
                heapq.heappush(open_heap, (h, nb))

        # No path found
        ms = (time.perf_counter() - t0) * 1000
        return SearchResult(
            path=[],
            nodes_explored=len(visited),
            nodes_seen=len(visited),
            time_ms=ms,
            algorithm=self.name,
        )
