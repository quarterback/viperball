import json
import random
import sqlite3
from pathlib import Path
from shutil import copyfile

import pytest
from fastapi.testclient import TestClient

from engine import db, team_installation
from engine.custom_playbooks import get_book, save_book, validate_book
from engine.team_installation import sync_installation
from tests.test_team_installation import STATS, card, staff


def book(name, side, school, *packages):
    return {"version": 1, "name": name, "side": side, "school": school,
            "packages": list(packages), "preferred": packages[0]}


def test_playbook_library_team_setup_and_simulated_week(tmp_path, monkeypatch):
    from api import main

    monkeypatch.setattr(main, "sessions", {})
    monkeypatch.setattr(db, "_db_path", tmp_path / "cookbook.db")
    db.init_db()
    team_dir = tmp_path / "teams"
    team_dir.mkdir()
    for team in ("alabama", "duke", "gonzaga", "lafayette"):
        copyfile(Path("data/teams") / f"{team}.json", team_dir / f"{team}.json")
    monkeypatch.setattr(main, "TEAMS_DIR", str(team_dir))
    monkeypatch.setattr(team_installation, "league_roster_profiles",
                        lambda teams: {name: STATS.copy() for name in teams})

    client = TestClient(main.app)
    draft = book("Opening Script", "offense", "ghost", "rugby_first_phase_strike")
    imported = client.post("/stats/playbooks/import", data={"playbook_json": json.dumps(draft)})
    assert imported.status_code == 200
    assert 'value="Opening Script"' in imported.text
    assert db.list_saves("playbook") == []
    invalid = client.post("/stats/playbooks", data={**draft, "school": "swarm"})
    assert invalid.status_code == 400
    saved = client.post("/stats/playbooks", data=draft, follow_redirects=False)
    assert saved.status_code == 303
    offense = saved.headers["location"].split("edit=")[1]
    assert client.get(f"/stats/playbooks/{offense}/export").json() == draft
    defense = save_book(book("Early Containment", "defense", "fortress", "swarm_containment"))
    for mode in ("college", "dynasty"):
        page = client.get(f"/stats/{mode}/new")
        assert page.status_code == 200
        assert offense in page.text and defense in page.text
        assert 'name="computer_playbooks"' in page.text

    sid = client.post("/sessions").json()["session_id"]
    teams = list(main.load_teams_from_directory(str(team_dir)))
    controlled = teams[0]
    setup = client.post(f"/sessions/{sid}/season", json={
        "games_per_team": 2, "human_teams": [controlled],
        "conferences": {"Test": teams},
        "playbooks": {controlled: {"offense": offense, "defense": defense}},
        "ai_seed": 26,
    })
    assert setup.status_code == 200, setup.text
    season = main.sessions[sid]["season"]
    assert season.style_configs[controlled]["offense_style"] == "ghost"
    assert season.style_configs[controlled]["defense_style"] == "fortress"
    save_book({**get_book(offense), "name": "Later revision"}, offense)
    assert client.post(f"/sessions/{sid}/season/portal/skip").status_code == 200
    rng_state = random.getstate()
    try:
        random.seed(104)
        week = client.post(f"/sessions/{sid}/season/simulate-week", json={})
    finally:
        random.setstate(rng_state)
    assert week.status_code == 200, week.text
    number = week.json()["week"]
    games = [game for game in season.schedule if game.week == number]
    game = next(game for game in games if controlled in (game.home_team, game.away_team))
    side = "home" if game.home_team == controlled else "away"
    assert game.full_result["custom_playbooks"][side]["offense"]["name"] == draft["name"]
    assert game.full_result["custom_playbooks"][side]["defense"]["ready"] == ["swarm_containment"]
    assert game.full_result["coach_tactics"][side]["selected"]["packages"]["rugby_first_phase_strike"] > 0
    assert game.full_result["defensive_coach_tactics"][side]["packages"]["selected"]["swarm_containment"] > 0
    page = client.get(f"/stats/college/{sid}/game/{number}/{games.index(game)}")
    assert page.status_code == 200
    assert "Custom playbook usage" in page.text and "Selected snaps" in page.text
    snapshot = db.load_blob("season_archive", f"college_{sid}")
    assert snapshot["playbook_assignments"][controlled]["offense"] == draft

    ai_styles = {team: {"offense_style": "ghost", "defense_style": "fortress"} for team in teams}
    config = {"games_per_team": 2, "conferences": {"Test": teams},
              "style_configs": ai_styles, "ai_seed": 26}
    ai_id = client.post("/sessions").json()["session_id"]
    assert client.post(f"/sessions/{ai_id}/season", json=config).status_code == 200
    assert not main.sessions[ai_id]["season"].playbook_assignments

    ai_id = client.post("/sessions").json()["session_id"]
    setup = client.post(f"/sessions/{ai_id}/season", json={**config, "computer_playbooks": True})
    assert setup.status_code == 200, setup.text
    ai_season = main.sessions[ai_id]["season"]
    assert not ai_season.human_teams
    for unit in ("offense", "defense"):
        assert sum(unit in books for books in ai_season.playbook_assignments.values()) == 2
    rng_state = random.getstate()
    try:
        random.seed(104)
        week = client.post(f"/sessions/{ai_id}/season/simulate-week", json={})
    finally:
        random.setstate(rng_state)
    assert week.status_code == 200, week.text
    assert any(
        "offense" in result.get("custom_playbooks", {}).get(side, {})
        and counts.get("selected", {}).get("packages", {}).get("rugby_first_phase_strike", 0)
        for game in ai_season.schedule if (result := game.full_result)
        for side, counts in result["coach_tactics"].items()
    )

    from engine import college_feeder

    monkeypatch.setattr(college_feeder, "build_college_feeder_in_background", lambda *args, **kwargs: None)
    monkeypatch.setattr(main, "auto_assign_all_teams", lambda *args, **kwargs: ai_styles)
    dynasty_id = client.post("/sessions").json()["session_id"]
    created = client.post(f"/sessions/{dynasty_id}/dynasty", json={
        "dynasty_name": "Cookbook Dynasty", "coach_name": "Coach",
        "coach_team": controlled, "games_per_team": 2,
        "conferences": {"Test": teams},
        "playbooks": {"offense": offense, "defense": defense},
        "computer_playbooks": True,
    })
    assert created.status_code == 200, created.text
    dynasty = db.load_dynasty(dynasty_id)
    assert dynasty.playbook_assignments[controlled]["offense"]["name"] == "Later revision"
    assert dynasty.pending_computer_books
    main.sessions[dynasty_id]["dynasty"] = dynasty
    started = client.post(f"/sessions/{dynasty_id}/dynasty/start-season", json={"ai_seed": 26})
    assert started.status_code == 200, started.text
    next_season = main.sessions[dynasty_id]["season"]
    assert next_season.playbook_assignments == dynasty.playbook_assignments
    assert next_season.style_configs[controlled]["offense_style"] == "ghost"
    assert next_season.style_configs[controlled]["defense_style"] == "fortress"
    assert next_season.playbook_assignments.keys() - {controlled}
    persisted = db.load_dynasty(dynasty_id)
    assert persisted.playbook_assignments == next_season.playbook_assignments
    assert not persisted.pending_computer_books


