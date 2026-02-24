"""Per-user state management for the NiceGUI Viperball app.

Uses app.storage.user (cookie-based, no await required) so that the
page can render synchronously. This works with NiceGUI 3.x without
needing ``await client.connected()``.
"""

from __future__ import annotations
from typing import Optional

from nicegui import app


class UserState:
    """Holds all mutable state for a single user session.

    Core session fields are backed by app.storage.user (NiceGUI's
    cookie-based persistent storage) so that creating a season/dynasty
    and refreshing the page preserves the active session.
    """

    def __init__(self):
        self._store = app.storage.user

        self.last_result: Optional[dict] = None
        self.last_seed: int = 0
        self.batch_results: Optional[list] = None
        self.play_inspector_results: Optional[list] = None
        self.dq_css_injected: bool = False
        self._team_states_cache: Optional[dict] = None

    @property
    def session_id(self) -> Optional[str]:
        return self._store.get("session_id")

    @session_id.setter
    def session_id(self, value: Optional[str]):
        self._store["session_id"] = value

    @property
    def mode(self) -> Optional[str]:
        return self._store.get("mode")

    @mode.setter
    def mode(self, value: Optional[str]):
        self._store["mode"] = value

    @property
    def human_teams(self) -> list[str]:
        return self._store.get("human_teams", [])

    @human_teams.setter
    def human_teams(self, value: list[str]):
        self._store["human_teams"] = value

    @property
    def dynasty_teams(self) -> list[str]:
        return self._store.get("dynasty_teams", [])

    @dynasty_teams.setter
    def dynasty_teams(self, value: list[str]):
        self._store["dynasty_teams"] = value

    @property
    def playoff_size(self) -> int:
        return self._store.get("playoff_size", 8)

    @playoff_size.setter
    def playoff_size(self, value: int):
        self._store["playoff_size"] = value

    @property
    def bowl_count(self) -> int:
        return self._store.get("bowl_count", 4)

    @bowl_count.setter
    def bowl_count(self, value: int):
        self._store["bowl_count"] = value

    @property
    def season_ai_seed(self) -> int:
        return self._store.get("season_ai_seed", 0)

    @season_ai_seed.setter
    def season_ai_seed(self, value: int):
        self._store["season_ai_seed"] = value

    @property
    def season_conf_seed(self) -> int:
        return self._store.get("season_conf_seed", 0)

    @season_conf_seed.setter
    def season_conf_seed(self, value: int):
        self._store["season_conf_seed"] = value

    @property
    def season_phase(self) -> str:
        return self._store.get("season_phase", "setup")

    @season_phase.setter
    def season_phase(self, value: str):
        self._store["season_phase"] = value

    @property
    def dyn_season_phase(self) -> str:
        return self._store.get("dyn_season_phase", "setup")

    @dyn_season_phase.setter
    def dyn_season_phase(self, value: str):
        self._store["dyn_season_phase"] = value

    @property
    def dyn_playoff_size(self) -> int:
        return self._store.get("dyn_playoff_size", 8)

    @dyn_playoff_size.setter
    def dyn_playoff_size(self, value: int):
        self._store["dyn_playoff_size"] = value

    @property
    def dyn_bowl_count(self) -> int:
        return self._store.get("dyn_bowl_count", 4)

    @dyn_bowl_count.setter
    def dyn_bowl_count(self, value: int):
        self._store["dyn_bowl_count"] = value

    @property
    def dq_current_week(self) -> int:
        return self._store.get("dq_current_week", 0)

    @dq_current_week.setter
    def dq_current_week(self, value: int):
        self._store["dq_current_week"] = value

    def clear_session(self):
        """Reset all session-related state."""
        self.session_id = None
        self.mode = None
        self.human_teams = []
        self.playoff_size = 8
        self.bowl_count = 4
        self.season_ai_seed = 0
        self.season_conf_seed = 0
        self.season_phase = "setup"
        self.dynasty_teams = []
        self.dyn_season_phase = "setup"
        self.dyn_playoff_size = 8
        self.dyn_bowl_count = 4
        self.dq_current_week = 0
        self.last_result = None
        self.last_seed = 0
        self.batch_results = None
        self._team_states_cache = None
