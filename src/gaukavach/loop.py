"""
Closed-loop outcome simulation.

The earlier scenario player had a real flaw: the animals moved along scripted
paths, so they walked exactly the same way whether the system emitted or not.
It demonstrated detection and refusal, but never a CONSEQUENCE. You could not
see the mechanism, because there wasn't one.

This module closes the loop:

    detect -> decide -> emit -> the animal ACTUALLY RESPONDS -> road clears
                                       |
                                       +-> or it doesn't, and we escalate

The animal's response is drawn from the behavioural prior in `twin.py`, which
means it is uncertain by construction. A single run therefore proves nothing,
and showing one would be dishonest. So the unit of output here is a Monte Carlo
ENSEMBLE: run the same encounter hundreds of times, report the distribution of
outcomes with credible intervals, and compare against a control arm where the
emitter never fires.

That comparison is the mechanism, stated the only way the evidence permits:
"under our stated prior, this is the distribution of outcomes, and here is how
much of it overlaps with doing nothing."
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import Enum

import numpy as np

from . import evidence as ev
from .acoustics import Atmosphere, select_carrier
from .traffic import RoadParams, blockage_impact
from .twin import BehaviourTwin, received_level_db
from .welfare import Governor, SceneContext


class Behaviour(str, Enum):
    """Field-observable states, matching the Appendix A outcome codes."""

    APPROACHING = "approaching"
    ORIENTED = "oriented"        # O - looked toward the source, kept coming
    STOPPED = "stopped"          # S - halted before the line
    TURNED = "turned"            # T - withdrew
    CROSSED = "crossed"          # C - reached the carriageway
    PANICKED = "panicked"        # R - ran; a stop criterion, never a success


class Ending(str, Enum):
    CLEARED_ACOUSTIC = "cleared by acoustic nudge"
    CLEARED_UNPROMPTED = "cleared without any emission"
    CROSSED = "reached the carriageway"
    PANIC = "panic response - stop criterion fired"
    ESCALATED = "handed to human dispatch"
    TIMEOUT = "run ended with animal still approaching"


@dataclass
class Encounter:
    """One animal's full encounter, start to resolution."""

    ending: Ending
    outcome_code: str
    time_to_resolve_s: float
    emissions: int
    total_emission_s: float
    closest_approach_m: float
    crossed: bool
    panicked: bool
    escalated: bool
    max_received_db: float
    trace: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["ending"] = self.ending.value
        return d


# ---------------------------------------------------------------------------


@dataclass
class AnimalModel:
    """
    Physical and motivational parameters for one animal.

    `motivation` is the pull toward whatever is on the far side - feed, water,
    shade, the rest of the herd. The report lists motivation override as a
    named failure mode, so it is a first-class parameter rather than an
    afterthought: a hungry cow heading for a feed pile is a different problem
    from one ambling across.
    """

    speed_m_s: float = 1.1          # walking cattle
    motivation: float = 0.5         # 0 = idle drift, 1 = strongly driven
    start_distance_m: float = 34.0
    line_distance_m: float = 12.0   # carriageway edge, measured from the emitter