def test_standalone_season_runs_and_reports_paired_calls(tmp_path, monkeypatch):
    from api import main

    monkeypatch.setattr(main, "sessions", {})
    monkeypatch.setattr(db, "_db_path", tmp_path / "standalone.db")
    db.init_db()
    team_dir = tmp_path / "teams"
    team_dir.mkdir()
    for team in ("alabama", "duke", "gonzaga", "lafayette"):
        copyfile(Path("data/teams") / f"{team}.json", team_dir / f"{team}.json")
    monkeypatch.setattr(main, "TEAMS_DIR", str(team_dir))
    monkeypatch.setattr(team_installation, "league_roster_profiles",
                        lambda teams: {name: STATS.copy() for name in teams})
    client = TestClient(main.app)
    packages = ["gaelic_kick_and_follow", "rugby_carry_release"]
    pair = {**book("Split answers", "offense", "ghost", *packages), "version": 2,
            "same_look_pairs": [{"formation": "split", "packages": packages}]}
    key = save_book(pair)
    teams = list(main.load_teams_from_directory(str(team_dir)))
    controlled = teams[0]
    sid = client.post("/sessions").json()["session_id"]
    config = {"games_per_team": 2, "conferences": {"Test": teams}, "human_teams": [controlled],
              "playbooks": {controlled: {"offense": key}}, "ai_seed": 26}
    response = client.post(f"/sessions/{sid}/season", json=config)
    assert response.status_code == 200, response.text
    assert client.post(f"/sessions/{sid}/season/portal/skip").status_code == 200
    rng_state = random.getstate()
    try:
        random.seed(104)
        response = client.post(f"/sessions/{sid}/season/simulate-week", json={})
    finally:
        random.setstate(rng_state)
    assert response.status_code == 200, response.text
    week = response.json()["week"]
    season = main.sessions[sid]["season"]
    games = [g for g in season.schedule if g.week == week]
    index, played = next((i, g) for i, g in enumerate(games) if controlled in (g.home_team, g.away_team))
    side = "home" if played.home_team == controlled else "away"
    result = played.full_result
    calls = [call for play in result["play_by_play"] if (call := play.get("offensive_call"))
             and call.get("offense_side") == side and call.get("sequence")]
    assert any(call["sequence"]["status"] == "probe" for call in calls)
    assert all(call["sequence"]["book_revision"] == get_book(key)["revision"] for call in calls)
    game_page = client.get(f"/stats/college/{sid}/game/{week}/{index}")
    assert game_page.status_code == 200
    assert "Drive plan" in game_page.text and "Eligible packages" in game_page.text
    archived = db.load_box_score(sid, week, played.home_team, played.away_team)
    assert archived and any((p.get("offensive_call") or {}).get("sequence") for p in archived["play_by_play"])


