"""
Outdoor ultrasonic propagation and link budget.

Two independent absorption models are carried deliberately:

  * ISO 9613-1 analytical model (R15) - complete, weather-dependent, but its
    stated validity ends at 10 kHz, so at 22-35 kHz we are extrapolating.
  * Lawrence & Simmons (R14) - a direct laboratory MEASUREMENT at ultrasonic
    frequencies, but only characterised at one temperature/humidity point.

They disagree: at 30 kHz / 25 C / 50% RH, ISO predicts ~0.91 dB/m while L&S
measured ~0.70 dB/m. Neither is "the" answer, so GauKavach never silently
picks one. It designs against the PESSIMISTIC model when asking "can the
animal hear this?" (range) and against the OPTIMISTIC model when asking "is
anyone over-exposed?" (welfare). Both answers are therefore conservative in
the direction that matters, and the disagreement is reported, not hidden.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Literal

from . import evidence as ev

Model = Literal["iso9613", "lawrence_simmons"]

T0_K = 293.15      # ISO 9613-1 reference temperature
T01_K = 273.16     # triple-point temperature
PR_KPA = 101.325   # reference ambient pressure
SPEED_OF_SOUND_REF = 343.0  # m/s at 20 C, used only for wavelength reporting


@dataclass(frozen=True)
class Atmosphere:
    """Ambient conditions at the deployment site."""

    temp_c: float = 25.0
    rh_pct: float = 50.0
    pressure_kpa: float = PR_KPA
    ambient_spl_db: float = 55.0  # broadband roadside noise floor

    def speed_of_sound(self) -> float:
        return 331.3 * math.sqrt(1.0 + self.temp_c / 273.15)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["speed_of_sound_m_s"] = round(self.speed_of_sound(), 2)
        return d


def iso9613_alpha(freq_hz: float, atm: Atmosphere) -> float:
    """
    Atmospheric absorption coefficient in dB/m per ISO 9613-1:1993 (R15).

    Returned as-is; callers are responsible for surfacing the >10 kHz
    extrapolation caveat via `extrapolation_warning()`.
    """
    t_k = atm.temp_c + 273.15
    pa = atm.pressure_kpa

    # Saturation vapour pressure ratio, ISO 9613-1 Annex B
    psat_ratio = 10.0 ** (-6.8346 * (T01_K / t_k) ** 1.261 + 4.6151)
    # Molar concentration of water vapour, percent
    h = atm.rh_pct * psat_ratio / (pa / PR_KPA)

    # Oxygen and nitrogen relaxation frequencies
    fr_o = (pa / PR_KPA) * (24.0 + 4.04e4 * h * (0.02 + h) / (0.391 + h))
    fr_n = (
        (pa / PR_KPA)
        * (t_k / T0_K) ** -0.5
        * (9.0 + 280.0 * h * math.exp(-4.170 * ((t_k / T0_K) ** (-1.0 / 3.0) - 1.0)))
    )

    f2 = freq_hz * freq_hz
    classical = 1.84e-11 * (PR_KPA / pa) * math.sqrt(t_k / T0_K)
    relaxation = (t_k / T0_K) ** -2.5 * (
        0.01275 * math.exp(-2239.1 / t_k) / (fr_o + f2 / fr_o)
        + 0.1068 * math.exp(-3352.0 / t_k) / (fr_n + f2 / fr_n)
    )
    return 8.686 * f2 * (classical + relaxation)


def lawrence_simmons_alpha(freq_hz: float, atm: Atmosphere | None = None) -> float:
    """
    Measured ultrasonic absorption (R14), anchored at 0.7 dB/m at 30 kHz.

    L&S characterised 30-200 kHz at 25 C / 50% RH only. Away from 30 kHz we
    scale by the ISO model's frequency shape, anchored to the measurement -
    that hybrid is our construction, not theirs, so it is graded HEURISTIC in
    everything but the anchor point itself.
    """
    anchor_hz = 30_000.0
    anchor = ev.get("ls_alpha_30k_db_per_m")
    if abs(freq_hz - anchor_hz) < 1.0:
        return anchor
    ref = Atmosphere(temp_c=25.0, rh_pct=50.0)
    shape = iso9613_alpha(freq_hz, ref) / iso9613_alpha(anchor_hz, ref)
    scaled = anchor * shape
    if atm is not None:
        # Carry weather sensitivity from the analytical model.
        scaled *= iso9613_alpha(freq_hz, atm) / iso9613_alpha(freq_hz, ref)
    return scaled


def alpha(freq_hz: float, atm: Atmosphere, model: Model = "iso9613") -> float:
    if model == "iso9613":
        return iso9613_alpha(freq_hz, atm)
    if model == "lawrence_simmons":
        return lawrence_simmons_alpha(freq_hz, atm)
    raise ValueError(f"unknown absorption model {model!r}")


def extrapolation_warning(freq_hz: float, model: Model) -> str | None:
    if model == "iso9613" and freq_hz > 10_000.0:
        return (
            f"ISO 9613-1 is specified to 10 kHz; {freq_hz / 1000:.1f} kHz is an "
            f"extrapolation. Treat the absorption term as indicative, not certified."
        )
    if model == "lawrence_simmons" and not (25_000.0 <= freq_hz <= 40_000.0):
        return (
            f"Lawrence & Simmons anchor is 30 kHz at 25 C/50% RH; "
            f"{freq_hz / 1000:.1f} kHz uses an ISO-shaped rescaling (ours)."
        )
    return None


def spreading_loss_db(distance_m: float, ref_m: float = 1.0) -> float:
    """Free-field geometric spreading, 6 dB per doubling (R13)."""
    if distance_m <= 0:
        raise ValueError("distance must be positive")
    return 20.0 * math.log10(max(distance_m, 1e-6) / ref_m)


def total_loss_db(
    distance_m: float,
    freq_hz: float,
    atm: Atmosphere,
    model: Model = "iso9613",
    ref_m: float = 1.0,
) -> float:
    """Total propagation loss from `ref_m` out to `distance_m`."""
    absorb = alpha(freq_hz, atm, model) * max(distance_m - ref_m, 0.0)
    return spreading_loss_db(distance_m, ref_m) + absorb


def wavelength_cm(freq_hz: float, atm: Atmosphere | None = None) -> float:
    c = atm.speed_of_sound() if atm else SPEED_OF_SOUND_REF
    return 100.0 * c / freq_hz


# ---------------------------------------------------------------------------
# Link budget
# ---------------------------------------------------------------------------


@dataclass
class LinkBudget:
    """
    The complete answer to: 'what must the emitter do so this animal, at this
    distance, in this weather, can actually detect the signal - and is that
    level allowed?'
    """

    freq_hz: float
    distance_m: float
    required_at_animal_db: float
    spreading_db: float
    absorption_db: float
    required_at_1m_db: float
    absorption_model: Model
    alpha_db_per_m: float
    caveat: str | None
    ambient_spl_db: float
    directivity_gain_db: float

    def as_dict(self) -> dict:
        d = asdict(self)
        d["freq_khz"] = round(self.freq_hz / 1000.0, 2)
        d["wavelength_cm"] = round(wavelength_cm(self.freq_hz), 2)
        return d


def required_level_at_animal_db(atm: Atmosphere, margin_db: float | None = None) -> float:
    """
    Minimum SPL that must arrive at the animal.

    Two independent floors, take the higher:
      1. Audiogram criterion - R1 defines the 35 kHz endpoint at 60 dB SPL, so
         anything less cannot be assumed detectable near the band edge.
      2. Ambient + masking margin - a signal buried in roadside noise is
         inaudible regardless of the audiogram.
    """
    margin = ev.get("masking_margin_db") if margin_db is None else margin_db
    return max(ev.get("audiogram_criterion_db"), atm.ambient_spl_db + margin)


def link_budget(
    freq_hz: float,
    distance_m: float,
    atm: Atmosphere,
    model: Model = "iso9613",
    directivity_gain_db: float = 0.0,
    margin_db: float | None = None,
) -> LinkBudget:
    """Solve for the emitter level needed at 1 m. Does not check legality."""
    need = required_level_at_animal_db(atm, margin_db)
    spread = spreading_loss_db(distance_m)
    a = alpha(freq_hz, atm, model)
    absorb = a * max(distance_m - 1.0, 0.0)
    return LinkBudget(
        freq_hz=freq_hz,
        distance_m=distance_m,
        required_at_animal_db=need,
        spreading_db=spread,
        absorption_db=absorb,
        required_at_1m_db=need + spread + absorb - directivity_gain_db,
        absorption_model=model,
        alpha_db_per_m=a,
        caveat=extrapolation_warning(freq_hz, model),
        ambient_spl_db=atm.ambient_spl_db,
        directivity_gain_db=directivity_gain_db,
    )


def max_effective_range_m(
    freq_hz: float,
    atm: Atmosphere,
    emitter_cap_db: float,
    model: Model = "iso9613",
    directivity_gain_db: float = 0.0,
    margin_db: float | None = None,
    resolution_m: float = 0.25,
    search_limit_m: float = 200.0,
) -> float:
    """
    Furthest distance at which the animal still receives a detectable level
    without the emitter exceeding its welfare cap.

    This is the number that kills the 'ultrasonic wall across a highway'
    fantasy, and it is computed rather than asserted.
    """
    best = 0.0
    d = 1.0
    while d <= search_limit_m:
        lb = link_budget(freq_hz, d, atm, model, directivity_gain_db, margin_db)
        if lb.required_at_1m_db <= emitter_cap_db:
            best = d
        else:
            break
        d += resolution_m
    return best


# ---------------------------------------------------------------------------
# Frequency selection
# ---------------------------------------------------------------------------


def human_audibility_risk(freq_hz: float) -> float:
    """
    Probability that a nearby adult perceives the carrier, 0..1.

    HEURISTIC. OSHA (R13) states the audibility limit is ~15-20 kHz and varies
    between individuals and with age, but publishes no population curve, so we
    fit a logistic through those two anchor points. Labelled as ours wherever
    it is displayed; it never authorises emission, it only restricts it.
    """
    lo = ev.get("human_audibility_low_hz")
    hi = ev.get("human_audibility_high_hz")
    midpoint = (lo + hi) / 2.0
    steepness = 6.0 / max(hi - lo, 1.0)
    return 1.0 / (1.0 + math.exp(steepness * (freq_hz - midpoint)))


def cattle_sensitivity_penalty_db(freq_hz: float) -> float:
    """
    Extra SPL needed near the top of the audiogram, in dB.

    HEURISTIC shape. R1/R3 establish that sensitivity falls steeply toward the
    35 kHz endpoint and varies by individual and breed, but do not publish a
    usable band-edge curve, so we model the roll-off as rising quadratically
    from zero at 22 kHz to the endpoint. Always applied as a PENALTY, so the
    error direction is conservative.
    """
    band_lo = ev.get("experimental_band_low_hz")
    edge = ev.get("cattle_hearing_high_hz")
    if freq_hz <= band_lo:
        return 0.0
    frac = min((freq_hz - band_lo) / (edge - band_lo), 1.5)
    return 18.0 * frac * frac


@dataclass
class FrequencyCandidate:
    freq_hz: float
    effective_range_m: float
    required_at_1m_db: float
    human_risk: float
    sensitivity_penalty_db: float
    alpha_db_per_m: float
    wavelength_cm: float
    feasible: bool
    reject_reason: str | None

    def as_dict(self) -> dict:
        d = asdict(self)
        d["freq_khz"] = round(self.freq_hz / 1000.0, 1)
        return d


def sweep_frequencies(
    atm: Atmosphere,
    target_distance_m: float,
    emitter_cap_db: float,
    model: Model = "iso9613",
    directivity_gain_db: float = 0.0,
    lo_hz: float = 18_000.0,
    hi_hz: float = 36_000.0,
    step_hz: float = 500.0,
    max_human_risk: float | None = None,
    allow_below_band: bool = False,
) -> list[FrequencyCandidate]:
    """
    Evaluate every candidate carrier against the four hard constraints:
    reach the animal, stay under the welfare cap, stay inaudible to people,
    and stay inside the documented experimental band.
    """
    risk_cap: float = (
        float(ev.get("max_human_audibility_risk"))
        if max_human_risk is None
        else max_human_risk
    )
    max_human_risk = risk_cap
    band_floor: float = float(ev.get("experimental_band_low_hz"))
    band_ceiling: float = float(ev.get("experimental_band_high_hz"))
    enforce_floor = ev.get("enforce_band_floor") and not allow_below_band

    out: list[FrequencyCandidate] = []
    f = lo_hz
    while f <= hi_hz:
        penalty = cattle_sensitivity_penalty_db(f)
        lb = link_budget(f, target_distance_m, atm, model, directivity_gain_db)
        required = lb.required_at_1m_db + penalty
        risk = human_audibility_risk(f)
        rng = max_effective_range_m(
            f, atm, emitter_cap_db - penalty, model, directivity_gain_db
        )

        reason = None
        if enforce_floor and f < band_floor:
            reason = (
                f"below the documented experimental band floor "
                f"({band_floor / 1000:.0f} kHz); requires an explicit override"
            )
        elif enforce_floor and f > band_ceiling:
            reason = (
                f"above the documented experimental band ceiling "
                f"({band_ceiling / 1000:.0f} kHz); cattle sensitivity falls and "
                f"range collapses under absorption"
            )
        elif risk > max_human_risk:
            reason = f"human audibility risk {risk:.1%} exceeds {max_human_risk:.1%}"
        elif required > emitter_cap_db:
            reason = (
                f"needs {required:.0f} dB @1m, cap is {emitter_cap_db:.0f} dB "
                f"(short by {required - emitter_cap_db:.0f} dB)"
            )
        elif f > ev.get("cattle_hearing_high_hz"):
            reason = "above the cattle audiogram endpoint"

        out.append(FrequencyCandidate(
            freq_hz=f,
            effective_range_m=rng,
            required_at_1m_db=required,
            human_risk=risk,
            sensitivity_penalty_db=penalty,
            alpha_db_per_m=alpha(f, atm, model),
            wavelength_cm=wavelength_cm(f, atm),
            feasible=reason is None,
            reject_reason=reason,
        ))
        f += step_hz
    return out


def select_carrier(
    atm: Atmosphere,
    target_distance_m: float,
    emitter_cap_db: float,
    model: Model = "iso9613",
    directivity_gain_db: float = 0.0,
    max_human_risk: float | None = None,
    allow_below_band: bool = False,
) -> tuple[FrequencyCandidate | None, list[FrequencyCandidate]]:
    """
    Pick the carrier with the largest safety margin, or return None.

    Returning None is a first-class outcome: it means physics says this
    geometry cannot be served inside the welfare envelope, and the site must
    escalate to a human instead of turning the volume up.
    """
    sweep = sweep_frequencies(
        atm, target_distance_m, emitter_cap_db, model,
        directivity_gain_db,
        max_human_risk=max_human_risk,
        allow_below_band=allow_below_band,
    )
    feasible = [c for c in sweep if c.feasible]
    if not feasible:
        return None, sweep
    best = max(feasible, key=lambda c: (emitter_cap_db - c.required_at_1m_db))
    return best, sweep


def model_disagreement(freq_hz: float, distance_m: float, atm: Atmosphere) -> dict:
    """Quantify how far apart the two absorption models are. Reported, never hidden."""
    iso = total_loss_db(distance_m, freq_hz, atm, "iso9613")
    ls = total_loss_db(distance_m, freq_hz, atm, "lawrence_simmons")
    return {
        "freq_khz": round(freq_hz / 1000.0, 2),
        "distance_m": distance_m,
        "iso9613_total_loss_db": round(iso, 2),
        "lawrence_simmons_total_loss_db": round(ls, 2),
        "disagreement_db": round(abs(iso - ls), 2),
        "pessimistic_model": "iso9613" if iso > ls else "lawrence_simmons",
        "policy": (
            "Range decisions use the pessimistic model; exposure decisions use "
            "the optimistic model. Both errors then fall on the safe side."
        ),
    }
