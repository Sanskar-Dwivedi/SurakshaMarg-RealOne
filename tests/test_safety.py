"""
Safety tests for the non-target, herd and flight-geometry protections.

Written as claims, like the rest of the suite. These are the assertions that
answer the two questions that drove this work: can a household animal be
harmed, and can a flock be panicked into violent or dangerous behaviour.
"""

from __future__ import annotations

import pytest

from gaukavach import evidence as ev
from gaukavach import hazard as hz
from gaukavach import species as sp
from gaukavach.acoustics import Atmosphere, human_audibility_risk
from gaukavach.detect import DEMO_SITE, SimpleTracker
from gaukavach.ledger import Ledger
from gaukavach.policy import EngineConfig, PolicyEngine
from gaukavach.scenario import SCENARIOS, run as run_scenario
from gaukavach.welfare import Denial, Governor, SceneContext

SITE_ATM = Atmosphere(temp_c=32.0, rh_pct=60.0, ambient_spl_db=58.0)


def _run(name: str):
    engine = PolicyEngine(DEMO_SITE, SITE_ATM, Ledger(), EngineConfig())
    snaps = run_scenario(SCENARIOS[name], engine, SimpleTracker())
    actions = [a for s in snaps for a in s["actions"]]
    return engine, snaps, actions


# ---------------------------------------------------------------------------
# Comparative audiogram - the finding that reshaped the design
# ---------------------------------------------------------------------------


def test_frequency_provides_no_species_selectivity():
    """The headline safety finding, locked in so it cannot regress."""
    for carrier in (22_000.0, 25_000.0, 30_000.0):
        v = sp.selectivity_verdict(carrier)
        assert v["frequency_is_selective"] is False
        assert v["non_target_species_affected"] >= 5


def test_cattle_are_among_the_least_sensitive_affected_species():
    """Cats, dogs, sheep, pigs and goats all hear the carrier better than cattle."""
    beaten_by = sp.more_sensitive_than_target(25_000.0)
    for name in ("Cat", "Dog", "Sheep", "Pig", "Goat"):
        assert name in beaten_by, f"{name} should out-hear the target"


def test_household_animals_are_all_more_sensitive_than_the_target():
    """Directly answers the requirement that no household animal be harmed."""
    target_hi = sp.SPECIES[sp.TARGET_KEY].hearing_high_hz
    household = [s for s in sp.SPECIES.values() if s.group is sp.Group.HOUSEHOLD]
    assert household
    for s in household:
        assert s.hearing_high_hz > target_hi


def test_poultry_are_correctly_identified_as_unaffected():
    """The register must say what is NOT at risk, not only what is."""
    assert not sp.SPECIES["chicken"].audible(22_000.0)


def test_children_hear_higher_than_adults():
    for f in (20_000.0, 22_000.0, 24_000.0):
        assert sp.child_audibility_risk(f) > human_audibility_risk(f)


def test_sensitive_receptor_sites_raise_the_band_floor():
    assert sp.sensitive_receptor_floor_hz(True) > sp.sensitive_receptor_floor_hz(False)


def test_goat_label_ambiguity_is_declared_not_hidden():
    assert sp.label_is_ambiguous("sheep")
    names = {p.name for p in sp.species_for_label("sheep")}
    assert "Goat" in names and "Sheep" in names


def test_undetectable_species_are_listed():
    assert sp.UNDETECTABLE_AT_RISK
    assert "macaque" in sp.UNDETECTABLE_NOTE.lower()


def test_bat_echolocation_overlap_is_flagged():
    assert sp.bat_echolocation_overlap(25_000.0)["overlaps_bat_echolocation"]


def test_every_species_profile_cites_a_real_source():
    for key, s in sp.SPECIES.items():
        assert s.source_key in ev.SOURCES, f"{key} cites unknown source"


# ---------------------------------------------------------------------------
# Hazard register
# ---------------------------------------------------------------------------


def test_hazard_register_admits_unmitigated_hazards():
    """A register with no open rows has been edited, not completed."""
    assert hz.unmitigated(), "a register with zero open hazards is not credible"
    assert "listed anyway" in hz.summary()["honesty_note"]


def test_every_hazard_states_a_residual_risk():
    for h in hz.REGISTER:
        assert h.residual.strip(), f"{h.id} has no residual risk stated"
        assert h.mechanism.strip()
        assert h.detection.strip()
        assert h.mitigation.strip()


def test_hazard_sources_all_resolve():
    for h in hz.REGISTER:
        for s in h.sources:
            assert s in ev.SOURCES, f"{h.id} cites unknown source {s}"


def test_the_user_raised_hazards_are_covered():
    """Household animals and herd panic must both be explicitly registered."""
    cats = {h.category for h in hz.REGISTER}
    assert "Household animals" in cats
    assert "Herd and stampede" in cats


def test_catastrophic_hazards_are_identified():
    ids = {h.id for h in hz.catastrophic()}
    assert "H08" in ids   # animal driven onto the carriageway
    assert "H05" in ids   # flock panic cascade


def test_hazard_ids_are_unique():
    ids = [h.id for h in hz.REGISTER]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Flight geometry
# ---------------------------------------------------------------------------


def test_animal_on_the_carriageway_is_recognised_as_already_in_hazard():
    a = DEMO_SITE.flight_assessment((640, 600), 25.0)
    assert a["already_in_hazard"]
    assert not a["safe"]


