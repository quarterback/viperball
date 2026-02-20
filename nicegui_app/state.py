"""Per-user state management for the NiceGUI Viperball app.

Replaces Streamlit's st.session_state. Each browser tab gets its own
UserState instance via the @ui.page decorator scope.
"""

from __future__ import annotations
from typing import Optional


class UserState:
    """Holds all mutable state for a single user session."""

    def __init__(self):
        # API session
        self.session_id: Optional[str] = None
        self.mode: Optional[str] = None  # "season" or "dynasty"

        # Season setup
        self.human_teams: list[str] = []
        self.playoff_size: int = 8
        self.bowl_count: int = 4
        self.season_ai_seed: int = 0
        self.season_conf_seed: int = 0
        self.season_phase: str = "setup"  # setup, regular, portal, playoffs, bowls, complete

        # Dynasty setup
        self.dynasty_teams: list[str] = []
        self.dyn_season_phase: str = "setup"
        self.dyn_playoff_size: int = 8
        self.dyn_bowl_count: int = 4

        # Game simulator
        self.last_result: Optional[dict] = None
        self.last_seed: int = 0

        # Batch simulator
        self.batch_results: Optional[list] = None

        # DraftyQueenz
        self.dq_css_injected: bool = False

        # Caches
        self._team_states_cache: Optional[dict] = None

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
        self.last_result = None
        self.last_seed = 0
        self.batch_results = None
        self._team_states_cache = None
