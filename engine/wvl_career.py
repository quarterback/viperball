"""
WVL Career League
=================

A single-purpose pro league whose ONLY reason to exist is to be the
destination for CVL (college) graduates.  When a player graduates out of a
CVL dynasty their *same* PlayerCard is imported here — not a fresh player —
so the same career object keeps accumulating.  Games are simulated one at a
time with the real ViperballEngine, and each game's production is appended
to the card's career, season after season.

Source of truth = the PlayerCard objects in `self.cards`.  Everything else
(club Team objects, schedule, standings) is rebuildable; cards carry the
careers that must persist, so they are what gets serialized.

The league is the Galactic Premiership (18 clubs).  Club rosters are the
generated WVL women's rosters loaded from disk, with imported CVL graduates
spliced in (replacing the weakest filler so roster sizes stay stable).
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional

from engine.wvl_config import TIER_1_CLUBS, CLUBS_BY_KEY
from engine.game_engine import load_team_from_json, ViperballEngine
from engine.player_card import PlayerCard, card_to_player
from engine.db import (
    load_graduating_pools,
    consume_graduating_pool,
    save_blob,
    load_blob,
    list_saves,
)

import os

_LEAGUE_TYPE = "wvl_career_league"
_TIER1_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "wvl_teams", "tier1",
)

RETIREMENT_AGE = 34
DEFAULT_ENTRY_AGE = 22  # CVL grads enter their pro careers around 22


def _new_record(key: str, name: str) -> dict:
    return {
        "team_key": key, "team_name": name,
        "wins": 0, "losses": 0, "ties": 0,
        "pf": 0, "pa": 0,
    }


class WVLCareerLeague:
    """Galactic Premiership — a career-continuation league for CVL graduates."""

    def __init__(self, league_id: str, year: int = 2027):
        self.league_id = league_id
        self.year = year
        self.club_keys: List[str] = [c.key for c in TIER_1_CLUBS]

        # Persistent career state (source of truth)
        self.cards: Dict[str, PlayerCard] = {}          # player_id -> card
        self.roster_cards: Dict[str, List[str]] = {     # club_key -> [player_id]
            k: [] for k in self.club_keys
        }
        self.consumed_pools: List[str] = []
        self.history: List[dict] = []                   # per-season champion summaries

        # Per-season transient state (rebuilt each season)
        self.teams: Dict[str, object] = {}              # club_key -> game_engine.Team
        self.name_to_card: Dict[str, Dict[str, str]] = {}
        self.schedule: List[List[tuple]] = []
        self.results: Dict[int, List[dict]] = {}
        self.standings: Dict[str, dict] = {}
        self.current_week = 0
        self.total_weeks = 0
        self.phase = "preseason"

    # ─────────────────────────────────────────────────────────────
    # SETUP
    # ─────────────────────────────────────────────────────────────
    def _club_name(self, key: str) -> str:
        club = CLUBS_BY_KEY.get(key)
        return club.name if club else key.replace("_", " ").title()

    def _load_clubs(self) -> None:
        """Load each club's generated roster Team from disk."""
        self.teams = {}
        for key in self.club_keys:
            path = os.path.join(_TIER1_DIR, f"{key}.json")
            if not os.path.exists(path):
                continue
            try:
                self.teams[key] = load_team_from_json(path)
            except Exception:
                continue

    def _splice_cards_into_rosters(self) -> None:
        """Put each club's imported graduate cards onto its game Team.

        Replaces the weakest filler players so the roster size is stable and
        the imported stars actually see the field.
        """
        self.name_to_card = {k: {} for k in self.club_keys}
        for key, team in self.teams.items():
            pids = [p for p in self.roster_cards.get(key, []) if p in self.cards]
            if not pids:
                continue
            # Replace the weakest filler 1:1 with imported cards so roster size
            # is stable and the imports (often the best players) see the field.
            fillers = sorted(team.players, key=lambda p: getattr(p, "speed", 0))
            keep = fillers[len(pids):] if len(pids) <= len(fillers) else []
            new_players = list(keep)
            for pid in pids:
                player = card_to_player(self.cards[pid])
                new_players.append(player)
                self.name_to_card[key][player.name] = pid
            team.players = new_players

    def _build_schedule(self) -> None:
        """Single round-robin among the clubs (circle method)."""
        keys = [k for k in self.club_keys if k in self.teams]
        if len(keys) % 2:
            keys = keys + [None]  # bye marker
        n = len(keys)
        rounds = n - 1
        half = n // 2
        arr = list(keys)
        schedule: List[List[tuple]] = []
        for r in range(rounds):
            week = []
            for i in range(half):
                a, b = arr[i], arr[n - 1 - i]
                if a is None or b is None:
                    continue
                # alternate home/away for fairness
                if r % 2 == 0:
                    week.append((a, b))
                else:
                    week.append((b, a))
            schedule.append(week)
            arr = [arr[0]] + [arr[-1]] + arr[1:-1]  # rotate, keep first fixed
        self.schedule = schedule
        self.total_weeks = len(schedule)

    def _init_standings(self) -> None:
        self.standings = {
            k: _new_record(k, self._club_name(k))
            for k in self.club_keys if k in self.teams
        }

    def setup_season(self) -> None:
        """(Re)build the transient season state from persistent card state."""
        self._load_clubs()
        self._splice_cards_into_rosters()
        self._build_schedule()
        self._init_standings()
        self.results = {}
        self.current_week = 0
        self.phase = "regular"

    # ─────────────────────────────────────────────────────────────
    # GRADUATE IMPORT
    # ─────────────────────────────────────────────────────────────
    def import_graduates(self, consume: bool = True) -> dict:
        """Pull unconsumed CVL graduate pools and distribute them to clubs.

        The SAME PlayerCard is carried over — careers persist.  Returns a
        summary of what was imported.
        """
        pools = load_graduating_pools(unconsumed_only=True)
        imported: List[PlayerCard] = []
        sources: List[dict] = []
        for pool in pools:
            cnt = 0
            for pd in pool.get("players", []):
                try:
                    card = PlayerCard.from_dict(pd)
                except Exception:
                    continue
                if not card.player_id:
                    card.player_id = f"grad_{len(self.cards)}_{card.last_name}"
                if card.player_id in self.cards:
                    continue
                if card.age is None:
                    card.age = DEFAULT_ENTRY_AGE
                card.pro_status = "active"
                self.cards[card.player_id] = card
                imported.append(card)
                cnt += 1
            sources.append({
                "dynasty": pool.get("source_dynasty", "?"),
                "year": pool.get("source_year"),
                "count": cnt,
            })
            if consume and pool.get("save_key"):
                consume_graduating_pool(pool["save_key"])
                self.consumed_pools.append(pool["save_key"])

        self._distribute(imported)
        return {
            "imported": len(imported),
            "sources": sources,
            "total_tracked": len(self.cards),
        }

    def _distribute(self, cards: List[PlayerCard]) -> None:
        """Assign newly imported cards to clubs by prestige (stars to big clubs)."""
        if not cards:
            return
        clubs_by_prestige = sorted(
            self.club_keys,
            key=lambda k: -(CLUBS_BY_KEY.get(k).prestige if CLUBS_BY_KEY.get(k) else 50),
        )
        ranked = sorted(cards, key=lambda c: -c.overall)
        for i, card in enumerate(ranked):
            club = clubs_by_prestige[i % len(clubs_by_prestige)]
            card.current_team = self._club_name(club)
            card.pro_team = club
            self.roster_cards.setdefault(club, []).append(card.player_id)

    def seed_synthetic_graduates(self, n_per_club: int = 2) -> dict:
        """Test/seed helper: invent graduate cards when no real CVL pool exists.

        Used only for verification / empty-league bootstrap so the league has
        trackable careers even before a CVL dynasty has published a class.
        Cards get unique invented names and are spliced in through the normal
        roster path (call setup_season() afterward), so persistence and stat
        accumulation behave identically to real imports.
        """
        from engine.player_card import player_to_card
        made = 0
        idx = len(self.cards)
        for key in self.club_keys:
            team = self.teams.get(key)
            if not team:
                continue
            # Source from the WEAKEST fillers — exactly the ones _splice drops —
            # so each card replaces its source 1:1 with no name duplication.
            for p in sorted(team.players, key=lambda x: getattr(x, "speed", 0))[:n_per_club]:
                card = player_to_card(p, team_name=self._club_name(key))
                card.player_id = f"synthgrad_{idx}"
                card.age = DEFAULT_ENTRY_AGE
                card.pro_status = "active"
                card.year = "Pro"
                card.pro_team = key
                card.current_team = self._club_name(key)
                self.cards[card.player_id] = card
                self.roster_cards.setdefault(key, []).append(card.player_id)
                made += 1
                idx += 1
        return {"imported": made, "synthetic": True, "total_tracked": len(self.cards)}

    # ─────────────────────────────────────────────────────────────
    # SIMULATION
    # ─────────────────────────────────────────────────────────────
    def _accumulate(self, club_key: str, result: dict, side: str) -> None:
        """Append a game's production to each tracked card's current season."""
        name_map = self.name_to_card.get(club_key, {})
        if not name_map:
            return
        rows = result.get("player_stats", {}).get(side, [])
        team_name = self._club_name(club_key)
        for ps in rows:
            name = ps.get("name", "")
            pid = name_map.get(name)
            if not pid:
                continue
            card = self.cards.get(pid)
            if not card:
                continue
            s = card.get_or_create_season(self.year, team_name)
            s.games_played += 1
            ry = ps.get("rushing_yards", ps.get("game_rushing_yards", ps.get("yards", 0))) or 0
            ly = ps.get("lateral_yards", ps.get("game_lateral_yards", 0)) or 0
            kpy = ps.get("kick_pass_yards", ps.get("game_kick_pass_yards", 0)) or 0
            s.rushing_yards += ry
            s.lateral_yards += ly
            s.kick_pass_yards += kpy
            s.total_yards += ry + ly + kpy
            s.touchdowns += ps.get("tds", ps.get("touchdowns", ps.get("game_touchdowns", 0))) or 0
            s.fumbles += ps.get("fumbles", ps.get("game_fumbles", 0)) or 0
            s.tackles += ps.get("tackles", ps.get("game_tackles", 0)) or 0
            s.tfl += ps.get("tfl", ps.get("game_tfl", 0)) or 0
            s.sacks += ps.get("sacks", ps.get("game_sacks", 0)) or 0
            rush_car = ps.get("rush_carries", ps.get("carries", ps.get("game_carries", 0))) or 0
            s.rush_carries += rush_car
            s.touches += rush_car + (ps.get("lateral_receptions", 0) or 0)
            s.dk_makes += ps.get("dk_made", ps.get("game_dk_made", 0)) or 0
            s.dk_attempts += ps.get("dk_att", ps.get("dk_attempted", ps.get("game_dk_attempted", 0))) or 0
            s.kick_pass_tds += ps.get("kick_pass_tds", ps.get("game_kick_pass_tds", 0)) or 0

    def _record(self, key: str, pf: int, pa: int) -> None:
        rec = self.standings.get(key)
        if not rec:
            return
        rec["pf"] += pf
        rec["pa"] += pa
        if pf > pa:
            rec["wins"] += 1
        elif pf < pa:
            rec["losses"] += 1
        else:
            rec["ties"] += 1

    def sim_week(self) -> dict:
        if self.phase != "regular":
            return {"error": f"League is in '{self.phase}' phase", "week": self.current_week}
        if self.current_week >= self.total_weeks:
            self.phase = "complete"
            return {"error": "Season complete", "week": self.current_week}

        week_idx = self.current_week
        games = []
        for home_key, away_key in self.schedule[week_idx]:
            home = self.teams.get(home_key)
            away = self.teams.get(away_key)
            if not home or not away:
                continue
            engine = ViperballEngine(home, away, seed=random.randint(1, 1_000_000))
            result = engine.simulate_game()
            hs = int(result["final_score"]["home"]["score"])
            as_ = int(result["final_score"]["away"]["score"])
            self._record(home_key, hs, as_)
            self._record(away_key, as_, hs)
            self._accumulate(home_key, result, "home")
            self._accumulate(away_key, result, "away")
            games.append({
                "home_key": home_key, "away_key": away_key,
                "home_name": self._club_name(home_key),
                "away_name": self._club_name(away_key),
                "home_score": hs, "away_score": as_,
            })
        self.results[week_idx + 1] = games
        self.current_week += 1
        if self.current_week >= self.total_weeks:
            self.phase = "complete"
        return {"week": self.current_week, "games": games, "phase": self.phase}

    def sim_all(self) -> dict:
        weeks = 0
        while self.phase == "regular" and self.current_week < self.total_weeks:
            self.sim_week()
            weeks += 1
        return {"weeks_simulated": weeks, "phase": self.phase, "champion": self.champion()}

    def champion(self) -> Optional[str]:
        if self.phase != "complete":
            return None
        table = self.standings_table()
        return table[0]["team_name"] if table else None

    # ─────────────────────────────────────────────────────────────
    # SEASON ROLLOVER
    # ─────────────────────────────────────────────────────────────
    def advance_season(self) -> dict:
        """Close the current season, age the league, and start the next one.

        Careers persist on the cards (their current SeasonStats stays in
        career_seasons); aging players retire out but keep their history.
        New CVL graduates are pulled in for the new year.
        """
        champ = self.champion()
        self.history.append({
            "year": self.year,
            "champion": champ,
            "standings": self.standings_table(),
        })

        # Age every tracked player; retire the old ones.
        retired = []
        for pid, card in list(self.cards.items()):
            if card.pro_status == "retired":
                continue
            if card.age is not None:
                card.age += 1
            self._age_decline(card)
            if card.age is not None and card.age >= RETIREMENT_AGE:
                card.pro_status = "retired"
                retired.append(pid)
                # pull retirees off active rosters (history stays on the card)
                for club, pids in self.roster_cards.items():
                    if pid in pids:
                        pids.remove(pid)

        self.year += 1
        imp = self.import_graduates(consume=True)
        self.setup_season()
        return {
            "year": self.year,
            "previous_champion": champ,
            "retired": len(retired),
            "imported": imp.get("imported", 0),
        }

    @staticmethod
    def _age_decline(card: PlayerCard) -> None:
        """Mild physical decline past 30."""
        if card.age is None or card.age < 30:
            return
        card.speed = max(40, card.speed - 1)
        card.stamina = max(40, card.stamina - 1)
        card.agility = max(40, card.agility - 1)

    # ─────────────────────────────────────────────────────────────
    # VIEWS
    # ─────────────────────────────────────────────────────────────
    def standings_table(self) -> List[dict]:
        rows = []
        for rec in self.standings.values():
            r = dict(rec)
            r["diff"] = r["pf"] - r["pa"]
            r["games"] = r["wins"] + r["losses"] + r["ties"]
            rows.append(r)
        rows.sort(key=lambda r: (-r["wins"], -r["diff"], -r["pf"]))
        for i, r in enumerate(rows, 1):
            r["position"] = i
        return rows

    def status(self) -> dict:
        return {
            "league_id": self.league_id,
            "year": self.year,
            "phase": self.phase,
            "current_week": self.current_week,
            "total_weeks": self.total_weeks,
            "clubs": len([k for k in self.club_keys if k in self.teams]),
            "tracked_players": len(self.cards),
            "active_players": sum(1 for c in self.cards.values() if c.pro_status != "retired"),
            "seasons_completed": len(self.history),
            "champion": self.champion(),
        }

    def schedule_view(self) -> List[dict]:
        out = []
        for wk, games in enumerate(self.schedule, 1):
            played = self.results.get(wk)
            out.append({
                "week": wk,
                "played": played is not None,
                "games": played if played is not None else [
                    {
                        "home_key": h, "away_key": a,
                        "home_name": self._club_name(h),
                        "away_name": self._club_name(a),
                    } for (h, a) in games
                ],
            })
        return out

    def _card_brief(self, card: PlayerCard) -> dict:
        cur = next((s for s in card.career_seasons if s.season_year == self.year), None)
        return {
            "player_id": card.player_id,
            "name": card.full_name,
            "position": card.position,
            "overall": card.overall,
            "age": card.age,
            "club": card.current_team,
            "club_key": card.pro_team,
            "status": card.pro_status or "active",
            "career_games": card.career_games,
            "career_yards": card.career_yards,
            "career_touchdowns": card.career_touchdowns,
            "career_seasons": len(card.career_seasons),
            "season_yards": cur.total_yards if cur else 0,
            "season_tds": cur.touchdowns if cur else 0,
            "season_games": cur.games_played if cur else 0,
        }

    def players_view(self, include_retired: bool = True) -> List[dict]:
        out = []
        for card in self.cards.values():
            if not include_retired and card.pro_status == "retired":
                continue
            out.append(self._card_brief(card))
        out.sort(key=lambda r: -r["career_yards"])
        return out

    def player_detail(self, player_id: str) -> Optional[dict]:
        card = self.cards.get(player_id)
        if not card:
            return None
        return {
            **self._card_brief(card),
            "first_name": card.first_name,
            "last_name": card.last_name,
            "nationality": card.nationality,
            "archetype": card.archetype,
            "ratings": {
                "overall": card.overall, "speed": card.speed, "stamina": card.stamina,
                "agility": card.agility, "power": card.power, "awareness": card.awareness,
                "hands": card.hands, "kicking": card.kicking, "lateral_skill": card.lateral_skill,
                "tackling": card.tackling,
            },
            "career_seasons": [
                {
                    "year": s.season_year,
                    "team": s.team,
                    "games": s.games_played,
                    "yards": s.total_yards,
                    "rushing_yards": s.rushing_yards,
                    "lateral_yards": s.lateral_yards,
                    "kick_pass_yards": s.kick_pass_yards,
                    "touchdowns": s.touchdowns,
                    "tackles": s.tackles,
                    "fumbles": s.fumbles,
                    # league=WVL once they have a pro_team, else college
                    "league": "WVL" if (card.pro_team and s.season_year >= self._first_pro_year(card)) else "CVL",
                }
                for s in sorted(card.career_seasons, key=lambda x: x.season_year)
            ],
        }

    def _first_pro_year(self, card: PlayerCard) -> int:
        # Pro seasons are those recorded at/after league entry; approximate by
        # the earliest season whose team matches a WVL club name.
        club_names = {self._club_name(k) for k in self.club_keys}
        pro_years = [s.season_year for s in card.career_seasons if s.team in club_names]
        return min(pro_years) if pro_years else self.year

    def leaders(self, limit: int = 25) -> dict:
        briefs = [self._card_brief(c) for c in self.cards.values()]
        season = [b for b in briefs if b["season_games"] > 0]
        return {
            "season_yards": sorted(season, key=lambda b: -b["season_yards"])[:limit],
            "season_tds": sorted(season, key=lambda b: -b["season_tds"])[:limit],
            "career_yards": sorted(briefs, key=lambda b: -b["career_yards"])[:limit],
            "career_touchdowns": sorted(briefs, key=lambda b: -b["career_touchdowns"])[:limit],
        }

    def roster_view(self, club_key: str) -> dict:
        pids = self.roster_cards.get(club_key, [])
        players = [self._card_brief(self.cards[p]) for p in pids if p in self.cards]
        players.sort(key=lambda r: -r["overall"])
        return {
            "club_key": club_key,
            "club_name": self._club_name(club_key),
            "graduates": players,
            "graduate_count": len(players),
        }

    # ─────────────────────────────────────────────────────────────
    # PERSISTENCE  (only the durable career state is stored)
    # ─────────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "league_id": self.league_id,
            "year": self.year,
            "club_keys": self.club_keys,
            "cards": {pid: c.to_dict() for pid, c in self.cards.items()},
            "roster_cards": self.roster_cards,
            "consumed_pools": self.consumed_pools,
            "history": self.history,
            "current_week": self.current_week,
            "phase": self.phase,
            "standings": self.standings,
            "results": self.results,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WVLCareerLeague":
        league = cls(d.get("league_id", ""), year=d.get("year", 2027))
        league.club_keys = d.get("club_keys", league.club_keys)
        league.cards = {
            pid: PlayerCard.from_dict(cd) for pid, cd in d.get("cards", {}).items()
        }
        league.roster_cards = {k: list(v) for k, v in d.get("roster_cards", {}).items()}
        league.consumed_pools = d.get("consumed_pools", [])
        league.history = d.get("history", [])
        # Rebuild transient season state, then restore in-season progress.
        league.setup_season()
        saved_standings = d.get("standings")
        saved_results = d.get("results")
        saved_week = d.get("current_week", 0)
        if saved_standings:
            league.standings = saved_standings
        if saved_results:
            league.results = {int(k): v for k, v in saved_results.items()}
        league.current_week = saved_week
        league.phase = d.get("phase", league.phase)
        return league

    def save(self) -> None:
        save_blob(
            _LEAGUE_TYPE, self.league_id, self.to_dict(),
            label=f"WVL Career League Y{self.year}",
        )


# ─────────────────────────────────────────────────────────────────
# MODULE-LEVEL HELPERS
# ─────────────────────────────────────────────────────────────────
def create_league(year: int = 2027, import_graduates: bool = True,
                   seed_if_empty: bool = True) -> WVLCareerLeague:
    import uuid
    league = WVLCareerLeague(str(uuid.uuid4()), year=year)
    league.setup_season()
    imported = 0
    if import_graduates:
        imported = league.import_graduates(consume=True).get("imported", 0)
        league.setup_season()  # re-splice with imported cards
    if imported == 0 and seed_if_empty:
        league.seed_synthetic_graduates(n_per_club=2)
        league.setup_season()  # splice synthetic grads onto rosters
    league.save()
    return league


def load_league(league_id: str) -> Optional[WVLCareerLeague]:
    data = load_blob(_LEAGUE_TYPE, league_id)
    if data is None:
        return None
    return WVLCareerLeague.from_dict(data)


def list_leagues() -> List[dict]:
    return list_saves(save_type=_LEAGUE_TYPE)