def test_animal_on_the_verge_has_a_safe_flight_path():
    a = DEMO_SITE.flight_assessment((640, 400), 25.0)
    assert not a["already_in_hazard"]
    assert a["safe"]
    assert a["escape_corridor_m"] >= ev.get("min_escape_corridor_m")


def test_flight_into_hazard_is_vetoed():
    gov = Governor(SITE_ATM)
    auth = gov.request(
        "COW-1", 24_000.0, 12.0, 0.5, now_t=100.0,
        scene=SceneContext(flight_enters_hazard=True, escape_corridor_m=2.0),
    )
    assert not auth.granted
    assert Denial.FLIGHT_INTO_HAZARD in auth.denials
    assert Denial.NO_ESCAPE_ROUTE in auth.denials


def test_ground_coordinates_are_metric_and_monotone():
    zs = [DEMO_SITE.ground_xz((640, y))[1] for y in (350, 450, 550, 650)]
    assert all(a > b for a, b in zip(zs, zs[1:]))


# ---------------------------------------------------------------------------
# Herd, juvenile, posture and restraint vetoes
# ---------------------------------------------------------------------------


def test_large_group_blocks_emission():
    """Directly answers the stampede concern."""
    gov = Governor(SITE_ATM)
    n = ev.get("max_herd_size_for_emission") + 2
    auth = gov.request(
        "COW-1", 24_000.0, 12.0, 0.5, now_t=100.0,
        scene=SceneContext(group_size=n),
    )
    assert not auth.granted
    assert Denial.HERD_SIZE in auth.denials


def test_small_group_is_still_permitted():
    gov = Governor(SITE_ATM)
    auth = gov.request(
        "COW-1", 24_000.0, 12.0, 0.5, now_t=100.0,
        scene=SceneContext(group_size=1),
    )
    assert auth.granted


def test_juvenile_blocks_emission():
    gov = Governor(SITE_ATM)
    auth = gov.request(
        "COW-1", 24_000.0, 12.0, 0.5, now_t=100.0,
        scene=SceneContext(juvenile_in_group=True),
    )
    assert not auth.granted
    assert Denial.JUVENILE_PRESENT in auth.denials


def test_downed_animal_blocks_emission():
    gov = Governor(SITE_ATM)
    auth = gov.request(
        "COW-1", 24_000.0, 12.0, 0.5, now_t=100.0,
        scene=SceneContext(downed_animal=True),
    )
    assert not auth.granted
    assert Denial.DOWNED_ANIMAL in auth.denials


def test_immobile_animal_blocks_further_emission():
    """An animal that cannot leave must not be pressed again."""
    gov = Governor(SITE_ATM)
    auth = gov.request(
        "COW-1", 24_000.0, 12.0, 0.5, now_t=100.0,
        scene=SceneContext(immobile_after_emission=True),
    )
    assert not auth.granted
    assert Denial.IMMOBILE_ANIMAL in auth.denials


def test_sensitive_receptors_raise_the_carrier_floor():
    gov = Governor(SITE_ATM)
    low = gov.request(
        "COW-1", 22_000.0, 12.0, 0.5, now_t=100.0,
        scene=SceneContext(sensitive_receptors_nearby=True),
    )
    assert not low.granted
    assert Denial.CHILD_AUDIBILITY in low.denials

    high = gov.request(
        "COW-2", 26_000.0, 12.0, 0.5, now_t=100.0,
        scene=SceneContext(sensitive_receptors_nearby=True),
    )
    assert high.granted


def test_height_estimate_separates_calf_from_cow():
    tall = DEMO_SITE.estimate_height_m((600, 600 - 110, 700, 600))
    short = DEMO_SITE.estimate_height_m((600, 600 - 50, 700, 600))
    assert tall > 1.1
    assert short < 0.9


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------


def test_goat_flock_scenario_never_emits():
    """The user-raised goat-flock hazard, verified end to end."""
    _, _, actions = _run("goat-flock")
    assert not [a for a in actions if a["action"] == "emit"]


def test_cow_with_calf_never_emits():
    _, _, actions = _run("cow-with-calf")
    assert not [a for a in actions if a["action"] == "emit"]


def test_large_herd_scenario_never_emits():
    engine, _, actions = _run("herd-stampede-risk")
    assert not [a for a in actions if a["action"] == "emit"]
    denials = engine.governor.summary()["denials_by_reason"]
    assert any("cascade" in r for r in denials)


def test_animal_on_road_is_never_pushed_across_it():
    """The worst failure mode this system could have."""
    engine, _, actions = _run("flight-into-road")
    assert not [a for a in actions if a["action"] == "emit"]
    denials = engine.governor.summary()["denials_by_reason"]
    assert any("carriageway" in r for r in denials)


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_no_scenario_with_a_nontarget_animal_ever_emits(name):
    """Sweeping invariant across every scenario containing a non-target species."""
    labels = {a.label for a in SCENARIOS[name].actors}
    if not (labels & {"dog", "cat", "sheep", "horse", "person"}):
        pytest.skip("no non-target species in this scenario")
    engine, _, _ = _run(name)
    assert not engine.ledger.of_kind("emission"), (
        f"{name} emitted while a non-target species was present"
    )
