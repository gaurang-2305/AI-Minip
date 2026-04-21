"""
main.py
=======
Main game loop — orchestrates all modules.

Architecture overview
---------------------
  KNOWLEDGE BASE     engine/entities.py  + engine/grid.py
                     → Snake, Food, grid helpers

  INFERENCE ENGINE   ai/inference_engine.py (Forward Chaining)
                     → Fires reactive rules each tick

  PLANNER            ai/planner.py (Backward Chaining)
                     → Selects algorithm, runs search, handles fallback

  STRATEGIES         strategies/*.py
                     → A*, BFS, DFS, Greedy, Hill Climbing

  LIVE STATE         engine/state.py
                     → Written by game loop; read by UI

  RENDERERS          ui/game_renderer.py + ui/panel.py
                     → Draw game area and info panel

  COMPARISON         utils/comparison.py
                     → Accumulates per-algorithm performance stats

  LOGGER             utils/logger.py
                     → Writes decision log to file

  CONFIG             config/loader.py
                     → JSON config loaded once; hot-reloaded on R key

Controls
--------
  Arrow Keys       Manual movement
  A                Toggle AI mode ON / OFF
  Q                Switch to A*
  W                Switch to BFS
  E                Switch to DFS
  S                Switch to Greedy
  D                Switch to Hill Climbing
  H                Toggle Hybrid mode (Greedy → A* after threshold)
  P / SPACE        Pause / Resume
  N                Step one frame (while paused)
  R                Restart game
  TAB              Cycle panel tabs
  1-5              Jump to panel tab
  Scroll Wheel     Scroll panel content
  ESC              Quit
"""

import sys
import pygame

from engine.constants import (
    WINDOW_W, WINDOW_H, GAME_W, BASE_FPS, MAX_FPS, FPS_INCREMENT,
    UP, DOWN, LEFT, RIGHT,
    DIR_NAMES, DIR_ARROW,
)
from engine.entities  import Snake, Food
from engine.state     import LiveState
from engine.grid      import wrap, manhattan_wrap, direction_to

from ai.knowledge_base   import KnowledgeBase
from ai.inference_engine import ForwardChainingEngine
from ai.planner          import Planner

from strategies          import get_strategy
from strategies.astar    import AStarStrategy

from ui.game_renderer    import GameRenderer
from ui.panel            import PanelRenderer

from utils.comparison    import ComparisonTracker
from utils.logger        import make_logger

from config              import get_config, VALID_ALGORITHMS


# ── Algorithm hotkeys ─────────────────────────────────────────────────────────
ALG_HOTKEYS = {
    pygame.K_q: "astar",
    pygame.K_w: "bfs",
    pygame.K_e: "dfs",
    pygame.K_s: "greedy",
    pygame.K_d: "hill_climbing",
}


