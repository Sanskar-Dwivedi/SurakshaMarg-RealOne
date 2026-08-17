"""
Road occupancy and violation watch.

Two questions this answers that the cattle governor does not:

  1. How many people are standing on the carriageway, per unit area?
  2. Is a vehicle doing something a camera can actually evidence - travelling
     against the flow, stopped in a live lane, or a person walking in one?

WHAT A CAMERA CAN AND CANNOT ESTABLISH
--------------------------------------
It cannot establish that anything is *illegal*. Legality is a judgement about
intent, permits, exemptions and local rules, none of which are in the frame. An
ambulance on the wrong side of the road is doing the right thing; a broken-down
car stopped in a lane is unlucky, not criminal.

So nothing here decides legality. Each detector reports a geometric fact with a
duration attached - "this vehicle's ground track opposed the flow direction for
4.2 seconds" - and that fact is what gets logged, warned about and escalated. A
person reads it and decides what it means.

WHY THERE IS NO AUTOMATIC REPORT TO AUTHORITIES
-----------------------------------------------
Because a false positive here accuses someone. The detectors below run on a
monocular camera with a flat-ground assumption and a +/-20% range error, over
a tracker that swaps identities when boxes overlap. That error rate is fine for
"warn the road" and completely unfit for "report this vehicle".

The governor already has the right pattern for this and it is followed exactly:
when it runs out of confidence it does not act harder, it escalates to a human
(`ESCALATED -> traffic warning + human dispatch`). An Incident here therefore
ends in an operator's queue with its evidence attached. `authority_notified` is
a field only a person may set, for the same reason `first_party_verified` in
the evidence registry is - a machine setting it would be the whole point of the
field going missing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence

from .detect import VEHICLE_ROLES, Site, Track, point_in_polygon

# Geometric events this module is willing to assert. Deliberately narrow: each
# one is a statement about pixels and seconds, not about the law.
WRONG_WAY = "vehicle-against-flow"
STOPPED_IN_LANE = "vehicle-stopped-in-lane"
PERSON_IN_LANE = "person-on-carriageway"

# Imported rather than restated: when a non-COCO detector adds a class the
# governor knows about - autorickshaw, tractor, cart - the violation watch
# must see it too, or it silently stops watching most of an Indian road.
VEHICLE_LABELS = VEHICLE_ROLES

# Crowding bands, in people per 100 m2 of carriageway.
#
# These are presentation bands, not a safety threshold, and they are graded
# HEURISTIC for that reason: they were chosen so the three states are visually
# distinct on the dashboard, not derived from a crowd-dynamics source. Do not
# cite them. Fruin's level-of-service work is the thing to calibrate against if
# this ever needs to mean something.
CROWD_BANDS = ((2.0, "clear"), (8.0, "busy"), (float("inf"), "crowded"))


def polygon_area_m2(poly_m: Sequence[tuple[float, float]]) -> float:
    """Shoelace area of a polygon already projected to metric ground coords."""
    n = len(poly_m)
    if n < 3:
        return 0.0
    total = 0.0
    for i in range(n):
        x1, z1 = poly_m[i]
        x2, z2 = poly_m[(i + 1) % n]
        total += x1 * z2 - x2 * z1
    return abs(total) / 2.0


@dataclass(frozen=True)
class CrowdReading:
    """How many people are on the carriageway, and how tightly packed."""

    count: int
    area_m2: float
    per_100m2: float
    level: str

    def as_dict(self) -> dict:
        return {
            "count": self.count,
            "area_m2": round(self.area_m2, 1),
            "per_100m2": round(self.per_100m2, 2),
            "level": self.level,
        }


@dataclass
class Event:
    """
    One geometric fact, with how long it has held.

    `warned` and `escalated` are latches: an event that is warned about once
    does not re-warn every frame, or the speaker never stops and the operator's
    queue fills with the same vehicle a hundred times.
    """

    kind: str
    track_id: str
    label: str
    first_seen_s: float
    last_seen_s: float
    detail: str = ""
    warned: bool = False
    escalated: bool = False

    @property
    def duration_s(self) -> float:
        return max(0.0, self.last_seen_s - self.first_seen_s)

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "track_id": self.track_id,
            "label": self.label,
            "duration_s": round(self.duration_s, 2),
            "detail": self.detail,
            "warned": self.warned,
            "escalated": self.escalated,
        }


@dataclass
class Incident:
    """
    An event that outlived its warning, packaged for a human.

    Nothing in this module ever sets `authority_notified`. It exists so the
    dashboard can show that the step happened and who did it, and so an audit
    can tell an automated report from a human one. If a future version wires a
    machine into that field, the distinction this whole module rests on is gone.
    """

    kind: str
    track_id: str
    label: str
    raised_at_s: float
    duration_s: float
    detail: str
    evidence_frame: int
    authority_notified: bool = False        # only a person may set this
    notified_by: str = ""

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "track_id": self.track_id,
            "label": self.label,
            "raised_at_s": round(self.raised_at_s, 2),
            "duration_s": round(self.duration_s, 2),
            "detail": self.detail,
            "evidence_frame": self.evidence_frame,
            "authority_notified": self.authority_notified,
            "notified_by": self.notified_by,
        }


@dataclass
class RoadWatch:
    """
    Per-frame occupancy and violation watch for one site.

    Thresholds are all durations rather than instants, because every one of
    these events has a benign one-frame version: a tracker id-swap can reverse
    an apparent direction, a car at a light is stopped for a moment, and a
    pedestrian crossing legitimately is in the lane for a second or two. The
    duration is what separates the event from the noise.
    """

    site: Site
    flow_dz: float = 1.0            # +1 traffic recedes from camera, -1 approaches
    confirm_s: float = 1.5          # hold before the event is believed at all
    warn_after_s: float = 2.5       # hold before the speaker says anything
    escalate_after_s: float = 8.0   # hold before a human is asked to look
    stopped_speed_ms: float = 0.6   # below this counts as stopped
    min_speed_ms: float = 1.0       # below this, direction is meaningless noise
    speed_window: int = 6           # trailing points used for speed and direction

    events: dict[tuple[str, str], Event] = field(default_factory=dict)
    incidents: list[Incident] = field(default_factory=list)

    # (kind, track_id) whose condition actually held on the current frame.
    # Rebuilt every step; see the note in `step` for why presence of the track
    # is not enough.
    _fired: set[tuple[str, str]] = field(default_factory=set, repr=False)

    # -- geometry ------------------------------------------------------------

    def _carriageway_m(self) -> list[tuple[float, float]]:
        return [self.site.ground_xz(p) for p in self.site.carriageway]

    def carriageway_area_m2(self) -> float:
        return polygon_area_m2(self._carriageway_m())

    def on_carriageway(self, track: Track) -> bool:
        """Foot point, not centroid: a tall box's centre floats above the road."""
        return point_in_polygon(track.foot_point, self.site.carriageway)

    def _window(self, track: Track) -> list[tuple[float, float]]:
        """
        The trailing slice of history that speed and direction are read from.

        Bounded on purpose. `Track.history` is owned by the caller's tracker and
        may hold the whole life of the track, and measuring across all of it
        gives a lifetime average: a vehicle that drove in and then parked keeps
        reporting the speed of its arrival, so it never registers as stopped.
        A trailing window answers "what is it doing now", which is the only
        question any of these detectors is asking.
        """
        return list(track.history[-max(2, self.speed_window):])

    def ground_speed_ms(self, track: Track, fps: float) -> float:
        """
        Track speed in m/s, measured on the ground plane rather than in pixels.

        Pixel speed is unusable for a threshold because perspective makes the
        same vehicle move an order of magnitude more pixels near the camera
        than at the horizon. Both endpoints are projected first.
        """
        if len(track.history) < 2 or fps <= 0:
            return 0.0
        pts = self._window(track)
        a = self.site.ground_xz(pts[0])
        b = self.site.ground_xz(pts[-1])
        span = (len(pts) - 1) / fps
        if span <= 0:
            return 0.0
        return math.hypot(b[0] - a[0], b[1] - a[1]) / span

    # -- readings ------------------------------------------------------------

    def crowd(self, tracks: Iterable[Track]) -> CrowdReading:
        """People per 100 m2 of carriageway."""
        count = sum(1 for t in tracks if t.label == "person" and self.on_carriageway(t))
        area = self.carriageway_area_m2()
        per = (count / area * 100.0) if area > 0 else 0.0
        level = next(name for cap, name in CROWD_BANDS if per < cap)
        return CrowdReading(count=count, area_m2=area, per_100m2=per, level=level)

    def _observe(self, kind: str, track: Track, now_s: float, detail: str) -> None:
        key = (kind, track.track_id)
        self._fired.add(key)
        ev = self.events.get(key)
        if ev is None:
            self.events[key] = Event(
                kind=kind, track_id=track.track_id, label=track.label,
                first_seen_s=now_s, last_seen_s=now_s, detail=detail,
            )
        else:
            ev.last_seen_s = now_s
            ev.detail = detail

    def _check_wrong_way(self, track: Track, now_s: float, fps: float) -> None:
        if track.label not in VEHICLE_LABELS or not self.on_carriageway(track):
            return
        speed = self.ground_speed_ms(track, fps)
        if speed < self.min_speed_ms:
            return          # too slow for a direction to mean anything
        pts = self._window(track)
        a = self.site.ground_xz(pts[0])
        b = self.site.ground_xz(pts[-1])
        travelled_dz = b[1] - a[1]
        if travelled_dz * self.flow_dz < 0:
            self._observe(WRONG_WAY, track, now_s,
                          f"ground track opposed flow at {speed:.1f} m/s")

    def _check_stopped(self, track: Track, now_s: float, fps: float) -> None:
        if track.label not in VEHICLE_LABELS or not self.on_carriageway(track):
            return
        if len(track.history) < 2:
            return          # a brand-new track has no speed, not zero speed
        speed = self.ground_speed_ms(track, fps)
        if speed < self.stopped_speed_ms:
            self._observe(STOPPED_IN_LANE, track, now_s,
                          f"stationary in a live lane at {speed:.2f} m/s")

    def _check_person(self, track: Track, now_s: float) -> None:
        if track.label == "person" and self.on_carriageway(track):
            self._observe(PERSON_IN_LANE, track, now_s, "on the carriageway")

    # -- the frame step ------------------------------------------------------

    def step(self, tracks: Sequence[Track], now_s: float, fps: float,
             frame_index: int) -> dict:
        """
        Advance one frame. Returns what to warn about and what to escalate.

        The caller owns the speaker and the dashboard; this returns decisions,
        it does not perform them. Same split as the governor: the thing that
        decides is not the thing that emits.
        """
        self._fired = set()
        for t in tracks:
            self._check_wrong_way(t, now_s, fps)
            self._check_stopped(t, now_s, fps)
            self._check_person(t, now_s)

        # Drop events whose condition stopped holding.
        #
        # This keys on whether the CONDITION fired this frame, not on whether
        # the track is still visible. An earlier version kept any event whose
        # track was present, so a car that stopped and then drove away stayed
        # listed as stopped for as long as it remained in shot - and worse, if
        # it stopped again later, `last_seen_s` advanced against the original
        # `first_seen_s`, so the duration jumped straight past the escalation
        # threshold and put a human on a car that had just braked twice.
        for key in [k for k in self.events if k not in self._fired]:
            del self.events[key]

        warn: list[Event] = []
        escalate: list[Incident] = []
        for ev in self.events.values():
            if ev.duration_s < self.confirm_s:
                continue
            if not ev.warned and ev.duration_s >= self.warn_after_s:
                ev.warned = True
                warn.append(ev)
            if not ev.escalated and ev.duration_s >= self.escalate_after_s:
                ev.escalated = True
                inc = Incident(
                    kind=ev.kind, track_id=ev.track_id, label=ev.label,
                    raised_at_s=now_s, duration_s=ev.duration_s,
                    detail=ev.detail, evidence_frame=frame_index,
                )
                self.incidents.append(inc)
                escalate.append(inc)

        return {
            "crowd": self.crowd(tracks).as_dict(),
            "active": [e.as_dict() for e in self.events.values()
                       if e.duration_s >= self.confirm_s],
            "warn": [e.as_dict() for e in warn],
            "escalate": [i.as_dict() for i in escalate],
        }

    # -- the human step ------------------------------------------------------

    def mark_notified(self, incident: Incident, person: str) -> Incident:
        """
        Record that a named person forwarded an incident. Refuses a blank name,
        because an unattributed notification is indistinguishable from an
        automatic one, which is the exact thing this module exists to prevent.
        """
        if not person.strip():
            raise ValueError("a notification needs the name of the person making it")
        incident.authority_notified = True
        incident.notified_by = person.strip()
        return incident
