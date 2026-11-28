"""Cape Cod: the offensive hook and the defensive trap."""
from engine.offensive_concepts import cape_cod_call, sequence_call, CAPE_COD
from engine.playbook_catalog import get_package, get_scheme_family
from engine.defensive_commitments import eligibility


def test_offense_sets_up_then_hooks_or_kicks_across():
    assert cape_cod_call([]) == {"phase": "setup", "lane": "left", "family": "lateral_spread"}
    chased = [{"lane": "left", "alignment": "spread", "blitz": False}]
    assert cape_cod_call(chased) == {"phase": "hook", "lane": "right", "family": "counter"}
    blitzed = [{"lane": "right", "alignment": "balanced", "blitz": True}]
    assert cape_cod_call(blitzed)["phase"] == "hook"
    crowded = [{"lane": "left", "alignment": "stacked", "blitz": False}]
    assert cape_cod_call(crowded) == {"phase": "kick_across", "lane": "right",
                                      "family": "kick_pass", "kick_pass": "territory"}
    held = [{"lane": "left", "alignment": "balanced", "blitz": False}]
    assert cape_cod_call(held)["phase"] == "setup"
    assert sequence_call(CAPE_COD, chased)["phase"] == "hook"


def test_catalog_and_schools():
    off, de = get_package("cape_cod_hook"), get_package("cape_cod_trap")
    assert off["side"] == "offense" and de["side"] == "defense"
    assert "cape_cod_hook" in get_scheme_family("offense", "lateral_spread")["packages"]
    assert "cape_cod_hook" in get_scheme_family("offense", "chain_gang")["packages"]
    assert "cape_cod_trap" in get_scheme_family("defense", "swarm")["packages"]


def test_trap_waits_for_lateral_or_perimeter_threats():
    quiet = {"recent_lateral_rate": 0.05, "recent_perimeter_rate": 0.05}
    busy = {"recent_lateral_rate": 0.15, "recent_perimeter_rate": 0.15}
    assert eligibility("cape_cod_trap", ["early_down"], quiet, ["early_down"]) == 0.0
    assert eligibility("cape_cod_trap", ["early_down"], busy, ["early_down"]) == 1.0
    assert eligibility("cape_cod_trap", ["late_downs"], busy, ["early_down"]) == .45
