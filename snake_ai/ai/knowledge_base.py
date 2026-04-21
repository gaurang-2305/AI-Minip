"""
ai/knowledge_base.py
====================
The KNOWLEDGE BASE (KB) — the AI's complete picture of the world.
"""

from engine.entities import Snake, Food
from engine.grid import wrap, manhattan_wrap, flood_fill
from engine.constants import DIRS, COLS, ROWS


class KnowledgeBase:
    def __init__(self, snake: Snake, food: Food):
        self.head         = snake.head
        self.food         = food.position
        self.body_set     = snake.body_set
        self.snake_length = snake.length
        self.direction    = snake.direction

        body_list = list(snake.body)
        self.obstacles = set(body_list[:-1]) if len(body_list) > 1 else set()

        self.food_adjacent  = self._food_adjacent()
        self.danger_ahead   = self._danger_ahead()
        self.open_space     = flood_fill(self.head, self.obstacles, limit=120)
        self.dist_to_food   = manhattan_wrap(self.head, self.food)

    def _food_adjacent(self) -> bool:
        hx, hy = self.head
        for dx, dy in DIRS:
            if wrap(hx + dx, hy + dy) == self.food:
                return True
        return False

    def _danger_ahead(self) -> bool:
        hx, hy = self.head
        dx, dy = self.direction
        next_cell = wrap(hx + dx, hy + dy)
        return next_cell in self.obstacles

    def safe_neighbours(self) -> list[tuple[int, int]]:
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