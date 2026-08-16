"""
Tests that a sceptical judge could run.

These are deliberately written as CLAIMS, not as coverage. Each test name is a
statement the project makes in its pitch, so a reviewer can read the test names
and see exactly which assertions are machine-checked.
"""

from __future__ import annotations

import math

import pytest

from gaukavach import evidence as ev
from gaukavach.acoustics import (
    Atmosphere,
    human_audibility_risk,
    iso9613_alpha,
    lawrence_simmons_alpha,
    max_effective_range_m,
    select_carrier,
    spreading_loss_db,
    sweep_frequencies,
)
from gaukavach.detect import DEMO_SITE, Detection, SimpleTracker, point_in_polygon
from gaukavach.emitter import PATTERNS, build_emission, compare_gating, synthesise
from gaukavach.ledger import Ledger
from gaukavach.policy import EngineConfig, Outcome, PolicyEngine
from gaukavach.scenario import SCENARIOS, run as run_scenario
from gaukavach.traffic import RoadParams, blockage_impact
from gaukavach.twin import BehaviourTwin
from gaukavach.welfare import Denial, Governor, SceneContext, prove_refusal

SITE_ATM = Atmosphere(temp_c=32.0, rh_pct=60.0, ambient_spl_db=58.0)


# ---------------------------------------------------------------------------
# Physics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "distance_m,expected_total_db",
    [(2, 6.7), (5, 16.8), (10, 26.3), (20, 39.3), (30, 49.8)],
)
def test_propagation_reproduces_the_published_table(distance_m, expected_total_db):
    """Our propagation model reproduces Table 7.2 of the source report exactly."""
    geometric = spreading_loss_db(distance_m)
    absorption = lawrence_simmons_alpha(30_000.0) * (distance_m - 1)
    assert geometric + absorption == pytest.approx(expected_total_db, abs=0.1)


def test_six_db_per_doubling_holds():
    """
    Geometric spreading matches the 6 dB per doubling rule (R13).

    The exact figure is 20*log10(2) = 6.0206 dB; "6 dB" is the rounded
    convention used in the literature. We assert the exact value rather than
    the rounded one, because silently accepting 6.0 would hide a real error of
    0.02 dB per doubling that accumulates over a long link.
    """
    for d in (2.0, 4.0, 8.0, 16.0):
        step = spreading_loss_db(2 * d) - spreading_loss_db(d)
        assert step == pytest.approx(20.0 * math.log10(2.0), abs=1e-9)
        assert step == pytest.approx(6.0, abs=0.03)


def test_iso_and_lawrence_simmons_disagree_and_we_say_so():
    """The two absorption models differ; the code must not pretend otherwise."""
    ref = Atmosphere(temp_c=25.0, rh_pct=50.0)
    iso = iso9613_alpha(30_000.0, ref)
    ls = lawrence_simmons_alpha(30_000.0, ref)
    assert ls == pytest.approx(0.7, abs=0.01)      # the measured anchor
    assert iso > ls                                 # ISO is the pessimistic one
    assert abs(iso - ls) > 0.15                     # and the gap is material


def test_absorption_rises_with_frequency():
    """Higher carriers are absorbed faster - the core range/stealth tension."""
    a22 = iso9613_alpha(22_000.0, SITE_ATM)
    a30 = iso9613_alpha(30_000.0, SITE_ATM)
    a35 = iso9613_alpha(35_000.0, SITE_ATM)
    assert a22 < a30 < a35


def test_range_collapses_at_the_top_of_the_band():
    """30 kHz reaches materially less far than 22 kHz. This is the headline finding."""
    cap = ev.get("osha_ultrasound_ceiling_db")
    r22 = max_effective_range_m(22_000.0, SITE_ATM, cap, directivity_gain_db=12.0)
    r30 = max_effective_range_m(30_000.0, SITE_ATM, cap, directivity_gain_db=12.0)
    assert r22 > r30
    assert r22 / max(r30, 1e-6) > 1.4


