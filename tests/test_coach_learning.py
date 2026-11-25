from types import SimpleNamespace
from engine.coaching import CoachCard
from engine.coach_learning import adapt, observe, offense_bias, pressure_bias, LIMIT, STEP
from engine.coach_tactics import ensure_coach_tactical_profile

def card(role="oc"):
    return CoachCard(coach_id="learning-"+role,first_name="Test",last_name="Coach",
        gender="female",age=40,role=role,classification="scheme_master",
        instincts=70,leadership=70,composure=70,rotations=60,development=65,recruiting=65,
        personality_sliders={"adaptability":100,"stubbornness":0})

def season(c, n=6):
    plays=[]
    for _ in range(6):
        for family,yards in (("kick_pass",20),("power",0)):
            plays.append({"snap_possession":"home","play_family":family,"down":1,
                "yards_to_go":20,"field_position":40,"yards":yards,"result":"gain"})
    games=[SimpleNamespace(completed=True,home_team="A",away_team="B",full_result={
        "coach_tactics":{"home":{"oc_id":c.coach_id}},"play_by_play":plays}) for _ in range(n)]
    return SimpleNamespace(schedule=games,playoff_bracket=[])

def test_evidence_floor_and_idempotence():
    c=card()
    assert not adapt(c,"oc","A",2026,season(c,2))["sufficient"]
    assert adapt(c,"oc","A",2026,season(c)) is None
    p=ensure_coach_tactical_profile(c)
    identity=p["identity"].copy()
    e=adapt(c,"oc","A",2027,season(c))
    assert e["sufficient"] and 0 < e["after"] <= STEP
    assert p["identity"] == identity
    assert offense_bias(p)["kick_pass"] > p["offense"]["family_bias"].get("kick_pass",0)
    for y in range(2028,2040):
        adapt(c,"oc","A",y,season(c))
    assert abs(p["learning"]["kick_mix"]) <= LIMIT
    loaded=CoachCard.from_dict(c.to_dict())
    assert ensure_coach_tactical_profile(loaded) == p

def test_unattributed_games_do_not_teach():
    c=card()
    s=season(card("dc"))
    assert observe(s,"A",c,"oc")["games"] == 0


def test_mentor_influence_requires_shared_season_and_survives_moves():
    from engine.coach_learning import learn_from_mentor, mentor_bias, MENTOR_LIMIT, MENTOR_STEP

    pupil, mentor = card("oc"), card("head_coach")
    mentor.career_development["management"]["specialty"] = "oc"
    profile = ensure_coach_tactical_profile(pupil)
    source = ensure_coach_tactical_profile(mentor)
    profile["offense"]["family_bias"]["kick_pass"] = -.08
    source["offense"]["family_bias"]["kick_pass"] = .14
    identity = profile["identity"].copy()
    assert learn_from_mentor(pupil, mentor, "oc", "A", 2026) is None
    pupil.coaching_tree.append({"coach_id": mentor.coach_id, "team_name": "A",
                                "year_start": 2026, "year_end": 2035})
    assert learn_from_mentor(pupil, mentor, "oc", "B", 2026) is None
    assert learn_from_mentor(pupil, mentor, "dc", "A", 2026) is None
    event = learn_from_mentor(pupil, mentor, "oc", "A", 2026)
    assert 0 < event["after"] <= MENTOR_STEP
    assert learn_from_mentor(pupil, mentor, "oc", "A", 2026) is None
    for year in range(2027, 2036):
        learn_from_mentor(pupil, mentor, "oc", "A", year)
    assert 0 < mentor_bias(profile, "kick_mix") <= MENTOR_LIMIT
    assert profile["identity"] == identity
    assert offense_bias(profile)["kick_pass"] > -.08
    pupil.team_name = "B"
    loaded = CoachCard.from_dict(pupil.to_dict())
    assert ensure_coach_tactical_profile(loaded) == profile
    assert learn_from_mentor(loaded, mentor, "oc", "B", 2036) is None


