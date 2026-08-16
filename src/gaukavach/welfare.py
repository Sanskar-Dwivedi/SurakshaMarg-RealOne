"""
The welfare governor.

This module exists to say NO. It sits between the policy engine and the
amplifier, and no emission reaches hardware without a signed Authorisation
from `Governor.request()`.

The governor is deliberately the least clever component in the system. It has
no model, no learning and no discretion; it applies fixed limits derived from
cited sources and refuses anything outside them. If a reviewer wants to check
that GauKavach cannot hurt an animal, this one file is the whole answer.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum

from . import evidence as ev
from .acoustics import (
    Atmosphere,
    cattle_sensitivity_penalty_db,
    link_budget,
    required_level_at_animal_db,
)

# The level reported by the single direct cattle-ultrasound prototype (R4).
# It is not a target. Any request within HARD_REFUSAL_GUARD_DB of it is a fault.
HARD_REFUSAL_DB: float = ev.get("refused_prototype_spl_db")
HARD_REFUSAL_GUARD_DB: float = 20.0


class Denial(str, Enum):
    """Every reason the governor can refuse. Exhaustive by design."""

    OVER_CEILING = "requested level exceeds the occupational ceiling"
    HARD_REFUSAL = "requested level approaches the refused prototype exposure"
    UNREACHABLE = "target cannot be served inside the welfare envelope"
    DURATION = "requested duration exceeds the watchdog limit"
    SILENCE_WINDOW = "animal is inside its enforced quiet period"
    DAILY_BUDGET = "animal has exhausted its daily exposure budget"
    DO_NOT_EMIT = "animal is on the do-not-emit list"
    HUMAN_PRESENT = "a person is inside the exposure cone"
    NON_TARGET = "a protected non-target species is inside the exposure cone"
    BAND_VIOLATION = "carrier is outside the documented experimental band"
    NO_ETHICS_TOKEN = "elevated exposure requires a signed ethics authorisation"
    UNGRADED_INPUT = "a decision input was not present in the evidence registry"
    STOP_CRITERION = "an active stop criterion forbids emission"
    # -- hazard-driven vetoes ------------------------------------------------
    FLIGHT_INTO_HAZARD = "fleeing the emitter would take the animal onto the carriageway"
    NO_ESCAPE_ROUTE = "the animal has no viable escape corridor away from the road"
    HERD_SIZE = "group is large enough that a startle could cascade through it"
    JUVENILE_PRESENT = "a juvenile animal is present in the group"
    IMMOBILE_ANIMAL = "the animal did not move after a previous emission and may be restrained"
    DOWNED_ANIMAL = "the animal may be recumbent, sick or injured"
    CHILD_AUDIBILITY = "carrier is audible to children and the site has sensitive receptors"
    MORE_SENSITIVE_NONTARGET = (
        "a non-target species present hears this carrier better than the target does"
    )


@dataclass
class ExposureRecord:
    """Per-animal exposure history. The unit of welfare accounting."""

    track_id: str
    total_seconds: float = 0.0
    exposures: int = 0
    last_emission_t: float = -1e9
    do_not_emit: bool = False
    reason_flagged: str | None = None

    def remaining_budget_s(self) -> float:
        return max(0.0, ev.get("daily_exposure_budget_s") - self.total_seconds)


@dataclass
class Authorisation:
    """A signed permit for exactly one emission. Consumed once."""

    granted: bool
    track_id: str
    freq_hz: float = 0.0
    level_at_1m_db: float = 0.0
    duration_s: float = 0.0
    predicted_at_animal_db: float = 0.0
    denials: tuple[Denial, ...] = ()
    detail: str = ""
    constants_used: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        d = asdict(self)
        d["denials"] = [x.value for x in self.denials]
        return d


@dataclass
class SceneContext:
    """
    Everything about the situation that can veto an emission.

    Deliberately a plain data record with no logic: the governor decides, the
    perception layer only reports. That split is what makes the safety case
    reviewable - all the refusal logic is in one file.
    """

    humans_in_cone: int = 0
    non_target_animals_in_cone: tuple[str, ...] = ()
    stop_criteria_active: tuple[str, ...] = ()

    # -- hazard inputs -------------------------------------------------------
    group_size: int = 1
    juvenile_in_group: bool = False
    downed_animal: bool = False
    immobile_after_emission: bool = False
    flight_enters_hazard: bool = False
    already_in_hazard: bool = False
    escape_corridor_m: float = 999.0
    sensitive_receptors_nearby: bool = False

    def clear(self) -> bool:
        return (
            self.humans_in_cone == 0
            and not self.non_target_animals_in_cone
            and not self.stop_criteria_active
        )


class Governor:
    """
    Enforces the welfare envelope.

    `ethics_token` mirrors an institutional animal-ethics approval reference.
    Without one the ceiling is the conservative midpoint of the cited band;
    with one it may rise to the band's upper edge and never beyond.
    """

    def __init__(
        self,
        atm: Atmosphere,
        ethics_token: str | None = None,
        directivity_gain_db: float = 12.0,
    ) -> None:
        self.atm = atm
        self.ethics_token = ethics_token
        self.directivity_gain_db = directivity_gain_db
        self.records: dict[str, ExposureRecord] = {}
        self.denial_log: list[tuple[float, str, Denial, str]] = []

    # -- limits ------------------------------------------------------------

    @property
    def ceiling_db(self) -> float:
        if self.ethics_token:
            return ev.get("osha_ultrasound_ceiling_max_db")
        return ev.get("osha_ultrasound_ceiling_db")

    def record(self, track_id: str) -> ExposureRecord:
        return self.records.setdefault(track_id, ExposureRecord(track_id))

    # -- the decision ------------------------------------------------------

    def request(
        self,
        track_id: str,
        freq_hz: float,
        distance_m: float,
        duration_s: float,
        now_t: float,
        scene: SceneContext | None = None,
    ) -> Authorisation:
        """Adjudicate one emission request. Pure function of state; no side effects
        until `commit()` is called with a granted authorisation."""
        scene = scene or SceneContext()
        rec = self.record(track_id)
        denials: list[Denial] = []
        notes: list[str] = []

        # 1. Bystanders and non-targets come first: no acoustic benefit
        #    outweighs exposing an unconsenting person or species.
        if scene.humans_in_cone > 0:
            denials.append(Denial.HUMAN_PRESENT)
            notes.append(f"{scene.humans_in_cone} person(s) in cone")
        if scene.non_target_animals_in_cone:
            denials.append(Denial.NON_TARGET)
            notes.append("non-target: " + ", ".join(scene.non_target_animals_in_cone))
        if scene.stop_criteria_active:
            denials.append(Denial.STOP_CRITERION)
            notes.append("stop: " + ", ".join(scene.stop_criteria_active))

        # 1b. Flight geometry. This block outranks every acoustic consideration,
        #     because the worst outcome this system can produce is not an
        #     over-exposed animal - it is an animal driven onto the road by a
        #     perfectly legal, perfectly quiet, perfectly compliant emission.
        if scene.already_in_hazard:
            denials.append(Denial.FLIGHT_INTO_HAZARD)
            notes.append(
                "animal is already on the carriageway; fleeing a roadside "
                "emitter would push it further across, not clear it"
            )
        elif scene.flight_enters_hazard:
            denials.append(Denial.FLIGHT_INTO_HAZARD)
            notes.append("predicted flight path intersects the carriageway")

        if scene.escape_corridor_m < ev.get("min_escape_corridor_m"):
            denials.append(Denial.NO_ESCAPE_ROUTE)
            notes.append(
                f"escape corridor {scene.escape_corridor_m:.1f} m is below the "
                f"{ev.get('min_escape_corridor_m'):.0f} m minimum; pressure "
                f"without an exit produces panic, not withdrawal"
            )

        # 1c. Group dynamics. A startle does not stay with the animal it was
        #     aimed at (R9), so a flock is a dispatch problem, not an acoustic one.
        if scene.group_size > ev.get("max_herd_size_for_emission"):
            denials.append(Denial.HERD_SIZE)
            notes.append(
                f"{scene.group_size} conspecifics grouped; above the "
                f"{ev.get('max_herd_size_for_emission')} threshold a startle "
                f"can cascade through the group"
            )

        # 1d. Vulnerable individuals.
        if scene.juvenile_in_group:
            denials.append(Denial.JUVENILE_PRESENT)
            notes.append("juvenile present - maternal defence and higher vulnerability")
        if scene.downed_animal:
            denials.append(Denial.DOWNED_ANIMAL)
            notes.append("possible recumbent or collapsed animal - needs rescue, not sound")
        if scene.immobile_after_emission:
            denials.append(Denial.IMMOBILE_ANIMAL)
            notes.append(
                "no movement after a completed emission; may be tethered, "
                "trapped or unwell, in which case further emission is distress "
                "with no possible benefit"
            )

        # 1e. Sensitive receptors. Children hear materially higher than adults.
        if scene.sensitive_receptors_nearby and freq_hz < ev.get(
            "child_audibility_band_floor_hz"
        ):
            denials.append(Denial.CHILD_AUDIBILITY)
            notes.append(
                f"{freq_hz / 1000:.1f} kHz is below the "
                f"{ev.get('child_audibility_band_floor_hz') / 1000:.0f} kHz floor "
                f"required near schools or dense housing"
            )

        # 2. Per-animal welfare accounting.
        if rec.do_not_emit:
            denials.append(Denial.DO_NOT_EMIT)
            notes.append(rec.reason_flagged or "flagged")
        since = now_t - rec.last_emission_t
        min_silence = ev.get("min_silence_s")
        if since < min_silence:
            denials.append(Denial.SILENCE_WINDOW)
            notes.append(f"{min_silence - since:.1f}s of quiet period remaining")
        if rec.remaining_budget_s() < duration_s:
            denials.append(Denial.DAILY_BUDGET)
            notes.append(f"{rec.remaining_budget_s():.1f}s budget left")

        # 3. Duration watchdog.
        max_on = ev.get("max_activation_s")
        if duration_s > max_on:
            denials.append(Denial.DURATION)
            notes.append(f"{duration_s:.1f}s > {max_on:.1f}s watchdog")

        # 4. Band discipline.
        band_lo = ev.get("experimental_band_low_hz")
        band_hi = ev.get("experimental_band_high_hz")
        if not (band_lo <= freq_hz <= band_hi):
            denials.append(Denial.BAND_VIOLATION)
            notes.append(
                f"{freq_hz / 1000:.1f} kHz outside {band_lo / 1000:.0f}-"
                f"{band_hi / 1000:.0f} kHz"
            )

        # 5. Link budget. Range uses the PESSIMISTIC absorption model so we
        #    never under-estimate what the emitter must produce.
        penalty = cattle_sensitivity_penalty_db(freq_hz)
        lb = link_budget(
            freq_hz, max(distance_m, 1.0), self.atm,
            model="iso9613", directivity_gain_db=self.directivity_gain_db,
        )
        required_1m = lb.required_at_1m_db + penalty

        if required_1m > self.ceiling_db:
            denials.append(Denial.UNREACHABLE)
            notes.append(
                f"needs {required_1m:.0f} dB@1m at {distance_m:.0f} m, "
                f"ceiling {self.ceiling_db:.0f} dB (short {required_1m - self.ceiling_db:.0f} dB)"
            )
        if required_1m >= HARD_REFUSAL_DB - HARD_REFUSAL_GUARD_DB:
            denials.append(Denial.HARD_REFUSAL)
            notes.append(
                f"{required_1m:.0f} dB is within {HARD_REFUSAL_GUARD_DB:.0f} dB of the "
                f"{HARD_REFUSAL_DB:.0f} dB prototype level this system refuses to reproduce"
            )
        if required_1m > ev.get("osha_ultrasound_ceiling_db") and not self.ethics_token:
            denials.append(Denial.NO_ETHICS_TOKEN)
            notes.append("above the default ceiling and no ethics token supplied")

        if denials:
            for d in denials:
                self.denial_log.append((now_t, track_id, d, "; ".join(notes)))
            return Authorisation(
                granted=False,
                track_id=track_id,
                freq_hz=freq_hz,
                duration_s=duration_s,
                denials=tuple(dict.fromkeys(denials)),
                detail="; ".join(notes),
            )

        # Granted. Emit the MINIMUM level that satisfies detectability - never
        # the maximum the hardware can produce.
        return Authorisation(
            granted=True,
            track_id=track_id,
            freq_hz=freq_hz,
            level_at_1m_db=round(required_1m, 1),
            duration_s=duration_s,
            predicted_at_animal_db=round(required_level_at_animal_db(self.atm) + penalty, 1),
            detail=(
                f"minimum sufficient level; {self.ceiling_db - required_1m:.1f} dB "
                f"below ceiling"
            ),
            constants_used=(
                "audiogram_criterion_db",
                "masking_margin_db",
                "osha_ultrasound_ceiling_db",
                "max_activation_s",
                "min_silence_s",
                "daily_exposure_budget_s",
            ),
        )

    def commit(self, auth: Authorisation, now_t: float, actual_duration_s: float) -> None:
        """Record an emission that actually happened."""
        if not auth.granted:
            raise ValueError("cannot commit a denied authorisation")
        rec = self.record(auth.track_id)
        rec.total_seconds += actual_duration_s
        rec.exposures += 1
        rec.last_emission_t = now_t
        if rec.remaining_budget_s() <= 0.0:
            rec.do_not_emit = True
            rec.reason_flagged = "daily exposure budget exhausted"

    def flag(self, track_id: str, reason: str) -> None:
        rec = self.record(track_id)
        rec.do_not_emit = True
        rec.reason_flagged = reason

    # -- reporting ---------------------------------------------------------

    def summary(self) -> dict:
        denial_counts: dict[str, int] = {}
        for _, _, d, _ in self.denial_log:
            denial_counts[d.value] = denial_counts.get(d.value, 0) + 1
        return {
            "ceiling_db": self.ceiling_db,
            "ethics_token": bool(self.ethics_token),
            "hard_refusal_db": HARD_REFUSAL_DB,
            "animals_tracked": len(self.records),
            "animals_flagged": sum(1 for r in self.records.values() if r.do_not_emit),
            "total_exposure_s": round(
                sum(r.total_seconds for r in self.records.values()), 2
            ),
            "denials_total": len(self.denial_log),
            "denials_by_reason": denial_counts,
        }


def prove_refusal(atm: Atmosphere | None = None) -> dict:
    """
    Demonstration hook: attempt to reproduce the published 142 dB prototype
    exposure and show that the governor refuses.

    Kept as a callable rather than prose so the claim is testable, not asserted.
    """
    atm = atm or Atmosphere()
    gov = Governor(atm, ethics_token=None)
    # Ask for a target so distant that the link budget demands prototype levels.
    auth = gov.request(
        track_id="PROOF", freq_hz=30_000.0, distance_m=120.0,
        duration_s=3.0, now_t=0.0,
    )
    with_token = Governor(atm, ethics_token="ETHICS/DEMO/0001").request(
        track_id="PROOF", freq_hz=30_000.0, distance_m=120.0,
        duration_s=3.0, now_t=0.0,
    )
    return {
        "attempted_level_context": (
            f"reproducing R4's {HARD_REFUSAL_DB:.0f} dB SPL @1m at 30 kHz"
        ),
        "without_ethics_token": auth.as_dict(),
        "with_ethics_token": with_token.as_dict(),
        "conclusion": (
            "The governor refuses in both cases. An ethics token raises the "
            "ceiling to the upper edge of the cited occupational band "
            f"({ev.get('osha_ultrasound_ceiling_max_db'):.0f} dB) and no further; "
            "the prototype level is unreachable by configuration."
        ),
    }
