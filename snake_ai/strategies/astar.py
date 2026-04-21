"""
strategies/astar.py
===================
A* Search — finds the OPTIMAL (shortest) path.

AI Concepts
-----------
  Category      : Informed search (uses heuristic)
  Completeness  : Yes — always finds a path if one exists
  Optimality    : Yes — guaranteed shortest path (admissible heuristic)
  Space         : O(b^d) — all nodes in open+closed sets
  Time          : O(b^d) in the worst case; much better in practice with good h

How it works
------------
  f(n) = g(n) + h(n)
  g(n) = exact cost from start to n (number of steps)
  h(n) = wrap-aware Manhattan distance from n to goal (admissible estimate)

  A min-heap is used so we always expand the lowest-f node first.
  Once the goal is popped from the heap, we have the shortest path.
"""

import heapq
import time

from .base import BaseStrategy, SearchResult
from engine.grid import manhattan_wrap, wrap
from engine.constants import DIRS


class AStarStrategy(BaseStrategy):

    @property
    def name(self) -> str:
        return "astar"

    def find_path(
        self,
        start:     tuple[int, int],
        goal:      tuple[int, int],
        obstacles: set,
    ) -> SearchResult:
        t0 = time.perf_counter()

        # open_heap entries: (f, g, node)
        # tie-break on g (prefer deeper nodes when f is equal → greedier)
        open_heap  = []
        heapq.heappush(open_heap, (manhattan_wrap(start, goal), 0, start))

        came_from  : dict[tuple, tuple] = {}
        g_scores   : dict[tuple, int]   = {start: 0}
        closed_set : set                = set()

        while open_heap:
            f, g, current = heapq.heappop(open_heap)

            if current == goal:
                # ── Reconstruct path ────────────────────────────────────────
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                ms = (time.perf_counter() - t0) * 1000
                return SearchResult(
                    path=path,
                    nodes_explored=len(closed_set),
                    nodes_seen=len(g_scores),
                    time_ms=ms,
                    algorithm=self.name,
                )

            if current in closed_set:
                continue
            closed_set.add(current)

            cx, cy = current
            for dx, dy in DIRS:
                nb = wrap(cx + dx, cy + dy)
                if nb in obstacles or nb in closed_set:
                    continue
                tentative_g = g + 1
                if tentative_g < g_scores.get(nb, 10 ** 9):
                    g_scores[nb]  = tentative_g
                    came_from[nb] = current
                    h = manhattan_wrap(nb, goal)
                    heapq.heappush(open_heap, (tentative_g + h, tentative_g, nb))

        # No path found
        ms = (time.perf_counter() - t0) * 1000
        return SearchResult(
            path=[],
            nodes_explored=len(closed_set),
            nodes_seen=len(g_scores),
            time_ms=ms,
            algorithm=self.name,
        )

    def get_closed_set_after(
        self,
        start:     tuple[int, int],
        goal:      tuple[int, int],
        obstacles: set,
    ) -> set:
        """
        Re-run search and return the closed set for visualisation.
        Separate from find_path to keep the main API clean.
        """
        open_heap  = []
        heapq.heappush(open_heap, (manhattan_wrap(start, goal), 0, start))
        g_scores   : dict[tuple, int] = {start: 0}
        closed_set : set              = set()

        while open_heap:
            f, g, current = heapq.heappop(open_heap)
            if current in closed_set:
                continue
            closed_set.add(current)
            if current == goal:
                break
            cx, cy = current
            for dx, dy in DIRS:
                nb = wrap(cx + dx, cy + dy)
                if nb in obstacles or nb in closed_set:
                    continue
                tg = g + 1
                if tg < g_scores.get(nb, 10 ** 9):
                    g_scores[nb] = tg
                    heapq.heappush(open_heap, (tg + manhattan_wrap(nb, goal), tg, nb))

        return closed_set