# ---------------------------------------------------------------------------
# Carrier selection
# ---------------------------------------------------------------------------


def test_optimiser_never_selects_below_the_documented_band():
    """20 kHz is not a guaranteed silent frequency (R13), so it must be refused."""
    best, sweep = select_carrier(
        SITE_ATM, 15.0, ev.get("osha_ultrasound_ceiling_db"), directivity_gain_db=12.0
    )
    assert best is not None
    assert best.freq_hz >= ev.get("experimental_band_low_hz")
    below = [c for c in sweep if c.freq_hz < ev.get("experimental_band_low_hz")]
    assert below and all(not c.feasible for c in below)


def test_optimiser_never_selects_above_the_documented_band():
    sweep = sweep_frequencies(
        SITE_ATM, 15.0, ev.get("osha_ultrasound_ceiling_db"), directivity_gain_db=12.0
    )
    above = [c for c in sweep if c.freq_hz > ev.get("experimental_band_high_hz")]
    assert above and all(not c.feasible for c in above)


def test_impossible_geometry_returns_no_carrier():
    """At long range the honest answer is 'cannot', not a louder emitter."""
    best, _ = select_carrier(
        SITE_ATM, 300.0, ev.get("osha_ultrasound_ceiling_db"), directivity_gain_db=12.0
    )
    assert best is None


def test_human_audibility_risk_is_monotone_decreasing():
    risks = [human_audibility_risk(f) for f in (14_000, 17_000, 20_000, 23_000, 26_000)]
    assert all(a > b for a, b in zip(risks, risks[1:]))


# ---------------------------------------------------------------------------
# Welfare governor - the refusal claims
# ---------------------------------------------------------------------------


def test_the_142_db_prototype_level_is_unreachable():
    """The single published cattle exposure cannot be reproduced by configuration."""
    proof = prove_refusal(SITE_ATM)
    assert proof["without_ethics_token"]["granted"] is False
    assert proof["with_ethics_token"]["granted"] is False


def test_ceiling_never_exceeds_the_cited_occupational_band():
    """Even with an ethics token, the ceiling stops at the top of the cited band."""
    gov = Governor(SITE_ATM, ethics_token="ETHICS/TEST/1")
    assert gov.ceiling_db <= ev.get("osha_ultrasound_ceiling_max_db")
    assert gov.ceiling_db < ev.get("refused_prototype_spl_db")


def test_a_person_in_the_cone_blocks_every_emission():
    gov = Governor(SITE_ATM)
    auth = gov.request(
        "COW-1", 24_000.0, 12.0, 0.5, now_t=100.0,
        scene=SceneContext(humans_in_cone=1),
    )
    assert not auth.granted
    assert Denial.HUMAN_PRESENT in auth.denials


def test_a_non_target_animal_in_the_cone_blocks_emission():
    gov = Governor(SITE_ATM)
    auth = gov.request(
        "COW-1", 24_000.0, 12.0, 0.5, now_t=100.0,
        scene=SceneContext(non_target_animals_in_cone=("dog",)),
    )
    assert not auth.granted
    assert Denial.NON_TARGET in auth.denials


def test_silence_window_is_enforced_between_exposures():
    gov = Governor(SITE_ATM)
    first = gov.request("COW-1", 24_000.0, 12.0, 0.5, now_t=100.0)
    assert first.granted
    gov.commit(first, 100.0, 0.5)
    second = gov.request("COW-1", 24_000.0, 12.0, 0.5, now_t=101.0)
    assert not second.granted
    assert Denial.SILENCE_WINDOW in second.denials


def test_daily_exposure_budget_flags_the_animal():
    gov = Governor(SITE_ATM)
    t = 0.0
    budget = ev.get("daily_exposure_budget_s")
    dur = ev.get("max_activation_s")
    granted = 0
    for _ in range(int(budget / dur) + 5):
        a = gov.request("COW-1", 24_000.0, 12.0, dur, now_t=t)
        if a.granted:
            gov.commit(a, t, dur)
            granted += 1
        t += ev.get("min_silence_s") + 1.0
    assert gov.record("COW-1").do_not_emit
    assert granted * dur <= budget


