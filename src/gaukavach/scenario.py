"""
Synthetic scenario generator - the hardware-in-the-loop stand-in.

There is no transducer, no cow and no highway in this repository. Rather than
imply otherwise, this module produces clearly-labelled synthetic tracks that
exercise every branch of the policy engine, including the ones we hope never
fire in the field: a person walking into the beam, a dog in the cone, an animal
that panics, a herd that breaks through.

A demo built on this is a demo of the DECISION LOGIC, which is the part we
actually built. Any frame rendered from it is watermarked SIMULATED.
"""

from __future__ import annotations


from dataclasses import dataclass
from typing import Callable, Iterator

from .detect import Detection, SimpleTracker


@dataclass
class Actor:
    """A synthetic entity moving through the scene in pixel coordinates."""

    label: str
    start: tuple[float, float]
    end: tuple[float, float]
    t_enter: float
    t_exit: float
    box_w: float = 140.0
    box_h: float = 110.0
    conf: float = 0.88
    # Optional override: if set, the actor stops at this fraction of its path
    # (used to simulate an animal that turns away).
    stop_at_frac: float | None = None

    def position(self, t: float) -> tuple[float, float] | None:
        if t < self.t_enter or t > self.t_exit:
            return None
        frac = (t - self.t_enter) / max(self.t_exit - self.t_enter, 1e-6)
        if self.stop_at_frac is not None:
            frac = min(frac, self.stop_at_frac)
        x = self.start[0] + (self.end[0] - self.start[0]) * frac
        y = self.start[1] + (self.end[1] - self.start[1]) * frac
        return (x, y)

    def detection(self, t: float) -> Detection | None:
        pos = self.position(t)
        if pos is None:
            return None
        # Scale the box with depth so distance estimation has something to bite on.
        depth = max(pos[1] / 719.0, 0.25)
        w, h = self.box_w * depth, self.box_h * depth
        x, y = pos
        cls_id = {"cow": 19, "person": 0, "dog": 16, "car": 2}.get(self.label, 19)
        return Detection(
            cls_id=cls_id,
            label=self.label,
            conf=self.conf,
            xyxy=(x - w / 2, y - h, x + w / 2, y),
        )


@dataclass
class Scenario:
    name: str
    description: str
    actors: list[Actor]
    duration_s: float
    fps: float = 5.0
    # Called after each step so a scenario can inject observed outcomes.
    on_step: Callable[[object, float], None] | None = None

    def frames(self) -> Iterator[tuple[float, list[Detection]]]:
        n = int(self.duration_s * self.fps)
        for i in range(n):
            t = i / self.fps
            dets = [d for a in self.actors if (d := a.detection(t)) is not None]
            yield t, dets


def _cow(start, end, t0, t1, **kw) -> Actor:
    return Actor("cow", start, end, t0, t1, **kw)


SCENARIOS: dict[str, Scenario] = {}


def register(s: Scenario) -> Scenario:
    SCENARIOS[s.name] = s
    return s


register(Scenario(
    name="single-approach",
    description=(
        "One cow walks from the verge onto the carriageway. The nominal happy "
        "path: detect, authorise, emit the minimum sufficient level, observe."
    ),
    actors=[_cow((300, 340), (620, 640), 0.0, 20.0)],
    duration_s=20.0,
))

register(Scenario(
    name="person-in-cone",
    description=(
        "A cow approaches while a pedestrian is inside the exposure cone. The "
        "governor must refuse every request for as long as the person is there. "
        "This is the scenario that should be run first in any demo."
    ),
    actors=[
        _cow((300, 340), (620, 640), 0.0, 20.0),
        Actor("person", (900, 400), (500, 660), 2.0, 16.0, box_w=55, box_h=150),
    ],
    duration_s=20.0,
))

register(Scenario(
    name="non-target-dog",
    description=(
        "A stray dog shares the cone with the target animal. Dogs hear well "
        "above human range, so the system suppresses emission rather than "
        "assuming the frequency is cattle-specific."
    ),
    actors=[
        _cow((320, 350), (640, 650), 0.0, 20.0),
        Actor("dog", (820, 500), (700, 640), 1.0, 18.0, box_w=60, box_h=45),
    ],
    duration_s=20.0,
))

register(Scenario(
    name="herd-breakthrough",
    description=(
        "Four animals approach together. Social facilitation (R9) means they "
        "move as a group; the per-animal exposure budgets and the attempt cap "
        "force escalation rather than an escalating sound level."
    ),
    actors=[
        _cow((260, 340), (560, 650), 0.0, 22.0),
        _cow((330, 335), (630, 655), 1.0, 22.0),
        _cow((400, 345), (700, 645), 2.0, 22.0),
        _cow((470, 338), (770, 650), 3.0, 22.0),
    ],
    duration_s=24.0,
))

register(Scenario(
    name="distant-target",
    description=(
        "An animal is detected far beyond the acoustic envelope. No carrier in "
        "the documented band reaches it within the welfare ceiling, so the "
        "system escalates immediately instead of turning the level up. This is "
        "the scenario that proves the device knows its own limits."
    ),
    actors=[_cow((620, 338), (650, 356), 0.0, 20.0, box_w=40, box_h=32)],
    duration_s=20.0,
))