def test_stubborn_coach_retains_identity_under_mentorship():
    from engine.coach_learning import learn_from_mentor, mentor_bias
    pupil, mentor = card("dc"), card("head_coach")
    pupil.personality_sliders["stubbornness"] = 100
    mentor.career_development["management"]["specialty"] = "dc"
    pupil.coaching_tree.append({"coach_id": mentor.coach_id, "team_name": "A",
                                "year_start": 2026, "year_end": 2026})
    event = learn_from_mentor(pupil, mentor, "dc", "A", 2026)
    assert event["before"] == event["after"] == 0
    assert mentor_bias(pupil.tactical_profile, "pressure") == 0


def test_school_fit_changes_equal_quality_cpu_recruit_rankings():
    from engine.coach_recruiting_fit import ATTRS, MAX_FIT, recruiting_fit, recruiting_preferences
    from engine.recruiting import auto_recruit_team

    def prospect(name, specialized, stars=3):
        return SimpleNamespace(
            recruit_id=name, position="Zeroback", region="midwest", stars=stars,
            true_overall=70, committed_to=None, signed=False, offers=[],
            **{"true_" + k: 90 if k in specialized else 50 for k in ATTRS})

    class NoNoise:
        def uniform(self, lo, hi):
            return (lo + hi) / 2

    def targets(school):
        recruits = [prospect("runner", {"awareness", "agility", "hands"}),
                    prospect("kicker", {"kicking", "kick_power", "kick_accuracy"})]
        board, nil = auto_recruit_team("A", recruits, 60, "midwest",
            scholarships=1, rng=NoNoise(), style_config={"offense_style": school})
        return board.offered, nil

    ground, ground_nil = targets("ground_pound")
    vertical, vertical_nil = targets("shock_and_awe")
    assert ground[0] == "runner" and "runner" in ground_nil
    assert vertical[0] == "kicker" and "kicker" in vertical_nil
    r = prospect("kicker", {"kicking", "kick_power", "kick_accuracy"})
    assert recruiting_fit(r, recruiting_preferences(None)) == 0
    assert abs(recruiting_fit(r, recruiting_preferences(None, {"offense_style":"shock_and_awe"}))) <= MAX_FIT
    # Fit cannot displace a much higher star prospect with otherwise equal context.
    board, _ = auto_recruit_team("A", [r, prospect("five_star", {"awareness", "agility", "hands"}, 5)],
        80, "midwest", rng=NoNoise(), style_config={"offense_style":"shock_and_awe"})
    assert board.offered[0] == "five_star"


def test_cpu_schools_are_stable_except_at_real_coaching_transitions():
    from engine.coach_school_continuity import plan_schools

    old = card("head_coach")
    incoming = card("head_coach")
    # Fixture must represent a distinct coach with a valid owned profile.
    incoming.coach_id = "new-head-coach"
    incoming.tactical_profile["coach_id"] = incoming.coach_id
    incoming.tactical_profile["identity"]["offense_interpretation"] = "vertical_attack"
    incoming.career_development["management"]["specialty"] = "oc"
    config = {"offense_style": "ground_pound", "defense_style": "fortress", "st_scheme": "aces"}
    previous = {"A": config, "Human": config}
    catalogs = ({"ground_pound": {}, "shock_and_awe": {}}, {"fortress": {}})

    same = plan_schools(previous, {"A": {"head_coach": old}, "Human": {"head_coach": old}},
                        {"A": old.coach_id}, "Human", *catalogs)
    assert same == {"A": config}
    assert same["A"] is not config

    changed = plan_schools(previous, {"A": {"head_coach": incoming}},
                           {"A": old.coach_id}, "Human", *catalogs)
    assert changed["A"] == {**config, "offense_style": "shock_and_awe"}
    assert previous["A"] == config

    incoming.coaching_tree.append({"coach_id": old.coach_id, "team_name": "A",
                                   "year_start": 2024, "year_end": 2026})
    internal = plan_schools(previous, {"A": {"head_coach": incoming}},
                            {"A": old.coach_id}, "Human", *catalogs)
    assert internal["A"] == config
    retired_style = plan_schools(previous, {"A": {"head_coach": old}},
                                 {"A": old.coach_id}, "Human", {}, catalogs[1])
    assert "offense_style" not in retired_style["A"]
