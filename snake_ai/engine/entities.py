"""
engine/entities.py
==================
Snake and Food game entities — the physical objects in the game world.

AI Concept: these objects, together with the grid, form the KNOWLEDGE BASE.
The AI reads their state each frame to make decisions.
"""

import random
from collections import deque
from .constants import COLS, ROWS, RIGHT
from .grid import wrap


# ── Snake ─────────────────────────────────────────────────────────────────────

class Snake:
    """
    Represents the snake's body, direction, and movement.

    body:      deque of (col, row) tuples, head at index 0.
    direction: current movement direction as (dx, dy).
    grew:      flag — if True the tail is not removed on next move (ate food).
    """

    def __init__(self):
        self.reset()

    def reset(self):
        cx, cy        = COLS // 2, ROWS // 2
        self.body     = deque([(cx, cy), (cx - 1, cy), (cx - 2, cy)])
        self.direction = RIGHT
        self.grew      = False

    # ── movement ────────────────────────────────────────────────────────────

    def set_direction(self, d: tuple[int, int]):
        """
        Change direction. Prevents reversing directly into the body.
        180° reversal is only allowed if the snake is length 1.
        """
        opposite = (-d[0], -d[1])
        if d != opposite or len(self.body) == 1:
            self.direction = d

    def move(self) -> tuple[int, int]:
        """
        Advance the snake one step.
        Returns the new head position.
        """
        hx, hy   = self.head
        dx, dy   = self.direction
        new_head = wrap(hx + dx, hy + dy)
        self.body.appendleft(new_head)
        if not self.grew:
            self.body.pop()
        else:
            self.grew = False
        return new_head

    def grow(self):
        """Mark that the next move should not remove the tail."""
        self.grew = True

    # ── collision ────────────────────────────────────────────────────────────

    def hits_self(self) -> bool:
        """True if the head overlaps any body segment."""
        return self.head in list(self.body)[1:]

    # ── properties ──────────────────────────────────────────────────────────

    @property
    def head(self) -> tuple[int, int]:
        return self.body[0]

    @property
    def body_set(self) -> set:
        return set(self.body)

    @property
    def length(self) -> int:
        return len(self.body)


# ── Food ──────────────────────────────────────────────────────────────────────

class Food:
    """
    A single food pellet placed on a random empty cell.
    """

    def __init__(self, occupied: set):
        self.position = self._pick(occupied)

    def _pick(self, occupied: set) -> tuple[int, int]:
        empty = [
            (c, r)
            for c in range(COLS)
            for r in range(ROWS)
            if (c, r) not in occupied
        ]
        return random.choice(empty) if empty else (0, 0)

    def respawn(self, occupied: set):
        """Place food at a new random unoccupied cell."""
        self.position = self._pick(occupied)
