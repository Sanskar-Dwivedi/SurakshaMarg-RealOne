"""Cattle-road MVP: cow detection, tracking, road polygon and speaker choice.

This module is deliberately separate from the evidence-graded GauKavach policy
engine. It provides the source project's software MVP without bypassing or
changing the existing welfare, acoustics, hardware, dashboard, or scenario
pipelines.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from math import hypot
from pathlib import Path
from typing import Any, Iterable

Point = tuple[float, float]
BBox = tuple[int, int, int, int]
NO_VALID_SPEAKER = "NO_VALID_SPEAKER"


def point_in_polygon(point: Point, polygon: Iterable[Iterable[float]]) -> bool:
    """Return True for points inside or on the boundary of a polygon."""

    vertices = [(float(x), float(y)) for x, y in polygon]
    if len(vertices) < 3:
        return False
    x, y = point
    inside = False
    for index, (x1, y1) in enumerate(vertices):
        x2, y2 = vertices[(index + 1) % len(vertices)]
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if abs(cross) < 1e-9 and min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2):
            return True
        if (y1 > y) != (y2 > y):
            intersection_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < intersection_x:
                inside = not inside
    return inside


def ground_contact_point(bbox: Iterable[float]) -> Point:
    x1, _, x2, y2 = [float(value) for value in bbox]
    return ((x1 + x2) / 2.0, y2)


@dataclass(frozen=True)
class CowDetection:
    bbox: BBox
    confidence: float
    class_id: int
    class_name: str
    track_id: int | None = None

    @property
    def ground_point(self) -> Point:
        return ground_contact_point(self.bbox)


@dataclass
class CowTrack:
    track_id: int
    bbox: BBox
    confidence: float
    age: int = 1
    consecutive_frames: int = 1
    last_seen_frame: int = 0
    confirmed: bool = False

    @property
    def ground_point(self) -> Point:
        return ground_contact_point(self.bbox)




class CowDetector:
    """Cow-only adapter for the supplied custom Ultralytics model."""

    def __init__(self, weights: str | Path, confidence: float = 0.18, iou: float = 0.45, imgsz: int = 640) -> None:
        self.weights = Path(weights)
        if not self.weights.is_file():
            raise FileNotFoundError(f"cow model not found: {self.weights}")
        try:
            import os
            import torch
            from ultralytics import YOLO
            torch.set_num_threads(max(1, (os.cpu_count() or 4) - 1))
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("Install the vision extra: pip install -e '.[vision]'") from exc
        self.confidence = confidence
        self.iou = iou
        self.imgsz = imgsz
        self.model = YOLO(str(self.weights))

    def _parse(self, result: Any) -> list[CowDetection]:
        if result is None or result.boxes is None:
            return []
        names = result.names if isinstance(result.names, dict) else dict(enumerate(result.names))
        detections: list[CowDetection] = []
        for index in range(len(result.boxes)):
            box = result.boxes[index]
            class_id = int(box.cls[0].item())
            class_name = str(names.get(class_id, class_id))
            name_lower = class_name.lower()
            # Allow all cattle/livestock classes and custom single-class models
            if len(names) > 1 and name_lower not in ["cow", "cattle", "bull", "calf", "bovine", "horse", "donkey", "animal", "0"]:
                continue
            coords = tuple(int(round(value)) for value in box.xyxy[0].tolist())
            track_id = int(box.id[0].item()) if box.id is not None else None
            detections.append(CowDetection(coords, float(box.conf[0].item()), class_id, class_name, track_id))
        return detections

    def detect(self, frame: Any) -> list[CowDetection]:
        import torch
        with torch.no_grad():
            results = self.model.predict(source=frame, conf=self.confidence, iou=self.iou, imgsz=self.imgsz, verbose=False)
        return self._parse(results[0] if results else None)

    def track(self, frame: Any) -> list[CowDetection]:
        import torch
        with torch.no_grad():
            results = self.model.track(
                source=frame,
                conf=self.confidence,
                iou=self.iou,
                imgsz=self.imgsz,
                persist=True,
                tracker="bytetrack.yaml",
                verbose=False,
            )
        return self._parse(results[0] if results else None)


class CowTrackManager:
    """Require configurable multi-frame confirmation before acting."""

    def __init__(self, confirmation_frames: int = 3) -> None:
        if confirmation_frames < 1:
            raise ValueError("confirmation_frames must be at least 1")
        self.confirmation_frames = confirmation_frames
        self.tracks: dict[int, CowTrack] = {}

    def update(self, detections: Iterable[CowDetection], frame_index: int) -> list[CowTrack]:
        visible: list[CowTrack] = []
        for detection in detections:
            if detection.track_id is None:
                continue
            previous = self.tracks.get(detection.track_id)
            continuous = previous is not None and previous.last_seen_frame == frame_index - 1
            track = CowTrack(
                track_id=detection.track_id,
                bbox=detection.bbox,
                confidence=detection.confidence,
                age=(previous.age + 1) if previous else 1,
                consecutive_frames=(previous.consecutive_frames + 1) if continuous and previous else 1,
                last_seen_frame=frame_index,
                confirmed=((previous.consecutive_frames + 1) if continuous and previous else 1) >= self.confirmation_frames,
            )
            self.tracks[track.track_id] = track
            visible.append(track)
        return visible


@dataclass(frozen=True)
class Speaker:
    speaker_id: str
    position: Point
    coverage_polygon: tuple[Point, ...] = ()
    enabled: bool = True

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Speaker":
        position = value.get("position_px", value.get("position"))
        if position is None:
            position = [value["position_x"], value["position_y"]]
        return cls(
            speaker_id=str(value["speaker_id"]),
            position=(float(position[0]), float(position[1])),
            coverage_polygon=tuple((float(x), float(y)) for x, y in value.get("coverage_polygon", [])),
            enabled=bool(value.get("enabled", True)),
        )


@dataclass(frozen=True)
class SpeakerChoice:
    speaker_id: str | None
    distance: float | None
    state: str


def select_speaker(
    cow_position: Point,
    speakers: Iterable[Speaker],
    current_speaker_id: str | None = None,
    switch_margin: float = 0.5,
) -> SpeakerChoice:
    """Return the nearest enabled speaker in fixed-camera pixel coordinates.

    The operator supplies speaker locations during installation. Coverage circles
    are intentionally not inferred: a fixed radius in pixels is not a reliable
    physical speaker range in a perspective CCTV image.
    """
    candidates = [speaker for speaker in speakers if speaker.enabled]
    if not candidates:
        return SpeakerChoice(None, None, NO_VALID_SPEAKER)
    distances = {
        speaker.speaker_id: hypot(cow_position[0] - speaker.position[0], cow_position[1] - speaker.position[1])
        for speaker in candidates
    }
    best = min(candidates, key=lambda speaker: distances[speaker.speaker_id])
    if current_speaker_id in distances and current_speaker_id != best.speaker_id:
        if distances[best.speaker_id] >= distances[current_speaker_id] - switch_margin:
            return SpeakerChoice(current_speaker_id, distances[current_speaker_id], current_speaker_id)
    return SpeakerChoice(best.speaker_id, distances[best.speaker_id], best.speaker_id)


@dataclass(frozen=True)
class SceneConfig:
    road_polygon: tuple[Point, ...]
    speakers: tuple[Speaker, ...]
    camera_id: str | None = None
    frame_size: tuple[int, int] | None = None

    @classmethod
    def load(cls, path: str | Path) -> "SceneConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        road = tuple((float(x), float(y)) for x, y in data.get("road_polygon", []))
        raw_size = data.get("frame_size")
        frame_size = None if raw_size is None else (int(raw_size["width"]), int(raw_size["height"]))
        return cls(road, tuple(Speaker.from_dict(item) for item in data.get("speakers", [])), data.get("camera_id"), frame_size)

    def save(self, path: str | Path) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 2,
            "camera_id": self.camera_id,
            "frame_size": None if self.frame_size is None else {"width": self.frame_size[0], "height": self.frame_size[1]},
            "road_polygon": [[x, y] for x, y in self.road_polygon],
            "speakers": [
                {"speaker_id": speaker.speaker_id, "position_px": list(speaker.position), "enabled": speaker.enabled}
                for speaker in self.speakers
            ],
        }
        temporary = output.with_suffix(f"{output.suffix}.tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(output)

    def validate_for_frame(self, camera_id: str, width: int, height: int) -> None:
        if self.camera_id is not None and self.camera_id != camera_id:
            raise RuntimeError("scene configuration belongs to a different camera ID; configure this camera again")
        if self.frame_size is not None and self.frame_size != (width, height):
            raise RuntimeError(
                f"video resolution changed from {self.frame_size[0]}x{self.frame_size[1]} to {width}x{height}; configure this camera again"
            )


def draw_frame(
    frame: Any,
    tracks: Iterable[CowTrack],
    scene: SceneConfig,
    selected_ids: set[str] | None = None,
    nearest_speakers: dict[int, SpeakerChoice] | None = None,
) -> Any:
    import cv2
    import numpy as np

    selected_ids = selected_ids or set()
    nearest_speakers = nearest_speakers or {}
    output = frame.copy()
    if len(scene.road_polygon) >= 3:
        road = np.array([(int(x), int(y)) for x, y in scene.road_polygon], dtype=np.int32)
        cv2.polylines(output, [road], True, (255, 180, 0), 2)
    for speaker in scene.speakers:
        color = (0, 255, 0) if speaker.speaker_id in selected_ids else (180, 80, 255)
        point = (int(speaker.position[0]), int(speaker.position[1]))
        cv2.circle(output, point, 7, color, -1)
        cv2.putText(output, speaker.speaker_id, (point[0] + 8, point[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    for track in tracks:
        x1, y1, x2, y2 = track.bbox
        on_road = point_in_polygon(track.ground_point, scene.road_polygon)
        color = (0, 220, 0) if track.confirmed else (0, 165, 255)
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
        ground = (int(track.ground_point[0]), int(track.ground_point[1]))
        cv2.circle(output, ground, 5, (255, 0, 255), -1)
        state = "UNCONFIRMED_COW"
        choice = nearest_speakers.get(track.track_id)
        if track.confirmed:
            state = "ON_ROAD" if on_road else "OFF_ROAD"
        label = f"ID:{track.track_id} {track.confidence:.2f} {state}"
        if choice and choice.speaker_id:
            label += f" | Nearest: {choice.speaker_id} ({choice.distance:.0f}px)"
        cv2.putText(output, label, (x1, max(18, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 1, cv2.LINE_AA)
    return output


def _configure_scene(source_path: str, output_path: str, camera_id: str = "default-camera") -> None:
    import cv2
    import numpy as np

    source = Path(source_path)
    if not source.is_file():
        raise RuntimeError(f"selected image/video not found: {source_path}")
    if source.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        image = cv2.imread(str(source))
    else:
        capture = cv2.VideoCapture(str(source))
        ok, image = capture.read()
        capture.release()
        if not ok:
            image = None
    if image is None:
        raise RuntimeError(f"could not read the first frame from: {source_path}")
    window = "cattle scene configuration"

    def collect(title: str, minimum: int, points: list[list[int]]) -> list[list[int]]:
        canvas = image.copy()

        def redraw() -> None:
            canvas[:] = image
            for index, point in enumerate(points, 1):
                cv2.circle(canvas, tuple(point), 7, (0, 255, 0), -1)
                cv2.putText(canvas, f"{index}", (point[0] + 8, point[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(canvas, f"{title} | left-click add | right-click undo | C clear | ENTER finish", (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

        def callback(event: int, x: int, y: int, _flags: int, _param: object) -> None:
            if event == cv2.EVENT_LBUTTONDOWN:
                points.append([x, y])
                redraw()
            elif event == cv2.EVENT_RBUTTONDOWN and points:
                points.pop()
                redraw()

        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(window, callback)
        redraw()
        while True:
            cv2.imshow(window, canvas)
            key = cv2.waitKey(20) & 0xFF
            if key in (10, 13) and len(points) >= minimum:
                return points
            if key in (ord("c"), ord("C")):
                points.clear()
                redraw()
            if key == 27:
                raise RuntimeError("scene configuration cancelled")

    try:
        while True:
            road = collect("Road polygon", 3, [])
            locations = collect("Speaker locations", 1, [])
            preview = image.copy()
            cv2.polylines(preview, [np.array(road, dtype="int32")], True, (255, 180, 0), 2)
            for index, (x, y) in enumerate(locations, 1):
                cv2.circle(preview, (x, y), 8, (0, 255, 0), -1)
                cv2.putText(preview, f"S{index}", (x + 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
            cv2.putText(preview, "Review | S save | R redraw | ESC cancel", (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
            while True:
                cv2.imshow(window, preview)
                key = cv2.waitKey(20) & 0xFF
                if key in (ord("s"), ord("S")):
                    height, width = image.shape[:2]
                    SceneConfig(
                        tuple((float(x), float(y)) for x, y in road),
                        tuple(Speaker(f"S{index}", (float(x), float(y))) for index, (x, y) in enumerate(locations, 1)),
                        camera_id,
                        (width, height),
                    ).save(output_path)
                    print(f"Saved scene configuration to {Path(output_path).resolve()}")
                    return
                if key in (ord("r"), ord("R")):
                    break
                if key == 27:
                    raise RuntimeError("scene configuration cancelled")
    finally:
        cv2.destroyAllWindows()


def configure_scene(source_path: str, output_path: str, camera_id: str = "default-camera") -> None:
    """Configure a fixed camera using an image or the first frame of a video."""
    _configure_scene(source_path, output_path, camera_id)


def run_cattle(source_path: str, weights: str, scene_path: str, output_path: str | None = None, confidence: float = 0.30, confirmation_frames: int = 3, max_frames: int = 0, show: bool = False, camera_id: str = "default-camera", event_log_path: str | None = None) -> dict[str, Any]:
    """Run the cow-only MVP on an image or video. No hardware is activated."""

    import cv2

    scene = SceneConfig.load(scene_path)
    detector = CowDetector(weights, confidence=confidence)
    manager = CowTrackManager(confirmation_frames)
    source = Path(source_path)
    image_mode = source.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    capture = None
    writer = None
    if image_mode:
        image = cv2.imread(str(source))
        if image is None:
            raise RuntimeError(f"could not read image source: {source}")
    else:
        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            raise RuntimeError(f"could not open video source: {source}")
    frame_index = 0
    total_detections = 0
    confirmed = 0
    selected_counts: dict[str, int] = {}
    event_log = Path(event_log_path) if event_log_path else None
    events: list[dict[str, Any]] = []
    last_output = None
    while True:
        if image_mode:
            ok, frame = frame_index == 0, image.copy()
        else:
            ok, frame = capture.read()
        if not ok:
            break
        if frame_index == 0:
            scene.validate_for_frame(camera_id, frame.shape[1], frame.shape[0])
        detections = detector.track(frame)
        total_detections += len(detections)
        tracks = manager.update(detections, frame_index)
        selected_ids: set[str] = set()
        nearest_speakers: dict[int, SpeakerChoice] = {}
        for track in tracks:
            choice = select_speaker(track.ground_point, scene.speakers)
            nearest_speakers[track.track_id] = choice
            on_road = point_in_polygon(track.ground_point, scene.road_polygon)
            events.append({
                "frame_index": frame_index,
                "track_id": track.track_id,
                "on_road": on_road,
                "speaker_id": choice.speaker_id,
                "distance_px": choice.distance,
                "state": choice.state,
            })
            if track.confirmed:
                confirmed += 1
            if track.confirmed and on_road and choice.speaker_id:
                selected_ids.add(choice.speaker_id)
                selected_counts[choice.speaker_id] = selected_counts.get(choice.speaker_id, 0) + 1
        rendered = draw_frame(frame, tracks, scene, selected_ids, nearest_speakers)
        last_output = rendered
        if image_mode:
            destination = Path(output_path) if output_path else source.with_name(f"{source.stem}_cattle.jpg")
            destination.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(destination), rendered)
        else:
            if output_path and writer is None:
                fps = capture.get(cv2.CAP_PROP_FPS) or 20.0
                writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (rendered.shape[1], rendered.shape[0]))
            if writer is not None:
                writer.write(rendered)
        if show:
            cv2.imshow("GauKavach cattle MVP", rendered)
            if cv2.waitKey(1) & 0xFF == 27:
                break
        frame_index += 1
        if image_mode or (max_frames and frame_index >= max_frames):
            break
    if capture is not None:
        capture.release()
    if writer is not None:
        writer.release()
    if show:
        cv2.destroyAllWindows()
    if event_log is not None:
        event_log.parent.mkdir(parents=True, exist_ok=True)
        event_log.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    return {
        "frames": frame_index,
        "detections": total_detections,
        "confirmed_track_updates": confirmed,
        "selected_speakers": selected_counts,
        "output": output_path,
        "hardware_activated": False,
        "last_frame_available": last_output is not None,
        "event_log": str(event_log) if event_log else None,
    }
