"""
Snake Game with AI (A* Search) — Enhanced Edition
==================================================
Controls:
  Arrow Keys    Manual movement
  A             Toggle AI mode ON / OFF
  P  or SPACE   Pause / Resume
  N             Step forward one frame (while paused)
  R             Restart game
  ESC           Quit

Run:
  pip install pygame
  python3 snake_game.py
"""

import pygame
import random
import heapq
import sys
from collections import deque

# ════════════════════════════════════════════════════════
#  LAYOUT & CONSTANTS
# ════════════════════════════════════════════════════════
GAME_W, GAME_H = 600, 400
PANEL_W        = 320
WINDOW_W       = GAME_W + PANEL_W
WINDOW_H       = GAME_H

CELL  = 20
COLS  = GAME_W // CELL   # 30
ROWS  = GAME_H // CELL   # 20

BASE_FPS      = 6
FPS_INCREMENT = 1
MAX_FPS       = 14

# ── Palette ──────────────────────────────────────────
C_BG           = ( 8,  10,  18)
C_PANEL        = (12,  15,  26)
C_PANEL_BORDER = (38,  48,  76)
C_GRID         = (18,  22,  36)

C_HEAD         = (  0, 245, 145)
C_BODY         = (  0, 185, 105)
C_FOOD         = (255,  55,  80)
C_PATH_DOT     = ( 55,  85, 195)
C_CLOSED_DOT   = ( 80,  40,  80)   # explored (closed set) tint

C_TEXT         = (205, 215, 235)
C_DIM          = ( 75,  88, 115)
C_ACCENT       = (  0, 225, 255)
C_GOOD         = (  0, 225, 140)
C_WARN         = (255, 205,  55)
C_BAD          = (255,  75,  75)
C_PAUSE        = (255, 185,   0)
C_SECTION      = ( 36,  46,  72)
C_HIGHLIGHT    = ( 22,  30,  55)   # row background highlight

UP    = ( 0, -1)
DOWN  = ( 0,  1)
LEFT  = (-1,  0)
RIGHT = ( 1,  0)
DIRS  = [UP, DOWN, LEFT, RIGHT]
DIR_NAMES = {UP:"UP", DOWN:"DOWN", LEFT:"LEFT", RIGHT:"RIGHT"}
DIR_ARROW = {UP:"↑", DOWN:"↓", LEFT:"←", RIGHT:"→"}


# ════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════
def wrap(x, y):
    """Portal wrap: exit one edge → enter opposite edge."""
    return x % COLS, y % ROWS


def manhattan_wrap(a, b):
    """
    Wrap-aware Manhattan distance.
    On each axis: take min(direct gap, wrap-around gap).
    Always admissible (never overestimates real cost).
    """
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return min(dx, COLS - dx) + min(dy, ROWS - dy)


# ════════════════════════════════════════════════════════
#  A*  SEARCH
# ════════════════════════════════════════════════════════
def astar(start, goal, obstacles):
    """
    Classic A* on a toroidal (wrap-around) grid.

    OPEN SET   — candidates to explore, ordered by f = g + h
    CLOSED SET — already fully explored nodes
    g(n)       — exact steps from start to n
    h(n)       — wrap-aware Manhattan distance n → goal
    f(n)       — g + h  (lower = higher priority)

    Returns (path, closed_set, g_scores) so the panel can visualise them.
      path        : list of cells [start … goal], or []
      closed_set  : set of cells that were explored
      g_scores    : dict {cell: g_value}
    """
    open_heap  = []
    heapq.heappush(open_heap, (manhattan_wrap(start, goal), 0, start))

    came_from  = {}
    g_scores   = {start: 0}
    closed_set = set()

    while open_heap:
        f, g, current = heapq.heappop(open_heap)

        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path, closed_set, g_scores

        if current in closed_set:
            continue
        closed_set.add(current)

        cx, cy = current
        for dx, dy in DIRS:
            nb = wrap(cx + dx, cy + dy)
            if nb in obstacles or nb in closed_set:
                continue
            tg = g + 1
            if tg < g_scores.get(nb, 10**9):
                g_scores[nb]   = tg
                came_from[nb]  = current
                h = manhattan_wrap(nb, goal)
                heapq.heappush(open_heap, (tg + h, tg, nb))

    return [], closed_set, g_scores


