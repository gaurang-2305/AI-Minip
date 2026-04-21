"""
utils/comparison.py
===================
Performance Comparison Tracker.

Records metrics for each algorithm run during a game session.
Provides a summary table (console + panel) and supports runtime
algorithm switching so the player can directly compare strategies.

Metrics tracked per algorithm per episode (game session)
---------------------------------------------------------
  total_path_len   : sum of path lengths found (shorter = more efficient routing)
  total_nodes      : sum of nodes explored (lower = less wasted computation)
  total_time_ms    : total milliseconds spent in search calls
  total_fallbacks  : how many ticks the fallback strategy was used
  decisions        : total number of search calls made
  score            : best score achieved while this algorithm was active
  survival_ticks   : ticks alive while this algorithm was active
  successes        : decisions where a valid path WAS found (not fallback)
  path_hist        : recent path lengths for sparkline / trend display
"""

from dataclasses import dataclass, field
from engine.constants import ALG_LABELS

# Maximum recent-path samples stored per algorithm (used for trend display)
HIST_LEN = 30


@dataclass
class AlgStats:
    """Accumulated statistics for one algorithm."""
    name:             str
    total_path_len:   int   = 0
    total_nodes:      int   = 0
    total_time_ms:    float = 0.0
    total_fallbacks:  int   = 0
    decisions:        int   = 0
    successes:        int   = 0   # decisions with a real path found
    score:            int   = 0
    survival_ticks:   int   = 0
    # Rolling window of recent path lengths for trend display
    path_hist:        list  = field(default_factory=list)
    # Rolling window of recent node counts
    node_hist:        list  = field(default_factory=list)

    # ── Derived properties ────────────────────────────────────────────────

    @property
    def avg_path_len(self) -> float:
        return self.total_path_len / max(self.decisions, 1)

    @property
    def avg_nodes(self) -> float:
        return self.total_nodes / max(self.decisions, 1)

    @property
    def avg_time_ms(self) -> float:
        return self.total_time_ms / max(self.decisions, 1)

    @property
    def fallback_rate(self) -> float:
        return self.total_fallbacks / max(self.decisions, 1)

    @property
    def success_rate(self) -> float:
        return self.successes / max(self.decisions, 1)

    @property
    def efficiency_score(self) -> float:
        """
        Composite efficiency: high success rate, low nodes, short paths.
        Returns a value roughly in [0, 1] where higher is better.
        Useful for ranking algorithms at a glance.
        """
        if self.decisions == 0:
            return 0.0
        # Penalise fallback and high node counts
        sr = self.success_rate
        node_penalty = min(self.avg_nodes / 400.0, 1.0)   # 400 = rough max
        return max(0.0, sr - node_penalty * 0.2)

    def add_path_sample(self, path_len: int):
        self.path_hist.append(path_len)
        if len(self.path_hist) > HIST_LEN:
            self.path_hist.pop(0)

    def add_node_sample(self, nodes: int):
        self.node_hist.append(nodes)
        if len(self.node_hist) > HIST_LEN:
            self.node_hist.pop(0)

    @property
    def path_trend(self) -> str:
        """Return '↑', '↓', '→' based on recent path length trend."""
        h = self.path_hist
        if len(h) < 4:
            return "→"
        recent  = sum(h[-3:]) / 3
        earlier = sum(h[-6:-3]) / 3 if len(h) >= 6 else recent
        if recent > earlier * 1.1:
            return "↑"
        if recent < earlier * 0.9:
            return "↓"
        return "→"


class ComparisonTracker:
    """
    Singleton-style tracker updated each AI tick.
    Call record() after every Planner decision.
    Maintains per-algorithm stats across the session.
    """

    # Defined algorithm order for consistent display
    ALG_ORDER = ["astar", "bfs", "dfs", "greedy", "hill_climbing"]

    def __init__(self):
        self._stats: dict[str, AlgStats] = {}

    def reset(self):
        self._stats.clear()

    def _ensure(self, alg: str):
        if alg not in self._stats:
            self._stats[alg] = AlgStats(name=alg)

    # ── Recording ────────────────────────────────────────────────────────────

    def record(
        self,
        alg:          str,
        path_len:     int,
        nodes:        int,
        time_ms:      float,
        used_fallback: bool,
        score:        int,
    ):
        """Call once per AI tick to accumulate stats."""
        self._ensure(alg)
        s = self._stats[alg]
        s.total_path_len  += path_len
        s.total_nodes     += nodes
        s.total_time_ms   += time_ms
        s.total_fallbacks += int(used_fallback)
        s.decisions       += 1
        if not used_fallback and path_len > 0:
            s.successes += 1
        s.score            = max(s.score, score)
        s.survival_ticks  += 1
        # Rolling samples for trend display
        if path_len > 0:
            s.add_path_sample(path_len)
        s.add_node_sample(nodes)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def stats(self, alg: str) -> AlgStats | None:
        return self._stats.get(alg)

    def all_stats(self) -> list[AlgStats]:
        """
        Return all tracked algorithms in canonical order,
        with any unknown algorithms appended at the end.
        """
        ordered = []
        for name in self.ALG_ORDER:
            if name in self._stats:
                ordered.append(self._stats[name])
        # Add any extra algorithms not in ALG_ORDER
        for name, stat in self._stats.items():
            if name not in self.ALG_ORDER:
                ordered.append(stat)
        return ordered

    def best_algorithm(self) -> str | None:
        """Return name of the best-performing algorithm seen this session."""
        stats = [s for s in self._stats.values() if s.decisions >= 5]
        if not stats:
            return None
        return max(stats, key=lambda s: s.efficiency_score).name

    # ── Console summary table ─────────────────────────────────────────────────

    def print_summary(self):
        all_s = self.all_stats()
        if not all_s:
            print("[Comparison] No data recorded yet.")
            return

        header = (
            f"{'Algorithm':<22} {'Decisions':>10} {'Avg Path':>10} "
            f"{'Avg Nodes':>11} {'Avg ms':>8} {'Fallback%':>10} "
            f"{'Success%':>9} {'Score':>7}"
        )
        sep = "-" * len(header)
        print("\n" + sep)
        print("  ALGORITHM COMPARISON SUMMARY")
        print(sep)
        print(header)
        print(sep)
        for s in all_s:
            label = ALG_LABELS.get(s.name, s.name)
            print(
                f"{label:<22} {s.decisions:>10} {s.avg_path_len:>10.1f} "
                f"{s.avg_nodes:>11.1f} {s.avg_time_ms:>8.3f} "
                f"{s.fallback_rate*100:>9.1f}% "
                f"{s.success_rate*100:>8.1f}% {s.score:>7}"
            )
        print(sep + "\n")

    # ── Panel rows (for UI rendering) ────────────────────────────────────────

    def panel_rows(self) -> list[dict]:
        """Return a list of dicts suitable for the comparison panel renderer."""
        best = self.best_algorithm()
        rows = []
        for s in self.all_stats():
            rows.append({
                "name":         s.name,
                "label":        ALG_LABELS.get(s.name, s.name),
                "decisions":    s.decisions,
                "avg_path":     round(s.avg_path_len, 1),
                "avg_nodes":    round(s.avg_nodes, 1),
                "avg_ms":       round(s.avg_time_ms, 3),
                "fallback_pct": round(s.fallback_rate * 100, 1),
                "success_pct":  round(s.success_rate * 100, 1),
                "score":        s.score,
                "trend":        s.path_trend,
                "is_best":      (s.name == best and s.decisions >= 5),
            })
        return rows