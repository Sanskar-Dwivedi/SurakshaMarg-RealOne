"""
Perception: detection, tracking, zone geometry and species gating.

The report's central architectural claim is that species selectivity must live
in the DETECTION layer, not in the choice of frequency - a 25 kHz tone is not
cattle-specific and never will be. PIR cannot distinguish a cow from a person.
So this module classifies before it ever allows the emitter to be considered.

YOLO's COCO vocabulary already contains cow, horse, sheep, dog and person,
which is exactly the discrimination the welfare argument requires. No custom
dataset is needed for the safety-critical distinction; a fine-tuned Indian
street-cattle model improves recall but is not load-bearing for safety.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Iterable, Sequence

import numpy as np

# COCO class ids as shipped with the pretrained YOLO weights.
COCO_TARGET = {19: "cow"}
COCO_NON_TARGET_ANIMAL = {16: "dog", 17: "horse", 18: "sheep", 20: "elephant", 15: "cat"}
COCO_HUMAN = {0: "person"}
COCO_VEHICLE = {1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}

ALL_CLASSES = {**COCO_HUMAN, **COCO_VEHICLE, **COCO_TARGET, **COCO_NON_TARGET_ANIMAL}


@dataclass
class Detection:
    cls_id: int
    label: str
    conf: float
    xyxy: tuple[float, float, float, float]

    @property
    def centroid(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def foot_point(self) -> tuple[float, float]:
        """Bottom-centre: where the animal contacts the ground plane."""
        x1, _, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, y2)

    @property
    def height_px(self) -> float:
        return abs(self.xyxy[3] - self.xyxy[1])

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Track:
    track_id: str
    label: str
    xyxy: tuple[float, float, float, float]
    conf: float
    age: int = 0
    misses: int = 0
    history: list[tuple[float, float]] = field(default_factory=list)
    distance_m: float = 0.0
    in_zone: bool = False

    @property
    def centroid(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def foot_point(self) -> tuple[float, float]:
        x1, _, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, y2)

    def velocity(self, n: int = 5) -> tuple[float, float]:
        """Mean pixel velocity over the last n frames."""
        if len(self.history) < 2:
            return (0.0, 0.0)
        pts = self.history[-n:]
        dx = (pts[-1][0] - pts[0][0]) / max(len(pts) - 1, 1)
        dy = (pts[-1][1] - pts[0][1]) / max(len(pts) - 1, 1)
        return (dx, dy)

    def speed_px(self) -> float:
        dx, dy = self.velocity()
        return math.hypot(dx, dy)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["centroid"] = self.centroid
        d["speed_px"] = round(self.speed_px(), 2)
        return d


def iou(a: Sequence[float], b: Sequence[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


class SimpleTracker:
    """
    IoU-greedy tracker with track persistence.

    Deliberately simple. Identity persistence matters here for one reason only:
    per-animal exposure budgets in the welfare governor are meaningless if the
    same cow is re-identified as a new track every few frames. Tracking is a
    WELFARE component in this system, not a convenience.
    """

    def __init__(self, iou_threshold: float = 0.3, max_misses: int = 15) -> None:
        self.iou_threshold = iou_threshold
        self.max_misses = max_misses
        self.tracks: dict[str, Track] = {}
        self._next = 0

    def _new_id(self, label: str) -> str:
        self._next += 1
        return f"{label[:3].upper()}-{self._next:04d}"

    def update(self, detections: Iterable[Detection]) -> list[Track]:
        dets = list(detections)
        unmatched = set(self.tracks.keys())
        used: set[int] = set()

        pairs: list[tuple[float, str, int]] = []
        for tid, tr in self.tracks.items():
            for i, d in enumerate(dets):
                if d.label != tr.label:
                    continue
                score = iou(tr.xyxy, d.xyxy)
                if score >= self.iou_threshold:
                    pairs.append((score, tid, i))
        pairs.sort(reverse=True)

        for score, tid, i in pairs:
            if tid not in unmatched or i in used:
                continue
            tr = self.tracks[tid]
            d = dets[i]
            tr.xyxy = d.xyxy
            tr.conf = d.conf
            tr.age += 1
            tr.misses = 0
            tr.history.append(d.foot_point)
            unmatched.discard(tid)
            used.add(i)

        for tid in unmatched:
            self.tracks[tid].misses += 1

        for i, d in enumerate(dets):
            if i in used:
                continue
            tid = self._new_id(d.label)
            self.tracks[tid] = Track(
                track_id=tid, label=d.label, xyxy=d.xyxy, conf=d.conf,
                history=[d.foot_point],
            )

        for tid in [t for t, tr in self.tracks.items() if tr.misses > self.max_misses]:
            del self.tracks[tid]

        return list(self.tracks.values())


# ---------------------------------------------------------------------------
# Zone geometry
# ---------------------------------------------------------------------------


def point_in_polygon(pt: tuple[float, float], poly: Sequence[tuple[float, float]]) -> bool:
    """Ray casting. Small enough to audit by eye."""
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xin = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1
            if x < xin:
                inside = not inside
    return inside


@dataclass
class Site:
    """
    Deployment geometry for one location.

    `carriageway` is the polygon we want clear. `warning_zone` is the larger
    polygon in which an approaching animal may be acted upon. Emission is only
    ever considered for an animal inside the warning zone AND moving toward the
    carriageway - a stationary cow grazing on the verge is left alone.
    """

    name: str
    carriageway: tuple[tuple[float, float], ...]
    warning_zone: tuple[tuple[float, float], ...]
    emitter_px: tuple[float, float]
    camera_height_m: float = 4.0
    focal_px: float = 900.0
    horizon_y: float = 280.0
    principal_x: float = 640.0
    lanes: int = 2
    speed_limit_kmh: float = 50.0
    distance_error_frac: float = 0.20

    def estimate_distance_m(self, pt: tuple[float, float]) -> float:
        """
        Monocular ground-plane range by inverse perspective mapping.

        For a camera of height H with focal length f looking at a flat ground
        plane whose horizon projects to `horizon_y`, a ground contact point at
        image row y lies at longitudinal range:

            Z = H * f / (y - horizon_y)

        with lateral offset X = Z * (x - cx) / f, giving slant range hypot(X, Z).

        Honest limitations, stated because they change the safety case:
          * The ground is assumed flat. Camber, potholes and gradients break it.
          * H, f and horizon_y must come from a real calibration; the defaults
            here are plausible values for a 4 m pole camera, not measurements.
          * Residual error is roughly +/-20% and grows sharply near the horizon,
            where (y - horizon_y) approaches zero.

        That error budget is exactly why the governor solves the link budget
        with the PESSIMISTIC absorption model: an under-estimated distance
        would otherwise silently under-power the emitter, and an over-estimated
        one would over-expose the animal. The two conservatisms are stacked on
        purpose.
        """
        x, y = pt
        depth_px = y - self.horizon_y
        if depth_px <= 1.0:
            # At or above the horizon the model is undefined. Return a large
            # value so the policy engine escalates instead of guessing.
            return 1e4
        z = self.camera_height_m * self.focal_px / depth_px
        lateral = z * (x - self.principal_x) / self.focal_px
        return math.hypot(lateral, z)

    def distance_bounds_m(self, pt: tuple[float, float]) -> tuple[float, float]:
        """Range interval implied by `distance_error_frac`. Used for reporting."""
        d = self.estimate_distance_m(pt)
        return (d * (1.0 - self.distance_error_frac), d * (1.0 + self.distance_error_frac))

    # -- metric ground plane -------------------------------------------------

    def ground_xz(self, pt: tuple[float, float]) -> tuple[float, float]:
        """
        Image point -> metric ground coordinates (lateral X, longitudinal Z),
        origin at the camera, +Z away down the road, +X to the right.

        Flight-path geometry has to be done in metres, not pixels: perspective
        makes "8 metres of clear ground" a wildly different pixel distance at
        the top and bottom of the frame.
        """
        x, y = pt
        depth_px = y - self.horizon_y
        if depth_px <= 1.0:
            return (0.0, 1e4)
        z = self.camera_height_m * self.focal_px / depth_px
        return (z * (x - self.principal_x) / self.focal_px, z)

    def carriageway_ground(self) -> list[tuple[float, float]]:
        return [self.ground_xz(p) for p in self.carriageway]

    def estimate_height_m(self, xyxy: tuple[float, float, float, float]) -> float:
        """
        Real-world height of a detection from its pixel height and range.

        h = h_px * Z / f. Used to separate a calf from a cow - juveniles mean
        maternal defence and a more vulnerable animal, so the distinction is a
        welfare gate, not a statistic. Inherits the camera's calibration error.
        """
        x1, y1, x2, y2 = xyxy
        foot = ((x1 + x2) / 2.0, y2)
        _, z = self.ground_xz(foot)
        if z >= 1e3:
            return 0.0
        return abs(y2 - y1) * z / self.focal_px

    # -- flight geometry -----------------------------------------------------

    def flight_vector(self, pt: tuple[float, float]) -> tuple[float, float]:
        """
        Unit vector along which the animal is expected to flee: directly away
        from the emitter, in ground coordinates.

        A first-order model. Grandin's handling literature (R24) describes
        animals moving away from applied pressure, but real flight paths bend
        with terrain, herd position and prior route. Stated as first-order
        rather than dressed up as prediction.
        """
        ex, ez = self.ground_xz(self.emitter_px)
        ax, az = self.ground_xz(pt)
        dx, dz = ax - ex, az - ez
        n = math.hypot(dx, dz)
        if n < 1e-6:
            return (0.0, 1.0)
        return (dx / n, dz / n)

    def flight_crosses_carriageway(
        self, pt: tuple[float, float], check_m: float, step_m: float = 0.5
    ) -> tuple[bool, float]:
        """
        Would fleeing from the emitter take this animal onto the road?

        Ray-casts along the flight vector and returns (crosses, distance_m).
        This is the check that stops the system causing the collision it
        exists to prevent.
        """
        poly = self.carriageway_ground()
        ax, az = self.ground_xz(pt)
        vx, vz = self.flight_vector(pt)
        d = 0.0
        while d <= check_m:
            if point_in_polygon((ax + vx * d, az + vz * d), poly):
                return (True, d)
            d += step_m
        return (False, -1.0)

    def flight_assessment(
        self, pt: tuple[float, float], check_m: float, step_m: float = 0.5
    ) -> dict:
        """
        Full verdict on where fleeing would take this animal.

        Distinguishes two cases the single boolean above conflates:

          * `already_in_hazard` - the animal is standing on the carriageway.
            Fleeing away from a roadside emitter pushes it further ACROSS,
            not off. This is why GauKavach is an approach deterrent and not a
            road-clearer, and why clearing an animal from mid-road needs an
            emitter on the far side or a human, not more volume.
          * `enters_hazard` - the animal is clear but its flight path leads
            onto the road.

        Either way the answer is refuse; the distinction matters because the
        operator response differs, and because a system that cannot say which
        case it is in should not be trusted with the decision.
        """
        poly = self.carriageway_ground()
        ax, az = self.ground_xz(pt)
        vx, vz = self.flight_vector(pt)
        already = point_in_polygon((ax, az), poly)

        road_span = 0.0
        entry = -1.0
        clear_before = None
        d = 0.0
        while d <= check_m:
            inside = point_in_polygon((ax + vx * d, az + vz * d), poly)
            if inside:
                road_span += step_m
                if entry < 0 and not already:
                    entry = d
            elif clear_before is None and not already:
                pass
            d += step_m

        corridor = entry if entry >= 0 else (0.0 if already else check_m)
        return {
            "already_in_hazard": already,
            "enters_hazard": entry >= 0,
            "entry_distance_m": round(entry, 1) if entry >= 0 else None,
            "road_metres_along_flight": round(road_span, 1),
            "escape_corridor_m": round(corridor, 1),
            "flight_vector": (round(vx, 3), round(vz, 3)),
            "safe": (not already) and entry < 0,
        }

    def escape_corridor_m(
        self, pt: tuple[float, float], limit_m: float = 40.0, step_m: float = 0.5
    ) -> float:
        """
        Clear ground along the flight vector before the carriageway is reached.

        An animal with nowhere to go panics rather than withdrawing (R24), so
        this must exceed `min_escape_corridor_m` before any emission.
        """
        crosses, at = self.flight_crosses_carriageway(pt, limit_m, step_m)
        return at if crosses else limit_m

    def as_dict(self) -> dict:
        return asdict(self)

    def classify_position(self, pt: tuple[float, float]) -> str:
        if point_in_polygon(pt, self.carriageway):
            return "carriageway"
        if point_in_polygon(pt, self.warning_zone):
            return "warning"
        return "outside"

    def approaching(self, track: Track) -> bool:
        """Is the track moving toward the carriageway centroid?"""
        vx, vy = track.velocity()
        if math.hypot(vx, vy) < 0.5:
            return False
        cx = sum(p[0] for p in self.carriageway) / len(self.carriageway)
        cy = sum(p[1] for p in self.carriageway) / len(self.carriageway)
        fx, fy = track.foot_point
        tox, toy = cx - fx, cy - fy
        norm = math.hypot(tox, toy)
        if norm < 1e-6:
            return True
        return (vx * tox + vy * toy) / norm > 0.3


DEMO_SITE = Site(
    name="Village crossing on a 2-lane state highway (SIMULATED geometry)",
    carriageway=((240, 470), (1040, 470), (1180, 700), (100, 700)),
    warning_zone=((330, 330), (960, 330), (1260, 719), (20, 719)),
    emitter_px=(640, 719),
    camera_height_m=4.0,
    focal_px=900.0,
    horizon_y=280.0,
    principal_x=640.0,
    lanes=2,
    speed_limit_kmh=50.0,
)


# ---------------------------------------------------------------------------
# YOLO adapter
# ---------------------------------------------------------------------------


class Perception:
    """
    Wraps ultralytics YOLO. Degrades to a no-op if weights are unavailable so
    the rest of the pipeline stays testable without a model download.
    """

    def __init__(self, weights: str = "yolov8n.pt", conf: float = 0.35) -> None:
        self.conf = conf
        self.model = None
        self.error: str | None = None
        try:
            from ultralytics import YOLO  # noqa: PLC0415

            self.model = YOLO(weights)
        except Exception as exc:  # pragma: no cover - environment dependent
            self.error = f"{type(exc).__name__}: {exc}"

    @property
    def available(self) -> bool:
        return self.model is not None

    def detect(self, frame: np.ndarray) -> list[Detection]:
        if self.model is None:
            return []
        results = self.model.predict(
            frame, conf=self.conf, classes=sorted(ALL_CLASSES), verbose=False
        )
        out: list[Detection] = []
        for r in results:
            boxes = getattr(r, "boxes", None)
            if boxes is None:
                continue
            for b in boxes:
                cls_id = int(b.cls.item())
                label = ALL_CLASSES.get(cls_id)
                if label is None:
                    continue
                x1, y1, x2, y2 = (float(v) for v in b.xyxy[0].tolist())
                out.append(Detection(cls_id, label, float(b.conf.item()), (x1, y1, x2, y2)))
        return out


def social_group_size(
    track: Track, tracks: Iterable[Track], site: Site, radius_m: float
) -> int:
    """
    How many conspecifics share this animal's immediate space.

    Counted in METRES on the ground plane, not pixels, because perspective
    makes a pixel radius meaningless. Drives the stampede veto: R9 showed
    responses are socially facilitated, so a startle does not stay with the
    animal it was aimed at.
    """
    ax, az = site.ground_xz(track.foot_point)
    n = 0
    for t in tracks:
        if t.label != track.label:
            continue
        bx, bz = site.ground_xz(t.foot_point)
        if math.hypot(bx - ax, bz - az) <= radius_m:
            n += 1
    return n


def is_juvenile(track: Track, site: Site, adult_height_m: float, ratio: float) -> bool:
    """
    Estimated shorter than `ratio` of species-typical adult height.

    A juvenile means two things at once: a more vulnerable animal, and very
    likely a defensive dam nearby. Both point the same way - do not emit.
    """
    h = site.estimate_height_m(track.xyxy)
    return 0.05 < h < adult_height_m * ratio


def is_downed(track: Track, aspect_threshold: float) -> bool:
    """
    Bounding box much wider than tall - possibly recumbent or collapsed.

    Crude and deliberately biased toward false positives. Wrongly sparing a
    grazing animal costs one missed nudge; harassing a collapsed animal that
    needs rescue is a welfare failure we are not willing to risk.
    """
    x1, y1, x2, y2 = track.xyxy
    h = abs(y2 - y1)
    if h < 1.0:
        return False
    return abs(x2 - x1) / h >= aspect_threshold


def displacement_m(track: Track, site: Site, over_frames: int = 25) -> float:
    """Ground-plane distance moved recently. Small values suggest restraint."""
    if len(track.history) < 2:
        return 0.0
    pts = track.history[-over_frames:]
    x0, z0 = site.ground_xz(pts[0])
    x1, z1 = site.ground_xz(pts[-1])
    return math.hypot(x1 - x0, z1 - z0)


def split_by_role(tracks: Iterable[Track]) -> dict[str, list[Track]]:
    """Partition tracks into the three groups the governor cares about."""
    target_labels = set(COCO_TARGET.values())
    human_labels = set(COCO_HUMAN.values())
    nontarget_labels = set(COCO_NON_TARGET_ANIMAL.values())
    out: dict[str, list[Track]] = {"target": [], "human": [], "non_target": [], "vehicle": []}
    for t in tracks:
        if t.label in target_labels:
            out["target"].append(t)
        elif t.label in human_labels:
            out["human"].append(t)
        elif t.label in nontarget_labels:
            out["non_target"].append(t)
        else:
            out["vehicle"].append(t)
    return out
