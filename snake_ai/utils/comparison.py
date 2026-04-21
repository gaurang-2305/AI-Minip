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
"""

from dataclasses import dataclass, field
from engine.constants import ALG_LABELS


@dataclass
class AlgStats:
    """Accumulated statistics for one algorithm."""
    name:             str
    total_path_len:   int   = 0
    total_nodes:      int   = 0
    total_time_ms:    float = 0.0
    total_fallbacks:  int   = 0
    decisions:        int   = 0
    score:            int   = 0
    survival_ticks:   int   = 0

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


class ComparisonTracker:
    """
    Singleton-style tracker updated each AI tick.
    Call record() after every Planner decision.
    """

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
        s.score            = max(s.score, score)
        s.survival_ticks  += 1

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def stats(self, alg: str) -> AlgStats | None:
        return self._stats.get(alg)

    def all_stats(self) -> list[AlgStats]:
        """Return all tracked algorithms sorted by avg path length (ascending)."""
        return sorted(self._stats.values(), key=lambda s: s.avg_path_len)

    # ── Console summary table ─────────────────────────────────────────────────

    def print_summary(self):
        all_s = self.all_stats()
        if not all_s:
            print("[Comparison] No data recorded yet.")
            return

        header = (
            f"{'Algorithm':<22} {'Decisions':>10} {'Avg Path':>10} "
            f"{'Avg Nodes':>11} {'Avg ms':>8} {'Fallback%':>10} {'Score':>7}"
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
                f"{s.fallback_rate*100:>9.1f}% {s.score:>7}"
            )
        print(sep + "\n")

    # ── Panel rows (for UI rendering) ────────────────────────────────────────

    def panel_rows(self) -> list[dict]:
        """Return a list of dicts suitable for the comparison panel renderer."""
        rows = []
        for s in self.all_stats():
            rows.append({
                "name":       s.name,
                "label":      ALG_LABELS.get(s.name, s.name),
                "decisions":  s.decisions,
                "avg_path":   round(s.avg_path_len, 1),
                "avg_nodes":  round(s.avg_nodes, 1),
                "avg_ms":     round(s.avg_time_ms, 3),
                "fallback_pct": round(s.fallback_rate * 100, 1),
                "score":      s.score,
            })
        return rows