# ════════════════════════════════════════════════════════
#  SNAKE
# ════════════════════════════════════════════════════════
class Snake:
    def __init__(self):
        self.reset()

    def reset(self):
        cx, cy         = COLS // 2, ROWS // 2
        self.body      = deque([(cx, cy), (cx-1, cy), (cx-2, cy)])
        self.direction = RIGHT
        self.grew      = False

    def set_direction(self, d):
        opp = (-d[0], -d[1])
        if d != opp or len(self.body) == 1:
            self.direction = d

    def move(self):
        hx, hy   = self.head
        dx, dy   = self.direction
        new_head = wrap(hx + dx, hy + dy)
        self.body.appendleft(new_head)
        if not self.grew:
            self.body.pop()
        else:
            self.grew = False
        return new_head

    def grow(self):       self.grew = True
    def hits_self(self):  return self.head in list(self.body)[1:]

    @property
    def head(self):       return self.body[0]
    @property
    def body_set(self):   return set(self.body)
    @property
    def length(self):     return len(self.body)


# ════════════════════════════════════════════════════════
#  FOOD
# ════════════════════════════════════════════════════════
class Food:
    def __init__(self, occupied):
        self.position = self._pick(occupied)

    def _pick(self, occupied):
        empty = [(c, r) for c in range(COLS) for r in range(ROWS)
                 if (c, r) not in occupied]
        return random.choice(empty) if empty else (0, 0)

    def respawn(self, occupied):
        self.position = self._pick(occupied)


# ════════════════════════════════════════════════════════
#  LIVE STATE  (snapshot fed to the panel every tick)
# ════════════════════════════════════════════════════════
class LiveState:
    def __init__(self):
        self.reset()

    def reset(self):
        # game
        self.mode        = "MANUAL"
        self.paused      = False
        self.score       = 0
        self.fps         = BASE_FPS
        self.snake_len   = 3
        self.head_pos    = (0, 0)
        self.food_pos    = (0, 0)
        self.direction   = "RIGHT"
        self.dir_arrow   = "→"
        # A*
        self.path_found  = False
        self.path_len    = 0
        self.g_head      = 0
        self.h_head      = 0
        self.f_head      = 0
        self.g_next      = 0
        self.h_next      = 0
        self.f_next      = 0
        self.next_cell   = None
        self.open_count  = 0
        self.closed_count= 0
        self.fallback    = False
        self.wrap_used   = False
        # decision log: last 5 lines of reasoning
        self.log         = []

    def push_log(self, msg):
        self.log.append(msg)
        if len(self.log) > 6:
            self.log.pop(0)