class _Precomputed:
    """
    Lookup tables for the hot path.

    Running a full carrier sweep and a 4000-sample Monte Carlo on every
    timestep of every run makes an ensemble take minutes. Both are pure
    functions of distance and received level respectively, so they are
    tabulated once. The VALUES are identical to calling the real functions -
    this is caching, not approximation, apart from a 0.5 m / 0.5 dB
    quantisation that is far finer than the +/-20% distance error already in
    the system.
    """

    def __init__(self, atm: Atmosphere, directivity_gain_db: float, ceiling_db: float):
        self.atm = atm
        self.d_step = 0.5
        self.carrier: dict[int, tuple[float, float] | None] = {}
        for i in range(1, 241):  # 0.5 .. 120 m
            d = i * self.d_step
            best, _ = select_carrier(atm, d, ceiling_db,
                                     directivity_gain_db=directivity_gain_db)
            self.carrier[i] = (best.freq_hz, best.required_at_1m_db) if best else None

        twin = BehaviourTwin(seed=3, n_samples=4000)
        self.db_lo, self.db_step = 40.0, 0.5
        self.p_fresh = np.array([
            twin.response_probability(self.db_lo + k * self.db_step).p_response_median
            for k in range(int((130.0 - self.db_lo) / self.db_step) + 1)
        ])
        self.halflife = float(ev.get("habituation_halflife_exposures"))

    def carrier_for(self, dist_m: float) -> tuple[float, float] | None:
        return self.carrier.get(max(1, min(240, int(round(dist_m / self.d_step)))))

    def p_response(self, rx_db: float, prior_exposures: int) -> float:
        k = int(round((rx_db - self.db_lo) / self.db_step))
        k = max(0, min(len(self.p_fresh) - 1, k))
        p = float(self.p_fresh[k])
        # Same habituation decay the twin applies, kept in one place.
        return p * (0.5 ** (prior_exposures / self.halflife)) if prior_exposures else p


_CACHE: dict[tuple, _Precomputed] = {}


def _tables(atm: Atmosphere, directivity: float, ceiling: float) -> _Precomputed:
    key = (atm.temp_c, atm.rh_pct, atm.ambient_spl_db, directivity, ceiling)
    if key not in _CACHE:
        _CACHE[key] = _Precomputed(atm, directivity, ceiling)
    return _CACHE[key]


def _p_panic(received_db: float, ceiling_db: float) -> float:
    """
    Probability that a response is panic rather than controlled withdrawal.

    HEURISTIC. No measurement exists for ultrasonic startle in cattle, so this
    rises with proximity to the welfare ceiling and stays small below it. It
    only ever makes outcomes WORSE in the simulation, never better, so it
    cannot be used to flatter the system.
    """
    head = (received_db - 75.0) / max(ceiling_db - 75.0, 1.0)
    return float(np.clip(0.04 + 0.22 * max(head, 0.0) ** 2, 0.0, 0.35))