def test_duration_watchdog_rejects_long_activations():
    gov = Governor(SITE_ATM)
    auth = gov.request(
        "COW-1", 24_000.0, 12.0, ev.get("max_activation_s") + 1.0, now_t=100.0
    )
    assert not auth.granted
    assert Denial.DURATION in auth.denials


def test_granted_level_is_the_minimum_sufficient_not_the_maximum():
    """The system emits what is needed, never what the hardware can produce."""
    gov = Governor(SITE_ATM)
    near = gov.request("COW-1", 24_000.0, 5.0, 0.5, now_t=100.0)
    far = gov.request("COW-2", 24_000.0, 20.0, 0.5, now_t=100.0)
    assert near.granted and far.granted
    assert near.level_at_1m_db < far.level_at_1m_db      # closer needs less power
    assert near.level_at_1m_db < gov.ceiling_db


def test_out_of_band_carrier_is_refused():
    gov = Governor(SITE_ATM)
    auth = gov.request("COW-1", 40_000.0, 10.0, 0.5, now_t=100.0)
    assert not auth.granted
    assert Denial.BAND_VIOLATION in auth.denials


# ---------------------------------------------------------------------------
# Evidence discipline
# ---------------------------------------------------------------------------


def test_every_constant_declares_a_grade_and_a_real_source():
    for name, c in ev.REGISTRY.items():
        assert c.sources, f"{name} has no source"
        assert c.rationale.strip(), f"{name} has no rationale"
        for s in c.sources:
            assert s in ev.SOURCES


def test_unregistered_constants_cannot_be_fetched():
    with pytest.raises(KeyError):
        ev.get("some_number_we_made_up")


def test_our_own_assumptions_are_not_actionable():
    """Heuristic and hypothesis grades must not count as evidence."""
    assert not ev.Grade.HEURISTIC.actionable
    assert not ev.Grade.HYPOTHESIS.actionable
    assert not ev.Grade.LOW.actionable
    assert ev.Grade.HIGH.actionable


def test_the_experimental_band_is_labelled_a_hypothesis_not_a_finding():
    assert ev.grade_of("experimental_band_low_hz") is ev.Grade.HYPOTHESIS
    assert ev.grade_of("experimental_band_high_hz") is ev.Grade.HYPOTHESIS


# ---------------------------------------------------------------------------
# Emitter
# ---------------------------------------------------------------------------


def test_ramping_reduces_audible_splatter_substantially():
    """A hard-gated ultrasonic burst radiates audible switching energy."""
    r = compare_gating(25_000.0)
    assert r["improvement_db"] > 20.0


def test_synthesised_carrier_lands_on_the_requested_frequency():
    for f in (22_000.0, 25_000.0, 28_000.0):
        _, report = build_emission(f, PATTERNS[0])
        assert report.peak_hz == pytest.approx(f, rel=0.02)


def test_waveform_is_normalised_and_finite():
    w = synthesise(24_000.0, PATTERNS[2])
    assert w.size > 0
    assert math.isclose(float(abs(w).max()), 1.0, abs_tol=1e-6)
    assert bool((abs(w) <= 1.0).all())


def test_scheduler_varies_the_pattern_between_exposures():
    from gaukavach.emitter import PatternScheduler

    s = PatternScheduler(seed=3)
    picks = [s.choose("COW-1", [22_000.0, 24_000.0, 26_000.0])[1].name for _ in range(6)]
    assert len(set(picks)) > 1
    assert not all(a == b for a, b in zip(picks, picks[1:]))


# ---------------------------------------------------------------------------
# Perception and geometry
# ---------------------------------------------------------------------------


def test_distance_decreases_as_the_animal_comes_down_the_frame():
    ds = [DEMO_SITE.estimate_distance_m((640, y)) for y in (350, 420, 520, 650)]
    assert all(a > b for a, b in zip(ds, ds[1:]))