# ════════════════════════════════════════════════════════
#  GAME
# ════════════════════════════════════════════════════════
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("Snake  +  A* AI  |  P=Pause  N=Step  A=AI  R=Restart")
        self.clock  = pygame.time.Clock()

        self.fB  = pygame.font.SysFont("Courier New", 14, bold=True)
        self.fN  = pygame.font.SysFont("Courier New", 12)
        self.fXS = pygame.font.SysFont("Courier New", 11)
        self.fLG = pygame.font.SysFont("Courier New", 30, bold=True)

        self.ls = LiveState()
        self.reset()

    # ── reset ──────────────────────────────────────────
    def reset(self):
        self.snake      = Snake()
        self.food       = Food(self.snake.body_set)
        self.score      = 0
        self.fps        = BASE_FPS
        self.game_over  = False
        self.paused     = False
        self.ai_mode    = False
        self.ai_path    = []
        self.closed_vis = set()   # A* closed set for visualisation
        self.ls.reset()

    # ── events ─────────────────────────────────────────
    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                k = ev.key
                if k == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if k == pygame.K_r:
                    self.reset(); return
                if k in (pygame.K_p, pygame.K_SPACE):
                    if not self.game_over:
                        self.paused = not self.paused
                        self.ls.push_log("PAUSED" if self.paused else "RESUMED")
                if k == pygame.K_n and self.paused and not self.game_over:
                    # step one frame forward while paused
                    self._tick()
                if k == pygame.K_a:
                    self.ai_mode = not self.ai_mode
                    self.ai_path = []
                    self.ls.push_log("AI ON" if self.ai_mode else "AI OFF")
                if not self.ai_mode and not self.game_over and not self.paused:
                    if k == pygame.K_UP:    self.snake.set_direction(UP)
                    elif k == pygame.K_DOWN:  self.snake.set_direction(DOWN)
                    elif k == pygame.K_LEFT:  self.snake.set_direction(LEFT)
                    elif k == pygame.K_RIGHT: self.snake.set_direction(RIGHT)

    # ── AI decision ────────────────────────────────────
    def _ai_decide(self):
        head      = self.snake.head
        food      = self.food.position
        obstacles = set(list(self.snake.body)[:-1])

        path, closed, g_scores = astar(head, food, obstacles)

        self.closed_vis = closed

        ls = self.ls
        ls.g_head = 0
        ls.h_head = manhattan_wrap(head, food)
        ls.f_head = ls.h_head
        ls.closed_count = len(closed)
        ls.open_count   = len(g_scores)

        if len(path) >= 2:
            next_cell     = path[1]
            self.ai_path  = path
            ls.path_found = True
            ls.path_len   = len(path) - 1
            ls.fallback   = False

            ls.g_next = 1
            ls.h_next = manhattan_wrap(next_cell, food)
            ls.f_next = ls.g_next + ls.h_next
            ls.next_cell = next_cell

            dx = next_cell[0] - head[0]
            dy = next_cell[1] - head[1]
            if dx >  1: dx = -1
            if dx < -1: dx =  1
            if dy >  1: dy = -1
            if dy < -1: dy =  1
            self.snake.set_direction((dx, dy))

            ls.wrap_used = (
                (head[0] == 0       and next_cell[0] == COLS-1) or
                (head[0] == COLS-1  and next_cell[0] == 0)      or
                (head[1] == 0       and next_cell[1] == ROWS-1) or
                (head[1] == ROWS-1  and next_cell[1] == 0)
            )
            if ls.wrap_used:
                ls.push_log("Portal wrap used this step!")
            ls.push_log("Path found: %d steps to food" % ls.path_len)
        else:
            self.ai_path  = []
            ls.path_found = False
            ls.path_len   = 0
            ls.fallback   = True
            ls.next_cell  = None
            ls.push_log("No A* path! Using flood-fill fallback")
            nb = self._fallback(head, obstacles)
            if nb:
                dx = nb[0] - head[0]
                dy = nb[1] - head[1]
                if dx >  1: dx = -1
                if dx < -1: dx =  1
                if dy >  1: dy = -1
                if dy < -1: dy =  1
                self.snake.set_direction((dx, dy))

    def _fallback(self, head, obstacles):
        best, best_s = None, -1
        for dx, dy in DIRS:
            nb = wrap(head[0]+dx, head[1]+dy)
            if nb in obstacles:
                continue
            opp = (-self.snake.direction[0], -self.snake.direction[1])
            if (dx, dy) == opp and self.snake.length > 1:
                continue
            s = self._flood(nb, obstacles)
            if s > best_s:
                best_s, best = s, nb
        return best

    def _flood(self, start, obstacles, lim=120):
        vis, q, n = {start}, deque([start]), 0
        while q and n < lim:
            cx, cy = q.popleft(); n += 1
            for dx, dy in DIRS:
                nb = wrap(cx+dx, cy+dy)
                if nb not in obstacles and nb not in vis:
                    vis.add(nb); q.append(nb)
        return n

    # ── single game tick ───────────────────────────────
    def _tick(self):
        if self.game_over:
            return
        if self.ai_mode:
            self._ai_decide()
        new_head = self.snake.move()
        if self.snake.hits_self():
            self.game_over = True
            self.ls.push_log("GAME OVER — self collision!")
            return
        if new_head == self.food.position:
            self.snake.grow()
            self.score += 1
            self.food.respawn(self.snake.body_set)
            self.ai_path    = []
            self.closed_vis = set()
            self.fps        = min(BASE_FPS + (self.score // 5)*FPS_INCREMENT, MAX_FPS)
            self.ls.push_log("Ate food! Score = %d" % self.score)
        # sync live state
        ls = self.ls
        ls.mode      = "AI AUTO" if self.ai_mode else "MANUAL"
        ls.paused    = self.paused
        ls.score     = self.score
        ls.fps       = self.fps
        ls.snake_len = self.snake.length
        ls.head_pos  = self.snake.head
        ls.food_pos  = self.food.position
        ls.direction = DIR_NAMES.get(self.snake.direction, "?")
        ls.dir_arrow = DIR_ARROW.get(self.snake.direction, "?")
        if not self.ai_mode:
            ls.path_found = False
            ls.path_len   = 0
            ls.fallback   = False
            ls.wrap_used  = False
            ls.next_cell  = None

    # ── update ─────────────────────────────────────────
    def update(self):
        if not self.paused:
            self._tick()

    # ════════════════════════════════════════════════════
    #  DRAWING
    # ════════════════════════════════════════════════════
    def _draw_grid(self):
        for c in range(0, GAME_W, CELL):
            pygame.draw.line(self.screen, C_GRID, (c,0), (c,GAME_H))
        for r in range(0, GAME_H, CELL):
            pygame.draw.line(self.screen, C_GRID, (0,r), (GAME_W,r))

    def _draw_closed(self):
        """Faintly tint cells in A* closed set (explored but not on path)."""
        for cx, cy in self.closed_vis:
            if (cx, cy) not in self.snake.body_set and (cx, cy) != self.food.position:
                s = pygame.Surface((CELL-2, CELL-2), pygame.SRCALPHA)
                s.fill((80, 40, 110, 40))
                self.screen.blit(s, (cx*CELL+1, cy*CELL+1))

    def _draw_path(self):
        if not self.ai_path or len(self.ai_path) < 3:
            return
        for i, (cx, cy) in enumerate(self.ai_path[1:-1], 1):
            # Gradient: brighter near the head
            alpha = max(80, 200 - i * 8)
            s = pygame.Surface((CELL-6, CELL-6), pygame.SRCALPHA)
            s.fill((55, 85, 200, alpha))
            self.screen.blit(s, (cx*CELL+3, cy*CELL+3))

    def _draw_snake(self):
        body_list = list(self.snake.body)
        total = len(body_list)
        for i, (cx, cy) in enumerate(body_list):
            if i == 0:
                col = C_HEAD
            else:
                # fade body from bright to dark
                t   = i / max(total - 1, 1)
                col = (int(C_BODY[0]*(1-t*0.5)),
                       int(C_BODY[1]*(1-t*0.5)),
                       int(C_BODY[2]*(1-t*0.5)))
            rect = pygame.Rect(cx*CELL+1, cy*CELL+1, CELL-2, CELL-2)
            pygame.draw.rect(self.screen, col, rect, border_radius=5)
            if i == 0:
                # eyes
                ex1 = cx*CELL + 5
                ex2 = cx*CELL + CELL - 7
                ey  = cy*CELL + 7
                pygame.draw.circle(self.screen, C_BG, (ex1, ey), 2)
                pygame.draw.circle(self.screen, C_BG, (ex2, ey), 2)

    def _draw_food(self):
        cx, cy = self.food.position
        px, py = cx*CELL + CELL//2, cy*CELL + CELL//2
        pygame.draw.circle(self.screen, C_FOOD,         (px, py), CELL//2-2)
        pygame.draw.circle(self.screen, (255,150,165),  (px-3,py-3), 3)

    def _draw_hud(self):
        sc = self.fB.render("Score: %d" % self.score, True, C_TEXT)
        self.screen.blit(sc, (8, 5))
        ai_c = C_ACCENT if self.ai_mode else C_DIM
        ai_s = self.fB.render("AI:%s" % ("ON" if self.ai_mode else "OFF"), True, ai_c)
        self.screen.blit(ai_s, (GAME_W - ai_s.get_width() - 8, 5))
        hint = self.fXS.render(
            "[A]AI  [P/SPC]Pause  [N]Step  [R]Restart  [ESC]Quit", True, C_DIM)
        self.screen.blit(hint, (8, GAME_H - 15))

    def _draw_pause_overlay(self):
        ov = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        ov.fill((8, 10, 18, 160))
        self.screen.blit(ov, (0, 0))
        ps = self.fLG.render("PAUSED", True, C_PAUSE)
        ns = self.fB.render("Press N to step one frame forward", True, C_DIM)
        rs = self.fB.render("Press P or SPACE to resume", True, C_DIM)
        self.screen.blit(ps, ps.get_rect(center=(GAME_W//2, GAME_H//2 - 30)))
        self.screen.blit(ns, ns.get_rect(center=(GAME_W//2, GAME_H//2 + 10)))
        self.screen.blit(rs, rs.get_rect(center=(GAME_W//2, GAME_H//2 + 32)))

    def _draw_game_over(self):
        ov = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        ov.fill((8, 10, 18, 210))
        self.screen.blit(ov, (0, 0))
        for surf, cy in [
            (self.fLG.render("GAME  OVER", True, C_BAD),            GAME_H//2-38),
            (self.fB.render("Score: %d" % self.score, True, C_TEXT), GAME_H//2+6),
            (self.fB.render("Press R to Restart", True, C_ACCENT),   GAME_H//2+36),
        ]:
            self.screen.blit(surf, surf.get_rect(center=(GAME_W//2, cy)))

    # ════════════════════════════════════════════════════
    #  EXPLANATION PANEL
    # ════════════════════════════════════════════════════
    def _draw_panel(self):
        px = GAME_W
        pygame.draw.rect(self.screen, C_PANEL, (px, 0, PANEL_W, WINDOW_H))
        pygame.draw.line(self.screen, C_PANEL_BORDER, (px, 0), (px, WINDOW_H), 2)

        ls   = self.ls
        x0   = px + 10
        rw   = PANEL_W - 20   # usable row width
        y    = 6
        SLH  = 13   # small line height
        MLH  = 16   # medium line height
        TLH  = 18   # title line height

        # ── helpers ─────────────────────────────────
        def title(text, col=C_ACCENT):
            nonlocal y
            pygame.draw.rect(self.screen, C_HIGHLIGHT,
                             (px+2, y-1, PANEL_W-4, TLH+2))
            self.screen.blit(self.fB.render(text, True, col), (x0, y))
            y += TLH
            pygame.draw.line(self.screen, C_SECTION,
                             (x0, y), (px+PANEL_W-10, y), 1)
            y += 4

        def kv(label, value, vc=C_TEXT, lc=C_DIM):
            nonlocal y
            self.screen.blit(self.fXS.render(label, True, lc),         (x0,       y))
            self.screen.blit(self.fXS.render(str(value), True, vc),    (x0 + 148, y))
            y += SLH

        def bar(label, val, maxv, col=C_ACCENT):
            """Mini progress bar row."""
            nonlocal y
            self.screen.blit(self.fXS.render(label, True, C_DIM), (x0, y))
            bx, bw, bh = x0+100, rw-102, 8
            pygame.draw.rect(self.screen, C_SECTION, (bx, y+2, bw, bh), border_radius=3)
            fill = int(bw * min(val/max(maxv,1), 1.0))
            if fill > 0:
                pygame.draw.rect(self.screen, col, (bx, y+2, fill, bh), border_radius=3)
            self.screen.blit(self.fXS.render(str(val), True, col), (bx+bw+4, y))
            y += SLH + 2

        def note(text, col=C_DIM, indent=0):
            nonlocal y
            words, line = text.split(), ""
            mx = rw - indent
            for w in words:
                test = line + w + " "
                if self.fXS.size(test)[0] > mx:
                    self.screen.blit(
                        self.fXS.render(line.strip(), True, col), (x0+indent, y))
                    y += SLH; line = w + " "
                else:
                    line = test
            if line.strip():
                self.screen.blit(
                    self.fXS.render(line.strip(), True, col), (x0+indent, y))
                y += SLH

        def spacer(n=4):
            nonlocal y; y += n

        # ══════════════════════════════════════════════
        #  SECTION 1 — GAME STATE
        # ══════════════════════════════════════════════
        title("1. GAME STATE")
        mc = C_ACCENT if self.ai_mode else C_GOOD
        pc = C_PAUSE  if self.paused  else C_DIM
        kv("Mode:",          ls.mode,              mc)
        kv("Status:",
           "PAUSED  (N=step)" if ls.paused else "RUNNING",
           pc)
        kv("Score:",         ls.score,             C_GOOD)
        kv("Snake length:",  "%d cells" % ls.snake_len, C_TEXT)
        kv("Speed:",         "%d FPS" % ls.fps,    C_TEXT)
        kv("Head position:", "col%d row%d" % ls.head_pos, C_TEXT)
        kv("Food position:", "col%d row%d" % ls.food_pos, C_FOOD)
        kv("Moving:",        "%s  %s" % (ls.dir_arrow, ls.direction), C_WARN)
        spacer(6)

        # ══════════════════════════════════════════════
        #  SECTION 2 — A* ALGORITHM EXPLAINED
        # ══════════════════════════════════════════════
        title("2. HOW A* WORKS")
        note("A* is a best-first search. It explores the grid by always picking the node with the lowest total cost f(n).", C_DIM)
        spacer(3)
        note("FORMULA:", C_ACCENT)
        spacer(1)

        # Formula box
        fbox_y = y
        pygame.draw.rect(self.screen, C_HIGHLIGHT,
                         (x0, y, rw, SLH*3+8), border_radius=4)
        pygame.draw.rect(self.screen, C_SECTION,
                         (x0, y, rw, SLH*3+8), 1, border_radius=4)
        y += 4
        note("  f(n) = g(n)  +  h(n)", C_ACCENT, indent=4)
        note("  g(n) = exact steps taken so far", C_GOOD, indent=4)
        note("  h(n) = estimated steps remaining", C_WARN, indent=4)
        y += 4
        spacer(3)

        note("WHY IT WORKS:", C_ACCENT)
        note("g keeps path cost honest. h guides search toward the goal. Together they guarantee the shortest path as long as h never OVER-estimates.", C_DIM)
        spacer(3)

        note("HEURISTIC USED:", C_ACCENT)
        note("Manhattan distance with wrap-around: |dx| + |dy|, but taking the shorter path through a wall when applicable.", C_TEXT)
        spacer(6)

        # ══════════════════════════════════════════════
        #  SECTION 3 — LIVE A* VALUES THIS STEP
        # ══════════════════════════════════════════════
        title("3. LIVE A* VALUES")
        if self.ai_mode:
            hd = manhattan_wrap(ls.head_pos, ls.food_pos)
            note("At the snake HEAD (g=0 because we start here):", C_DIM)
            kv("  g(head) =",  "0  (start node)",     C_GOOD)
            kv("  h(head) =",  "%d  (dist to food)" % hd, C_WARN)
            kv("  f(head) =",  "%d  (= 0 + %d)" % (hd,hd), C_ACCENT)
            spacer(3)
            if ls.next_cell and ls.path_found:
                note("At the NEXT chosen cell %s:" % str(ls.next_cell), C_DIM)
                kv("  g(next) =",  "1  (one step taken)",   C_GOOD)
                kv("  h(next) =",  "%d  (dist to food)" % ls.h_next, C_WARN)
                kv("  f(next) =",  "%d  (= 1 + %d)" % (ls.f_next, ls.h_next), C_ACCENT)
            spacer(3)
            bar("Nodes explored:", ls.closed_count, max(ls.closed_count,50), C_DIM)
        else:
            note("Enable AI mode (press A) to see live A* values.", C_DIM)
        spacer(6)

        # ══════════════════════════════════════════════
        #  SECTION 4 — PATH STATUS
        # ══════════════════════════════════════════════
        title("4. PATH STATUS")
        if self.ai_mode:
            if ls.path_found:
                kv("Result:",    "PATH FOUND",          C_GOOD)
                kv("Length:",    "%d steps" % ls.path_len, C_TEXT)
                kv("Fallback:",  "NO",                  C_GOOD)
                note("Blue cells = planned route. Purple tint = cells A* explored but rejected.", C_DIM)
            else:
                kv("Result:",    "NO PATH EXISTS",      C_BAD)
                kv("Fallback:",  "YES — flood fill",    C_WARN)
                note("Flood fill counts open cells in each direction and picks the move that keeps the most space available.", C_WARN)
        else:
            note("Path planning is only active in AI mode.", C_DIM)
        spacer(6)

        # ══════════════════════════════════════════════
        #  SECTION 5 — WRAP-AROUND
        # ══════════════════════════════════════════════
        title("5. WRAP-AROUND WALLS")
        wc = C_ACCENT if ls.wrap_used else C_DIM
        kv("Portal this step:", "YES!" if ls.wrap_used else "no", wc)
        note("The grid is a torus: right edge connects to left edge, top connects to bottom. The snake reappears on the opposite side. A* knows this via the wrap-aware heuristic.", C_DIM)
        spacer(6)

        # ══════════════════════════════════════════════
        #  SECTION 6 — DECISION LOG
        # ══════════════════════════════════════════════
        title("6. DECISION LOG", C_DIM)
        for line in ls.log:
            note("> " + line, C_TEXT)
        spacer(4)

        # ══════════════════════════════════════════════
        #  SECTION 7 — CONTROLS
        # ══════════════════════════════════════════════
        title("7. CONTROLS", C_DIM)
        for k, v in [
            ("Arrow Keys", "Move (manual mode)"),
            ("A",          "Toggle AI on / off"),
            ("P / SPACE",  "Pause / Resume"),
            ("N",          "Step 1 frame (while paused)"),
            ("R",          "Restart game"),
            ("ESC",        "Quit"),
        ]:
            kv(k, v, C_TEXT)

    # ════════════════════════════════════════════════════
    #  MAIN RENDER
    # ════════════════════════════════════════════════════
    def draw(self):
        self.screen.fill(C_BG)
        self._draw_grid()
        if self.ai_mode:
            self._draw_closed()
            self._draw_path()
        self._draw_food()
        self._draw_snake()
        self._draw_hud()
        self._draw_panel()
        if self.paused and not self.game_over:
            self._draw_pause_overlay()
        if self.game_over:
            self._draw_game_over()
        pygame.display.flip()

    # ════════════════════════════════════════════════════
    #  GAME LOOP
    # ════════════════════════════════════════════════════
    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(self.fps)


# ════════════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════════════
if __name__ == "__main__":
    Game().run()