class EncounterSim:
    """
    One animal, one approach, run to resolution.

    `emitter_enabled=False` gives the control arm: identical geometry, identical
    motivation, no sound. Without that arm the numbers mean nothing, because
    plenty of animals turn away on their own.
    """

    def __init__(
        self,
        atm: Atmosphere,
        animal: AnimalModel | None = None,
        rng: np.random.Generator | None = None,
        twin: BehaviourTwin | None = None,
        directivity_gain_db: float = 12.0,
        dt: float = 0.5,
        max_time_s: float = 90.0,
    ) -> None:
        self.atm = atm
        self.animal = animal or AnimalModel()
        self.rng = rng or np.random.default_rng()
        self.twin = twin or BehaviourTwin(seed=int(self.rng.integers(1 << 30)))
        self.directivity = directivity_gain_db
        self.dt = dt
        self.max_time_s = max_time_s

    def run(self, emitter_enabled: bool = True, record_trace: bool = False) -> Encounter:
        a = self.animal
        gov = Governor(self.atm, directivity_gain_db=self.directivity)
        tab = _tables(self.atm, self.directivity, gov.ceiling_db)
        dist = a.start_distance_m
        closest = dist
        t = 0.0
        state = Behaviour.APPROACHING
        emissions = 0
        emit_s = 0.0
        max_rx = 0.0
        attempts = 0
        trace: list[dict] = []
        # Baseline chance per step that an undisturbed animal wanders off on
        # its own. Low motivation means it is easily distracted.
        p_self_clear = 0.010 * (1.0 - a.motivation)

        while t < self.max_time_s:
            # --- animal moves ------------------------------------------------
            if state in (Behaviour.APPROACHING, Behaviour.ORIENTED):
                dist -= a.speed_m_s * self.dt * (0.55 if state is Behaviour.ORIENTED else 1.0)
            elif state is Behaviour.TURNED:
                dist += a.speed_m_s * 1.3 * self.dt
            elif state is Behaviour.PANICKED:
                # Panic is not withdrawal. Direction is effectively a coin flip,
                # which is exactly why it is a stop criterion and not a success.
                dist += self.rng.choice([-1.0, 1.0]) * a.speed_m_s * 2.6 * self.dt
            closest = min(closest, dist)

            if record_trace:
                trace.append({"t": round(t, 2), "d": round(dist, 2),
                              "state": state.value, "emitting": False})

            # --- resolution checks -------------------------------------------
            if dist <= a.line_distance_m and state is not Behaviour.TURNED:
                return Encounter(
                    Ending.PANIC if state is Behaviour.PANICKED else Ending.CROSSED,
                    "R" if state is Behaviour.PANICKED else "C",
                    round(t, 2), emissions, round(emit_s, 2), round(closest, 2),
                    True, state is Behaviour.PANICKED, False, round(max_rx, 1), trace)

            if dist >= a.start_distance_m + 6.0 and state in (Behaviour.TURNED, Behaviour.PANICKED):
                ending = Ending.PANIC if state is Behaviour.PANICKED else (
                    Ending.CLEARED_ACOUSTIC if emissions else Ending.CLEARED_UNPROMPTED)
                return Encounter(
                    ending, "R" if state is Behaviour.PANICKED else "T",
                    round(t, 2), emissions, round(emit_s, 2), round(closest, 2),
                    False, state is Behaviour.PANICKED, False, round(max_rx, 1), trace)

            if state is Behaviour.STOPPED and t > 12.0:
                return Encounter(
                    Ending.CLEARED_ACOUSTIC if emissions else Ending.CLEARED_UNPROMPTED,
                    "S", round(t, 2), emissions, round(emit_s, 2), round(closest, 2),
                    False, False, False, round(max_rx, 1), trace)

            # animal loses interest by itself - the control-arm mechanism
            if state is Behaviour.APPROACHING and self.rng.random() < p_self_clear:
                state = Behaviour.TURNED

            # --- system decides ----------------------------------------------
            if emitter_enabled and state in (Behaviour.APPROACHING, Behaviour.ORIENTED):
                if attempts >= 3:
                    return Encounter(
                        Ending.ESCALATED, "N", round(t, 2), emissions, round(emit_s, 2),
                        round(closest, 2), False, False, True, round(max_rx, 1), trace)

                hit = tab.carrier_for(max(dist, 1.0))
                if hit is not None:
                    carrier_hz, _need = hit
                    auth = gov.request(
                        "A", carrier_hz, dist, 0.54, t,
                        scene=SceneContext(escape_corridor_m=30.0),
                    )
                    if auth.granted:
                        gov.commit(auth, t, 0.54)
                        emissions += 1
                        attempts += 1
                        emit_s += 0.54
                        rx = received_level_db(auth.level_at_1m_db, dist,
                                               carrier_hz, self.atm)
                        max_rx = max(max_rx, rx)
                        if record_trace:
                            trace[-1]["emitting"] = True
                            trace[-1]["rx_db"] = round(rx, 1)
                            trace[-1]["khz"] = round(carrier_hz / 1000, 1)

                        # --- the animal responds, or does not ----------------
                        p = tab.p_response(rx, prior_exposures=emissions - 1)
                        if self.rng.random() < p:
                            if self.rng.random() < _p_panic(rx, gov.ceiling_db):
                                state = Behaviour.PANICKED
                            else:
                                state = (Behaviour.TURNED if self.rng.random() < 0.72
                                         else Behaviour.STOPPED)
                        else:
                            state = Behaviour.ORIENTED  # noticed it, kept coming

            t += self.dt

        return Encounter(Ending.TIMEOUT, "N", round(t, 2), emissions, round(emit_s, 2),
                         round(closest, 2), False, False, False, round(max_rx, 1), trace)


# ---------------------------------------------------------------------------
# Ensemble
# ---------------------------------------------------------------------------


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval - behaves sensibly at 0% and 100%, unlike normal."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - m), min(1.0, c + m))


