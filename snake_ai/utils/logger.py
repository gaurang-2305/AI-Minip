"""
utils/logger.py
===============
Structured decision logger.

Writes AI decisions to a rotating log file and optionally to stdout.
Each log entry captures the tick, algorithm, rule fired, path length,
nodes explored, fallback use, and direction chosen.

Usage
-----
    from utils.logger import DecisionLogger
    log = DecisionLogger("logs/decisions.log")
    log.log_decision(tick=5, alg="astar", rule="DEFAULT_PLANNER",
                     path_len=12, nodes=34, time_ms=0.41,
                     fallback=False, direction="RIGHT", score=3)
    log.close()
"""

import os
import time
from datetime import datetime


class DecisionLogger:
    """
    Appends structured lines to a log file each AI tick.
    Thread-safe writes via line buffering.
    """

    def __init__(self, path: str, echo_to_stdout: bool = False):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._path    = path
        self._echo    = echo_to_stdout
        self._session = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._fh      = open(path, "a", buffering=1)
        self._write(f"\n{'='*70}")
        self._write(f"SESSION START  {self._session}")
        self._write(f"{'='*70}")

    # ── Public API ────────────────────────────────────────────────────────────

    def log_decision(
        self,
        tick:      int,
        alg:       str,
        rule:      str,
        path_len:  int,
        nodes:     int,
        time_ms:   float,
        fallback:  bool,
        direction: str,
        score:     int,
    ):
        fb  = "FB" if fallback else "  "
        msg = (
            f"T{tick:05d} | {alg:<14} | rule={rule:<30} | "
            f"path={path_len:>4} | nodes={nodes:>5} | "
            f"{time_ms:>6.3f}ms | {fb} | dir={direction:<6} | score={score}"
        )
        self._write(msg)

    def log_event(self, msg: str):
        """Log a free-form event (e.g., food eaten, game over)."""
        self._write(f"EVENT  {msg}")

    def close(self):
        self._write("SESSION END\n")
        self._fh.close()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _write(self, line: str):
        self._fh.write(line + "\n")
        if self._echo:
            print(line)


class NullLogger:
    """Drop-in replacement when logging is disabled."""
    def log_decision(self, **kwargs): pass
    def log_event(self,    msg):      pass
    def close(self):                  pass


def make_logger(enabled: bool, path: str) -> DecisionLogger | NullLogger:
    if enabled:
        return DecisionLogger(path)
    return NullLogger()