register(Scenario(
    name="turn-away",
    description=(
        "A cow approaches, is nudged, and turns away before the carriageway. "
        "The incident closes, emission stops immediately, and the ledger "
        "records the outcome code T."
    ),
    actors=[_cow((300, 340), (620, 640), 0.0, 20.0, stop_at_frac=0.45)],
    duration_s=20.0,
))


register(Scenario(
    name="persistent-blocker",
    description=(
        "A cow settles on the carriageway and does not move. Attempts and the "
        "escalation timeout are both exhausted, so the system stops emitting "
        "and hands the incident to municipal dispatch. The demo point: the "
        "device gives up rather than getting louder."
    ),
    actors=[_cow((520, 400), (600, 560), 0.0, 45.0, stop_at_frac=0.6)],
    duration_s=45.0,
))


register(Scenario(
    name="goat-flock",
    description=(
        "A goat flock grazes beside the road while a cow approaches. Goats hear "
        "22-30 kHz BETTER than cattle do and panic propagates through a flock, "
        "so the system must refuse entirely. Note the detector reports them as "
        "'sheep' - COCO has no goat class, and that ambiguity is declared "
        "rather than hidden."
    ),
    actors=[
        _cow((300, 360), (600, 620), 0.0, 22.0),
        Actor("sheep", (830, 430), (870, 470), 0.0, 22.0, box_w=70, box_h=55),
        Actor("sheep", (890, 445), (930, 480), 0.0, 22.0, box_w=70, box_h=55),
        Actor("sheep", (950, 435), (985, 475), 0.0, 22.0, box_w=70, box_h=55),
        Actor("sheep", (860, 470), (900, 505), 0.0, 22.0, box_w=70, box_h=55),
    ],
    duration_s=22.0,
))

register(Scenario(
    name="cow-with-calf",
    description=(
        "A cow approaches with a calf at foot. The calf is classified as "
        "juvenile from its estimated real-world height, which vetoes emission "
        "for the whole group: young animals are more vulnerable and a dam with "
        "offspring is the classic maternal-aggression case."
    ),
    actors=[
        _cow((320, 380), (600, 620), 0.0, 22.0),
        _cow((400, 385), (670, 625), 0.0, 22.0, box_w=72, box_h=38),
    ],
    duration_s=22.0,
))

register(Scenario(
    name="herd-stampede-risk",
    description=(
        "Five cattle move together. Above the group-size threshold a startle "
        "can cascade through the whole group (R9), putting several animals on "
        "the road at once instead of one. The system refuses and escalates."
    ),
    actors=[
        _cow((250, 370), (520, 620), 0.0, 24.0),
        _cow((310, 365), (580, 625), 0.0, 24.0),
        _cow((370, 375), (640, 615), 0.0, 24.0),
        _cow((430, 368), (700, 622), 0.0, 24.0),
        _cow((490, 372), (760, 618), 0.0, 24.0),
    ],
    duration_s=24.0,
))

register(Scenario(
    name="flight-into-road",
    description=(
        "An animal already standing on the carriageway. Fleeing a roadside "
        "emitter would push it further ACROSS the road, not off it. This is "
        "the scenario that proves GauKavach is an approach deterrent, not a "
        "road-clearer - and that clearing a road needs a human, not volume."
    ),
    actors=[_cow((600, 560), (640, 600), 0.0, 20.0, stop_at_frac=0.3)],
    duration_s=20.0,
))


def _inject_panic(engine, t: float) -> None:
    """After the first emission, report a panic response at t ~= 12 s."""
    from .policy import Outcome

    if 11.9 <= t <= 12.1:
        for tid, inc in engine.incidents.items():
            if inc.attempts > 0 and not inc.outcomes:
                engine.observe(tid, Outcome.RAN, t, note="simulated panic response")


register(Scenario(
    name="panic-stop-criterion",
    description=(
        "An animal panics after the first burst. Section 12.2 of the report "
        "makes this a stop criterion, not a success: the animal is flagged "
        "do-not-emit for the rest of the session and the incident is inhibited."
    ),
    actors=[_cow((300, 360), (620, 640), 0.0, 30.0)],
    duration_s=30.0,
    on_step=_inject_panic,
))


def run(
    scenario: Scenario,
    engine,
    tracker: SimpleTracker | None = None,
    verbose: bool = False,
) -> list[dict]:
    """Drive a PolicyEngine through a scenario. Returns every frame snapshot."""
    tracker = tracker or SimpleTracker()
    snapshots: list[dict] = []
    for t, dets in scenario.frames():
        tracks = tracker.update(dets)
        snap = engine.step(tracks, t)
        snapshots.append(snap)
        if scenario.on_step:
            scenario.on_step(engine, t)
        if verbose and snap["actions"]:
            for a in snap["actions"]:
                print(f"  t={t:5.1f}s  {a.get('action','?'):<9} {a}")
    return snapshots
