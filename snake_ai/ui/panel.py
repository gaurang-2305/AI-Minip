"""
ui/panel.py
===========
Panel renderer — draws the right-side info panel with 5 scrollable tabs.

Tabs
----
  0  GAME STATE    — mode, score, speed, positions, path info, legend
  1  ALGORITHM     — explanation of the active algorithm
  2  LIVE VALUES   — real-time g/h/f scores, search stats
  3  LOG & CTRL    — decision log, keyboard controls, tips
  4  COMPARISON    — per-algorithm performance table

Rendering model
---------------
  Each tab draws into an off-screen pygame.Surface (2000px tall).
  Only the scrolled slice is blitted to the screen.
  A thin scrollbar on the right shows position and reacts to mouse wheel.
"""

import pygame
from engine.constants import (
    GAME_W, PANEL_W, WINDOW_H, SCROLLBAR_W,
    C_BG, C_PANEL, C_PANEL_BORDER, C_GRID,
    C_HEAD, C_BODY, C_FOOD, C_PATH_DOT,
    C_TEXT, C_DIM, C_ACCENT, C_GOOD, C_WARN, C_BAD,
    C_PAUSE, C_HIGHLIGHT, C_SECTION_LINE,
    C_TAB_ACTIVE, C_TAB_INACTIVE,
    C_SCROLLBAR, C_SCROLLBAR_THB,
    ALG_COLOURS, ALG_LABELS, TABS,
)
from engine.state import LiveState


# ── Constants ─────────────────────────────────────────────────────────────────
TAB_BAR_H = 42       # height of tab strip + divider
RENDER_H  = 3000     # off-screen surface height (more than enough)