def test_book_survives_dynasty_reload_and_coordinator_change(tmp_path, monkeypatch):
    from engine.dynasty import create_dynasty

    monkeypatch.setattr(db, "_db_path", tmp_path / "dynasty.db")
    db.init_db()
    dynasty = create_dynasty("Cookbook", "Coach", "Team")
    offense = book("Set plays", "offense", "ghost", "gp_heavy_push", "ec_two_minute")
    dynasty.playbook_assignments["Team"] = {"offense": offense}
    db.save_dynasty(dynasty, save_key="book")
    restored = db.load_dynasty("book")
    assert restored.playbook_assignments == dynasty.playbook_assignments

    records = restored._team_installations
    coaches = staff(card("first", "oc"))
    first = sync_installation(records, "Team", coaches, "ghost", "swarm",
                              STATS, books=restored.playbook_assignments["Team"])
    assert [p["package_id"] for p in first["offense"]["packages"]] == offense["packages"]
    coaches["oc"] = card("second", "oc")
    second = sync_installation(records, "Team", coaches, "ghost", "swarm",
                               STATS, books=restored.playbook_assignments["Team"])
    assert second["offense"]["coach_id"] == "second"
    assert second["offense"]["custom_book"] == offense
    assert [p["package_id"] for p in second["offense"]["packages"]] == offense["packages"]



