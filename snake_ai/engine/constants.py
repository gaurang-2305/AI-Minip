"""
engine/constants.py
===================
All layout, colour, and game constants in one place.
Importing this module is the single source of truth for the entire project.
"""

# ── Window / Grid ────────────────────────────────────────────────────────────
GAME_W,  GAME_H  = 620, 460
PANEL_W          = 380
WINDOW_W         = GAME_W + PANEL_W
WINDOW_H         = GAME_H

CELL  = 20
COLS  = GAME_W  // CELL     # 31 columns
ROWS  = GAME_H  // CELL     # 23 rows

# ── Gameplay ─────────────────────────────────────────────────────────────────
BASE_FPS      = 6
FPS_INCREMENT = 1
MAX_FPS       = 14
SCROLLBAR_W   = 6

# ── Directions ───────────────────────────────────────────────────────────────
UP    = ( 0, -1)
DOWN  = ( 0,  1)
LEFT  = (-1,  0)
RIGHT = ( 1,  0)
DIRS  = [UP, DOWN, LEFT, RIGHT]

DIR_NAMES  = {UP: "UP",  DOWN: "DOWN",  LEFT: "LEFT",  RIGHT: "RIGHT"}
DIR_ARROW  = {UP: "↑",   DOWN: "↓",     LEFT: "←",     RIGHT: "→"}
DIR_KEYS   = {
    "UP":    UP,
    "DOWN":  DOWN,
    "LEFT":  LEFT,
    "RIGHT": RIGHT,
}

# ── Palette ──────────────────────────────────────────────────────────────────
C_BG            = (  7,   9,  16)
C_PANEL         = ( 10,  13,  22)
C_PANEL_BORDER  = ( 45,  58,  92)
C_GRID          = ( 16,  20,  33)

C_HEAD          = (  0, 248, 150)
C_BODY          = (  0, 188, 108)
C_FOOD          = (255,  50,  78)
C_PATH_DOT      = ( 55,  88, 200)

C_TEXT          = (210, 220, 240)
C_DIM           = ( 90, 105, 135)
C_ACCENT        = (  0, 228, 255)
C_GOOD          = (  0, 230, 145)
C_WARN          = (255, 210,  55)
C_BAD           = (255,  75,  75)
C_PAUSE         = (255, 185,   0)
C_HIGHLIGHT     = ( 20,  28,  50)
C_SECTION_LINE  = ( 35,  46,  72)
C_TAB_ACTIVE    = ( 22,  32,  58)
C_TAB_INACTIVE  = ( 12,  16,  28)
C_TAB_HOVER     = ( 18,  25,  45)
C_SCROLLBAR     = ( 45,  60,  95)
C_SCROLLBAR_THB = ( 80, 110, 160)

# Per-algorithm accent colours (used in panels and comparison)
ALG_COLOURS = {
    "astar":        (  0, 228, 255),  # cyan
    "bfs":          ( 80, 210, 130),  # green
    "dfs":          (255, 120,  60),  # orange
    "greedy":       (220,  80, 220),  # magenta
    "hill_climbing":(255, 220,  50),  # yellow
}
ALG_LABELS = {
    "astar":         "A* (A-Star)",
    "bfs":           "BFS",
    "dfs":           "DFS",
    "greedy":        "Greedy Best-First",
    "hill_climbing": "Hill Climbing",
}

# ── Panel tabs ───────────────────────────────────────────────────────────────
TABS = ["GAME STATE", "A* / ALGORITHM", "LIVE VALUES", "LOG & CONTROLS", "COMPARISON"]