class PanelRenderer:
    """
    Owns all fonts and scroll state.
    Call draw(screen, ls) once per frame.
    """

    def __init__(self):
        self.panel_tab = 0
        self.tab_scroll    = [0] * len(TABS)
        self.tab_content_h = [WINDOW_H] * len(TABS)

        self.PANEL_CONTENT_H = WINDOW_H - TAB_BAR_H

        # ── Fonts ────────────────────────────────────────────────────────
        self.f_title = pygame.font.SysFont("Consolas", 13, bold=True)
        self.f_body  = pygame.font.SysFont("Consolas", 12)
        self.f_small = pygame.font.SysFont("Consolas", 11)
        self.f_hud   = pygame.font.SysFont("Consolas", 13, bold=True)
        self.f_huge  = pygame.font.SysFont("Consolas", 32, bold=True)
        self.f_tab   = pygame.font.SysFont("Consolas", 11, bold=True)
        self.f_val   = pygame.font.SysFont("Consolas", 13, bold=True)

    # ── Public entry point ────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface, ls: LiveState):
        px = GAME_W
        pygame.draw.rect(screen, C_PANEL, (px, 0, PANEL_W, WINDOW_H))
        pygame.draw.line(screen, C_PANEL_BORDER, (px, 0), (px, WINDOW_H), 2)

        x0  = px + 12
        rw  = PANEL_W - 24 - SCROLLBAR_W - 4

        # ── Tab bar ──────────────────────────────────────────────────────
        tab_y = 8
        tab_h = 26
        tw    = (PANEL_W - 16) // len(TABS)
        for i, name in enumerate(TABS):
            tx     = x0 + i * tw
            active = (i == self.panel_tab)
            pygame.draw.rect(screen, C_TAB_ACTIVE if active else C_TAB_INACTIVE,
                             (tx, tab_y, tw - 3, tab_h), border_radius=4)
            if active:
                alg_col = ALG_COLOURS.get(ls.algorithm, C_ACCENT)
                pygame.draw.rect(screen, alg_col,
                                 (tx, tab_y + tab_h - 2, tw - 3, 2), border_radius=1)
            short = f"{i+1}:{name.split()[0]}"
            tc    = C_ACCENT if active else C_DIM
            ts    = self.f_tab.render(short, True, tc)
            screen.blit(ts, ts.get_rect(center=(tx + (tw-3)//2, tab_y + tab_h//2)))

        line_y = tab_y + tab_h + 4
        pygame.draw.line(screen, C_PANEL_BORDER,
                         (px + 4, line_y), (px + PANEL_W - 4, line_y), 1)

        content_top = line_y + 8
        content_h   = WINDOW_H - content_top

        # ── Off-screen surface ───────────────────────────────────────────
        surf = pygame.Surface((PANEL_W, RENDER_H))
        surf.fill(C_PANEL)
        sx, srw, sy = 12, rw, 8

        if   self.panel_tab == 0: sy = self._tab_game_state(surf, sx, sy, srw, ls)
        elif self.panel_tab == 1: sy = self._tab_algorithm  (surf, sx, sy, srw, ls)
        elif self.panel_tab == 2: sy = self._tab_live       (surf, sx, sy, srw, ls)
        elif self.panel_tab == 3: sy = self._tab_log        (surf, sx, sy, srw, ls)
        elif self.panel_tab == 4: sy = self._tab_comparison (surf, sx, sy, srw, ls)

        actual_h = sy + 12
        self.tab_content_h[self.panel_tab] = actual_h

        max_scroll = max(0, actual_h - content_h)
        scroll = min(self.tab_scroll[self.panel_tab], max_scroll)
        self.tab_scroll[self.panel_tab] = scroll

        clip = pygame.Rect(0, scroll, PANEL_W, content_h)
        screen.blit(surf, (px, content_top), clip)

        # ── Scrollbar ────────────────────────────────────────────────────
        sb_x = px + PANEL_W - SCROLLBAR_W - 2
        pygame.draw.rect(screen, C_SCROLLBAR,
                         (sb_x, content_top, SCROLLBAR_W, content_h), border_radius=3)
        if actual_h > content_h:
            ratio   = content_h / actual_h
            thumb_h = max(20, int(content_h * ratio))
            thumb_y = content_top + int((content_h - thumb_h) * scroll / max(max_scroll, 1))
            pygame.draw.rect(screen, C_SCROLLBAR_THB,
                             (sb_x, thumb_y, SCROLLBAR_W, thumb_h), border_radius=3)
            hint = self.f_small.render("↕ scroll", True, C_DIM)
            screen.blit(hint, hint.get_rect(bottomright=(px + PANEL_W - 10, WINDOW_H - 4)))

    # ── Scroll input ──────────────────────────────────────────────────────────

    def scroll(self, delta_y: int):
        tab     = self.panel_tab
        max_s   = max(0, self.tab_content_h[tab] - self.PANEL_CONTENT_H)
        self.tab_scroll[tab] = max(0, min(max_s,
                                          self.tab_scroll[tab] - delta_y * 22))

    def handle_tab_click(self, mx: int, my: int):
        if mx < GAME_W:
            return
        x0 = GAME_W + 12
        tw = (PANEL_W - 16) // len(TABS)
        for i in range(len(TABS)):
            tx = x0 + i * tw
            if tx <= mx <= tx + tw and 8 <= my <= 34:
                self.panel_tab = i
                return

    def reset_scroll(self):
        self.tab_scroll = [0] * len(TABS)

    # ════════════════════════════════════════════════════════════════════════
    #  SURFACE DRAWING HELPERS
    # ════════════════════════════════════════════════════════════════════════

    def _section_header(self, surf, text, x, y, rw, col=C_ACCENT):
        pygame.draw.rect(surf, C_HIGHLIGHT, (x - 4, y - 2, rw + 8, 20), border_radius=3)
        surf.blit(self.f_title.render(text, True, col), (x, y))
        return y + 22

    def _kv_row(self, surf, label, value, x, y, lc=C_DIM, vc=C_TEXT, split=165):
        surf.blit(self.f_small.render(label, True, lc),    (x, y))
        surf.blit(self.f_val.render(str(value), True, vc), (x + split, y))
        return y + 16

    def _note(self, surf, text, x, y, rw, col=C_DIM, font=None):
        font  = font or self.f_small
        words = text.split()
        line  = ""
        for w in words:
            test = line + w + " "
            if font.size(test)[0] > rw:
                surf.blit(font.render(line.strip(), True, col), (x, y))
                y += 14
                line = w + " "
            else:
                line = test
        if line.strip():
            surf.blit(font.render(line.strip(), True, col), (x, y))
            y += 14
        return y

    def _mini_bar(self, surf, label, val, maxv, x, y, rw, col=C_ACCENT):
        surf.blit(self.f_small.render(label, True, C_DIM), (x, y))
        bx = x + 130; bw = rw - 138; bh = 9
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
            surf.blit(self.f_body.render(line, True, col), (x + 10, fy))
            fy += 18
        return y + h + 6

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 0 — GAME STATE
    # ════════════════════════════════════════════════════════════════════════

    def _tab_game_state(self, surf, x, y, rw, ls: LiveState):
        alg_col = ALG_COLOURS.get(ls.algorithm, C_ACCENT)
        alg_lbl = ALG_LABELS.get(ls.algorithm, ls.algorithm)

        y = self._section_header(surf, "GAME STATE", x, y, rw)
        mc = C_ACCENT if ls.mode != "MANUAL" else C_GOOD
        pc = C_PAUSE  if ls.paused          else C_GOOD
        status_txt = "PAUSED  (N=step)" if ls.paused else "RUNNING"
        y = self._kv_row(surf, "Mode:",           ls.mode,                      x, y, vc=mc)
        y = self._kv_row(surf, "Status:",         status_txt,                   x, y, vc=pc)
        y = self._kv_row(surf, "Algorithm:",      alg_lbl,                      x, y, vc=alg_col)
        y = self._kv_row(surf, "Score:",          ls.score,                     x, y, vc=C_GOOD)
        y = self._kv_row(surf, "Snake length:",   f"{ls.snake_len} cells",      x, y)
        y = self._kv_row(surf, "Speed:",          f"{ls.fps} FPS",              x, y)
        y = self._kv_row(surf, "Decision time:",  f"{ls.decision_ms:.3f} ms",   x, y)
        y += 6

        y = self._section_header(surf, "POSITIONS", x, y, rw, C_WARN)
        y = self._kv_row(surf, "Head:",      f"col {ls.head_pos[0]}  row {ls.head_pos[1]}", x, y, vc=C_HEAD)
        y = self._kv_row(surf, "Food:",      f"col {ls.food_pos[0]}  row {ls.food_pos[1]}", x, y, vc=C_FOOD)
        y = self._kv_row(surf, "Direction:", f"{ls.dir_arrow}  {ls.direction}",             x, y, vc=C_WARN)
        y += 8

        y = self._section_header(surf, "AI STATUS", x, y, rw, C_DIM)
        if ls.mode != "MANUAL":
            rule_col = C_WARN if "FALLBACK" in ls.active_rule or "SURVIVAL" in ls.active_rule else C_GOOD
            y = self._kv_row(surf, "Rule fired:", ls.active_rule or "—", x, y, vc=rule_col)
            pfound_c = C_GOOD if ls.path_found else C_BAD
            pfound_t = f"FOUND ({ls.path_len} steps)" if ls.path_found else "NO PATH"
            y = self._kv_row(surf, "Path:", pfound_t, x, y, vc=pfound_c)
            fb_c = C_WARN if ls.fallback else C_DIM
            y = self._kv_row(surf, "Fallback:", "YES — flood fill" if ls.fallback else "No", x, y, vc=fb_c)
            wc = C_ACCENT if ls.wrap_used else C_DIM
            y = self._kv_row(surf, "Wrap used:", "YES — portal!" if ls.wrap_used else "No", x, y, vc=wc)
        else:
            y = self._note(surf, "Press A to enable AI mode.", x, y, rw)
        y += 8

        y = self._section_header(surf, "COLOUR LEGEND", x, y, rw, C_DIM)
        legend = [
            (C_HEAD,       "Snake head"),
            (C_BODY,       "Snake body"),
            (C_FOOD,       "Food"),
            (C_PATH_DOT,   "A* planned path"),
            ((80, 40, 110),"Explored cells (closed set)"),
        ]
        for col, label in legend:
            pygame.draw.rect(surf, col, (x, y + 2, 12, 12), border_radius=2)
            surf.blit(self.f_small.render(label, True, C_DIM), (x + 18, y))
            y += 15
        return y

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 1 — ALGORITHM EXPLAINED
    # ════════════════════════════════════════════════════════════════════════

    def _tab_algorithm(self, surf, x, y, rw, ls: LiveState):
        alg     = ls.algorithm
        alg_col = ALG_COLOURS.get(alg, C_ACCENT)
        alg_lbl = ALG_LABELS.get(alg, alg)

        y = self._section_header(surf, f"ACTIVE: {alg_lbl}", x, y, rw, alg_col)
        y += 4

        # Per-algorithm description
        DESCRIPTIONS = {
            "astar": [
                ("CATEGORY",    "Informed search  (uses heuristic h)"),
                ("COMPLETE",    "Yes — always finds path if one exists"),
                ("OPTIMAL",     "Yes — guaranteed shortest path"),
                ("FORMULA",     "f(n) = g(n) + h(n)"),
                ("g(n)",        "Exact steps taken from start"),
                ("h(n)",        "Wrap Manhattan distance to food"),
                ("HEURISTIC",   "Admissible — never over-estimates"),
            ],
            "bfs": [
                ("CATEGORY",    "Uninformed (blind) search"),
                ("COMPLETE",    "Yes — finds path if one exists"),
                ("OPTIMAL",     "Yes — shortest path (unit cost)"),
                ("STRUCTURE",   "FIFO queue — expands layer by layer"),
                ("WEAKNESS",    "Explores many more nodes than A*"),
                ("NOTES",       "No heuristic — ignores direction to goal"),
            ],
            "dfs": [
                ("CATEGORY",    "Uninformed (blind) search"),
                ("COMPLETE",    "Yes (with visited tracking)"),
                ("OPTIMAL",     "NO — often finds very long paths"),
                ("STRUCTURE",   "LIFO stack — dives deep first"),
                ("WEAKNESS",    "Path can spiral entire grid"),
                ("NOTES",       "Memory efficient but poor routing"),
            ],
            "greedy": [
                ("CATEGORY",    "Informed search (heuristic only)"),
                ("COMPLETE",    "Yes (with visited tracking)"),
                ("OPTIMAL",     "NO — ignores path cost g(n)"),
                ("FORMULA",     "f(n) = h(n)  [no g term!]"),
                ("STRENGTH",    "Very fast in open spaces"),
                ("WEAKNESS",    "Gets trapped by obstacles"),
            ],
            "hill_climbing": [
                ("CATEGORY",    "Local / greedy search"),
                ("COMPLETE",    "NO — gets stuck at local minima"),
                ("OPTIMAL",     "NO"),
                ("STRUCTURE",   "No open list — O(1) memory"),
                ("WEAKNESS",    "Random restart when stuck"),
                ("NOTES",       "Works well early, risky late-game"),
            ],
        }

        props = DESCRIPTIONS.get(alg, [])
        for label, val in props:
            y = self._kv_row(surf, label + ":", val, x, y, vc=alg_col, split=110)
        y += 8

        # Shared formula box
        y = self._section_header(surf, "A* CORE FORMULA (reference)", x, y, rw, C_WARN)
        y = self._formula_box(surf,
            ["  f(n) = g(n) + h(n)",
             "  g(n) = steps taken so far (exact)",
             "  h(n) = steps left to goal (estimate)",
             "  f(n) = total estimated path cost"],
            [C_ACCENT, C_GOOD, C_WARN, C_TEXT],
            x, y, rw)
        y += 4

        y = self._section_header(surf, "ALGORITHM COMPARISON", x, y, rw, C_DIM)
        comparison = [
            ("A*",           "Optimal + informed",     C_ACCENT),
            ("BFS",          "Optimal + blind",        C_GOOD),
            ("DFS",          "Sub-optimal + blind",    C_WARN),
            ("Greedy",       "Fast + heuristic only",  (220,80,220)),
            ("Hill Climbing","Local + no backtrack",   (255,220,50)),
        ]
        for name, desc, col in comparison:
            pygame.draw.rect(surf, col, (x, y + 3, 8, 8), border_radius=2)
            surf.blit(self.f_small.render(f"{name:<16} {desc}", True, C_DIM), (x + 14, y))
            y += 14
        y += 8

        y = self._section_header(surf, "SWITCH ALGORITHM", x, y, rw, C_DIM)
        keys = [("Q","astar"),("W","bfs"),("E","dfs"),("S","greedy"),("D","hill_climbing")]
        for k, name in keys:
            lbl = ALG_LABELS.get(name, name)
            col = ALG_COLOURS.get(name, C_DIM)
            ks  = self.f_tab.render(f"[{k}]", True, col)
            kr  = ks.get_rect(topleft=(x, y + 2))
            pygame.draw.rect(surf, C_HIGHLIGHT, kr.inflate(6, 4), border_radius=3)
            surf.blit(ks, (x + 3, y + 4))
            surf.blit(self.f_small.render(lbl, True, C_DIM), (x + 32, y + 4))
            y += 17

        y += 6
        y = self._section_header(surf, "FALLBACK STRATEGY", x, y, rw, C_WARN)
        steps = [
            "1. Run chosen algorithm.  If path found → follow it.",
            "2. If no path: evaluate all 4 neighbouring cells.",
            "3. For each safe neighbour run flood-fill BFS.",
            "4. Count reachable cells (cap 120).",
            "5. Move to neighbour with most open space.",
            "6. This maximises survival options.",
        ]
        for s in steps:
            y = self._note(surf, s, x + 6, y, rw - 6, C_DIM)
        return y

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 2 — LIVE VALUES
    # ════════════════════════════════════════════════════════════════════════

    def _tab_live(self, surf, x, y, rw, ls: LiveState):
        if ls.mode == "MANUAL":
            y += 20
            y = self._note(surf, "Press A to enable AI and see live values.", x, y, rw, C_DIM)
            return y

        alg_col = ALG_COLOURS.get(ls.algorithm, C_ACCENT)
        hd      = ls.h_head

        y = self._section_header(surf, "AT SNAKE HEAD  (start node)", x, y, rw, C_HEAD)
        y = self._note(surf, "g = 0 — this is where the search begins.", x, y, rw, C_DIM)
        y += 4
        y = self._formula_box(surf,
            [f"  g(head) = 0       (start — no steps taken)",
             f"  h(head) = {hd:<5}   (dist to food)",
             f"  f(head) = {hd:<5}   (= 0 + {hd})"],
            [C_GOOD, C_WARN, C_ACCENT], x, y, rw)
        y += 6

        if ls.next_cell and ls.path_found:
            y = self._section_header(surf, f"NEXT CHOSEN CELL  {ls.next_cell}", x, y, rw, alg_col)
            y = self._note(surf, "One step taken — g increases by 1.", x, y, rw, C_DIM)
            y += 4
            y = self._formula_box(surf,
                [f"  g(next) = 1       (one step taken)",
                 f"  h(next) = {ls.h_next:<5}   (dist to food)",
                 f"  f(next) = {ls.f_next:<5}   (= 1 + {ls.h_next})"],
                [C_GOOD, C_WARN, C_ACCENT], x, y, rw)
            y += 6
        else:
            y = self._section_header(surf, "NEXT CELL", x, y, rw, C_DIM)
            y = self._note(surf, "No path found — running fallback strategy.", x, y, rw, C_WARN)
            y += 4

        y = self._section_header(surf, "SEARCH STATISTICS", x, y, rw, C_DIM)
        y = self._mini_bar(surf, "Nodes explored:", ls.nodes_explored,
                           max(ls.nodes_explored, 50), x, y, rw, C_DIM)
        y = self._mini_bar(surf, "Nodes seen:",     ls.nodes_seen,
                           max(ls.nodes_seen, 50),     x, y, rw, alg_col)
        y = self._kv_row(surf, "Decision time:", f"{ls.decision_ms:.3f} ms", x, y)
        y += 6

        y = self._section_header(surf, "PATH RESULT", x, y, rw, C_DIM)
        if ls.path_found:
            y = self._kv_row(surf, "Status:",   "PATH FOUND",              x, y, vc=C_GOOD)
            y = self._kv_row(surf, "Length:",   f"{ls.path_len} steps",    x, y, vc=C_TEXT)
            y = self._kv_row(surf, "Fallback:", "No",                       x, y, vc=C_GOOD)
            y += 4
            y = self._note(surf,
                "Blue cells show the planned route. "
                "Purple tint marks the closed set (explored but rejected).",
                x, y, rw, C_DIM)
        else:
            y = self._kv_row(surf, "Status:",   "NO PATH EXISTS",           x, y, vc=C_BAD)
            y = self._kv_row(surf, "Fallback:", "YES — flood fill",         x, y, vc=C_WARN)
            y += 4
            y = self._note(surf,
                "Flood fill picks the direction with the most open space.",
                x, y, rw, C_WARN)

        y += 8
        y = self._section_header(surf, "FORWARD CHAINING RULE", x, y, rw, C_DIM)
        rc = C_WARN if ls.active_rule in ("LOW_SPACE_SURVIVAL", "NO_SAFE_MOVE") else C_GOOD
        y = self._kv_row(surf, "Rule fired:", ls.active_rule or "—", x, y, vc=rc)
        y += 4
        rule_docs = {
            "FOOD_ADJACENT":          "Food is 1 step away — move directly.",
            "LOW_SPACE_SURVIVAL":     "Open space critical — flood fill mode.",
            "NO_SAFE_MOVE":           "All directions blocked — unavoidable death.",
            "DANGER_AHEAD_USE_PLANNER":"Obstacle ahead — planner routes around.",
            "DEFAULT_PLANNER":        "No reactive rule — full search ran.",
        }
        doc = rule_docs.get(ls.active_rule, "")
        if doc:
            y = self._note(surf, doc, x, y, rw, C_DIM)

        y += 8
        y = self._section_header(surf, "WRAP-AROUND", x, y, rw, C_ACCENT)
        wc = C_ACCENT if ls.wrap_used else C_DIM
        wt = "YES — portal used this step!" if ls.wrap_used else "Not used this step"
        y = self._kv_row(surf, "Portal:", wt, x, y, vc=wc)
        y += 4
        y = self._note(surf,
            "h = min(|dx|, COLS-|dx|) + min(|dy|, ROWS-|dy|) — "
            "ensures the wrap-around route is preferred when shorter.",
            x, y, rw, C_DIM)
        return y

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 3 — LOG & CONTROLS
    # ════════════════════════════════════════════════════════════════════════

    def _tab_log(self, surf, x, y, rw, ls: LiveState):
        y = self._section_header(surf, "DECISION LOG", x, y, rw, C_DIM)
        if ls.log:
            for i, line in enumerate(reversed(ls.log)):
                if i == 0:
                    age_col = C_TEXT
                elif i > 4:
                    age_col = C_DIM
                else:
                    t       = i / 5.0
                    age_col = tuple(int(C_TEXT[c] * (1-t) + C_DIM[c] * t) for c in range(3))
                y = self._note(surf, line, x, y, rw, age_col)
                y += 1
        else:
            y = self._note(surf, "No events yet.", x, y, rw, C_DIM)
        y += 10

        y = self._section_header(surf, "KEYBOARD CONTROLS", x, y, rw, C_DIM)
        controls = [
            ("Arrow Keys",    "Move snake (manual mode)"),
            ("A",             "Toggle AI on / off"),
            ("Q/W/E/S/D",     "Switch algorithm"),
            ("H",             "Toggle hybrid mode"),
            ("P / SPACE",     "Pause / Resume"),
            ("N",             "Step 1 frame (paused)"),
            ("R",             "Restart game"),
            ("TAB",           "Cycle panel tabs"),
            ("1–5",           "Jump to panel tab"),
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

        y = self._section_header(surf, "TIPS", x, y, rw, C_ACCENT)
        tips = [
            "Blue path cells update every frame in AI mode.",
            "Purple tint = closed set (explored but rejected by A*).",
            "N key lets you single-step AI decisions while paused.",
            "Switch algorithms live with Q/W/E/S/D keys.",
            "Tab 5 (COMPARISON) shows per-algorithm performance stats.",
            "Hybrid mode (H key): Greedy early-game, A* late-game.",
            "Log file written to logs/decisions.log when enabled in config.",
            "Score increases speed every 5 points (max 14 FPS).",
            "Wrap portals let the snake (and A*) cross edges freely.",
        ]
        for tip in tips:
            surf.blit(self.f_small.render("•", True, C_ACCENT), (x, y))
            y = self._note(surf, tip, x + 12, y, rw - 12, C_DIM)
            y += 3
        return y

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 4 — COMPARISON TABLE
    # ════════════════════════════════════════════════════════════════════════

    def _tab_comparison(self, surf, x, y, rw, ls: LiveState):
        y = self._section_header(surf, "ALGORITHM PERFORMANCE", x, y, rw, C_ACCENT)
        y = self._note(surf,
            "Stats accumulated this session. "
            "Switch algorithms with Q/W/E/S/D keys.",
            x, y, rw, C_DIM)
        y += 8

        rows = ls.comparison_rows
        if not rows:
            y = self._note(surf,
                "No comparison data yet. Enable AI (A key) and play for a few seconds.",
                x, y, rw, C_DIM)
            return y

        # ── Table header ─────────────────────────────────────────────────
        col_x = [x, x+86, x+134, x+182, x+234, x+280]
        headers = ["Algorithm", "AvgPath", "Nodes", "ms", "FB%", "Score"]
        hcols   = [C_DIM]*6
        for i, (hdr, hcol, cx) in enumerate(zip(headers, hcols, col_x)):
            surf.blit(self.f_small.render(hdr, True, C_ACCENT), (cx, y))
        y += 14
        pygame.draw.rect(surf, C_SECTION_LINE, (x, y, rw, 1))
        y += 4

        # ── Table rows ───────────────────────────────────────────────────
        for row in rows:
            is_active = (row["name"] == ls.algorithm)
            row_col   = ALG_COLOURS.get(row["name"], C_DIM)
            bg_col    = C_HIGHLIGHT if is_active else C_PANEL

            pygame.draw.rect(surf, bg_col, (x - 2, y - 1, rw + 4, 15), border_radius=2)
            if is_active:
                pygame.draw.rect(surf, row_col, (x - 2, y - 1, 3, 15), border_radius=1)

            vals = [
                row["label"][:10],
                str(row["avg_path"]),
                str(row["avg_nodes"]),
                str(row["avg_ms"]),
                f"{row['fallback_pct']}%",
                str(row["score"]),
            ]
            for val, cx in zip(vals, col_x):
                fc = row_col if is_active else C_DIM
                surf.blit(self.f_small.render(val, True, fc), (cx, y))
            y += 16

        y += 10
        y = self._section_header(surf, "HOW TO READ", x, y, rw, C_DIM)
        explanations = [
            ("AvgPath",  "Average path length (shorter = more direct)"),
            ("Nodes",    "Avg nodes explored (lower = more efficient)"),
            ("ms",       "Avg decision time in milliseconds"),
            ("FB%",      "Fallback rate (higher = more dangerous)"),
            ("Score",    "Best score achieved with this algorithm"),
        ]
        for col, desc in explanations:
            y = self._kv_row(surf, col + ":", desc, x, y, split=80, vc=C_TEXT)

        y += 8
        y = self._section_header(surf, "ALGORITHM RANKING", x, y, rw, C_DIM)
        ranking_notes = [
            "A*:           Best overall — optimal + informed",
            "BFS:          Optimal paths — but slow on dense grids",
            "Greedy:       Fast early game — risky late game",
            "DFS:          Survives well — very long paths",
            "Hill Climbing: Fastest — but dies most often",
        ]
        for note in ranking_notes:
            y = self._note(surf, note, x + 4, y, rw - 4, C_DIM)
            y += 2
        return y
