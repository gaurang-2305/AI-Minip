"""
engine/state.py
===============
LiveState — a structured snapshot of the current game state,
written each tick by the game loop and read by the UI renderer.

AI Concept: this is the WORKING MEMORY of the inference engine.
It holds the most recent observations and AI decisions so the UI
can display them without coupling to the game/AI internals.
"""

from dataclasses import dataclass, field


@dataclass
class AlgorithmSwitch:
    """Records a single algorithm change event."""
    algorithm: str
    tick:      int
    score:     int
    reason:    str = "manual"   # "manual" | "hybrid"


@dataclass
class LiveState:
    """
    Flat record updated each game tick.
    All fields have sensible defaults so the UI renders cleanly before
    the first AI decision is made.
    """

    # ── Mode / status ────────────────────────────────────────────────────────
    mode:      str  = "MANUAL"
    paused:    bool = False
    score:     int  = 0
    fps:       int  = 6
    algorithm: str  = "astar"   # currently active algorithm name

    # ── Snake / food positions ───────────────────────────────────────────────
    snake_len: int             = 3
    head_pos:  tuple[int, int] = (0, 0)
    food_pos:  tuple[int, int] = (0, 0)
    direction: str             = "RIGHT"
    dir_arrow: str             = "→"

    # ── Path info ────────────────────────────────────────────────────────────
    path_found:    bool              = False
    path_len:      int               = 0
    next_cell:     tuple | None      = None
    nodes_explored: int              = 0   # closed-set size
    nodes_seen:     int              = 0   # open-set size (all g_scores entries)

    # ── g / h / f at head and next cell ─────────────────────────────────────
    g_head: int = 0
    h_head: int = 0
    f_head: int = 0
    g_next: int = 0
    h_next: int = 0
    f_next: int = 0

    # ── Flags ────────────────────────────────────────────────────────────────
    fallback:       bool = False
    wrap_used:      bool = False

    # ── Decision log (ring buffer, max 10 entries) ───────────────────────────
    log: list = field(default_factory=list)

    # ── Forward-chaining rule that fired this tick ───────────────────────────
    active_rule: str = ""

    # ── Timing (milliseconds for last AI decision) ───────────────────────────
    decision_ms: float = 0.0

    # ── Comparison stats (populated by ComparisonTracker) ───────────────────
    comparison_rows: list = field(default_factory=list)

    # ── Algorithm switch history ─────────────────────────────────────────────
    # Each entry is an AlgorithmSwitch dataclass recording when/why algo changed
    algorithm_history: list = field(default_factory=list)

    # ── Hybrid mode state ────────────────────────────────────────────────────
    hybrid_mode:      bool = False
    hybrid_threshold: int  = 10
    hybrid_early:     str  = "greedy"
    hybrid_late:      str  = "astar"

    # ── Tick counter (for history display) ───────────────────────────────────
    tick: int = 0

    # ── helpers ──────────────────────────────────────────────────────────────

    def push_log(self, msg: str):
        self.log.append(msg)
        if len(self.log) > 12:
            self.log.pop(0)

    def record_algorithm_switch(self, algorithm: str, tick: int, score: int,
                                 reason: str = "manual"):
        """
        Record an algorithm change in history.
        Only records if it's actually a different algorithm.
        """
        if (not self.algorithm_history or
                self.algorithm_history[-1].algorithm != algorithm):
            self.algorithm_history.append(
                AlgorithmSwitch(algorithm=algorithm, tick=tick,
                                score=score, reason=reason)
            )
            # Keep history bounded to last 20 entries
            if len(self.algorithm_history) > 20:
                self.algorithm_history.pop(0)

    def reset(self):
        """Reset to defaults (called on game restart)."""
        for f_name, f_def in self.__dataclass_fields__.items():
            default = f_def.default
            if default is not f_def.default_factory:
                setattr(self, f_name, default)
            else:
                setattr(self, f_name, f_def.default_factory())