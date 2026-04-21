"""
engine/grid.py
==============
Pure-function grid utilities.
No state — these are shared helpers for all search algorithms and game logic.

AI Concept: these form part of the KNOWLEDGE BASE — they encode the rules
of the environment (grid topology, movement, distance).
"""

from .constants import COLS, ROWS, DIRS


# ── Basic grid ops ───────────────────────────────────────────────────────────

def wrap(x: int, y: int) -> tuple[int, int]:
    """Wrap coordinates to a toroidal grid (snake exits one edge → enters opposite)."""
    return x % COLS, y % ROWS


def neighbours(pos: tuple[int, int], obstacles: set) -> list[tuple[int, int]]:
    """
    Return all 4-directional neighbours of `pos` that are not in `obstacles`.
    Edges wrap around.
    """
    cx, cy = pos
    result = []
    for dx, dy in DIRS:
        nb = wrap(cx + dx, cy + dy)
        if nb not in obstacles:
            result.append(nb)
    return result


def direction_to(frm: tuple[int, int], to: tuple[int, int]) -> tuple[int, int]:
    """
    Compute the logical direction vector from `frm` to `to`,
    accounting for wrap-around edges.
    Returns one of UP/DOWN/LEFT/RIGHT.
    """
    dx = to[0] - frm[0]
    dy = to[1] - frm[1]
    # Correct for wrap-around on each axis
    if dx >  1:  dx = -1
    if dx < -1:  dx =  1
    if dy >  1:  dy = -1
    if dy < -1:  dy =  1
    return (dx, dy)


# ── Heuristics ───────────────────────────────────────────────────────────────

def manhattan_wrap(a: tuple[int, int], b: tuple[int, int]) -> int:
    """
    Wrap-aware Manhattan distance between two grid cells.
    On each axis, takes the shorter of the direct or wrap-around path.

    AI Concept: this is the ADMISSIBLE heuristic h(n) used by A* and Greedy.
    It never over-estimates true cost → guarantees A* optimality.
    """
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return min(dx, COLS - dx) + min(dy, ROWS - dy)


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Plain (no wrap) Manhattan distance — used by non-wrap-aware algorithms."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# ── Flood fill (survival heuristic) ─────────────────────────────────────────

def flood_fill(start: tuple[int, int], obstacles: set, limit: int = 120) -> int:
    """
    BFS flood fill: count reachable empty cells from `start`, up to `limit`.

    AI Concept: used as a FALLBACK STRATEGY when no path to food exists.
    By maximising reachable space, the snake avoids trapping itself.
    """
    from collections import deque
    visited = {start}
    queue   = deque([start])
    count   = 0
    while queue and count < limit:
        cx, cy = queue.popleft()
        count  += 1
        for dx, dy in DIRS:
            nb = wrap(cx + dx, cy + dy)
            if nb not in obstacles and nb not in visited:
                visited.add(nb)
                queue.append(nb)
    return count


def best_flood_direction(
    head: tuple[int, int],
    obstacles: set,
    current_dir: tuple[int, int],
    limit: int = 120,
) -> tuple[int, int] | None:
    """
    Evaluate all 4 neighbours via flood fill and return the direction
    toward the neighbour with the most open space.
    Skips cells in obstacles and the direct reverse of `current_dir`.

    Returns the raw direction tuple (dx, dy), or None if no safe move exists.
    """
    best_nb    = None
    best_score = -1
    reverse    = (-current_dir[0], -current_dir[1])

    for dx, dy in DIRS:
        nb = wrap(head[0] + dx, head[1] + dy)
        if nb in obstacles:
            continue
        if (dx, dy) == reverse:
            continue
        score = flood_fill(nb, obstacles, limit)
        if score > best_score:
            best_score, best_nb = score, nb

    return best_nb
