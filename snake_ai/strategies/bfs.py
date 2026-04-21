"""
strategies/bfs.py
=================
Breadth-First Search — finds the SHORTEST PATH in unweighted graphs.

AI Concepts
-----------
  Category      : Uninformed (blind) search
  Completeness  : Yes — finds a path if one exists
  Optimality    : Yes — guaranteed shortest path (all edges cost 1)
  Space         : O(b^d) — must store all nodes at current frontier depth
  Time          : O(b^d)

How it differs from A*
----------------------
  BFS expands nodes layer by layer (by depth), with no heuristic guidance.
  It always finds the optimal path but explores FAR more nodes than A*
  because it has no sense of which direction leads toward the goal.

  On a 31×23 grid with a long snake, BFS may explore 300+ nodes vs A*'s 30.

Wrap-awareness
--------------
  Uses engine.grid.wrap() so the snake can path through edges correctly.
"""

import time
from collections import deque

from .base import BaseStrategy, SearchResult
from engine.grid import wrap
from engine.constants import DIRS


class BFSStrategy(BaseStrategy):

    @property
    def name(self) -> str:
        return "bfs"

    def find_path(
        self,
        start:     tuple[int, int],
        goal:      tuple[int, int],
        obstacles: set,
    ) -> SearchResult:
        t0 = time.perf_counter()

        # Each queue entry: node
        queue      = deque([start])
        came_from  : dict[tuple, tuple | None] = {start: None}
        visited    : set                        = {start}

        while queue:
            current = queue.popleft()

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
                queue.append(nb)

        # No path found
        ms = (time.perf_counter() - t0) * 1000
        return SearchResult(
            path=[],
            nodes_explored=len(visited),
            nodes_seen=len(visited),
            time_ms=ms,
            algorithm=self.name,
        )