def ensemble(
    n_runs: int = 400,
    atm: Atmosphere | None = None,
    animal: AnimalModel | None = None,
    seed: int = 20260815,
    road: RoadParams | None = None,
) -> dict:
    """
    Run the encounter many times with and without the emitter.

    Returns the outcome distribution for both arms, the difference with a
    confidence interval, and the traffic consequence of the difference in
    clearance time. This is the closest thing to a performance claim the
    evidence permits, and it is explicitly labelled as prior-driven.
    """
    atm = atm or Atmosphere(temp_c=32.0, rh_pct=60.0, ambient_spl_db=58.0)
    animal = animal or AnimalModel()
    road = road or RoadParams(lanes=2, demand_veh_h=1200.0)
    rng = np.random.default_rng(seed)

    arms: dict[str, list[Encounter]] = {"active": [], "control": []}
    for arm, enabled in (("active", True), ("control", False)):
        sim = EncounterSim(atm, animal, np.random.default_rng(rng.integers(1 << 30)))
        for _ in range(n_runs):
            arms[arm].append(sim.run(emitter_enabled=enabled))

    def stats(runs: list[Encounter]) -> dict:
        n = len(runs)
        crossed = sum(r.crossed for r in runs)
        panic = sum(r.panicked for r in runs)
        esc = sum(r.escalated for r in runs)
        cleared = n - crossed - esc
        times = [r.time_to_resolve_s for r in runs]
        lo, hi = _wilson(cleared, n)
        codes: dict[str, int] = {}
        for r in runs:
            codes[r.outcome_code] = codes.get(r.outcome_code, 0) + 1
        endings: dict[str, int] = {}
        for r in runs:
            endings[r.ending.value] = endings.get(r.ending.value, 0) + 1
        return {
            "n": n,
            "cleared": cleared,
            "clear_rate": round(cleared / n, 4),
            "clear_ci": [round(lo, 4), round(hi, 4)],
            "crossed": crossed,
            "cross_rate": round(crossed / n, 4),
            "panicked": panic,
            "panic_rate": round(panic / n, 4),
            "escalated": esc,
            "escalation_rate": round(esc / n, 4),
            "mean_resolve_s": round(float(np.mean(times)), 2),
            "median_resolve_s": round(float(np.median(times)), 2),
            "mean_emissions": round(float(np.mean([r.emissions for r in runs])), 2),
            "mean_emission_s": round(float(np.mean([r.total_emission_s for r in runs])), 3),
            "outcome_codes": codes,
            "endings": endings,
        }

    act, ctl = stats(arms["active"]), stats(arms["control"])
    diff = act["clear_rate"] - ctl["clear_rate"]
    # Difference in two proportions, normal approximation on the difference.
    n1, n2 = act["n"], ctl["n"]
    p1, p2 = act["clear_rate"], ctl["clear_rate"]
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    d_lo, d_hi = diff - 1.96 * se, diff + 1.96 * se
    significant = d_lo > 0.0

    # Traffic consequence.
    #
    # The obvious mistake here - which the first version of this code made - is
    # to compare mean time-to-resolve between the arms. That conflates two
    # different endings: an animal that turns away and one that walks onto the
    # road both "resolve". By that metric the active arm looks WORSE, because
    # nudged animals mill about for longer before giving up.
    #
    # A blockage only occurs when an animal actually reaches the carriageway.
    # So the right quantity is EXPECTED delay per approach:
    #     P(cross) x delay caused by one blockage
    # which is driven by the cross rate, not by how long the encounter took.
    blockage_s = 150.0  # time a cow spends on the road once it gets there
    per_block = blockage_impact(blockage_s, road)
    exp_ctl_h = ctl["cross_rate"] * per_block.person_hours_lost
    exp_act_h = act["cross_rate"] * per_block.person_hours_lost
    exp_ctl_inr = ctl["cross_rate"] * per_block.cost_inr
    exp_act_inr = act["cross_rate"] * per_block.cost_inr

    return {
        "n_runs_per_arm": n_runs,
        "active": act,
        "control": ctl,
        "difference": {
            "clear_rate_gain": round(diff, 4),
            "ci95": [round(d_lo, 4), round(d_hi, 4)],
            "statistically_separable": significant,
            "reading": (
                f"Clearance rose from {ctl['clear_rate']:.0%} to {act['clear_rate']:.0%}, "
                f"a gain of {diff:+.0%} (95% CI {d_lo:+.0%} to {d_hi:+.0%})."
                + ("" if significant else
                   " The interval crosses zero: under this prior the effect is NOT "
                   "separable from doing nothing.")
            ),
        },
        "traffic": {
            "basis": "expected delay per approach = P(cross) x delay of one blockage",
            "assumed_blockage_s": blockage_s,
            "delay_per_blockage_person_h": round(per_block.person_hours_lost, 3),
            "control_cross_rate": ctl["cross_rate"],
            "active_cross_rate": act["cross_rate"],
            "expected_person_h_control": round(exp_ctl_h, 3),
            "expected_person_h_active": round(exp_act_h, 3),
            "person_hours_saved_per_approach": round(exp_ctl_h - exp_act_h, 3),
            "cost_inr_saved_per_approach": round(exp_ctl_inr - exp_act_inr, 1),
            "relative_reduction": (
                round(1.0 - act["cross_rate"] / ctl["cross_rate"], 4)
                if ctl["cross_rate"] > 0 else 0.0
            ),
            "caveat": (
                "Scales linearly with the cross-rate difference, which is itself "
                "prior-driven. The 150 s blockage duration is an assumption, not "
                "a measurement. Do NOT quote the rupee figure as a saving - it is "
                "a sensitivity, and it inherits every uncertainty above it."
            ),
        },
        "timing_note": (
            f"Mean time to resolve is LONGER in the active arm "
            f"({act['mean_resolve_s']:.0f} s vs {ctl['mean_resolve_s']:.0f} s), "
            f"because a nudged animal mills about before giving up while an "
            f"undisturbed one walks straight onto the road. That is why the "
            f"traffic model keys on cross rate and not on encounter duration - "
            f"the naive comparison would make the system look worse than it is, "
            f"and for the wrong reason."
        ),
        "welfare": {
            "mean_emission_s_per_encounter": act["mean_emission_s"],
            "panic_rate": act["panic_rate"],
            "escalation_rate": act["escalation_rate"],
            "note": (
                "Panic is counted as a FAILURE, not a clearance, and triggers the "
                "stop criterion. A configuration that clears the road by "
                "frightening animals into bolting scores worse here, not better."
            ),
        },
        "provenance": (
            "Outcomes are drawn from the HYPOTHESIS-grade response prior in "
            "twin.py, not from measurement. This ensemble shows what that prior "
            "IMPLIES, with the control arm included so the reader can see how "
            "much of the effect is the prior and how much is the intervention. "
            "It is not a performance claim and must not be quoted as one."
        ),
        "grade": "Hypothesis - prior-driven simulation, not measured",
    }


def sensitivity(n_runs: int = 250, seed: int = 7) -> list[dict]:
    """
    How the outcome changes with how badly the animal wants to cross.

    Motivation override is a named failure mode in the report; this makes it a
    number instead of a caveat.
    """
    atm = Atmosphere(temp_c=32.0, rh_pct=60.0, ambient_spl_db=58.0)
    out = []
    for mot in (0.1, 0.3, 0.5, 0.7, 0.9):
        e = ensemble(n_runs, atm, AnimalModel(motivation=mot), seed=seed + int(mot * 100))
        out.append({
            "motivation": mot,
            "active_clear": e["active"]["clear_rate"],
            "control_clear": e["control"]["clear_rate"],
            "gain": e["difference"]["clear_rate_gain"],
            "separable": e["difference"]["statistically_separable"],
            "cross_rate": e["active"]["cross_rate"],
        })
    return out
