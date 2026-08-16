"""
Real-footage pipeline.

Turns a real video clip into a frame pack the browser simulator can replay:
JPEG frames plus, for each frame, the genuine YOLO detections and the genuine
governor decision.

This is what replaces the cartoon road. The demo stops being a diagram of the
idea and becomes the system running on actual traffic, which is a different
kind of claim and a much harder one to wave away.

Calibration honesty: a downloaded clip comes with no camera parameters, so the
site geometry is fitted by eye to the visible road. Distances are therefore
INDICATIVE. Every frame carries that watermark, and `calibration_confidence`
is exported alongside so the page can say it out loud rather than implying a
precision nobody has earned.
"""

from __future__ import annotations

import base64
import json
from dataclasses import replace as dc_replace
from pathlib import Path

from . import evidence as ev
from .acoustics import Atmosphere
from .detect import (
    DEMO_SITE,
    Perception,
    Site,
    SimpleTracker,
    is_downed,
    is_juvenile,
    social_group_size,
)
from .ledger import Ledger
from .policy import EngineConfig, PolicyEngine
from .species import SPECIES, TARGET_KEY, species_for_label

SITE_ATM = Atmosphere(temp_c=32.0, rh_pct=60.0, ambient_spl_db=58.0)


def probe(path: str, sample_every: int = 15, conf: float = 0.30) -> dict:
    """
    Walk the clip and find the segment with the most target animals.

    Container metadata on web video is often wrong (this clip claims 600 fps),
    so frames are counted by reading, never by trusting CAP_PROP_FRAME_COUNT.
    """
    import cv2  # noqa: PLC0415

    per = Perception(conf=conf)
    if not per.available:
        raise RuntimeError(f"YOLO unavailable: {per.error}")

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {path}")

    counts: list[tuple[int, int, dict]] = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % sample_every == 0:
            dets = per.detect(frame)
            by = {}
            for d in dets:
                by[d.label] = by.get(d.label, 0) + 1
            counts.append((idx, by.get("cow", 0), by))
        idx += 1
    cap.release()

    best = max(counts, key=lambda c: c[1]) if counts else (0, 0, {})
    return {
        "path": path,
        "real_frame_count": idx,
        "sampled": len(counts),
        "best_frame": best[0],
        "best_cow_count": best[1],
        "labels_at_best": best[2],
        "timeline": [{"frame": f, "cows": c} for f, c, _ in counts],
    }


def fit_site(width: int, height: int, base: Site = DEMO_SITE) -> Site:
    """
    Scale the demo site geometry to a clip's resolution.

    Emphatically NOT a calibration. It keeps the zones on screen and in
    plausible proportion so the overlay is legible; the camera height, focal
    length and horizon are still the defaults, which is why everything derived
    from them is labelled indicative.
    """
    sx, sy = width / 1280.0, height / 720.0
    scale = lambda pts: tuple((p[0] * sx, p[1] * sy) for p in pts)  # noqa: E731
    return dc_replace(
        base,
        name=f"Real footage ({width}x{height}) - geometry fitted by eye, NOT calibrated",
        carriageway=scale(base.carriageway),
        warning_zone=scale(base.warning_zone),
        emitter_px=(base.emitter_px[0] * sx, base.emitter_px[1] * sy),
        horizon_y=base.horizon_y * sy,
        principal_x=base.principal_x * sx,
        focal_px=base.focal_px * sx,
    )