class Game:
    """
    Top-level game controller.
    Owns all subsystems; updates them each tick; coordinates rendering.
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption(
            "Snake + AI System  |  A/Q/W/E/S/D=Algo  P=Pause  H=Hybrid  R=Restart"
        )
        self.clock = pygame.time.Clock()

        # ── Subsystems ──────────────────────────────────────────────────────
        self.cfg        = get_config()
        self.inference  = ForwardChainingEngine()
        self.planner    = Planner()
        self.tracker    = ComparisonTracker()
        self.logger     = make_logger(
            self.cfg.log_decisions,
            self.cfg.log_file,
        )
        self.game_ren   = GameRenderer()
        self.panel_ren  = PanelRenderer()

        # ── A* for closed-set visualisation (always runs separately) ───────
        self._astar_vis = AStarStrategy()

        self.tick_count = 0
        self.reset()

    # ── Reset ─────────────────────────────────────────────────────────────────

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
        self.ls         = LiveState()
        self.tick_count = 0
        # Track the last hybrid algorithm to detect switches
        self._last_hybrid_alg = None
        self.panel_ren.reset_scroll()
        self.tracker.reset()
        self.cfg.load()   # re-read config on restart

    # ── Events ────────────────────────────────────────────────────────────────

    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self._quit()

            if ev.type == pygame.KEYDOWN:
                k = ev.key

                if k == pygame.K_ESCAPE:
                    self._quit()

                elif k == pygame.K_r:
                    self.logger.log_event("RESTART")
                    self.tracker.print_summary()
                    self.reset()
                    return

                elif k in (pygame.K_p, pygame.K_SPACE):
                    if not self.game_over:
                        self.paused = not self.paused
                        self.ls.push_log("⏸ PAUSED" if self.paused else "▶ RESUMED")

                elif k == pygame.K_n and self.paused and not self.game_over:
                    self._tick()

                elif k == pygame.K_a:
                    self.ai_mode = not self.ai_mode
                    self.ai_path = []
                    msg = f"AI ON — {self.cfg.algorithm}" if self.ai_mode else "AI OFF — Manual"
                    self.ls.push_log(msg)

                elif k == pygame.K_h:
                    self.cfg._data["hybrid_mode"] = not self.cfg.hybrid_mode
                    self.ls.push_log(
                        f"Hybrid ON ({self.cfg.hybrid_early}→{self.cfg.hybrid_late})"
                        if self.cfg.hybrid_mode else "Hybrid OFF"
                    )

                elif k in ALG_HOTKEYS:
                    alg = ALG_HOTKEYS[k]
                    self.cfg.set_algorithm(alg)
                    self.ai_path = []
                    self.ls.push_log(f"Algorithm: {alg}")
                    # Record the manual algorithm switch in history
                    self.ls.record_algorithm_switch(
                        algorithm=alg,
                        tick=self.tick_count,
                        score=self.score,
                        reason="manual",
                    )

                elif k == pygame.K_TAB:
                    self.panel_ren.panel_tab = (self.panel_ren.panel_tab + 1) % 5

                else:
                    for i, knum in enumerate([
                        pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5
                    ]):
                        if k == knum:
                            self.panel_ren.panel_tab = i

                    if not self.ai_mode and not self.game_over and not self.paused:
                        if k == pygame.K_UP:    self.snake.set_direction(UP)
                        elif k == pygame.K_DOWN:  self.snake.set_direction(DOWN)
                        elif k == pygame.K_LEFT:  self.snake.set_direction(LEFT)
                        elif k == pygame.K_RIGHT: self.snake.set_direction(RIGHT)

            elif ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                self.panel_ren.handle_tab_click(mx, my)

            elif ev.type == pygame.MOUSEWHEEL:
                mx, _ = pygame.mouse.get_pos()
                if mx >= GAME_W:
                    self.panel_ren.scroll(ev.y)

    # ── AI Decision ───────────────────────────────────────────────────────────

    def _ai_decide(self):
        """
        Full AI pipeline each tick:
          1. Build Knowledge Base from current game state.
          2. Forward Chaining: fire reactive rules.
          3. If no rule fired → Backward Chaining (Planner) runs search.
          4. Update LiveState for the UI.
          5. Record stats in ComparisonTracker.
          6. Log decision to file.
        """
        import time
        t0 = time.perf_counter()

        kb   = KnowledgeBase(self.snake, self.food)
        ir   = self.inference.infer(kb)
        ls   = self.ls

        # ── Forward chaining handled everything ─────────────────────────
        if not ir.use_planner:
            self.snake.set_direction(ir.direction)
            ls.active_rule    = ir.rule_fired
            ls.path_found     = False
            ls.path_len       = 0
            ls.fallback       = True
            ls.nodes_explored = 0
            ls.nodes_seen     = 0
            ls.next_cell      = None
            ls.wrap_used      = False
            alg = self.cfg.algorithm
            ms  = (time.perf_counter() - t0) * 1000
            ls.decision_ms = ms

            self.tracker.record(
                alg=alg, path_len=0, nodes=0, time_ms=ms,
                used_fallback=True, score=self.score,
            )
            self.logger.log_decision(
                tick=self.tick_count, alg=alg, rule=ir.rule_fired,
                path_len=0, nodes=0, time_ms=ms,
                fallback=True, direction=str(ir.direction), score=self.score,
            )
            return

        # ── Planner (backward chaining) ──────────────────────────────────
        pr   = self.planner.plan(kb, self.score)
        alg  = pr.algorithm
        ms   = (time.perf_counter() - t0) * 1000
        self.snake.set_direction(pr.direction)

        # ── Detect hybrid-driven algorithm switches ───────────────────────
        # When hybrid mode is on, the planner may switch algorithms
        # automatically based on score. Track this in history.
        if self.cfg.hybrid_mode and alg != self._last_hybrid_alg:
            if self._last_hybrid_alg is not None:
                # This is a genuine hybrid switch
                ls.record_algorithm_switch(
                    algorithm=alg,
                    tick=self.tick_count,
                    score=self.score,
                    reason="hybrid",
                )
            self._last_hybrid_alg = alg

        # ── Closed-set for visualisation (A* only, non-blocking) ─────────
        if alg == "astar" and not pr.used_fallback:
            self.closed_vis = self._astar_vis.get_closed_set_after(
                kb.head, kb.food, kb.obstacles
            )
        else:
            self.closed_vis = set()

        # ── Update LiveState ─────────────────────────────────────────────
        sr   = pr.search   # SearchResult (may have empty path on fallback)
        path = sr.path if sr else []

        ls.active_rule    = ir.rule_fired
        ls.algorithm      = alg
        ls.path_found     = len(path) >= 2
        ls.path_len       = len(path) - 1 if len(path) >= 2 else 0
        ls.fallback       = pr.used_fallback
        ls.nodes_explored = sr.nodes_explored if sr else 0
        ls.nodes_seen     = sr.nodes_seen     if sr else 0
        ls.decision_ms    = ms
        ls.wrap_used      = False

        if len(path) >= 2:
            next_cell      = path[1]
            ls.next_cell   = next_cell
            ls.g_next      = 1
            ls.h_next      = manhattan_wrap(next_cell, kb.food)
            ls.f_next      = ls.g_next + ls.h_next
            ls.h_head      = manhattan_wrap(kb.head, kb.food)
            ls.f_head      = ls.h_head
            self.ai_path   = path

            # Check wrap
            hx, hy = kb.head
            nx, ny = next_cell
            ls.wrap_used = (
                (hx == 0 and nx > hx + 1) or
                (ny == 0 and hy > ny + 1) or
                (abs(nx - hx) > 1) or (abs(ny - hy) > 1)
            )
            if ls.wrap_used:
                ls.push_log("Portal wrap used!")
            ls.push_log(f"{alg}: {ls.path_len} steps, {ls.nodes_explored} nodes")
        else:
            ls.next_cell = None
            self.ai_path = []
            ls.push_log(f"{alg}: no path found — fallback active")

        # ── Tracker + Logger ─────────────────────────────────────────────
        self.tracker.record(
            alg=alg,
            path_len=ls.path_len,
            nodes=ls.nodes_explored,
            time_ms=ms,
            used_fallback=pr.used_fallback,
            score=self.score,
        )
        self.logger.log_decision(
            tick=self.tick_count, alg=alg, rule=ir.rule_fired,
            path_len=ls.path_len, nodes=ls.nodes_explored, time_ms=ms,
            fallback=pr.used_fallback, direction=str(pr.direction), score=self.score,
        )

    # ── Single tick ───────────────────────────────────────────────────────────

    def _tick(self):
        if self.game_over:
            return

        self.tick_count += 1

        if self.ai_mode:
            self._ai_decide()

        new_head = self.snake.move()

        if self.snake.hits_self():
            self.game_over = True
            self.ls.push_log("GAME OVER — self collision!")
            self.logger.log_event(f"GAME_OVER score={self.score}")
            self.tracker.print_summary()
            return

        if new_head == self.food.position:
            self.snake.grow()
            self.score += 1
            self.food.respawn(self.snake.body_set)
            self.ai_path    = []
            self.closed_vis = set()
            self.fps        = min(BASE_FPS + (self.score // 5) * FPS_INCREMENT, MAX_FPS)
            self.ls.push_log(f"Food eaten! Score = {self.score}")
            self.logger.log_event(f"FOOD_EATEN score={self.score}")

        # ── Update LiveState ──────────────────────────────────────────────
        ls                   = self.ls
        ls.mode              = f"AI: {self.cfg.algorithm}" if self.ai_mode else "MANUAL"
        ls.algorithm         = self.cfg.algorithm
        ls.paused            = self.paused
        ls.score             = self.score
        ls.fps               = self.fps
        ls.snake_len         = self.snake.length
        ls.head_pos          = self.snake.head
        ls.food_pos          = self.food.position
        ls.direction         = DIR_NAMES.get(self.snake.direction, "?")
        ls.dir_arrow         = DIR_ARROW.get(self.snake.direction, "?")
        ls.comparison_rows   = self.tracker.panel_rows()
        ls.tick              = self.tick_count
        # Sync hybrid state to LiveState for panel display
        ls.hybrid_mode       = self.cfg.hybrid_mode
        ls.hybrid_threshold  = self.cfg.hybrid_threshold
        ls.hybrid_early      = self.cfg.hybrid_early
        ls.hybrid_late       = self.cfg.hybrid_late

        if not self.ai_mode:
            ls.path_found  = False
            ls.path_len    = 0
            ls.fallback    = False
            ls.wrap_used   = False
            ls.next_cell   = None
            ls.active_rule = ""

    # ── Update (called each frame) ────────────────────────────────────────────

    def update(self):
        if not self.paused:
            self._tick()

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self):
        self.game_ren.draw(
            screen     = self.screen,
            snake      = self.snake,
            food       = self.food,
            ai_path    = self.ai_path,
            closed_vis = self.closed_vis,
            score      = self.score,
            fps        = self.fps,
            ai_mode    = self.ai_mode,
            paused     = self.paused,
            game_over  = self.game_over,
            algorithm  = self.cfg.algorithm,
        )
        self.panel_ren.draw(self.screen, self.ls)
        pygame.display.flip()

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(self.fps)

    def _quit(self):
        self.logger.log_event("QUIT")
        self.logger.close()
        self.tracker.print_summary()
        pygame.quit()
        sys.exit()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    Game().run()