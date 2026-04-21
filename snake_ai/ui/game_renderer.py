"""
ui/game_renderer.py
===================
Renders the game area (left 620×460 px):
  grid, closed-set overlay, planned path, snake, food, HUD, pause/game-over overlays.
"""

import pygame
from engine.constants import (
    GAME_W, GAME_H, CELL, COLS, ROWS,
    C_BG, C_GRID, C_HEAD, C_BODY, C_FOOD,
    C_TEXT, C_DIM, C_ACCENT, C_GOOD, C_WARN, C_BAD, C_PAUSE,
    ALG_COLOURS, ALG_LABELS,
)
from engine.entities import Snake, Food


class GameRenderer:

    def __init__(self):
        self.f_hud   = pygame.font.SysFont("Consolas", 13, bold=True)
        self.f_small = pygame.font.SysFont("Consolas", 11)
        self.f_huge  = pygame.font.SysFont("Consolas", 32, bold=True)
        self.f_body  = pygame.font.SysFont("Consolas", 12)

    # ── Main draw call ────────────────────────────────────────────────────────

    def draw(
        self,
        screen:     pygame.Surface,
        snake:      Snake,
        food:       Food,
        ai_path:    list,
        closed_vis: set,
        score:      int,
        fps:        int,
        ai_mode:    bool,
        paused:     bool,
        game_over:  bool,
        algorithm:  str,
    ):
        screen.fill(C_BG, (0, 0, GAME_W, GAME_H))
        self._draw_grid(screen)
        if ai_mode:
            self._draw_closed(screen, closed_vis, snake.body_set, food.position)
            self._draw_path(screen, ai_path)
        self._draw_food(screen, food)
        self._draw_snake(screen, snake)
        self._draw_hud(screen, score, ai_mode, algorithm)
        if paused and not game_over:
            self._draw_pause_overlay(screen)
        if game_over:
            self._draw_game_over(screen, score)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _draw_grid(self, screen):
        for c in range(0, GAME_W, CELL):
            pygame.draw.line(screen, C_GRID, (c, 0), (c, GAME_H))
        for r in range(0, GAME_H, CELL):
            pygame.draw.line(screen, C_GRID, (0, r), (GAME_W, r))

    def _draw_closed(self, screen, closed_vis: set, body_set: set, food_pos: tuple):
        for cx, cy in closed_vis:
            if (cx, cy) not in body_set and (cx, cy) != food_pos:
                s = pygame.Surface((CELL - 2, CELL - 2), pygame.SRCALPHA)
                s.fill((80, 40, 110, 38))
                screen.blit(s, (cx * CELL + 1, cy * CELL + 1))

    def _draw_path(self, screen, ai_path: list):
        if not ai_path or len(ai_path) < 3:
            return
        for i, (cx, cy) in enumerate(ai_path[1:-1], 1):
            alpha = max(60, 200 - i * 7)
            s = pygame.Surface((CELL - 6, CELL - 6), pygame.SRCALPHA)
            s.fill((55, 88, 210, alpha))
            screen.blit(s, (cx * CELL + 3, cy * CELL + 3))

    def _draw_snake(self, screen, snake: Snake):
        body_list = list(snake.body)
        total     = len(body_list)
        for i, (cx, cy) in enumerate(body_list):
            if i == 0:
                col = C_HEAD
            else:
                t   = i / max(total - 1, 1)
                col = (
                    int(C_BODY[0] * (1 - t * 0.55)),
                    int(C_BODY[1] * (1 - t * 0.55)),
                    int(C_BODY[2] * (1 - t * 0.55)),
                )
            rect = pygame.Rect(cx * CELL + 1, cy * CELL + 1, CELL - 2, CELL - 2)
            pygame.draw.rect(screen, col, rect, border_radius=5)
            if i == 0:
                ex1, ex2 = cx * CELL + 5, cx * CELL + CELL - 7
                ey       = cy * CELL + 7
                pygame.draw.circle(screen, (0, 0, 0), (ex1, ey), 2)
                pygame.draw.circle(screen, (0, 0, 0), (ex2, ey), 2)

    def _draw_food(self, screen, food: Food):
        cx, cy = food.position
        px, py = cx * CELL + CELL // 2, cy * CELL + CELL // 2
        pygame.draw.circle(screen, C_FOOD,        (px, py), CELL // 2 - 2)
        pygame.draw.circle(screen, (255, 150, 165), (px - 3, py - 3), 3)

    def _draw_hud(self, screen, score: int, ai_mode: bool, algorithm: str):
        alg_col = ALG_COLOURS.get(algorithm, C_ACCENT) if ai_mode else C_DIM
        alg_lbl = ALG_LABELS.get(algorithm, algorithm) if ai_mode else "MANUAL"

        sc_surf = self.f_hud.render(f"Score: {score}", True, C_GOOD)
        sc_rect = sc_surf.get_rect(topleft=(10, 6))
        pygame.draw.rect(screen, (0, 0, 0), sc_rect.inflate(12, 6), border_radius=4)
        screen.blit(sc_surf, sc_rect)

        ai_surf = self.f_hud.render(f"AI: {alg_lbl}", True, alg_col)
        ai_rect = ai_surf.get_rect(topright=(GAME_W - 10, 6))
        screen.blit(ai_surf, ai_rect)

        hint = self.f_small.render(
            "[A] AI   [Q/W/E/S/D] Algo   [H] Hybrid   [P] Pause   [R] Restart   [TAB] Panel",
            True, C_DIM,
        )
        screen.blit(hint, (8, GAME_H - 14))

    def _draw_pause_overlay(self, screen):
        ov = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        ov.fill((7, 9, 16, 165))
        screen.blit(ov, (0, 0))
        for surf, cy in [
            (self.f_huge.render("PAUSED", True, C_PAUSE),                    GAME_H//2 - 28),
            (self.f_body.render("N = step one frame", True, C_DIM),          GAME_H//2 + 12),
            (self.f_body.render("P / SPACE = resume", True, C_DIM),          GAME_H//2 + 30),
        ]:
            screen.blit(surf, surf.get_rect(center=(GAME_W // 2, cy)))

    def _draw_game_over(self, screen, score: int):
        ov = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        ov.fill((7, 9, 16, 215))
        screen.blit(ov, (0, 0))
        for surf, cy in [
            (self.f_huge.render("GAME  OVER", True, C_BAD),                GAME_H//2 - 36),
            (self.f_hud.render(f"Final Score: {score}", True, C_TEXT),     GAME_H//2 + 8),
            (self.f_hud.render("Press R to Restart", True, C_ACCENT),      GAME_H//2 + 36),
        ]:
            screen.blit(surf, surf.get_rect(center=(GAME_W // 2, cy)))