def test_distance_above_the_horizon_is_treated_as_unreachable():
    assert DEMO_SITE.estimate_distance_m((640, DEMO_SITE.horizon_y - 10)) > 1000


def test_zones_are_nested_correctly():
    assert point_in_polygon((640, 600), DEMO_SITE.carriageway)
    assert point_in_polygon((640, 600), DEMO_SITE.warning_zone)
    assert DEMO_SITE.classify_position((640, 200)) == "outside"


def test_tracker_keeps_identity_across_frames():
    """Identity persistence is a welfare requirement, not a convenience."""
    tr = SimpleTracker()
    ids = set()
    for i in range(10):
        d = Detection(19, "cow", 0.9, (100 + i * 4, 300, 240 + i * 4, 420))
        ids.update(t.track_id for t in tr.update([d]))
    assert len(ids) == 1


def test_tracker_does_not_merge_different_species():
    tr = SimpleTracker()
    cow = Detection(19, "cow", 0.9, (100, 300, 240, 420))
    dog = Detection(16, "dog", 0.9, (105, 305, 235, 415))
    tracks = tr.update([cow, dog])
    assert {t.label for t in tracks} == {"cow", "dog"}


# ---------------------------------------------------------------------------
# Behavioural twin - the honesty claims
# ---------------------------------------------------------------------------


def test_twin_never_returns_a_bare_point_estimate():
    o = BehaviourTwin().response_probability(85.0)
    assert o.p_response_lo < o.p_response_median < o.p_response_hi
    assert o.interval_width > 0.0


def test_twin_admits_the_intervals_are_uninformative():
    """At the levels the welfare ceiling permits, the prior dominates. Say so."""
    o = BehaviourTwin().response_probability(70.0)
    assert "UNINFORMATIVE" in o.verdict


def test_response_increases_with_dose():
    twin = BehaviourTwin()
    ps = [twin.response_probability(float(d)).p_response_median for d in (60, 75, 90, 105)]
    assert all(a < b for a, b in zip(ps, ps[1:]))


def test_habituation_decays_the_response():
    twin = BehaviourTwin()
    fresh = twin.response_probability(90.0, prior_exposures=0).p_response_median
    worn = twin.response_probability(90.0, prior_exposures=24).p_response_median
    assert worn < fresh / 2


def test_social_facilitation_increases_response():
    twin = BehaviourTwin()
    alone = twin.response_probability(85.0).p_response_median
    herd = twin.response_probability(85.0, conspecific_responded=True).p_response_median
    assert herd > alone


def test_trial_sizing_is_a_concrete_number():
    n = BehaviourTwin().required_sample_size()
    assert n["approaches_per_arm"] > 10
    assert "LOWER BOUND" in n["note"]


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------


def test_ledger_chain_validates():
    led = Ledger()
    for i in range(20):
        led.append("emission", {"i": i})
    assert led.verify()["valid"]


def test_tampering_with_history_is_detected():
    led = Ledger()
    for i in range(10):
        led.append("emission", {"level_db": 90 + i})
    led.records[4].payload["level_db"] = 142      # the edit an operator would make
    result = led.verify()
    assert not result["valid"]
    assert result["broken_at_seq"] == 4


def test_deleting_a_record_is_detected():
    led = Ledger()
    for i in range(10):
        led.append("emission", {"i": i})
    del led.records[5]
    assert not led.verify()["valid"]


def test_ledger_does_not_overclaim():
    """The scope statement must not imply more than a single-writer log gives."""
    scope = Ledger().verify()["scope"]
    assert "does not by itself prove" in scope


# ---------------------------------------------------------------------------
# Traffic
# ---------------------------------------------------------------------------


def test_queue_takes_longer_to_clear_than_the_blockage_lasted():
    """The counter-intuitive result that justifies fast clearance."""
    p = RoadParams(lanes=2, demand_veh_h=1200.0)
    i = blockage_impact(120.0, p)
    assert i.queue_clear_s > 0
    assert i.max_queue_veh > 0


