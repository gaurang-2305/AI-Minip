# 🐍 Snake AI System — Comparative Study of Search Algorithms

A complete AI architecture built on top of a Snake game engine.
Five pluggable search algorithms, forward/backward chaining, live
performance comparison, and a scrollable info panel — all in one
self-contained Python + Pygame project.

---

## 📁 Folder Structure

```
snake_ai/
├── main.py                    ← Entry point / game loop
│
├── config/
│   ├── settings.json          ← Algorithm, hybrid, log settings
│   └── loader.py              ← Config singleton + validation
│
├── engine/                    ← KNOWLEDGE BASE
│   ├── constants.py           ← All layout, colour, direction constants
│   ├── grid.py                ← Wrap, neighbours, Manhattan, flood fill
│   ├── entities.py            ← Snake, Food game objects
│   └── state.py               ← LiveState (working memory for UI)
│
├── ai/                        ← INFERENCE ENGINE + PLANNER
│   ├── knowledge_base.py      ← Derived facts from game state
│   ├── inference_engine.py    ← Forward chaining (reactive rules)
│   └── planner.py             ← Backward chaining (goal-driven search)
│
├── strategies/                ← SEARCH ALGORITHMS (pluggable)
│   ├── base.py                ← BaseStrategy interface + SearchResult
│   ├── astar.py               ← A* (optimal + informed)
│   ├── bfs.py                 ← BFS (optimal + blind)
│   ├── dfs.py                 ← DFS (sub-optimal + blind)
│   ├── greedy.py              ← Greedy Best-First (fast + heuristic)
│   └── hill_climbing.py       ← Hill Climbing (local + no backtrack)
│
├── ui/
│   ├── game_renderer.py       ← Game area: grid, snake, food, HUD
│   └── panel.py               ← 5-tab info panel (scrollable)
│
├── utils/
│   ├── comparison.py          ← Per-algorithm performance tracker
│   └── logger.py              ← Decision log → file
│
└── logs/
    └── decisions.log          ← Written at runtime (if enabled)
```

---

## 🚀 Quick Start

```bash
pip install pygame
cd snake_ai
python main.py
```

---

## ⌨️ Controls

| Key | Action |
|-----|--------|
| Arrow Keys | Manual movement |
| **A** | Toggle AI mode ON/OFF |
| **Q** | Switch to A* |
| **W** | Switch to BFS |
| **E** | Switch to DFS |
| **S** | Switch to Greedy Best-First |
| **D** | Switch to Hill Climbing |
| **H** | Toggle Hybrid mode |
| **P / Space** | Pause / Resume |
| **N** | Step one frame (while paused) |
| **R** | Restart + print comparison table |
| **TAB** | Cycle panel tabs |
| **1–5** | Jump to panel tab |
| **Scroll Wheel** | Scroll panel |
| **ESC** | Quit |

---

## 🧠 AI Architecture

### Classical AI Component Mapping

| AI Concept | Module | Description |
|------------|--------|-------------|
| **Knowledge Base** | `engine/` | Snake position, food, grid topology, obstacles |
| **Working Memory** | `engine/state.py` | LiveState updated each tick for UI |
| **Inference Engine** | `ai/inference_engine.py` | Forward chaining — reactive rule system |
| **Planner** | `ai/planner.py` | Backward chaining — goal-driven search selection |
| **Search Algorithms** | `strategies/` | A*, BFS, DFS, Greedy, Hill Climbing |
| **Fallback Strategy** | `engine/grid.py` | Flood-fill survival (BFS open-space maximisation) |

---

### Forward Chaining (Reactive Rules)

Rules fire in priority order each tick. The **first** matching rule wins.

```
RULE 1  NO_SAFE_MOVE         All 4 directions blocked → accept death gracefully
RULE 2  FOOD_ADJACENT        Food is 1 step away → move directly to it
RULE 3  LOW_SPACE_SURVIVAL   Open space < 8 cells → immediate flood-fill mode
RULE 4  DANGER_AHEAD_PLANNER Current direction leads to wall → hand off to Planner
RULE 5  DEFAULT_PLANNER      No reactive condition → full search algorithm runs
```

### Backward Chaining (Goal-Driven Planner)

