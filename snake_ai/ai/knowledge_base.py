"""
ai/knowledge_base.py
====================
The KNOWLEDGE BASE (KB) — the AI's complete picture of the world.

In classical AI architecture, the KB stores facts about the environment.
Here it wraps Snake + Food + Grid into a single queryable object that the
Inference Engine and Planner read without needing direct access to the
game entities.

Design
------
  KnowledgeBase is rebuilt (or refreshed) each tick from the raw engine
  objects.  It exposes derived facts (adjacency, reachability, danger) that
  would be expensive or messy to recompute in multiple places.
"""

from engine.entities import Snake, Food
from engine.grid import wrap, manhattan_wrap, flood_fill
from engine.constants import DIRS, COLS, ROWS


class KnowledgeBase:
    """
    Facts available each tick:

    Positional
      head          : (col, row) of the snake's head
      food          : (col, row) of the current food
      obstacles     : set of cells the snake cannot enter (body minus tail tip)
      body_set      : full snake body set (including tail tip)
      snake_length  : int

    Derived
      food_adjacent : True if food is directly next to the head (1 step away)
      danger_ahead  : True if moving in current direction leads to collision
      open_space    : flood-fill count from head (measure of freedom)
      dist_to_food  : wrap-aware Manhattan distance head → food
    """

    def __init__(self, snake: Snake, food: Food):
        self.head         = snake.head
        self.food         = food.position
        self.body_set     = snake.body_set
        self.snake_length = snake.length
        self.direction    = snake.direction

        # Obstacles = body minus the very last tail cell (tail will move away)
        body_list = list(snake.body)
        self.obstacles = set(body_list[:-1]) if len(body_list) > 1 else set()

        # ── Derived facts ─────────────────────────────────────────────────
        self.food_adjacent  = self._food_adjacent()
        self.danger_ahead   = self._danger_ahead()
        self.open_space     = flood_fill(self.head, self.obstacles, limit=120)
        self.dist_to_food   = manhattan_wrap(self.head, self.food)

    # ── Internal fact computation ─────────────────────────────────────────

    def _food_adjacent(self) -> bool:
        """True if food is exactly 1 step from the head."""
        hx, hy = self.head
        for dx, dy in DIRS:
            if wrap(hx + dx, hy + dy) == self.food:
                return True
        return False

    def _danger_ahead(self) -> bool:
        """
        True if the cell directly in front of the head (in current direction)
        is an obstacle (would cause immediate self-collision).
        """
        hx, hy = self.head
        dx, dy = self.direction
        next_cell = wrap(hx + dx, hy + dy)
        return next_cell in self.obstacles

    def safe_neighbours(self) -> list[tuple[int, int]]:
        """Return all 4 neighbours that are not in obstacles."""
        hx, hy = self.head
        return [
            wrap(hx + dx, hy + dy)
            for dx, dy in DIRS
            if wrap(hx + dx, hy + dy) not in self.obstacles
        ]

    def is_safe(self, pos: tuple[int, int]) -> bool:
        return pos not in self.obstacles

    def __repr__(self):
        return (
            f"KB(head={self.head}, food={self.food}, "
            f"len={self.snake_length}, food_adj={self.food_adjacent}, "
            f"danger={self.danger_ahead}, space={self.open_space})"
        )