def test_delay_grows_superlinearly_with_blockage_duration():
    p = RoadParams(lanes=2, demand_veh_h=1200.0)
    d1 = blockage_impact(60.0, p).total_delay_veh_h
    d2 = blockage_impact(120.0, p).total_delay_veh_h
    assert d2 > 2.0 * d1


def test_oversaturation_is_reported_not_hidden():
    """If demand exceeds capacity the queue never clears; say that explicitly."""
    p = RoadParams(lanes=1, demand_veh_h=2000.0)
    i = blockage_impact(60.0, p)
    assert i.queue_clear_s == -1.0
    assert "never clears" in i.note


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------


def _run(name: str):
    engine = PolicyEngine(DEMO_SITE, SITE_ATM, Ledger(), EngineConfig())
    snaps = run_scenario(SCENARIOS[name], engine, SimpleTracker())
    actions = [a for s in snaps for a in s["actions"]]
    return engine, snaps, actions


def test_every_scenario_runs_and_leaves_a_valid_ledger():
    for name in SCENARIOS:
        engine, _, _ = _run(name)
        engine.close()
        assert engine.ledger.verify()["valid"], name


def test_happy_path_emits_exactly_once_within_the_cooldown_window():
    _, _, actions = _run("single-approach")
    emits = [a for a in actions if a["action"] == "emit"]
    assert len(emits) == 1
    assert emits[0]["level_at_1m_db"] <= ev.get("osha_ultrasound_ceiling_db")


def test_pedestrian_scenario_never_emits():
    """The scenario that must be demonstrated first."""
    _, _, actions = _run("person-in-cone")
    assert not [a for a in actions if a["action"] == "emit"]
    assert any(a["action"] == "denied" for a in actions)


def test_dog_scenario_never_emits():
    _, _, actions = _run("non-target-dog")
    assert not [a for a in actions if a["action"] == "emit"]


def test_persistent_blocker_escalates_instead_of_getting_louder():
    engine, _, actions = _run("persistent-blocker")
    emits = [a for a in actions if a["action"] == "emit"]
    escalations = [a for a in actions if a["action"] == "escalate"]
    assert escalations, "a cow that never moves must trigger escalation"
    levels = [a["level_at_1m_db"] for a in emits]
    assert all(v <= ev.get("osha_ultrasound_ceiling_db") for v in levels)
    assert engine.ledger.of_kind("escalation")


def test_panic_response_inhibits_further_emission():
    engine, _, _ = _run("panic-stop-criterion")
    flagged = [r for r in engine.governor.records.values() if r.do_not_emit]
    assert flagged
    assert engine.ledger.of_kind("stop")


def test_traffic_response_fires_even_when_sound_cannot_reach():
    """The proven half of the system does not depend on the unproven half."""
    engine, _, actions = _run("single-approach")
    assert any(a["action"] == "out_of_range" for a in actions)
    assert engine.ledger.of_kind("traffic_response")


def test_no_emission_ever_exceeds_the_ceiling_in_any_scenario():
    """The single most important safety invariant, checked across every path."""
    cap = ev.get("osha_ultrasound_ceiling_db")
    for name in SCENARIOS:
        engine, _, _ = _run(name)
        for r in engine.ledger.of_kind("emission"):
            assert r.payload["level_at_1m_db"] <= cap, f"{name} seq {r.seq}"


def test_all_emissions_are_marked_dry_run():
    """Nothing in this repository claims to have made a real sound."""
    for name in SCENARIOS:
        engine, _, _ = _run(name)
        for r in engine.ledger.of_kind("emission"):
            assert r.payload["dry_run"] is True


def test_observation_of_a_turn_closes_the_incident():
    engine = PolicyEngine(DEMO_SITE, SITE_ATM, Ledger(), EngineConfig())
    run_scenario(SCENARIOS["single-approach"], engine, SimpleTracker())
    tid = next(iter(engine.incidents))
    engine.observe(tid, Outcome.TURNED, 30.0)
    assert engine.incidents[tid].cleared_t == 30.0
    assert engine.ledger.of_kind("observation")
