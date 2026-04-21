"""
ui/panel.py
===========
Panel renderer — draws the right-side info panel with 5 scrollable tabs.

Tab layout (redesigned for clarity and live data)
--------------------------------------------------
  0  AI DECISION     — current algorithm, live path/node stats, active rule
  1  ALGORITHM INFO  — explanation of the active algorithm + formula reference
  2  LIVE METRICS    — real-time g/h/f values, search stats, wrap info
  3  LOGS & KEYS     — decision log (dynamic), keyboard reference, tips
  4  COMPARISON      — live per-algorithm comparison table + switch history

Design principles
-----------------
  - No placeholder markers ('*' or static fillers)
  - Every value shown is live and contextual
  - Algorithm name appears consistently with its accent colour
  - Best-performing algorithm is highlighted in the comparison table
  - Algorithm switch history is recorded and displayed in tab 5

Rendering model
---------------
  Each tab draws into an off-screen pygame.Surface (RENDER_H px tall).
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


# ── Layout constants ──────────────────────────────────────────────────────────
TAB_BAR_H = 42       # height of tab strip + divider
RENDER_H  = 3200     # off-screen surface height


# ── Tab labels (5 tabs matching TABS list indices) ────────────────────────────
_TAB_LABELS = [
    "1:AI",
    "2:ALGO",
    "3:LIVE",
    "4:LOG",
    "5:CMP",
]


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

        x0  = px + 10
        rw  = PANEL_W - 22 - SCROLLBAR_W - 4

        # ── Tab bar ──────────────────────────────────────────────────────
        tab_y = 7
        tab_h = 26
        tw    = (PANEL_W - 12) // len(TABS)
        alg_col = ALG_COLOURS.get(ls.algorithm, C_ACCENT)

        for i, label in enumerate(_TAB_LABELS):
            tx     = px + 6 + i * tw
            active = (i == self.panel_tab)
            bg     = C_TAB_ACTIVE if active else C_TAB_INACTIVE
            pygame.draw.rect(screen, bg, (tx, tab_y, tw - 2, tab_h), border_radius=3)
            if active:
                # Accent bar at bottom of active tab in current algo colour
                pygame.draw.rect(screen, alg_col,
                                 (tx, tab_y + tab_h - 2, tw - 2, 2), border_radius=1)
            tc   = alg_col if active else C_DIM
            ts   = self.f_tab.render(label, True, tc)
            screen.blit(ts, ts.get_rect(center=(tx + (tw - 2) // 2, tab_y + tab_h // 2)))

        line_y = tab_y + tab_h + 4
        pygame.draw.line(screen, C_PANEL_BORDER,
                         (px + 4, line_y), (px + PANEL_W - 4, line_y), 1)

        content_top = line_y + 6
        content_h   = WINDOW_H - content_top

        # ── Off-screen surface ───────────────────────────────────────────
        surf = pygame.Surface((PANEL_W, RENDER_H))
        surf.fill(C_PANEL)
        sx, srw, sy = 10, rw, 8

        if   self.panel_tab == 0: sy = self._tab_ai_decision  (surf, sx, sy, srw, ls)
        elif self.panel_tab == 1: sy = self._tab_algorithm     (surf, sx, sy, srw, ls)
        elif self.panel_tab == 2: sy = self._tab_live_metrics  (surf, sx, sy, srw, ls)
        elif self.panel_tab == 3: sy = self._tab_log           (surf, sx, sy, srw, ls)
        elif self.panel_tab == 4: sy = self._tab_comparison    (surf, sx, sy, srw, ls)

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
            thumb_y = content_top + int(
                (content_h - thumb_h) * scroll / max(max_scroll, 1)
            )
            pygame.draw.rect(screen, C_SCROLLBAR_THB,
                             (sb_x, thumb_y, SCROLLBAR_W, thumb_h), border_radius=3)
            hint = self.f_small.render("scroll", True, C_DIM)
            screen.blit(hint, hint.get_rect(bottomright=(px + PANEL_W - 10, WINDOW_H - 4)))

    # ── Scroll / mouse input ──────────────────────────────────────────────────

    def scroll(self, delta_y: int):
        tab   = self.panel_tab
        max_s = max(0, self.tab_content_h[tab] - self.PANEL_CONTENT_H)
        self.tab_scroll[tab] = max(0, min(max_s,
                                          self.tab_scroll[tab] - delta_y * 22))

    def handle_tab_click(self, mx: int, my: int):
        if mx < GAME_W:
            return
        tw = (PANEL_W - 12) // len(TABS)
        for i in range(len(TABS)):
            tx = GAME_W + 6 + i * tw
            if tx <= mx <= tx + tw and 7 <= my <= 33:
                self.panel_tab = i
                return

    def reset_scroll(self):
        self.tab_scroll = [0] * len(TABS)

    # ════════════════════════════════════════════════════════════════════════
    #  SURFACE DRAWING HELPERS
    # ════════════════════════════════════════════════════════════════════════

    def _section_header(self, surf, text: str, x: int, y: int, rw: int,
                        col=C_ACCENT) -> int:
        """Draw a highlighted section heading; return new y."""
        pygame.draw.rect(surf, C_HIGHLIGHT, (x - 4, y - 2, rw + 8, 20), border_radius=3)
        surf.blit(self.f_title.render(text, True, col), (x, y))
        return y + 22

    def _kv_row(self, surf, label: str, value, x: int, y: int,
                lc=C_DIM, vc=C_TEXT, split: int = 160) -> int:
        """Draw a key:value row; return new y."""
        surf.blit(self.f_small.render(label, True, lc),    (x, y))
        surf.blit(self.f_val.render(str(value), True, vc), (x + split, y))
        return y + 16

    def _note(self, surf, text: str, x: int, y: int, rw: int,
              col=C_DIM, font=None) -> int:
        """Word-wrapped single-colour note; return new y."""
        font  = font or self.f_small
        words = text.split()
        line  = ""
        for w in words:
            test = line + w + " "
            if font.size(test)[0] > rw:
                if line.strip():
                    surf.blit(font.render(line.strip(), True, col), (x, y))
                    y += 14
                line = w + " "
            else:
                line = test
        if line.strip():
            surf.blit(font.render(line.strip(), True, col), (x, y))
            y += 14
        return y

    def _mini_bar(self, surf, label: str, val: int, maxv: int,
                  x: int, y: int, rw: int, col=C_ACCENT) -> int:
        """Draw a labelled progress bar; return new y."""
        surf.blit(self.f_small.render(label, True, C_DIM), (x, y))
        bx = x + 140; bw = rw - 148; bh = 9
        pygame.draw.rect(surf, C_HIGHLIGHT, (bx, y + 2, bw, bh), border_radius=4)
        fill = int(bw * min(val / max(maxv, 1), 1.0))
        if fill > 0:
            pygame.draw.rect(surf, col, (bx, y + 2, fill, bh), border_radius=4)
        surf.blit(self.f_small.render(str(val), True, col), (bx + bw + 5, y))
        return y + 16

    def _formula_box(self, surf, lines: list, colors: list,
                     x: int, y: int, rw: int) -> int:
        """Draw a framed multi-line formula box; return new y."""
        h = len(lines) * 18 + 10
        pygame.draw.rect(surf, C_HIGHLIGHT,    (x, y, rw, h), border_radius=5)
        pygame.draw.rect(surf, C_SECTION_LINE, (x, y, rw, h), 1, border_radius=5)
        fy = y + 6
        for line, col in zip(lines, colors):
            surf.blit(self.f_body.render(line, True, col), (x + 10, fy))
            fy += 18
        return y + h + 6

    def _divider(self, surf, x: int, y: int, rw: int) -> int:
        """Thin horizontal divider line; return new y."""
        pygame.draw.rect(surf, C_SECTION_LINE, (x, y + 3, rw, 1))
        return y + 10

    def _colour_chip(self, surf, col: tuple, label: str,
                     x: int, y: int) -> int:
        """Small colour square + label; return new y."""
        pygame.draw.rect(surf, col, (x, y + 2, 11, 11), border_radius=2)
        surf.blit(self.f_small.render(label, True, C_DIM), (x + 16, y))
        return y + 15

    def _status_badge(self, surf, text: str, col: tuple,
                      x: int, y: int) -> int:
        """
        Draws a small pill badge with `text` in `col`.
        Returns the right edge x so caller can chain badges.
        """
        ts  = self.f_tab.render(text, True, col)
        rct = ts.get_rect(topleft=(x + 4, y + 3))
        bg  = pygame.Rect(x, y, rct.width + 8, rct.height + 6)
        pygame.draw.rect(surf, C_HIGHLIGHT, bg, border_radius=4)
        pygame.draw.rect(surf, col, bg, 1, border_radius=4)
        surf.blit(ts, rct)
        return bg.right + 6

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 0 — AI DECISION (current algorithm, path, rule, live snapshot)
    # ════════════════════════════════════════════════════════════════════════

    def _tab_ai_decision(self, surf, x: int, y: int, rw: int,
                         ls: LiveState) -> int:
        alg_col = ALG_COLOURS.get(ls.algorithm, C_ACCENT)
        alg_lbl = ALG_LABELS.get(ls.algorithm, ls.algorithm)

        # ── Current algorithm headline ────────────────────────────────────
        y = self._section_header(surf, "CURRENT ALGORITHM", x, y, rw, alg_col)
        # Large algorithm name
        name_surf = self.f_hud.render(alg_lbl, True, alg_col)
        surf.blit(name_surf, (x, y))
        y += 18

        # Mode badges
        badge_x = x
        if ls.mode != "MANUAL":
            badge_x = self._status_badge(surf, "AI ON", C_GOOD, badge_x, y)
        else:
            badge_x = self._status_badge(surf, "MANUAL", C_DIM, badge_x, y)
        if ls.paused:
            badge_x = self._status_badge(surf, "PAUSED", C_PAUSE, badge_x, y)
        if ls.hybrid_mode:
            self._status_badge(surf, "HYBRID", C_WARN, badge_x, y)
        y += 22

        # ── Game snapshot ─────────────────────────────────────────────────
        y = self._section_header(surf, "GAME SNAPSHOT", x, y, rw, C_DIM)
        pc = C_PAUSE if ls.paused else C_GOOD
        status_txt = "PAUSED  (N = step one frame)" if ls.paused else "RUNNING"
        y = self._kv_row(surf, "Status:",        status_txt,                    x, y, vc=pc)
        y = self._kv_row(surf, "Score:",         ls.score,                      x, y, vc=C_GOOD)
        y = self._kv_row(surf, "Snake length:",  f"{ls.snake_len} cells",       x, y)
        y = self._kv_row(surf, "Speed:",         f"{ls.fps} FPS",               x, y)
        y = self._kv_row(surf, "Tick:",          ls.tick,                       x, y, vc=C_DIM)
        y += 4

        # ── Positions ─────────────────────────────────────────────────────
        y = self._section_header(surf, "POSITIONS", x, y, rw, C_WARN)
        hx, hy = ls.head_pos
        fx, fy = ls.food_pos
        y = self._kv_row(surf, "Head:",       f"({hx}, {hy})",         x, y, vc=C_HEAD)
        y = self._kv_row(surf, "Food:",       f"({fx}, {fy})",         x, y, vc=C_FOOD)
        y = self._kv_row(surf, "Direction:",  f"{ls.dir_arrow} {ls.direction}", x, y, vc=C_WARN)
        y += 4

        # ── Last AI decision details ───────────────────────────────────────
        if ls.mode != "MANUAL":
            y = self._section_header(surf, "LAST AI DECISION", x, y, rw, alg_col)

            # Rule badge
            rule_col = (
                C_BAD  if ls.active_rule == "NO_SAFE_MOVE" else
                C_WARN if ls.active_rule in ("LOW_SPACE_SURVIVAL",) else
                C_GOOD
            )
            y = self._kv_row(surf, "Rule fired:", ls.active_rule or "—",
                             x, y, vc=rule_col)

            # Path result
            if ls.path_found:
                pfound_col = C_GOOD
                pfound_txt = f"FOUND  —  {ls.path_len} steps"
            else:
                pfound_col = C_BAD
                pfound_txt = "NO PATH  —  fallback active"
            y = self._kv_row(surf, "Path:", pfound_txt, x, y, vc=pfound_col)

            # Next move
            if ls.next_cell:
                y = self._kv_row(surf, "Next cell:",
                                 f"({ls.next_cell[0]}, {ls.next_cell[1]})",
                                 x, y, vc=alg_col)

            fb_col = C_WARN if ls.fallback else C_GOOD
            fb_txt = "YES — flood fill survival" if ls.fallback else "No"
            y = self._kv_row(surf, "Fallback:", fb_txt, x, y, vc=fb_col)

            wc = C_ACCENT if ls.wrap_used else C_DIM
            wt = "YES — portal used!" if ls.wrap_used else "No"
            y = self._kv_row(surf, "Wrap used:", wt, x, y, vc=wc)

            y = self._kv_row(surf, "Decision time:",
                             f"{ls.decision_ms:.3f} ms", x, y, vc=C_DIM)

            # Nodes explored bar
            y += 2
            y = self._mini_bar(surf, "Nodes explored:",
                               ls.nodes_explored, max(ls.nodes_explored, 60),
                               x, y, rw, C_DIM)
            y = self._mini_bar(surf, "Nodes seen:",
                               ls.nodes_seen, max(ls.nodes_seen, 60),
                               x, y, rw, alg_col)
            y += 4
        else:
            y = self._section_header(surf, "AI OFF", x, y, rw, C_DIM)
            y = self._note(surf,
                "Press A to enable AI mode. "
                "Use Q/W/E/S/D to select an algorithm first.",
                x, y, rw, C_DIM)
            y += 4

        # ── Hybrid mode status ────────────────────────────────────────────
        if ls.hybrid_mode:
            y = self._section_header(surf, "HYBRID MODE", x, y, rw, C_WARN)
            early_col = ALG_COLOURS.get(ls.hybrid_early, C_DIM)
            late_col  = ALG_COLOURS.get(ls.hybrid_late,  C_DIM)
            y = self._kv_row(surf, "Early algo:",
                             ALG_LABELS.get(ls.hybrid_early, ls.hybrid_early),
                             x, y, vc=early_col)
            y = self._kv_row(surf, "Late algo:",
                             ALG_LABELS.get(ls.hybrid_late, ls.hybrid_late),
                             x, y, vc=late_col)
            y = self._kv_row(surf, "Switch at score:", ls.hybrid_threshold,
                             x, y, vc=C_WARN)
            phase = ("LATE PHASE" if ls.score >= ls.hybrid_threshold
                     else f"EARLY  ({ls.hybrid_threshold - ls.score} pts to switch)")
            phase_col = late_col if ls.score >= ls.hybrid_threshold else early_col
            y = self._kv_row(surf, "Current phase:", phase, x, y, vc=phase_col)
            y += 4

        # ── Colour legend ─────────────────────────────────────────────────
        y = self._section_header(surf, "COLOUR LEGEND", x, y, rw, C_DIM)
        legend = [
            (C_HEAD,       "Snake head"),
            (C_BODY,       "Snake body (fades to tail)"),
            (C_FOOD,       "Food pellet"),
            (C_PATH_DOT,   "Planned path (A* / current algo)"),
            ((80, 40, 110),"Explored cells — A* closed set"),
        ]
        for col, label in legend:
            y = self._colour_chip(surf, col, label, x, y)
        return y + 4

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 1 — ALGORITHM INFO
    # ════════════════════════════════════════════════════════════════════════

    def _tab_algorithm(self, surf, x: int, y: int, rw: int,
                       ls: LiveState) -> int:
        alg     = ls.algorithm
        alg_col = ALG_COLOURS.get(alg, C_ACCENT)
        alg_lbl = ALG_LABELS.get(alg, alg)

        y = self._section_header(surf, f"ACTIVE ALGORITHM: {alg_lbl}", x, y, rw, alg_col)
        y += 4

        # Per-algorithm description
        DESCRIPTIONS = {
            "astar": [
                ("Category",   "Informed search  (uses heuristic h)"),
                ("Complete",   "Yes — always finds a path if one exists"),
                ("Optimal",    "Yes — guaranteed shortest path"),
                ("Formula",    "f(n) = g(n) + h(n)"),
                ("g(n)",       "Exact steps taken from start"),
                ("h(n)",       "Wrap-aware Manhattan distance to food"),
                ("Heuristic",  "Admissible — never over-estimates"),
                ("Best for",   "Dense boards, late game, high accuracy"),
            ],
            "bfs": [
                ("Category",   "Uninformed (blind) search"),
                ("Complete",   "Yes — finds a path if one exists"),
                ("Optimal",    "Yes — shortest path (unit edge cost)"),
                ("Structure",  "FIFO queue — expands layer by layer"),
                ("Weakness",   "Explores many more nodes than A*"),
                ("Notes",      "No heuristic — ignores direction to goal"),
                ("Best for",   "Guaranteed shortest routes, small boards"),
            ],
            "dfs": [
                ("Category",   "Uninformed (blind) search"),
                ("Complete",   "Yes (with visited-cell tracking)"),
                ("Optimal",    "No — often finds very long winding paths"),
                ("Structure",  "LIFO stack — dives deep first"),
                ("Weakness",   "Path can spiral around the entire grid"),
                ("Notes",      "Memory-efficient but poor route quality"),
                ("Best for",   "Demonstrating sub-optimality vs BFS/A*"),
            ],
            "greedy": [
                ("Category",   "Informed search (heuristic only)"),
                ("Complete",   "Yes (with visited-cell tracking)"),
                ("Optimal",    "No — ignores accumulated path cost g(n)"),
                ("Formula",    "f(n) = h(n)   [no g term]"),
                ("Strength",   "Very fast in open spaces, early game"),
                ("Weakness",   "Gets trapped by body obstacles late game"),
                ("Best for",   "Speed in sparse grids; hybrid early phase"),
            ],
            "hill_climbing": [
                ("Category",   "Local / greedy search"),
                ("Complete",   "No — gets stuck at local minima"),
                ("Optimal",    "No"),
                ("Structure",  "No open list — O(1) memory"),
                ("Weakness",   "Needs random restart when stuck"),
                ("Notes",      "Works well early, risky in late game"),
                ("Best for",   "Demonstrating local-search limitations"),
            ],
        }

        props = DESCRIPTIONS.get(alg, [])
        for label, val in props:
            y = self._kv_row(surf, label + ":", val, x, y, vc=alg_col, split=100)
        y += 8

        # ── A* core formula (reference box) ──────────────────────────────
        y = self._section_header(surf, "A* CORE FORMULA", x, y, rw, C_WARN)
        y = self._formula_box(surf,
            ["  f(n) = g(n) + h(n)",
             "  g(n) = exact steps from start",
             "  h(n) = estimated steps to goal",
             "  f(n) = total estimated path cost"],
            [C_ACCENT, C_GOOD, C_WARN, C_TEXT],
            x, y, rw)
        y += 4

        # ── Heuristic explanation ──────────────────────────────────────────
        y = self._section_header(surf, "WRAP-AWARE HEURISTIC", x, y, rw, C_DIM)
        y = self._formula_box(surf,
            ["  h = min(|dx|, COLS-|dx|)",
             "    + min(|dy|, ROWS-|dy|)",
             "  Admissible: never over-estimates"],
            [C_WARN, C_WARN, C_GOOD],
            x, y, rw)
        y = self._note(surf,
            "Because the snake can exit one edge and re-enter the opposite, "
            "the wrap-around distance is always a valid path. "
            "This keeps A* optimal.",
            x, y + 2, rw, C_DIM)
        y += 8

        # ── Algorithm comparison summary ──────────────────────────────────
        y = self._section_header(surf, "ALL ALGORITHMS", x, y, rw, C_DIM)
        comparison = [
            ("astar",         "Optimal + informed search"),
            ("bfs",           "Optimal + blind (no heuristic)"),
            ("dfs",           "Sub-optimal + blind + deep-first"),
            ("greedy",        "Fast + heuristic only (no g)"),
            ("hill_climbing", "Local + no backtrack"),
        ]
        for alg_name, desc in comparison:
            col     = ALG_COLOURS.get(alg_name, C_DIM)
            lbl     = ALG_LABELS.get(alg_name, alg_name)
            is_curr = (alg_name == alg)
            bg_col  = C_HIGHLIGHT if is_curr else C_PANEL
            pygame.draw.rect(surf, bg_col, (x - 2, y - 1, rw + 4, 15), border_radius=2)
            if is_curr:
                pygame.draw.rect(surf, col, (x - 2, y - 1, 3, 15), border_radius=1)
            pygame.draw.rect(surf, col, (x + 2, y + 3, 8, 8), border_radius=2)
            row_txt = f"{lbl:<18}  {desc}"
            surf.blit(self.f_small.render(row_txt, True, col if is_curr else C_DIM),
                      (x + 14, y))
            y += 15
        y += 8

        # ── Fallback strategy ─────────────────────────────────────────────
        y = self._section_header(surf, "FALLBACK STRATEGY (FLOOD FILL)", x, y, rw, C_WARN)
        steps = [
            "1. Run chosen algorithm.  If path found → follow it.",
            "2. If no path: evaluate all 4 neighbouring cells.",
            "3. For each safe neighbour, run BFS flood fill.",
            "4. Count reachable cells (capped at 120).",
            "5. Move toward the neighbour with the most open space.",
            "6. Maximises future survival options.",
        ]
        for s in steps:
            y = self._note(surf, s, x + 6, y, rw - 6, C_DIM)

        y += 8
        y = self._section_header(surf, "SWITCH ALGORITHM", x, y, rw, C_DIM)
        keys = [
            (pygame.K_q, "astar"),
            (pygame.K_w, "bfs"),
            (pygame.K_e, "dfs"),
            (pygame.K_s, "greedy"),
            (pygame.K_d, "hill_climbing"),
        ]
        key_names = {
            pygame.K_q: "Q", pygame.K_w: "W", pygame.K_e: "E",
            pygame.K_s: "S", pygame.K_d: "D",
        }
        for kcode, name in keys:
            lbl     = ALG_LABELS.get(name, name)
            col     = ALG_COLOURS.get(name, C_DIM)
            is_curr = (name == alg)
            ks      = self.f_tab.render(f"[{key_names[kcode]}]", True, col)
            kr      = ks.get_rect(topleft=(x, y + 2))
            pygame.draw.rect(surf, C_HIGHLIGHT, kr.inflate(6, 4), border_radius=3)
            if is_curr:
                pygame.draw.rect(surf, col, kr.inflate(6, 4), 1, border_radius=3)
            surf.blit(ks, (x + 3, y + 4))
            surf.blit(self.f_small.render(
                lbl + ("  ← active" if is_curr else ""), True,
                col if is_curr else C_DIM,
            ), (x + 32, y + 4))
            y += 17
        return y

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 2 — LIVE METRICS (g/h/f values, search stats, wrap)
    # ════════════════════════════════════════════════════════════════════════

    def _tab_live_metrics(self, surf, x: int, y: int, rw: int,
                          ls: LiveState) -> int:
        if ls.mode == "MANUAL":
            y += 20
            y = self._note(surf,
                "Press A to enable AI mode to see live search metrics.",
                x, y, rw, C_DIM)
            return y

        alg_col = ALG_COLOURS.get(ls.algorithm, C_ACCENT)
        alg_lbl = ALG_LABELS.get(ls.algorithm, ls.algorithm)
        hd      = ls.h_head

        # ── A* g/h/f values at head ───────────────────────────────────────
        y = self._section_header(surf,
            f"START NODE — Snake Head  {ls.head_pos}", x, y, rw, C_HEAD)
        y = self._note(surf, "g = 0 here: search always starts from head.", x, y, rw, C_DIM)
        y += 2
        y = self._formula_box(surf,
            [f"  g(head) = 0       (start — zero steps taken)",
             f"  h(head) = {hd:<5}   (Manhattan dist to food)",
             f"  f(head) = {hd:<5}   (= 0 + {hd})"],
            [C_GOOD, C_WARN, C_ACCENT], x, y, rw)
        y += 6

        # ── Values at next cell ───────────────────────────────────────────
        if ls.next_cell and ls.path_found:
            y = self._section_header(surf,
                f"NEXT CELL  {ls.next_cell}", x, y, rw, alg_col)
            y = self._note(surf, "One step from head — g increases by 1.", x, y, rw, C_DIM)
            y += 2
            y = self._formula_box(surf,
                [f"  g(next) = 1       (one step taken)",
                 f"  h(next) = {ls.h_next:<5}   (Manhattan dist to food)",
                 f"  f(next) = {ls.f_next:<5}   (= 1 + {ls.h_next})"],
                [C_GOOD, C_WARN, C_ACCENT], x, y, rw)
            y += 6
        else:
            y = self._section_header(surf, "NEXT CELL", x, y, rw, C_DIM)
            y = self._note(surf, "No valid path — running fallback flood fill.", x, y, rw, C_WARN)
            y += 4

        # ── Search statistics ──────────────────────────────────────────────
        y = self._section_header(surf, f"SEARCH STATISTICS  ({alg_lbl})", x, y, rw, C_DIM)
        y = self._mini_bar(surf, "Nodes explored:",
                           ls.nodes_explored, max(ls.nodes_explored, 60),
                           x, y, rw, C_DIM)
        y = self._mini_bar(surf, "Nodes seen:",
                           ls.nodes_seen, max(ls.nodes_seen, 60),
                           x, y, rw, alg_col)
        y = self._kv_row(surf, "Path length:", f"{ls.path_len} steps", x, y, vc=alg_col)
        y = self._kv_row(surf, "Decision time:",
                         f"{ls.decision_ms:.3f} ms", x, y, vc=C_DIM)
        y += 6

        # ── Path status ────────────────────────────────────────────────────
        y = self._section_header(surf, "PATH STATUS", x, y, rw, C_DIM)
        if ls.path_found:
            y = self._kv_row(surf, "Result:",   "PATH FOUND",           x, y, vc=C_GOOD)
            y = self._kv_row(surf, "Length:",   f"{ls.path_len} steps", x, y, vc=C_TEXT)
            y = self._kv_row(surf, "Fallback:", "No",                    x, y, vc=C_GOOD)
            y += 4
            y = self._note(surf,
                "Blue cells on the grid show the planned route. "
                "Purple tint marks the A* closed set (explored and rejected).",
                x, y, rw, C_DIM)
        else:
            y = self._kv_row(surf, "Result:",   "NO PATH EXISTS",      x, y, vc=C_BAD)
            y = self._kv_row(surf, "Fallback:", "YES — flood fill",    x, y, vc=C_WARN)
            y += 4
            y = self._note(surf,
                "Flood fill picks the safe direction with the most open space, "
                "maximising future survival options.",
                x, y, rw, C_WARN)

        # ── Forward-chaining rule ──────────────────────────────────────────
        y += 8
        y = self._section_header(surf, "ACTIVE FORWARD-CHAINING RULE", x, y, rw, C_DIM)
        rule_col = (
            C_BAD  if ls.active_rule == "NO_SAFE_MOVE" else
            C_WARN if ls.active_rule in ("LOW_SPACE_SURVIVAL",) else
            C_GOOD
        )
        y = self._kv_row(surf, "Rule:", ls.active_rule or "—", x, y, vc=rule_col)
        y += 4
        rule_docs = {
            "FOOD_ADJACENT":           "Food is 1 step away — move directly (fast path).",
            "LOW_SPACE_SURVIVAL":      "Critical space shortage — pure flood fill survival.",
            "NO_SAFE_MOVE":            "All 4 directions blocked — unavoidable death.",
            "DANGER_AHEAD_USE_PLANNER":"Obstacle directly ahead — planner routes around it.",
            "DEFAULT_PLANNER":         "No reactive condition — full search algorithm runs.",
        }
        doc = rule_docs.get(ls.active_rule, "")
        if doc:
            y = self._note(surf, doc, x + 4, y, rw - 4, C_DIM)
        y += 8

        # ── Wrap-around ────────────────────────────────────────────────────
        y = self._section_header(surf, "WRAP-AROUND (PORTAL)", x, y, rw, C_ACCENT)
        wc = C_ACCENT if ls.wrap_used else C_DIM
        wt = "YES — portal crossing used this step!" if ls.wrap_used else "Not used this step"
        y = self._kv_row(surf, "Portal:", wt, x, y, vc=wc)
        y += 4
        y = self._note(surf,
            "The grid is toroidal — exiting one edge enters the opposite. "
            "h = min(|dx|, COLS-|dx|) + min(|dy|, ROWS-|dy|) ensures "
            "A* always finds the shorter wrap-around route when available.",
            x, y, rw, C_DIM)
        return y

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 3 — LOGS & KEYBOARD REFERENCE
    # ════════════════════════════════════════════════════════════════════════

    def _tab_log(self, surf, x: int, y: int, rw: int, ls: LiveState) -> int:
        # ── Decision log ──────────────────────────────────────────────────
        y = self._section_header(surf, "DECISION LOG", x, y, rw, C_DIM)
        if ls.log:
            for i, line in enumerate(reversed(ls.log)):
                if i == 0:
                    age_col = C_TEXT
                elif i > 4:
                    age_col = C_DIM
                else:
                    t       = i / 5.0
                    age_col = tuple(
                        int(C_TEXT[c] * (1 - t) + C_DIM[c] * t) for c in range(3)
                    )
                y = self._note(surf, line, x, y, rw, age_col)
                y += 1
        else:
            y = self._note(surf, "No events yet — play a few ticks.", x, y, rw, C_DIM)
        y += 10

        # ── Keyboard reference ────────────────────────────────────────────
        y = self._section_header(surf, "KEYBOARD CONTROLS", x, y, rw, C_DIM)
        controls = [
            ("Arrow Keys",   "Move snake (manual mode)"),
            ("A",            "Toggle AI on / off"),
            ("Q",            "Algorithm: A* (A-Star)"),
            ("W",            "Algorithm: BFS"),
            ("E",            "Algorithm: DFS"),
            ("S",            "Algorithm: Greedy Best-First"),
            ("D",            "Algorithm: Hill Climbing"),
            ("H",            "Toggle hybrid mode"),
            ("P / SPACE",    "Pause / Resume"),
            ("N",            "Step 1 frame (while paused)"),
            ("R",            "Restart + print comparison table"),
            ("TAB",          "Cycle through panel tabs"),
            ("1 – 5",        "Jump directly to a panel tab"),
            ("Scroll Wheel", "Scroll panel content"),
            ("ESC",          "Quit"),
        ]
        for k, v in controls:
            ks  = self.f_tab.render(k, True, C_ACCENT)
            kr  = ks.get_rect(topleft=(x, y + 1))
            pygame.draw.rect(surf, C_HIGHLIGHT, kr.inflate(8, 4), border_radius=3)
            surf.blit(ks, (x + 4, y + 3))
            surf.blit(self.f_small.render(v, True, C_DIM), (x + kr.width + 14, y + 3))
            y += 18
        y += 10

        # ── Tips ──────────────────────────────────────────────────────────
        y = self._section_header(surf, "TIPS", x, y, rw, C_ACCENT)
        tips = [
            "Blue path cells update every frame in AI mode.",
            "Purple tint = A* closed set (nodes explored but not chosen).",
            "N key lets you step through AI decisions one frame at a time.",
            "Switch algorithms live — stats accumulate for comparison in Tab 5.",
            "Tab 5 shows per-algorithm performance and your switch history.",
            "Hybrid mode (H key): Greedy early-game speed, A* late-game safety.",
            "Score increases game speed every 5 points (max 14 FPS).",
            "Portals (wrap edges) let the snake and A* take shorter routes.",
            "Log file written to logs/decisions.log when enabled in config.",
        ]
        for tip in tips:
            surf.blit(self.f_small.render("•", True, C_ACCENT), (x, y))
            y = self._note(surf, tip, x + 12, y, rw - 12, C_DIM)
            y += 3
        return y

    # ════════════════════════════════════════════════════════════════════════
    #  TAB 4 — COMPARISON TABLE + ALGORITHM SWITCH HISTORY
    # ════════════════════════════════════════════════════════════════════════

    def _tab_comparison(self, surf, x: int, y: int, rw: int,
                        ls: LiveState) -> int:
        # ── Live comparison table ─────────────────────────────────────────
        y = self._section_header(surf, "ALGORITHM PERFORMANCE", x, y, rw, C_ACCENT)
        y = self._note(surf,
            "Stats accumulated this session. "
            "Switch algorithms with Q/W/E/S/D to build comparison data.",
            x, y, rw, C_DIM)
        y += 8

        rows = ls.comparison_rows
        if not rows:
            y = self._note(surf,
                "No data yet. Enable AI (A key) and play for a few seconds, "
                "then switch between algorithms to compare them.",
                x, y, rw, C_DIM)
        else:
            # ── Table header ─────────────────────────────────────────────
            # Column positions
            cx0, cx1, cx2, cx3, cx4, cx5, cx6 = (
                x, x+78, x+120, x+168, x+208, x+248, x+284
            )
            headers = ["Algorithm", "Path", "Nodes", "ms", "FB%", "OK%", "Score"]
            for hdr, cx_pos in zip(headers, (cx0, cx1, cx2, cx3, cx4, cx5, cx6)):
                surf.blit(self.f_small.render(hdr, True, C_ACCENT), (cx_pos, y))
            y += 14
            pygame.draw.rect(surf, C_SECTION_LINE, (x, y, rw, 1))
            y += 4

            # ── Table rows ────────────────────────────────────────────────
            for row in rows:
                is_active = (row["name"] == ls.algorithm)
                is_best   = row.get("is_best", False)
                row_col   = ALG_COLOURS.get(row["name"], C_DIM)

                bg_col = C_HIGHLIGHT if is_active else C_PANEL
                pygame.draw.rect(surf, bg_col, (x - 2, y - 1, rw + 4, 16), border_radius=2)

                # Left-edge accent bar: solid for active, dotted for best
                if is_active:
                    pygame.draw.rect(surf, row_col, (x - 2, y - 1, 3, 16), border_radius=1)
                elif is_best:
                    for yy in range(y, y + 16, 3):
                        pygame.draw.rect(surf, row_col, (x - 2, yy, 3, 2))

                trend = row.get("trend", "→")
                trend_col = C_GOOD if trend == "↓" else (C_BAD if trend == "↑" else C_DIM)

                vals = [
                    row["label"][:9],
                    f"{row['avg_path']}{trend}",
                    str(row["avg_nodes"]),
                    str(row["avg_ms"]),
                    f"{row['fallback_pct']}%",
                    f"{row.get('success_pct', '—')}%",
                    str(row["score"]),
                ]
                for val, cx_pos in zip(vals, (cx0, cx1, cx2, cx3, cx4, cx5, cx6)):
                    fc = row_col if is_active else C_DIM
                    surf.blit(self.f_small.render(val, True, fc), (cx_pos, y))

                # Best-performer crown marker
                if is_best and not is_active:
                    crown = self.f_small.render("best", True, C_GOOD)
                    surf.blit(crown, (x + rw - crown.get_width() - 4, y))

                y += 16

            y += 6

            # ── Column legend ─────────────────────────────────────────────
            y = self._section_header(surf, "COLUMN GUIDE", x, y, rw, C_DIM)
            cols_guide = [
                ("Path",  "Avg steps in planned path (↓ = improving trend)"),
                ("Nodes", "Avg nodes explored per decision"),
                ("ms",    "Avg decision time in milliseconds"),
                ("FB%",   "Fallback rate — higher means more dangerous"),
                ("OK%",   "Success rate — path found without fallback"),
                ("Score", "Best score achieved with this algorithm"),
            ]
            for col_lbl, desc in cols_guide:
                y = self._kv_row(surf, col_lbl + ":", desc, x, y, split=55, vc=C_TEXT)

            # ── Algorithm ranking ──────────────────────────────────────────
            y += 6
            y = self._section_header(surf, "ALGORITHM RANKING", x, y, rw, C_DIM)
            ranking = [
                ("astar",         "Best overall — optimal + informed"),
                ("bfs",           "Optimal paths — slow on dense grids"),
                ("greedy",        "Fast early game — risky late game"),
                ("dfs",           "Survives well — very long paths"),
                ("hill_climbing", "Fastest decisions — dies most often"),
            ]
            for rname, rdesc in ranking:
                rcol = ALG_COLOURS.get(rname, C_DIM)
                rlbl = ALG_LABELS.get(rname, rname)
                pygame.draw.rect(surf, rcol, (x + 2, y + 3, 7, 7), border_radius=2)
                surf.blit(self.f_small.render(f"{rlbl:<18}  {rdesc}", True, C_DIM),
                          (x + 14, y))
                y += 14

        # ── Algorithm switch history ──────────────────────────────────────
        y += 10
        y = self._section_header(surf, "ALGORITHM SWITCH HISTORY", x, y, rw, C_ACCENT)

        history = ls.algorithm_history
        if not history:
            y = self._note(surf,
                "No switches yet. Press Q/W/E/S/D to switch algorithms; "
                "each switch is recorded here with tick and score.",
                x, y, rw, C_DIM)
        else:
            # Header row
            hx0, hx1, hx2, hx3 = x, x + 86, x + 146, x + 200
            for hdr, hx_pos in zip(["Algorithm", "Tick", "Score", "Reason"],
                                    (hx0, hx1, hx2, hx3)):
                surf.blit(self.f_small.render(hdr, True, C_ACCENT), (hx_pos, y))
            y += 14
            pygame.draw.rect(surf, C_SECTION_LINE, (x, y, rw, 1))
            y += 4

            # Show most recent switches first (up to 15)
            for entry in reversed(history[-15:]):
                ecol   = ALG_COLOURS.get(entry.algorithm, C_DIM)
                elbl   = ALG_LABELS.get(entry.algorithm, entry.algorithm)
                reason_col = C_WARN if entry.reason == "hybrid" else C_DIM
                vals   = [elbl[:9], str(entry.tick), str(entry.score), entry.reason]
                colors = [ecol, C_DIM, C_GOOD, reason_col]
                for val, col, hx_pos in zip(vals, colors, (hx0, hx1, hx2, hx3)):
                    surf.blit(self.f_small.render(val, True, col), (hx_pos, y))
                y += 14

            y += 4
            y = self._note(surf,
                "Reason 'manual' = key press. 'hybrid' = automatic switch "
                "by hybrid mode when score crossed the threshold.",
                x, y, rw, C_DIM)

        return y + 6