```
GOAL:       head position == food position

SUB-GOAL 1: Find a path from head → food
            → Run selected search algorithm
            → If path found: follow it

SUB-GOAL 2: No path exists → survive
            → Run flood-fill on each safe neighbour
            → Move to neighbour with most open space

SUB-GOAL 3: No survival move → accept death
```

---

## 🔍 Algorithm Comparison

| Algorithm | Complete | Optimal | Nodes Explored | Notes |
|-----------|----------|---------|----------------|-------|
| **A\*** | ✅ Yes | ✅ Yes | ~30–80 | Best overall — informed + optimal |
| **BFS** | ✅ Yes | ✅ Yes | ~100–400 | Optimal but slow — no heuristic |
| **DFS** | ✅ Yes | ❌ No | ~100–400 | Often very long winding paths |
| **Greedy** | ✅ Yes | ❌ No | ~20–60 | Fast early, trapped late-game |
| **Hill Climbing** | ❌ No | ❌ No | O(steps) | Local only — random restart on stuck |

### Formula Reference

```
A*:       f(n) = g(n) + h(n)   ← balances cost + estimate
Greedy:   f(n) = h(n)           ← ignores cost already paid
BFS:      no f — expands by depth layer
DFS:      no f — LIFO stack, dives deep first
Hill Clmb: moves to best neighbour only — no open list
```

### Heuristic Used (A* and Greedy)

Wrap-aware Manhattan distance:
```python
h = min(|dx|, COLS - |dx|) + min(|dy|, ROWS - |dy|)
```

This is **admissible** (never over-estimates) because the snake can pass through
walls, so the wrap-around route is always a valid shorter path.

---

## ⚙️ Config File (`config/settings.json`)

```json
{
  "algorithm":         "astar",        // default algorithm
  "hybrid_mode":       false,          // Greedy early → A* late
  "hybrid_threshold":  10,             // score at which to switch
  "hybrid_early":      "greedy",
  "hybrid_late":       "astar",
  "fallback":          "flood_fill",
  "log_decisions":     true,
  "log_file":          "logs/decisions.log",
  "display": {
    "show_path":        true,
    "show_closed_set":  true,
    "fps_base":         6,
    "fps_max":          14,
    "fps_increment":    1
  }
}
```

---

## 📊 Comparison System

After each game (or on quit), a summary table prints to the console:

```
----------------------------------------------------------------------
  ALGORITHM COMPARISON SUMMARY
----------------------------------------------------------------------
Algorithm              Decisions   Avg Path   Avg Nodes    Avg ms  Fallback%   Score
----------------------------------------------------------------------
A* (A-Star)                  142       12.3        45.1     0.041       3.5%      18
BFS                           89       12.1       198.4     0.187       5.6%      12
Greedy Best-First            201        9.8        28.7     0.019      18.2%       9
DFS                           76       34.5       210.2     0.201       8.1%       8
Hill Climbing                112       11.2        15.3     0.008      31.4%       6
----------------------------------------------------------------------
```

The **COMPARISON** panel tab (press 5) shows this data live during gameplay.

---

## 🔀 Hybrid Mode

Press **H** to toggle hybrid mode:
- **Early game** (score < threshold): uses `Greedy` — fast, direct routes
- **Late game** (score ≥ threshold): uses `A*` — optimal routing through dense body

Configure in `settings.json`: `hybrid_mode`, `hybrid_threshold`, `hybrid_early`, `hybrid_late`.

---

## 📝 Decision Log

When `log_decisions: true` in config, every AI decision is written to `logs/decisions.log`:

```
T00042 | astar          | rule=DEFAULT_PLANNER                | path=  12 | nodes=   45 | 0.041ms |    | dir=(1, 0)  | score=3
T00043 | astar          | rule=FOOD_ADJACENT                  | path=   0 | nodes=    0 | 0.001ms | FB | dir=(0, 1)  | score=3
```

---

## 🎓 Key AI Concepts Demonstrated

1. **Search completeness** — A*/BFS always find a path; Hill Climbing may not
2. **Optimality** — A* and BFS guarantee shortest path; others don't
3. **Admissible heuristics** — wrap-aware Manhattan never over-estimates
4. **Forward chaining** — data-driven reactive rules that override the planner
5. **Backward chaining** — goal-directed reasoning decomposed into sub-goals
6. **Strategy pattern** — all algorithms implement the same interface
7. **Fallback strategy** — flood-fill survival maximises future option space
8. **Hybrid planning** — algorithm selected based on game phase / score
