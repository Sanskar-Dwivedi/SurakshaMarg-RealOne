"""
The closed-loop policy engine.

Implements the seven-stage architecture from the report - Detect, Classify,
Decide, Emit, Observe, Stop, Log - as an explicit state machine, with one
addition the report implies but does not name: ESCALATE.

Escalation is the load-bearing design decision of this whole project. R5
established that acoustic cues do not give stock-proof containment, so a system
that keeps emitting until the animal moves is arguing with the evidence. This
engine instead has a defined give-up point, after which it stops making noise
and hands the incident to a human while keeping the road protected by traffic
control rather than by sound.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from enum import Enum

from . import evidence as ev
from .acoustics import Atmosphere, select_carrier
from .detect import (
    Site,
    Track,
    displacement_m,
    is_downed,
    is_juvenile,
    social_group_size,
    split_by_role,
)
from .emitter import PatternScheduler, build_emission
from .ledger import Ledger
from .species import SPECIES, TARGET_KEY, species_for_label
from .traffic import signal_response_plan
from .twin import BehaviourTwin, received_level_db
from .welfare import Denial, Governor, SceneContext


class State(str, Enum):
    IDLE = "idle"
    TRACKING = "tracking"
    AUTHORISING = "authorising"
    EMITTING = "emitting"
    OBSERVING = "observing"
    ESCALATED = "escalated"
    INHIBITED = "inhibited"


class Outcome(str, Enum):
    """Field-test outcome codes, matching Appendix A of the report."""

    ORIENTED = "O"
    STOPPED = "S"
    TURNED = "T"
    CROSSED = "C"
    RAN = "R"
    NO_RESPONSE = "N"


@dataclass
class Incident:
    """One animal's encounter with the site, start to finish."""

    track_id: str
    opened_t: float
    state: State = State.TRACKING
    attempts: int = 0
    total_emission_s: float = 0.0
    outcomes: list[str] = field(default_factory=list)
    escalated: bool = False
    escalation_reason: str | None = None
    traffic_response_sent: bool = False
    cleared_t: float | None = None
    first_distance_m: float = 0.0

    def duration_s(self, now: float) -> float:
        return (self.cleared_t or now) - self.opened_t

    def as_dict(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value
        return d


@dataclass
class EngineConfig:
    directivity_gain_db: float = 12.0
    ethics_token: str | None = None
    max_attempts: int = 3
    observe_window_s: float = 4.0
    dry_run: bool = True  # never drive real hardware unless explicitly disabled
    # Set True when a school, clinic or dense housing is within earshot. Raises
    # the carrier floor to 25 kHz because children hear well above the adult
    # limit and a 22 kHz tone may be plainly audible to them.
    sensitive_receptors_nearby: bool = False


class PolicyEngine:
    """
    Orchestrates perception -> authorisation -> emission -> observation.

    `dry_run` defaults to True. Producing sound in the physical world is an
    opt-in, not a default, and the flag is written into every ledger record so
    a reader can always tell simulated events from real ones.
    """

    def __init__(
        self,
        site: Site,
        atm: Atmosphere,
        ledger: Ledger | None = None,
        config: EngineConfig | None = None,
        seed: int = 11,
    ) -> None:
        self.site = site
        self.atm = atm
        self.cfg = config or EngineConfig()
        self.ledger = ledger or Ledger()
        self.governor = Governor(
            atm,
            ethics_token=self.cfg.ethics_token,
            directivity_gain_db=self.cfg.directivity_gain_db,
        )
        self.scheduler = PatternScheduler(seed=seed)
        self.twin = BehaviourTwin(seed=seed)
        self.incidents: dict[str, Incident] = {}
        self.state = State.IDLE
        self.ledger.append("session_open", {
            "site": site.name,
            "atmosphere": atm.as_dict(),
            "dry_run": self.cfg.dry_run,
            "ceiling_db": self.governor.ceiling_db,
            "evidence_audit": ev.audit(),
        })

    # -- helpers -----------------------------------------------------------

    def _feasible_carriers(self, distance_m: float) -> list[float]:
        best, sweep = select_carrier(
            self.atm, distance_m, self.governor.ceiling_db,
            directivity_gain_db=self.cfg.directivity_gain_db,
        )
        if best is None:
            return []
        # Offer every feasible carrier so the scheduler can vary between them.
        return [c.freq_hz for c in sweep if c.feasible]

    def _incident(self, track: Track, now: float, distance_m: float) -> Incident:
        inc = self.incidents.get(track.track_id)
        if inc is None:
            inc = Incident(
                track_id=track.track_id, opened_t=now, first_distance_m=distance_m
            )
            self.incidents[track.track_id] = inc
            self.ledger.append("detection", {
                "track_id": track.track_id,
                "label": track.label,
                "distance_m": round(distance_m, 2),
                "conf": round(track.conf, 3),
                "position": self.site.classify_position(track.foot_point),
            })
        return inc

    # -- the loop ----------------------------------------------------------

    def step(self, tracks: list[Track], now: float) -> dict:
        """
        Advance one frame. Returns a snapshot for the dashboard.

        Pure orchestration: every limit is enforced by the governor, every
        physical number comes from the acoustics layer, every behavioural
        estimate comes from the twin with its interval attached.
        """
        roles = split_by_role(tracks)
        actions: list[dict] = []

        # Scene context is computed once and applies to every request this
        # frame: if a person is in the cone, nothing emits, full stop.
        humans_in_zone = [
            t for t in roles["human"]
            if self.site.classify_position(t.foot_point) != "outside"
        ]
        nontargets_in_zone = tuple(
            t.label for t in roles["non_target"]
            if self.site.classify_position(t.foot_point) != "outside"
        )
        # Non-target species are reported with WHY they matter, not just that
        # they are present: at 22-30 kHz most of them hear the carrier better
        # than the target does (see species.py).
        nontarget_detail: list[str] = []
        for t in roles["non_target"]:
            if self.site.classify_position(t.foot_point) == "outside":
                continue
            for prof in species_for_label(t.label):
                better = prof.hearing_high_hz > SPECIES[TARGET_KEY].hearing_high_hz
                nontarget_detail.append(
                    f"{prof.name}"
                    + (" (hears this carrier better than cattle)" if better else "")
                )
        # Vehicles were already being classified and then ignored. They are a
        # veto input: what makes a startle dangerous is not the animal, it is
        # what the animal might run into.
        vehicles_in_zone = [
            t for t in roles["vehicle"]
            if self.site.classify_position(t.foot_point) != "outside"
        ]
        scene = SceneContext(
            humans_in_cone=len(humans_in_zone),
            vehicles_in_zone=len(vehicles_in_zone),
            non_target_animals_in_cone=tuple(nontarget_detail) or nontargets_in_zone,
            sensitive_receptors_nearby=self.cfg.sensitive_receptors_nearby,
        )

        targets = [
            t for t in roles["target"]
            if self.site.classify_position(t.foot_point) != "outside"
        ]
        if not targets:
            self.state = State.IDLE
            return self._snapshot(now, tracks, actions, scene)

        self.state = State.TRACKING

        for track in targets:
            distance_m = self.site.estimate_distance_m(track.foot_point)
            track.distance_m = distance_m
            track.in_zone = True
            inc = self._incident(track, now, distance_m)

            if inc.state is State.INHIBITED:
                # A stop criterion holds this animal. That is a standing
                # refusal, not the absence of one - so it has to be said every
                # frame. Skipping silently made the panel and the ledger go
                # blank, which reads as "nothing here" rather than "refusing".
                actions.append({
                    "track_id": track.track_id, "action": "denied",
                    "reason": ("emission inhibited for this animal by an active "
                               "stop criterion"),
                    "denials": [Denial.STOP_CRITERION.value],
                })
                continue
            if inc.state is State.ESCALATED:
                # Same reasoning as INHIBITED above. Escalated means the system
                # has given up on acoustics and asked for a human; the engine
                # state stayed TRACKING and no action was emitted, so the panel
                # read "tracking, no vetoes" - indistinguishable from a quiet
                # road while a dispatch is outstanding.
                self.state = State.ESCALATED
                actions.append({
                    "track_id": track.track_id, "action": "escalate",
                    "reason": inc.escalation_reason,
                })
                continue

            position = self.site.classify_position(track.foot_point)
            approaching = self.site.approaching(track)

            # DECIDE: only act on an animal that is approaching the road, or
            # already on it. A cow standing on the verge is not a problem.
            if position == "warning" and not approaching:
                actions.append({
                    "track_id": track.track_id, "action": "monitor",
                    "reason": "in warning zone but not approaching the carriageway",
                })
                continue

            # Give-up point.
            elapsed = now - inc.opened_t
            if (
                elapsed > ev.get("escalation_timeout_s")
                or inc.attempts >= self.cfg.max_attempts
            ):
                self._escalate(
                    inc, now, track,
                    reason=(
                        f"{inc.attempts} attempt(s) over {elapsed:.0f}s did not clear "
                        f"the carriageway; acoustic deterrence is not stock-proof (R5)"
                    ),
                )
                actions.append({
                    "track_id": track.track_id, "action": "escalate",
                    "reason": inc.escalation_reason,
                })
                continue

            # Per-animal hazard assessment. Every one of these can veto, and
            # all of them are evaluated before the acoustics are even consulted.
            flight = self.site.flight_assessment(
                track.foot_point, ev.get("flight_vector_check_m")
            )
            group_n = social_group_size(
                track, targets, self.site, ev.get("herd_grouping_radius_m")
            )
            profiles = species_for_label(track.label)
            adult_h = profiles[0].typical_adult_height_m if profiles else 1.35
            juvenile = any(
                is_juvenile(t, self.site, adult_h, ev.get("juvenile_height_ratio"))
                for t in targets
                if social_group_size(t, [track], self.site,
                                     ev.get("herd_grouping_radius_m")) > 0
            )
            moved = displacement_m(track, self.site)
            track_scene = replace(
                scene,
                group_size=group_n,
                juvenile_in_group=juvenile,
                downed_animal=is_downed(track, ev.get("downed_aspect_ratio")),
                immobile_after_emission=(
                    inc.attempts > 0 and moved < ev.get("immobile_displacement_m")
                ),
                flight_enters_hazard=flight["enters_hazard"],
                already_in_hazard=flight["already_in_hazard"],
                escape_corridor_m=flight["escape_corridor_m"],
            )

            # Cooldown pre-check. The governor would refuse anyway, but asking
            # it every frame floods the ledger with identical denials and
            # buries the records that matter. Silence is the default state, so
            # it does not need to be re-litigated 5 times a second.
            rec = self.governor.record(track.track_id)
            cooling = now - rec.last_emission_t
            if cooling < ev.get("min_silence_s"):
                actions.append({
                    "track_id": track.track_id,
                    "action": "cooldown",
                    "reason": (
                        f"{ev.get('min_silence_s') - cooling:.1f}s of enforced "
                        f"quiet period remaining"
                    ),
                })
                continue

            carriers = self._feasible_carriers(distance_m)
            if not carriers:
                # Out of acoustic range is NOT an escalation - the animal may
                # still be approaching, and it would be wrong to permanently
                # give up on an incident that is about to become actionable.
                # The traffic response fires immediately regardless, because
                # warning drivers does not depend on reaching the animal.
                self._traffic_response(inc, track, distance_m, now)
                actions.append({
                    "track_id": track.track_id,
                    "action": "out_of_range",
                    "distance_m": round(distance_m, 1),
                    "reason": (
                        f"{distance_m:.0f} m is beyond the acoustic envelope; no "
                        f"carrier in the {ev.get('experimental_band_low_hz')/1000:.0f}-"
                        f"{ev.get('experimental_band_high_hz')/1000:.0f} kHz band reaches "
                        f"it within the {self.governor.ceiling_db:.0f} dB ceiling. "
                        f"Traffic warning issued; continuing to monitor."
                    ),
                })
                continue

            carrier, pattern = self.scheduler.choose(track.track_id, carriers)

            self.state = State.AUTHORISING
            auth = self.governor.request(
                track_id=track.track_id,
                freq_hz=carrier,
                distance_m=distance_m,
                duration_s=pattern.duration_s,
                now_t=now,
                scene=track_scene,
            )
            self.ledger.append("authorisation", {
                **auth.as_dict(),
                "distance_m": round(distance_m, 2),
                "pattern": pattern.as_dict(),
                "scene": asdict(track_scene),
                "flight": flight,
            })

            if not auth.granted:
                # A person in the cone must NOT latch the incident.
                #
                # It used to. The first denial with a human present pinned the
                # incident to INHIBITED, the loop then skipped that animal on
                # every later frame, and nothing cleared it when the person
                # walked away - so the scenario reported one veto and then went
                # silent for ninety-three frames, and the animal could never be
                # served again even on an empty road.
                #
                # Human presence is a live condition. It is re-evaluated every
                # frame from the scene and refuses on its own merits, exactly
                # like the non-target rule next to it. The only latching veto
                # is the panic stop criterion, which is a finding about the
                # animal rather than a passing fact about the scene.
                actions.append({
                    "track_id": track.track_id, "action": "denied",
                    "reason": auth.detail,
                    "denials": [d.value for d in auth.denials],
                })
                continue

            # EMIT (or simulate). Self-inspect the waveform first.
            wave, spectral = build_emission(carrier, pattern)
            if not spectral.passes:
                self.ledger.append("stop", {
                    "track_id": track.track_id,
                    "reason": "spectral self-check failed",
                    "spectral": spectral.as_dict(),
                })
                actions.append({
                    "track_id": track.track_id, "action": "aborted",
                    "reason": spectral.reason,
                })
                continue

            self.state = State.EMITTING
            inc.attempts += 1
            inc.total_emission_s += pattern.duration_s
            self.governor.commit(auth, now, pattern.duration_s)

            received = received_level_db(
                auth.level_at_1m_db, distance_m, carrier, self.atm
            )
            prediction = self.twin.response_probability(
                received,
                prior_exposures=self.scheduler.exposure_count(track.track_id) - 1,
                conspecific_responded=any(
                    Outcome.TURNED.value in self.incidents[o.track_id].outcomes
                    for o in targets if o.track_id != track.track_id
                    and o.track_id in self.incidents
                ),
            )

            self.ledger.append("emission", {
                "track_id": track.track_id,
                "dry_run": self.cfg.dry_run,
                "carrier_hz": carrier,
                "pattern": pattern.as_dict(),
                "level_at_1m_db": auth.level_at_1m_db,
                "predicted_received_db": round(received, 1),
                "distance_m": round(distance_m, 2),
                "samples": int(wave.size),
                "spectral": spectral.as_dict(),
                "predicted_response": prediction.as_dict(),
                "authorisation_hash_note": (
                    "level is the minimum sufficient value from the link budget, "
                    "not an operator-chosen volume"
                ),
            })
            actions.append({
                "track_id": track.track_id,
                "action": "emit",
                "carrier_khz": round(carrier / 1000.0, 1),
                "pattern": pattern.name,
                "level_at_1m_db": auth.level_at_1m_db,
                "received_db": round(received, 1),
                "p_response": prediction.p_response_median,
                "p_response_interval": [prediction.p_response_lo, prediction.p_response_hi],
            })
            self.state = State.OBSERVING

        return self._snapshot(now, tracks, actions, scene)

    def observe(self, track_id: str, outcome: Outcome, now: float, note: str = "") -> None:
        """Record what the animal actually did. The only ground truth we have."""
        inc = self.incidents.get(track_id)
        if inc is None:
            return
        inc.outcomes.append(outcome.value)
        if outcome in (Outcome.TURNED, Outcome.STOPPED):
            inc.cleared_t = now
            inc.state = State.IDLE
        if outcome == Outcome.RAN:
            # Panic is a stop criterion, not a success.
            self.governor.flag(track_id, "panic response observed - stop criterion")
            inc.state = State.INHIBITED
            self.ledger.append("stop", {
                "track_id": track_id,
                "reason": "panic/run response - emission inhibited for this animal",
                "criterion": "report section 12.2",
            })
        self.ledger.append("observation", {
            "track_id": track_id,
            "outcome": outcome.value,
            "outcome_name": outcome.name,
            "note": note,
        })

    def _traffic_response(
        self, inc: Incident, track: Track, distance_m: float, now: float
    ) -> None:
        """
        Fire the traffic-control half of the system. Idempotent per incident.

        This runs whether or not the acoustic layer can do anything, and it is
        the part of GauKavach whose mechanism is not in doubt: drivers who are
        warned about an obstruction slow down. Everything acoustic is an
        adjunct to this, never a replacement for it.
        """
        if inc.traffic_response_sent:
            return
        inc.traffic_response_sent = True
        plan = signal_response_plan(
            distance_m, self.site.speed_limit_kmh, lanes_blocked=1
        )
        self.ledger.append("traffic_response", {
            "track_id": inc.track_id,
            "trigger_distance_m": round(distance_m, 1),
            "position": self.site.classify_position(track.foot_point),
            "plan": plan,
        })

    def _escalate(self, inc: Incident, now: float, track: Track, reason: str) -> None:
        inc.state = State.ESCALATED
        inc.escalated = True
        inc.escalation_reason = reason
        self.state = State.ESCALATED
        self.ledger.append("escalation", {
            "track_id": inc.track_id,
            "reason": reason,
            "distance_m": round(track.distance_m, 2),
            "handoff": [
                "upstream variable message sign: LIVESTOCK ON ROAD",
                "signal controller: hold upstream green, extend clearance",
                "municipal dispatch ticket raised",
            ],
            "principle": (
                "The system stops making noise when noise stops being "
                "justified. Road safety is then maintained by traffic control, "
                "which is a proven mechanism, rather than by an unproven one."
            ),
        })

    def _snapshot(
        self, now: float, tracks: list[Track], actions: list[dict], scene: SceneContext
    ) -> dict:
        return {
            "t": round(now, 2),
            "state": self.state.value,
            "tracks": [t.as_dict() for t in tracks],
            "actions": actions,
            "scene": asdict(scene),
            "incidents": {k: v.as_dict() for k, v in self.incidents.items()},
            "governor": self.governor.summary(),
        }

    def close(self) -> dict:
        summary = {
            "incidents": len(self.incidents),
            "escalated": sum(1 for i in self.incidents.values() if i.escalated),
            "total_emission_s": round(
                sum(i.total_emission_s for i in self.incidents.values()), 2
            ),
            "governor": self.governor.summary(),
        }
        self.ledger.append("session_close", summary)
        return summary