def test_repertoire_book_roundtrips_editor_installation_and_dynasty(tmp_path, monkeypatch):
    from api import main
    from engine.dynasty import create_dynasty

    monkeypatch.setattr(db, "_db_path", tmp_path / "repertoire.db")
    db.init_db()
    focus, other = "gp_heavy_push", "rugby_first_phase_strike"
    draft = {**book("Same look", "offense", "ghost", focus, other), "version": 2,
             "practice_focus": focus,
             "same_look_pairs": [{"formation": "tight", "packages": [other, focus]}]}
    canonical = validate_book(draft)
    assert validate_book(canonical) == canonical
    assert validate_book({**draft, "packages": [other, focus]}) == canonical
    assert validate_book({**canonical, "name": "Revision 2"})["revision"] != canonical["revision"]
    client = TestClient(main.app)
    imported = client.post("/stats/playbooks/import", data={"playbook_json": json.dumps(draft)})
    assert imported.status_code == 200
    assert '"practice_focus": "gp_heavy_push"' in imported.text
    saved = client.post("/stats/playbooks", data={
        **{k: draft[k] for k in ("name", "side", "school", "packages", "preferred", "practice_focus")},
        "practice_budget": "1", "same_look_pairs": f"tight|{focus}|{other}",
    }, follow_redirects=False)
    assert saved.status_code == 303
    key = saved.headers["location"].split("edit=")[1]
    assert client.get(f"/stats/playbooks/{key}/export").json() == canonical

    dynasty = create_dynasty("Repertoire", "Coach", "Team")
    dynasty.playbook_assignments["Team"] = {"offense": get_book(key)}
    coaches = staff(card("repertoire-caller", "oc"))
    installed = sync_installation(dynasty._team_installations, "Team", coaches, "ghost", "swarm",
                                  STATS, books=dynasty.playbook_assignments["Team"])
    team_installation.record_game(installed)
    summary = team_installation.summarize(installed)["offense"]
    assert summary["practice"]["game"]["allocated"] == {focus: 40, other: 20}
    assert summary["same_look_pairs"] == canonical["same_look_pairs"]
    assert summary["book_revision"] == canonical["revision"]
    save_book({**canonical, "name": "Later revision"}, key)
    db.save_dynasty(dynasty, save_key="repertoire")
    restored = db.load_dynasty("repertoire")
    assert restored.playbook_assignments["Team"]["offense"] == canonical
    assert restored._team_installations["Team"] == installed

    reduced = sync_installation(restored._team_installations, "Team", coaches, "ghost", "swarm",
                                {**STATS, "avg_weight": 120},
                                books=restored.playbook_assignments["Team"])
    team_installation.record_game(reduced)
    summary = team_installation.summarize(reduced)["offense"]
    assert summary["same_look_pairs"] == []
    assert summary["practice"]["game"]["allocated"] == {other: 60}

    sync_installation(restored._team_installations, "Team", coaches, "ghost", "swarm",
                      {**STATS, "avg_weight": 120, "avg_speed": 0},
                      books=restored.playbook_assignments["Team"])
    team_installation.record_game(reduced)
    summary = team_installation.summarize(reduced)["offense"]
    assert summary["practice"]["game"] == {"budget": 60, "allocated": {}, "unused": 60}


def test_pairs_require_two_distinct_installed_actions_with_a_shared_formation():
    first, second = "gp_heavy_push", "rugby_first_phase_strike"
    draft = {**book("Paired looks", "offense", "ghost", first, second), "version": 2}
    for pair in ({"formation": "spread", "packages": [first, second]},
                 {"formation": "tight", "packages": [first, first]},
                 {"formation": "tight", "packages": [first, "lax_fast_break"]}):
        with pytest.raises(ValueError, match="Pair two distinct"):
            validate_book({**draft, "same_look_pairs": [pair]})
    with pytest.raises(ValueError, match="practice focus"):
        validate_book({**draft, "practice_focus": "lax_fast_break"})


def test_failed_save_keeps_the_draft_and_can_be_retried(tmp_path, monkeypatch):
    from api import main

    db_path = tmp_path / "cookbook.db"
    monkeypatch.setattr(db, "_db_path", db_path)
    db.init_db()
    client = TestClient(main.app)

    saved = book("Opening Script", "offense", "ghost", "rugby_first_phase_strike")
    key = save_book(saved)
    draft = {**saved, "name": "Revised Opening Script",
             "packages": ["rugby_first_phase_strike", "gp_heavy_push"],
             "preferred": "gp_heavy_push"}
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TRIGGER reject_playbook_update BEFORE UPDATE ON saves
            WHEN NEW.save_type = 'playbook'
            BEGIN SELECT RAISE(ABORT, 'write failed'); END;
        """)
    failed = client.post("/stats/playbooks", data={**draft, "book_id": key})
    assert failed.status_code == 503
    assert "Your draft is still here." in failed.text
    assert 'value="Revised Opening Script"' in failed.text
    assert f'name="book_id" value="{key}"' in failed.text
    assert '"preferred": "gp_heavy_push"' in failed.text
    assert get_book(key) == saved

    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TRIGGER reject_playbook_update")
    retried = client.post("/stats/playbooks", data={**draft, "book_id": key})
    assert retried.status_code == 200
    assert retried.url.params["edit"] == key
    assert get_book(key) == draft
