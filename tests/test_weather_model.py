"""WEA-02: weather as readings, by period, at real venues."""
import random
from collections import Counter
from types import SimpleNamespace

import pytest

from engine import weather as wx
from engine.game_engine import ViperballEngine
from engine.weather import GameWeather, Reading, Venue


def test_dome_blocks_weather():
    g = wx.build_game_weather("MN", None, 17, 18, venue=Venue(roof="dome", surface="turf"),
                              rng=random.Random(1))
    for q in (1, 2, 3, 4):
        r = g.reading(q)
        assert r.precip == "none" and r.wind_mph == 0 and r.temp_f == 70
        assert g.field_state(q).wetness == 0


def test_retractable_roof_closes_in_bad_weather():
    rng = random.Random(3)
    closed = 0
    for _ in range(200):
        g = wx.build_game_weather("MN", None, 17, 18, venue=Venue(roof="retractable"), rng=rng)
        if g.venue.roof == "closed":
            closed += 1
            assert g.reading(1).precip == "none"
    assert closed > 100  # a Minnesota December is mostly cold or snowing


def test_field_gets_wetter_while_it_rains_and_stays_wet():
    rain = Reading(temp_f=50, precip="rain", intensity=0.85)
    dry = Reading(temp_f=50)
    g = GameWeather(periods=[rain, rain, dry, dry])
    w = [g.field_state(q).wetness for q in (1, 2, 3, 4)]
    assert w[0] < w[1] < w[2]          # builds up through two periods of rain
    assert w[3] > 0.2                  # still wet after the rain stops
    turf = GameWeather(periods=[rain, rain, dry, dry], venue=Venue(surface="turf"))
    assert turf.field_state(4).wetness < w[3]   # turf drains faster


def test_wind_direction_flips_with_ends():
    e = object.__new__(ViperballEngine)
    e.weather_info = {"wind_along": 20.0}
    for q, home_sign in ((1, 1), (2, -1), (3, 1), (4, -1), (5, 1)):
        e.state = SimpleNamespace(quarter=q, possession="home")
        assert e._tailwind("home") == pytest.approx(20.0 * home_sign)
        assert e._tailwind("away") == pytest.approx(-20.0 * home_sign)


def test_effects_scale_with_intensity():
    f = wx.FieldState()
    light = wx.weather_effects(Reading(precip="rain", intensity=0.25), f, Venue())
    heavy = wx.weather_effects(Reading(precip="rain", intensity=0.85), f, Venue())
    assert 1.0 < light["fumble_mult"] < heavy["fumble_mult"]
    assert heavy["kick_accuracy_modifier"] < light["kick_accuracy_modifier"] < 0


def test_every_league_location_resolves():
    for code in ("AL", "AB", "QC", "ENG", "NED", "NET", "SPA", "ZAF", "MEX", "BOL", "THA"):
        zone, hemi, alt = wx.resolve_location(code)
        assert zone in wx.WEATHER_TABLE
    assert wx.resolve_location("ARG")[1] == "S"
    assert wx.resolve_location("CO", "Laramie")[2] == 7220


def test_southern_hemisphere_december_is_summer():
    assert wx.season_period(16, 18, "S") == "summer"
    assert wx.season_period(16, 18, "N") == "winter"
    assert wx.season_period(1, 18, "N", month="June") == "summer"


def test_snow_is_common_in_minnesota_december_and_rare_in_florida():
    rng = random.Random(7)
    mn = Counter(wx.build_game_weather("MN", None, 17, 18, rng=rng).label(1) for _ in range(600))
    fl = Counter(wx.build_game_weather("FL", None, 17, 18, rng=rng).label(1) for _ in range(600))
    assert mn["snow"] / 600 > 0.2
    assert fl["snow"] / 600 < 0.03
    pnw = Counter(wx.build_game_weather("OR", None, 10, 18, rng=rng).label(1) for _ in range(600))
    assert pnw["rain"] > mn["rain"]


def test_venue_is_the_same_every_season():
    a = wx.venue_for("Minnesota", "MN", "Minneapolis", "college")
    b = wx.venue_for("Minnesota", "MN", "Minneapolis", "college")
    assert a == b


def test_label_only_engine_stays_fixed_all_game():
    g = GameWeather.from_label("rain")
    assert len({(r.precip, r.intensity, r.wind_mph) for r in g.periods}) == 1
    clear = GameWeather.from_label("clear")
    assert clear.reading(1).wind_mph == 0