def build_pack(
    path: str,
    out_json: str = "dashboard/footage.json",
    start_frame: int = 0,
    n_frames: int = 150,
    stride: int = 3,
    out_w: int = 768,
    jpeg_quality: int = 58,
    conf: float = 0.30,
    attribution: str = "",
    licence: str = "",
) -> dict:
    """
    Export a frame pack: JPEG frames + real detections + real decisions.

    Frames are stride-sampled so a short pack covers a useful span of the clip
    without embedding a whole video.
    """
    import cv2  # noqa: PLC0415

    per = Perception(conf=conf)
    if not per.available:
        raise RuntimeError(f"YOLO unavailable: {per.error}")

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {path}")
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    if not (1.0 < src_fps < 121.0):
        src_fps = 25.0  # container metadata is unreliable on web video

    out_h = int(round(out_w * src_h / src_w))
    site = fit_site(out_w, out_h)
    engine = PolicyEngine(site, SITE_ATM, Ledger(), EngineConfig())
    tracker = SimpleTracker()

    frames: list[dict] = []
    idx = 0
    taken = 0
    while taken < n_frames:
        ok, frame = cap.read()
        if not ok:
            break
        if idx >= start_frame and (idx - start_frame) % stride == 0:
            small = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_AREA)
            dets = per.detect(small)
            tracks = tracker.update(dets)
            t = taken * stride / src_fps
            snap = engine.step(tracks, t)

            actors = []
            for tr in tracks:
                profiles = species_for_label(tr.label)
                adult_h = profiles[0].typical_adult_height_m if profiles else 1.35
                fl = site.flight_assessment(tr.foot_point, ev.get("flight_vector_check_m"))
                targets = [x for x in tracks if x.label == "cow"]
                actors.append({
                    "id": tr.track_id,
                    "l": tr.label,
                    "sp": profiles[0].name if profiles else tr.label,
                    "b": [int(v) for v in tr.xyxy],
                    "cf": round(tr.conf, 2),
                    "d": round(site.estimate_distance_m(tr.foot_point), 1),
                    "z": site.classify_position(tr.foot_point)[0],
                    "t": tr.label == "cow",
                    "juv": is_juvenile(tr, site, adult_h, ev.get("juvenile_height_ratio")),
                    "dn": is_downed(tr, ev.get("downed_aspect_ratio")),
                    "grp": social_group_size(tr, targets, site,
                                             ev.get("herd_grouping_radius_m")),
                    "fs": fl["safe"],
                    "fa": fl["already_in_hazard"],
                    "fv": fl["flight_vector"],
                    "oh": bool(profiles and profiles[0].hearing_high_hz
                               > SPECIES[TARGET_KEY].hearing_high_hz),
                })

            acts = []
            for a in snap["actions"]:
                slim = {"id": a.get("track_id", ""), "a": a["action"]}
                for k_src, k_dst in (("reason", "why"), ("carrier_khz", "khz"),
                                     ("level_at_1m_db", "lvl"), ("received_db", "rx"),
                                     ("p_response", "p"), ("pattern", "pat")):
                    if k_src in a:
                        slim[k_dst] = a[k_src]
                if a.get("denials"):
                    slim["den"] = a["denials"]
                acts.append(slim)

            ok2, buf = cv2.imencode(".jpg", small,
                                    [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
            frames.append({
                "t": round(t, 2),
                "img": base64.b64encode(buf).decode("ascii") if ok2 else "",
                "a": actors,
                "x": acts,
                "s": snap["state"],
            })
            taken += 1
        idx += 1
    cap.release()
    summary = engine.close()

    pack = {
        "source": Path(path).name,
        "attribution": attribution,
        "licence": licence,
        "src_resolution": [src_w, src_h],
        "out_resolution": [out_w, out_h],
        "fps": round(src_fps / stride, 2),
        "frames": frames,
        "site": {
            "name": site.name,
            "carriageway": [[round(x, 1), round(y, 1)] for x, y in site.carriageway],
            "warning_zone": [[round(x, 1), round(y, 1)] for x, y in site.warning_zone],
            "emitter_px": [round(v, 1) for v in site.emitter_px],
            "horizon_y": round(site.horizon_y, 1),
        },
        "summary": {
            "incidents": summary["incidents"],
            "escalated": summary["escalated"],
            "total_emission_s": summary["total_emission_s"],
            "denials": summary["governor"]["denials_by_reason"],
        },
        "records": len(engine.ledger),
        "chain_valid": engine.ledger.verify()["valid"],
        "calibration_confidence": "NONE - geometry fitted by eye",
        "honesty": (
            "Real footage, real YOLO detections, real governor decisions. The "
            "camera is NOT calibrated for this clip, so every distance and "
            "every level derived from it is indicative only. Nothing here is a "
            "field measurement."
        ),
    }
    p = Path(out_json)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(pack, separators=(",", ":")), encoding="utf-8")
    return pack


def detection_stats(path: str, sample_every: int = 20, conf: float = 0.30) -> dict:
    """
    Measure what the detector actually reports on this clip.

    Includes the labels we believe are wrong. On Indian street cattle the
    COCO detector emits `horse`, `sheep` and even `elephant`, which is hazard
    H19 (misclassification) observed on real data rather than hypothesised.
    Worth stating plainly: those errors fail SAFE here, because every one of
    those labels is a non-target and therefore vetoes emission.
    """
    import cv2  # noqa: PLC0415

    per = Perception(conf=conf)
    cap = cv2.VideoCapture(path)
    hits: dict[str, list[float]] = {}
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % sample_every == 0:
            for d in per.detect(frame):
                hits.setdefault(d.label, []).append(d.conf)
        idx += 1
    cap.release()
    rows = [
        {"label": k, "detections": len(v),
         "mean_conf": round(sum(v) / len(v), 3), "max_conf": round(max(v), 3)}
        for k, v in sorted(hits.items(), key=lambda kv: -len(kv[1]))
    ]
    likely_wrong = [r for r in rows if r["label"] in ("horse", "sheep", "elephant")]
    return {
        "frames_sampled": idx // sample_every,
        "labels": rows,
        "probable_misclassification": likely_wrong,
        "interpretation": (
            "Labels such as horse, sheep and elephant on a clip of cattle are "
            "almost certainly the detector confusing large quadrupeds. This is "
            "hazard H19 observed on real data. It fails SAFE: every one of "
            "those labels is a non-target, so the governor vetoes emission "
            "rather than acting on a misread animal."
        ),
    }
