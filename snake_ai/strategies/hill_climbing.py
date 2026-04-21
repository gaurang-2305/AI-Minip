"""
strategies/hill_climbing.py
===========================
Hill Climbing — a local search that greedily moves to the neighbour with
the lowest heuristic value, with NO backtracking.

AI Concepts
-----------
  Category      : Local / greedy search (does NOT build a full path tree)
  Completeness  : NO — gets permanently stuck in local minima
  Optimality    : NO
  Space         : O(1) — only one node is in memory at a time
  Time          : O(d) per step in the best case; can loop forever

How it differs from Greedy BFS
-------------------------------
  Greedy BFS maintains a priority queue and remembers visited nodes, so it
  can backtrack around dead ends.  Hill Climbing has NO open list — it only
  looks at the current node's neighbours and picks the single best one.

  If every neighbour is worse than the current position, the search FAILS
  (stuck at a local minimum or plateau).  This happens very often in Snake
  once the body creates L-shaped or U-shaped obstacles.

  In Snake this means: Hill Climbing reaches the food quickly in early game
  but DIES much more often than A* or BFS in late game.

Restart strategy
----------------
  Pure hill climbing on a grid loops when it gets stuck. Here we add a
  limited random-restart: if no improving neighbour exists, the algorithm
  picks a random non-obstacle neighbour and returns that single step.
  This keeps the snake moving even when optimality is impossible.
"""

import time
import random

from .base import BaseStrategy, SearchResult
from engine.grid import manhattan_wrap, wrap, neighbours as grid_neighbours
from engine.constants import DIRS


class HillClimbingStrategy(BaseStrategy):

    @property
    def name(self) -> str:
        return "hill_climbing"

    def find_path(
        self,
        start:     tuple[int, int],
        goal:      tuple[int, int],
        obstacles: set,
    ) -> SearchResult:
        """
        Hill Climbing returns a path of AT MOST a few steps (it is a local
        search, not a complete planner).  If it reaches the goal during its
        walk, the full walked path is returned.  Otherwise it returns whatever
        partial path it managed before getting stuck.

        The caller (Planner) must check path length: if len < 2 the fallback
        flood-fill survival strategy kicks in.
        """
        t0      = time.perf_counter()
        current = start
        path    = [start]
        visited = {start}
        steps   = 0
        MAX_STEPS = 200   # safety cap to prevent infinite loops

        while current != goal and steps < MAX_STEPS:
            cx, cy = current

            # ── Evaluate all 4 neighbours ────────────────────────────────
            best_nb = None
            best_h  = manhattan_wrap(current, goal)  # current heuristic value

            for dx, dy in DIRS:
                nb = wrap(cx + dx, cy + dy)
                if nb in obstacles or nb in visited:
                    continue
                h = manhattan_wrap(nb, goal)
                if h < best_h:
                    best_h, best_nb = h, nb

            if best_nb is None:
                # ── Local minimum: random restart to an unvisited safe cell ──
                safe = [
                    wrap(cx + dx, cy + dy)
                    for dx, dy in DIRS
                    if wrap(cx + dx, cy + dy) not in obstacles
                    and wrap(cx + dx, cy + dy) not in visited
                ]
                if not safe:
                    break   # fully trapped — return partial path
                best_nb = random.choice(safe)

            visited.add(best_nb)
            path.append(best_nb)
            current = best_nb
            steps  += 1

        ms = (time.perf_counter() - t0) * 1000
        goal_reached = (current == goal)

        return SearchResult(
            path=path if goal_reached or len(path) >= 2 else [],
            nodes_explored=len(visited),
            nodes_seen=len(visited),
            time_ms=ms,
            algorithm=self.name,
        )
