"""
Snake Game with AI (A* Search) — Enhanced Edition v3
=====================================================
Fixes:
  - Scrollable panel tabs (mouse wheel + scrollbar)
  - A* tab: Fallback Strategy fully visible
  - Live A* tab: Wrap-Around section fully visible
  - Log tab: Tips section fully visible

Controls:
  Arrow Keys    Manual movement
  A             Toggle AI mode ON / OFF
  P  or SPACE   Pause / Resume
  N             Step forward one frame (while paused)
  R             Restart game
  TAB           Cycle panel tabs
  1-4           Jump to panel tab
  Scroll Wheel  Scroll panel content
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
GAME_W, GAME_H = 620, 460
PANEL_W        = 380
WINDOW_W       = GAME_W + PANEL_W
WINDOW_H       = GAME_H

CELL  = 20
COLS  = GAME_W // CELL
ROWS  = GAME_H // CELL

BASE_FPS      = 6
FPS_INCREMENT = 1
MAX_FPS       = 14

SCROLLBAR_W   = 6   # scrollbar width in pixels

# ── Palette ──────────────────────────────────────────
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

UP    = ( 0, -1)
DOWN  = ( 0,  1)
LEFT  = (-1,  0)
RIGHT = ( 1,  0)
DIRS  = [UP, DOWN, LEFT, RIGHT]
DIR_NAMES = {UP:"UP", DOWN:"DOWN", LEFT:"LEFT", RIGHT:"RIGHT"}
DIR_ARROW = {UP:"↑", DOWN:"↓", LEFT:"←", RIGHT:"→"}

TABS = ["GAME STATE", "A* ALGORITHM", "LIVE VALUES", "LOG & CONTROLS"]

# ════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════
def wrap(x, y):
    return x % COLS, y % ROWS

def manhattan_wrap(a, b):
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return min(dx, COLS - dx) + min(dy, ROWS - dy)

# ════════════════════════════════════════════════════════
#  A*  SEARCH
# ════════════════════════════════════════════════════════
def astar(start, goal, obstacles):
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
#  LIVE STATE
# ════════════════════════════════════════════════════════
class LiveState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.mode        = "MANUAL"
        self.paused      = False
        self.score       = 0
        self.fps         = BASE_FPS
        self.snake_len   = 3
        self.head_pos    = (0, 0)
        self.food_pos    = (0, 0)
        self.direction   = "RIGHT"
        self.dir_arrow   = "→"
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
        self.log         = []

    def push_log(self, msg):
        self.log.append(msg)
        if len(self.log) > 10:
            self.log.pop(0)

# ════════════════════════════════════════════════════════
#  GAME
# ════════════════════════════════════════════════════════
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("Snake  +  A* AI  |  TAB=Switch Panel  A=AI  P=Pause  R=Restart")
        self.clock  = pygame.time.Clock()

        self.f_title  = pygame.font.SysFont("Consolas", 13, bold=True)
        self.f_body   = pygame.font.SysFont("Consolas", 12)
        self.f_small  = pygame.font.SysFont("Consolas", 11)
        self.f_hud    = pygame.font.SysFont("Consolas", 13, bold=True)
        self.f_huge   = pygame.font.SysFont("Consolas", 32, bold=True)
        self.f_tab    = pygame.font.SysFont("Consolas", 11, bold=True)
        self.f_val    = pygame.font.SysFont("Consolas", 13, bold=True)

        self.ls        = LiveState()
        self.panel_tab = 0

        # Scroll state per tab: offset in pixels
        self.tab_scroll    = [0] * len(TABS)
        # Track content height per tab for scrollbar
        self.tab_content_h = [WINDOW_H] * len(TABS)

        # Tab bar height constants
        self.TAB_BAR_H    = 42   # tabs + divider
        self.PANEL_CONTENT_H = WINDOW_H - self.TAB_BAR_H  # visible area height

        self.reset()

    def reset(self):
        self.snake      = Snake()
        self.food       = Food(self.snake.body_set)
        self.score      = 0
        self.fps        = BASE_FPS
        self.game_over  = False
        self.paused     = False
        self.ai_mode    = False
        self.ai_path    = []
        self.closed_vis = set()
        self.ls.reset()
        self.tab_scroll = [0] * len(TABS)

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
                        self.ls.push_log("⏸ PAUSED" if self.paused else "▶ RESUMED")
                if k == pygame.K_n and self.paused and not self.game_over:
                    self._tick()
                if k == pygame.K_a:
                    self.ai_mode = not self.ai_mode
                    self.ai_path = []
                    self.ls.push_log("🤖 AI ON — A* active" if self.ai_mode else "🕹  AI OFF — Manual")
                if k == pygame.K_TAB:
                    self.panel_tab = (self.panel_tab + 1) % len(TABS)
                for i, knum in enumerate([pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4]):
                    if k == knum:
                        self.panel_tab = i
                if not self.ai_mode and not self.game_over and not self.paused:
                    if k == pygame.K_UP:    self.snake.set_direction(UP)
                    elif k == pygame.K_DOWN:  self.snake.set_direction(DOWN)
                    elif k == pygame.K_LEFT:  self.snake.set_direction(LEFT)
                    elif k == pygame.K_RIGHT: self.snake.set_direction(RIGHT)
            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                self._handle_tab_click(mx, my)
                # Scrollbar drag start ignored for simplicity — wheel is enough
            if ev.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                if mx >= GAME_W:
                    tab = self.panel_tab
                    content_h = self.tab_content_h[tab]
                    max_scroll = max(0, content_h - self.PANEL_CONTENT_H)
                    self.tab_scroll[tab] = max(0, min(max_scroll,
                        self.tab_scroll[tab] - ev.y * 22))

    def _handle_tab_click(self, mx, my):
        if mx < GAME_W:
            return
        tab_area_y = 8
        tw = (PANEL_W - 16) // len(TABS)
        x0 = GAME_W + 8
        for i in range(len(TABS)):
            tx = x0 + i * tw
            if tx <= mx <= tx + tw and tab_area_y <= my <= tab_area_y + 26:
                self.panel_tab = i
                return

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
                ls.push_log("🌀 Portal wrap used this step!")
            ls.push_log("✓ Path: %d steps to food" % ls.path_len)
        else:
            self.ai_path  = []
            ls.path_found = False
            ls.path_len   = 0
            ls.fallback   = True
            ls.next_cell  = None
            ls.push_log("⚠ No A* path! Flood-fill fallback")
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
            self.ls.push_log("💀 GAME OVER — self collision!")
            return
        if new_head == self.food.position:
            self.snake.grow()
            self.score += 1
            self.food.respawn(self.snake.body_set)
            self.ai_path    = []
            self.closed_vis = set()
            self.fps        = min(BASE_FPS + (self.score // 5)*FPS_INCREMENT, MAX_FPS)
            self.ls.push_log("🍎 Ate food! Score = %d" % self.score)
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

    def update(self):
        if not self.paused:
            self._tick()

    # ════════════════════════════════════════════════════
    #  DRAWING — GAME AREA
    # ════════════════════════════════════════════════════
    def _draw_grid(self):
        for c in range(0, GAME_W, CELL):
            pygame.draw.line(self.screen, C_GRID, (c, 0), (c, GAME_H))
        for r in range(0, GAME_H, CELL):
            pygame.draw.line(self.screen, C_GRID, (0, r), (GAME_W, r))

    def _draw_closed(self):
        for cx, cy in self.closed_vis:
            if (cx, cy) not in self.snake.body_set and (cx, cy) != self.food.position:
                s = pygame.Surface((CELL-2, CELL-2), pygame.SRCALPHA)
                s.fill((80, 40, 110, 38))
                self.screen.blit(s, (cx*CELL+1, cy*CELL+1))

    def _draw_path(self):
        if not self.ai_path or len(self.ai_path) < 3:
            return
        for i, (cx, cy) in enumerate(self.ai_path[1:-1], 1):
            alpha = max(60, 200 - i * 7)
            s = pygame.Surface((CELL-6, CELL-6), pygame.SRCALPHA)
            s.fill((55, 88, 210, alpha))
            self.screen.blit(s, (cx*CELL+3, cy*CELL+3))

    def _draw_snake(self):
        body_list = list(self.snake.body)
        total = len(body_list)
        for i, (cx, cy) in enumerate(body_list):
            if i == 0:
                col = C_HEAD
            else:
                t   = i / max(total - 1, 1)
                col = (int(C_BODY[0]*(1-t*0.55)),
                       int(C_BODY[1]*(1-t*0.55)),
                       int(C_BODY[2]*(1-t*0.55)))
            rect = pygame.Rect(cx*CELL+1, cy*CELL+1, CELL-2, CELL-2)
            pygame.draw.rect(self.screen, col, rect, border_radius=5)
            if i == 0:
                ex1 = cx*CELL + 5
                ex2 = cx*CELL + CELL - 7
                ey  = cy*CELL + 7
                pygame.draw.circle(self.screen, C_BG, (ex1, ey), 2)
                pygame.draw.circle(self.screen, C_BG, (ex2, ey), 2)

    def _draw_food(self):
        cx, cy = self.food.position
        px, py = cx*CELL + CELL//2, cy*CELL + CELL//2
        pygame.draw.circle(self.screen, C_FOOD,        (px, py), CELL//2-2)
        pygame.draw.circle(self.screen, (255,150,165), (px-3,py-3), 3)

    def _draw_hud(self):
        sc_txt  = "Score: %d" % self.score
        sc_surf = self.f_hud.render(sc_txt, True, C_GOOD)
        sc_rect = sc_surf.get_rect(topleft=(10, 6))
        pygame.draw.rect(self.screen, (0,0,0,120),
                         sc_rect.inflate(12, 6), border_radius=4)
        self.screen.blit(sc_surf, sc_rect)

        ai_col  = C_ACCENT if self.ai_mode else C_DIM
        ai_txt  = "AI: ON" if self.ai_mode else "AI: OFF"
        ai_surf = self.f_hud.render(ai_txt, True, ai_col)
        ai_rect = ai_surf.get_rect(topright=(GAME_W - 10, 6))
        self.screen.blit(ai_surf, ai_rect)

        hint = self.f_small.render(
            "[A] AI   [P] Pause   [N] Step   [R] Restart   [TAB] Panel   [1-4] Tab", True, C_DIM)
        self.screen.blit(hint, (8, GAME_H - 14))

    def _draw_pause_overlay(self):
        ov = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        ov.fill((7, 9, 16, 165))
        self.screen.blit(ov, (0, 0))
        ps = self.f_huge.render("PAUSED", True, C_PAUSE)
        ns = self.f_body.render("Press N to step one frame forward", True, C_DIM)
        rs = self.f_body.render("Press P or SPACE to resume", True, C_DIM)
        self.screen.blit(ps, ps.get_rect(center=(GAME_W//2, GAME_H//2 - 28)))
        self.screen.blit(ns, ns.get_rect(center=(GAME_W//2, GAME_H//2 + 12)))
        self.screen.blit(rs, rs.get_rect(center=(GAME_W//2, GAME_H//2 + 34)))

    def _draw_game_over(self):
        ov = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        ov.fill((7, 9, 16, 215))
        self.screen.blit(ov, (0, 0))
        for surf, cy in [
            (self.f_huge.render("GAME  OVER", True, C_BAD),             GAME_H//2-36),
            (self.f_hud.render("Final Score: %d" % self.score, True, C_TEXT), GAME_H//2+8),
            (self.f_hud.render("Press R to Restart", True, C_ACCENT),  GAME_H//2+36),
        ]:
            self.screen.blit(surf, surf.get_rect(center=(GAME_W//2, cy)))

    # ════════════════════════════════════════════════════
    #  PANEL  (tabbed + scrollable)
    # ════════════════════════════════════════════════════
    def _draw_panel(self):
        px = GAME_W
        pygame.draw.rect(self.screen, C_PANEL, (px, 0, PANEL_W, WINDOW_H))
        pygame.draw.line(self.screen, C_PANEL_BORDER, (px, 0), (px, WINDOW_H), 2)

        ls  = self.ls
        x0  = px + 12
        rw  = PANEL_W - 24 - SCROLLBAR_W - 4   # subtract scrollbar width

        # ── Tab bar ──────────────────────────────────
        tab_y  = 8
        tab_h  = 26
        tw     = (PANEL_W - 16) // len(TABS)
        for i, name in enumerate(TABS):
            tx   = x0 + i * tw
            active = (i == self.panel_tab)
            bg   = C_TAB_ACTIVE if active else C_TAB_INACTIVE
            pygame.draw.rect(self.screen, bg,
                             (tx, tab_y, tw - 3, tab_h), border_radius=4)
            if active:
                pygame.draw.rect(self.screen, C_ACCENT,
                                 (tx, tab_y + tab_h - 2, tw - 3, 2), border_radius=1)
            short = [str(i+1)+":"+t.split()[0] for i, t in enumerate(TABS)][i]
            tc = C_ACCENT if active else C_DIM
            ts = self.f_tab.render(short, True, tc)
            self.screen.blit(ts, ts.get_rect(center=(tx + (tw-3)//2, tab_y + tab_h//2)))

        line_y = tab_y + tab_h + 4
        pygame.draw.line(self.screen, C_PANEL_BORDER,
                         (px + 4, line_y), (px + PANEL_W - 4, line_y), 1)

        content_top = line_y + 8   # screen y where content area starts
        content_h   = WINDOW_H - content_top  # visible height

        # ── Render tab content into an off-screen surface ──
        # First pass: measure content height by rendering to a tall surface
        RENDER_H = 2000
        surf = pygame.Surface((PANEL_W, RENDER_H))
        surf.fill(C_PANEL)

        # x offset inside the surface
        sx = 12
        srw = rw

        sy = 8  # start y in surface
        if self.panel_tab == 0:
            sy = self._tab_game_state(surf, sx, sy, srw, ls)
        elif self.panel_tab == 1:
            sy = self._tab_algorithm(surf, sx, sy, srw, ls)
        elif self.panel_tab == 2:
            sy = self._tab_live_values(surf, sx, sy, srw, ls)
        elif self.panel_tab == 3:
            sy = self._tab_log_controls(surf, sx, sy, srw, ls)

        actual_content_h = sy + 12
        self.tab_content_h[self.panel_tab] = actual_content_h

        # Clamp scroll
        max_scroll = max(0, actual_content_h - content_h)
        scroll = min(self.tab_scroll[self.panel_tab], max_scroll)
        self.tab_scroll[self.panel_tab] = scroll

        # Blit the visible slice of the surface
        clip_rect = pygame.Rect(0, scroll, PANEL_W, content_h)
        self.screen.blit(surf, (px, content_top), clip_rect)

        # ── Scrollbar ────────────────────────────────
        sb_x = px + PANEL_W - SCROLLBAR_W - 2
        sb_y = content_top
        sb_h = content_h
        pygame.draw.rect(self.screen, C_SCROLLBAR, (sb_x, sb_y, SCROLLBAR_W, sb_h), border_radius=3)

        if actual_content_h > content_h:
            ratio       = content_h / actual_content_h
            thumb_h     = max(20, int(sb_h * ratio))
            thumb_y     = sb_y + int((sb_h - thumb_h) * scroll / max_scroll)
            pygame.draw.rect(self.screen, C_SCROLLBAR_THB,
                             (sb_x, thumb_y, SCROLLBAR_W, thumb_h), border_radius=3)
            # Scroll hint text at bottom right
            hint = self.f_small.render("↕ scroll", True, C_DIM)
            self.screen.blit(hint, hint.get_rect(bottomright=(px + PANEL_W - 10, WINDOW_H - 4)))

    # ════════════════════════════════════════════════════
    #  SURFACE-BASED DRAWING HELPERS
    #  All draw onto `surf` at local coordinates
    # ════════════════════════════════════════════════════
    def _section_header(self, surf, text, x, y, rw, col=C_ACCENT):
        pygame.draw.rect(surf, C_HIGHLIGHT, (x - 4, y - 2, rw + 8, 20), border_radius=3)
        s = self.f_title.render(text, True, col)
        surf.blit(s, (x, y))
        return y + 22

    def _kv_row(self, surf, label, value, x, y, lc=C_DIM, vc=C_TEXT, split=165):
        surf.blit(self.f_small.render(label, True, lc),      (x, y))
        surf.blit(self.f_val.render(str(value), True, vc),   (x + split, y))
        return y + 16

    def _note(self, surf, text, x, y, rw, col=C_DIM, font=None):
        font = font or self.f_small
        words = text.split()
        line  = ""
        for w in words:
            test = line + w + " "
            if font.size(test)[0] > rw:
                surf.blit(font.render(line.strip(), True, col), (x, y))
                y += 14; line = w + " "
            else:
                line = test
        if line.strip():
            surf.blit(font.render(line.strip(), True, col), (x, y))
            y += 14
        return y

    def _mini_bar(self, surf, label, val, maxv, x, y, rw, col=C_ACCENT):
        surf.blit(self.f_small.render(label, True, C_DIM), (x, y))
        bx = x + 120; bw = rw - 128; bh = 9
        pygame.draw.rect(surf, C_HIGHLIGHT, (bx, y + 2, bw, bh), border_radius=4)
        fill = int(bw * min(val / max(maxv, 1), 1.0))
        if fill > 0:
            pygame.draw.rect(surf, col, (bx, y + 2, fill, bh), border_radius=4)
        surf.blit(self.f_small.render(str(val), True, col), (bx + bw + 5, y))
        return y + 16

    def _formula_box(self, surf, lines, colors, x, y, rw):
        h = len(lines) * 18 + 10
        pygame.draw.rect(surf, C_HIGHLIGHT,    (x, y, rw, h), border_radius=5)
        pygame.draw.rect(surf, C_SECTION_LINE, (x, y, rw, h), 1, border_radius=5)
        fy = y + 6
        for line, col in zip(lines, colors):
            s = self.f_body.render(line, True, col)
            surf.blit(s, (x + 10, fy))
            fy += 18
        return y + h + 6

    # ════════════════════════════════════════════════════
    #  TAB 0 — GAME STATE
    # ════════════════════════════════════════════════════
    def _tab_game_state(self, surf, x, y, rw, ls):
        y = self._section_header(surf, "GAME STATE", x, y, rw)

        mc = C_ACCENT if self.ai_mode else C_GOOD
        pc = C_PAUSE  if ls.paused  else C_GOOD
        status_txt = "PAUSED  (N=step)" if ls.paused else "RUNNING"

        y = self._kv_row(surf, "Mode:",           ls.mode,                     x, y, vc=mc)
        y = self._kv_row(surf, "Status:",         status_txt,                  x, y, vc=pc)
        y = self._kv_row(surf, "Score:",          ls.score,                    x, y, vc=C_GOOD)
        y = self._kv_row(surf, "Snake length:",   "%d cells" % ls.snake_len,  x, y)
        y = self._kv_row(surf, "Speed:",          "%d FPS" % ls.fps,          x, y)
        y += 6

        y = self._section_header(surf, "POSITIONS", x, y, rw, C_WARN)
        y = self._kv_row(surf, "Head:",  "col %d  row %d" % ls.head_pos,  x, y, vc=C_HEAD)
        y = self._kv_row(surf, "Food:",  "col %d  row %d" % ls.food_pos,  x, y, vc=C_FOOD)
        y = self._kv_row(surf, "Direction:", "%s  %s" % (ls.dir_arrow, ls.direction), x, y, vc=C_WARN)
        y += 10

        y = self._section_header(surf, "PATH INFO", x, y, rw, C_DIM)
        if self.ai_mode:
            pfound_c = C_GOOD if ls.path_found else C_BAD
            pfound_t = "FOUND (%d steps)" % ls.path_len if ls.path_found else "NO PATH"
            y = self._kv_row(surf, "A* result:", pfound_t, x, y, vc=pfound_c)
            fb_c = C_WARN if ls.fallback else C_DIM
            fb_t = "YES — flood fill" if ls.fallback else "Not needed"
            y = self._kv_row(surf, "Fallback:", fb_t, x, y, vc=fb_c)
            wc = C_ACCENT if ls.wrap_used else C_DIM
            wt = "YES — portal used!" if ls.wrap_used else "No"
            y = self._kv_row(surf, "Wrap this step:", wt, x, y, vc=wc)
        else:
            y = self._note(surf, "Enable AI mode (press A) to see path info.", x, y, rw)
        y += 8

        y = self._section_header(surf, "COLOUR LEGEND", x, y, rw, C_DIM)
        legend = [
            (C_HEAD,      "Snake head"),
            (C_BODY,      "Snake body"),
            (C_FOOD,      "Food"),
            (C_PATH_DOT,  "A* planned path"),
            ((80,40,110), "A* explored cells"),
        ]
        for col, label in legend:
            pygame.draw.rect(surf, col, (x, y + 2, 12, 12), border_radius=2)
            surf.blit(self.f_small.render(label, True, C_DIM), (x + 18, y))
            y += 15
        return y

    # ════════════════════════════════════════════════════
    #  TAB 1 — ALGORITHM EXPLAINED
    # ════════════════════════════════════════════════════
    def _tab_algorithm(self, surf, x, y, rw, ls):
        y = self._section_header(surf, "WHAT IS A*?", x, y, rw)
        y = self._note(surf,
            "A* is a best-first search algorithm. It finds the shortest path "
            "on a grid by always expanding the node with the lowest total cost f(n).",
            x, y, rw, C_TEXT)
        y += 8

        y = self._section_header(surf, "CORE FORMULA", x, y, rw, C_WARN)
        y = self._formula_box(surf,
            ["  f(n)  =  g(n)  +  h(n)",
             "  g(n)  =  steps taken so far (exact)",
             "  h(n)  =  steps left to goal (estimate)",
             "  f(n)  =  total estimated path cost"],
            [C_ACCENT, C_GOOD, C_WARN, C_TEXT],
            x, y, rw)
        y += 4

        y = self._section_header(surf, "WHY IT'S OPTIMAL", x, y, rw, C_GOOD)
        y = self._note(surf,
            "g(n) keeps the path cost honest — it tracks the real distance travelled. "
            "h(n) guides the search toward the goal. As long as h never over-estimates "
            "the true cost, A* guarantees the shortest path is found first.",
            x, y, rw, C_TEXT)
        y += 8

        y = self._section_header(surf, "HEURISTIC USED HERE", x, y, rw, C_WARN)
        y = self._note(surf,
            "Wrap-aware Manhattan distance:  min(|dx|, COLS-|dx|) + min(|dy|, ROWS-|dy|)",
            x, y, rw, C_ACCENT, self.f_body)
        y += 4
        y = self._note(surf,
            "On each axis it takes the shorter of the direct path or the wrap-around path. "
            "This is admissible (never over-estimates) because the snake can pass through walls.",
            x, y, rw, C_DIM)
        y += 8

        # ── FALLBACK STRATEGY — now fully visible via scroll ──
        y = self._section_header(surf, "FALLBACK STRATEGY", x, y, rw, C_WARN)
        y = self._note(surf,
            "When A* finds no path (snake body blocks all routes), the AI switches to "
            "a flood-fill survival strategy:", x, y, rw, C_TEXT)
        y += 4
        steps = [
            "1. Look at all 4 neighbouring cells from the head.",
            "2. Skip cells that are occupied by the snake body.",
            "3. Skip moving directly backward (into own neck).",
            "4. From each valid neighbour, run a flood-fill BFS.",
            "5. Count reachable empty cells (up to 120 limit).",
            "6. Pick the neighbour with the highest open-space count.",
        ]
        for step in steps:
            y = self._note(surf, step, x + 8, y, rw - 8, C_DIM)
        y += 4
        y = self._note(surf,
            "This keeps the snake alive as long as possible by preferring moves that "
            "preserve the most future options.",
            x, y, rw, C_DIM)
        y += 8

        y = self._section_header(surf, "WRAP-AROUND GRID", x, y, rw, C_DIM)
        y = self._note(surf,
            "The grid is a torus: the right edge connects to the left edge, and the top "
            "connects to the bottom. Both the snake movement and the A* heuristic are "
            "fully wrap-aware.",
            x, y, rw, C_DIM)
        y += 8

        y = self._section_header(surf, "ALGORITHM STEPS", x, y, rw, C_DIM)
        algo_steps = [
            "1. Push start node onto min-heap with f = h(start).",
            "2. Pop node with lowest f score.",
            "3. If it's the goal → reconstruct path and return.",
            "4. Add it to the closed set (don't revisit).",
            "5. For each valid neighbour: compute g, h, f.",
            "6. If better path found → update heap entry.",
            "7. If heap empty → no path exists → use fallback.",
        ]
        for step in algo_steps:
            y = self._note(surf, step, x + 8, y, rw - 8, C_DIM)
        return y

    # ════════════════════════════════════════════════════
    #  TAB 2 — LIVE A* VALUES
    # ════════════════════════════════════════════════════
    def _tab_live_values(self, surf, x, y, rw, ls):
        if not self.ai_mode:
            y += 20
            y = self._note(surf, "Press A to enable AI mode and see live A* values here.",
                           x, y, rw, C_DIM)
            return y

        hd = manhattan_wrap(ls.head_pos, ls.food_pos)

        y = self._section_header(surf, "AT THE SNAKE HEAD  (start node)", x, y, rw, C_HEAD)
        y = self._note(surf, "g = 0 because this is where the search begins.", x, y, rw, C_DIM)
        y += 4
        y = self._formula_box(surf,
            ["  g(head) = 0       (start — no steps taken)",
             "  h(head) = %-5d   (dist to food)" % hd,
             "  f(head) = %-5d   (= 0 + %d)" % (hd, hd)],
            [C_GOOD, C_WARN, C_ACCENT],
            x, y, rw)
        y += 6

        if ls.next_cell and ls.path_found:
            y = self._section_header(surf, "AT THE NEXT CHOSEN CELL  %s" % str(ls.next_cell),
                                     x, y, rw, C_ACCENT)
            y = self._note(surf, "One step was taken — g increases by 1.", x, y, rw, C_DIM)
            y += 4
            y = self._formula_box(surf,
                ["  g(next) = 1       (one step taken)",
                 "  h(next) = %-5d   (dist to food)" % ls.h_next,
                 "  f(next) = %-5d   (= 1 + %d)" % (ls.f_next, ls.h_next)],
                [C_GOOD, C_WARN, C_ACCENT],
                x, y, rw)
            y += 6
        else:
            y = self._section_header(surf, "NEXT CELL", x, y, rw, C_DIM)
            y = self._note(surf, "No valid path — running fallback strategy.", x, y, rw, C_WARN)
            y += 4

        y = self._section_header(surf, "SEARCH STATISTICS", x, y, rw, C_DIM)
        y = self._mini_bar(surf, "Nodes explored:", ls.closed_count,
                           max(ls.closed_count, 50), x, y, rw, C_DIM)
        y = self._mini_bar(surf, "Nodes seen:",     ls.open_count,
                           max(ls.open_count, 50), x, y, rw, C_ACCENT)
        y += 6

        y = self._section_header(surf, "PATH RESULT", x, y, rw, C_DIM)
        if ls.path_found:
            y = self._kv_row(surf, "Status:",    "PATH FOUND",          x, y, vc=C_GOOD)
            y = self._kv_row(surf, "Length:",    "%d steps" % ls.path_len, x, y, vc=C_TEXT)
            y = self._kv_row(surf, "Fallback:",  "No",                  x, y, vc=C_GOOD)
            y += 4
            y = self._note(surf,
                "Blue cells show the planned route. Purple tint marks cells A* explored "
                "and rejected (the closed set).", x, y, rw, C_DIM)
        else:
            y = self._kv_row(surf, "Status:",    "NO PATH EXISTS",      x, y, vc=C_BAD)
            y = self._kv_row(surf, "Fallback:",  "YES — flood fill",    x, y, vc=C_WARN)
            y += 4
            y = self._note(surf,
                "Flood fill counts reachable cells in each direction and picks "
                "the move that keeps the most space available.", x, y, rw, C_WARN)

        # ── WRAP-AROUND — now always fully visible ──
        y += 8
        y = self._section_header(surf, "WRAP-AROUND", x, y, rw, C_ACCENT)
        wc = C_ACCENT if ls.wrap_used else C_DIM
        wt = "YES — portal used this step!" if ls.wrap_used else "Not used this step"
        y = self._kv_row(surf, "Portal this step:", wt, x, y, vc=wc)
        y += 4

        # Wrap diagram explanation
        y = self._note(surf,
            "The grid wraps on both axes (torus topology). When the snake or "
            "the A* path crosses an edge, it reappears on the opposite side.",
            x, y, rw, C_DIM)
        y += 6

        # Visual torus diagram
        diagram_lines = [
            "  LEFT EDGE ←→ RIGHT EDGE",
            "   TOP EDGE ←→ BOTTOM EDGE",
        ]
        for dl in diagram_lines:
            surf.blit(self.f_small.render(dl, True, C_ACCENT if ls.wrap_used else C_DIM),
                      (x + 8, y))
            y += 14
        y += 4

        y = self._note(surf,
            "Heuristic accounts for wrap: h = min(|dx|, COLS-|dx|) + min(|dy|, ROWS-|dy|). "
            "This ensures the shortest wrapped distance is always preferred.",
            x, y, rw, C_DIM)
        return y

    # ════════════════════════════════════════════════════
    #  TAB 3 — LOG & CONTROLS
    # ════════════════════════════════════════════════════
    def _tab_log_controls(self, surf, x, y, rw, ls):
        y = self._section_header(surf, "DECISION LOG", x, y, rw, C_DIM)
        if ls.log:
            for i, line in enumerate(reversed(ls.log)):
                age_col = C_TEXT if i == 0 else (
                          C_DIM  if i > 4  else
                          tuple(int(C_TEXT[c] * (1 - i*0.12) + C_DIM[c] * i*0.12)
                                for c in range(3)))
                y = self._note(surf, line, x, y, rw, age_col)
                y += 1
        else:
            y = self._note(surf, "No events yet.", x, y, rw, C_DIM)
        y += 10

        y = self._section_header(surf, "KEYBOARD CONTROLS", x, y, rw, C_DIM)
        controls = [
            ("Arrow Keys",    "Move snake (manual mode)"),
            ("A",             "Toggle AI on / off"),
            ("P / SPACE",     "Pause / Resume"),
            ("N",             "Step 1 frame (paused)"),
            ("R",             "Restart game"),
            ("TAB",           "Cycle panel tabs"),
            ("1 / 2 / 3 / 4", "Jump to panel tab"),
            ("Scroll Wheel",  "Scroll panel content"),
            ("ESC",           "Quit"),
        ]
        for k, v in controls:
            ks = self.f_tab.render(k, True, C_ACCENT)
            kr = ks.get_rect(topleft=(x, y + 2))
            pygame.draw.rect(surf, C_HIGHLIGHT, kr.inflate(8, 4), border_radius=3)
            surf.blit(ks, (x + 4, y + 4))
            surf.blit(self.f_small.render(v, True, C_DIM), (x + kr.width + 14, y + 4))
            y += 18
        y += 10

        # ── TIPS — now fully visible ──
        y = self._section_header(surf, "TIPS", x, y, rw, C_ACCENT)
        tips = [
            "Watch the blue path cells update each frame in AI mode.",
            "Purple tint = cells A* explored but rejected (the closed set).",
            "N key lets you single-step through AI decisions while paused.",
            "Press TAB or 1-4 to switch between explanation panels.",
            "Use mouse scroll wheel to scroll this panel content.",
            "A* tab explains the full algorithm including fallback strategy.",
            "Live Values tab shows real-time g, h, f scores each frame.",
            "Score increases speed — the snake gets faster every 5 points.",
            "Wrap-around portals let the snake (and A*) cross edges freely.",
        ]
        for tip in tips:
            surf.blit(self.f_small.render("•", True, C_ACCENT), (x, y))
            y = self._note(surf, tip, x + 12, y, rw - 12, C_DIM)
            y += 3
        return y

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

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(self.fps)


if __name__ == "__main__":
    Game().run()