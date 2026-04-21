"""
config/loader.py
================
Loads and validates the JSON configuration file.
Provides a singleton Config object used throughout the system.
"""

import json
import os

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "settings.json")

# Valid algorithm names
VALID_ALGORITHMS = {"astar", "bfs", "dfs", "greedy", "hill_climbing"}


class Config:
    """
    Lightweight config wrapper.
    Access any setting as an attribute: cfg.algorithm, cfg.display['fps_base'], etc.
    """

    def __init__(self, path: str = _DEFAULT_PATH):
        self._path = path
        self._data: dict = {}
        self.load()

    # ── public interface ────────────────────────────────────────────────────
    def load(self):
        """(Re)load settings from disk."""
        with open(self._path, "r") as fh:
            self._data = json.load(fh)
        self._validate()

    def save(self):
        """Persist current settings back to disk."""
        with open(self._path, "w") as fh:
            json.dump(self._data, fh, indent=2)

    def set_algorithm(self, name: str):
        """Switch algorithm at runtime."""
        if name not in VALID_ALGORITHMS:
            raise ValueError(f"Unknown algorithm '{name}'. Valid: {VALID_ALGORITHMS}")
        self._data["algorithm"] = name

    # ── attribute-style access ──────────────────────────────────────────────
    def __getattr__(self, key: str):
        if key.startswith("_"):
            raise AttributeError(key)
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(f"Config has no setting '{key}'")

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    # ── validation ──────────────────────────────────────────────────────────
    def _validate(self):
        alg = self._data.get("algorithm", "astar")
        if alg not in VALID_ALGORITHMS:
            print(f"[Config] Invalid algorithm '{alg}', falling back to 'astar'.")
            self._data["algorithm"] = "astar"

    def __repr__(self):
        return f"Config(algorithm={self._data.get('algorithm')}, hybrid={self._data.get('hybrid_mode')})"


# Module-level singleton
_cfg_instance: Config | None = None


def get_config(path: str = _DEFAULT_PATH) -> Config:
    """Return the global Config singleton (lazy-init)."""
    global _cfg_instance
    if _cfg_instance is None:
        _cfg_instance = Config(path)
    return _cfg_instance
