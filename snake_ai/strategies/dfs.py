"""
strategies/dfs.py
=================
Depth-First Search — explores one branch to its full depth before backtracking.

AI Concepts
-----------
  Category      : Uninformed (blind) search
  Completeness  : Yes on finite graphs (with visited tracking)
  Optimality    : NO — DFS does NOT guarantee the shortest path
  Space         : O(bd) — only stores the current path + stack
  Time          : O(b^d)

How it differs from BFS / A*
-----------------------------
  DFS dives deep immediately, often finding a very LONG, winding path to food.
  It uses a LIFO stack instead of a queue (BFS) or min-heap (A*).
  Because it isn't breadth-bounded, the path length can be many times longer
  than the optimal route — but it uses less memory than BFS.

  On a wrapped grid, DFS sometimes finds paths that spiral around the entire
  grid before reaching the food just 5 cells away.

Wrap-awareness
--------------
  Uses engine.grid.wrap() so edges connect correctly.
"""

import time

from .base import BaseStrategy, SearchResult
from engine.grid import wrap
from engine.constants import DIRS


class DFSStrategy(BaseStrategy):

    @property
    def name(self) -> str:
        return "dfs"

    def find_path(
        self,
        start:     tuple[int, int],
        goal:      tuple[int, int],
        obstacles: set,
    ) -> SearchResult:
        t0 = time.perf_counter()

        # Stack entries: node
        stack      = [start]
        came_from  : dict[tuple, tuple | None] = {start: None}
        visited    : set                        = {start}

        while stack:
            current = stack.pop()   # LIFO — this is the key DFS distinction

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
                stack.append(nb)

        # No path found
        ms = (time.perf_counter() - t0) * 1000
        return SearchResult(
            path=[],
            nodes_explored=len(visited),
            nodes_seen=len(visited),
            time_ms=ms,
            algorithm=self.name,
        )
