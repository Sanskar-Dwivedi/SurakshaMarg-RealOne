"""
OpenCV renderer - the same engine, drawn onto pixels.

Two jobs:

  1. `render_scenario()` writes an MP4 of a synthetic scenario. Useful for
     slides, and for the case where the demo laptop cannot be trusted with a
     browser at the critical moment.

  2. `render_video()` overlays the live decision loop on REAL dashcam or CCTV
     footage using YOLO detections. This is the answer to "is any of this real?"
     - the perception is genuinely running, and every overlay is drawn from the
     same governor the tests exercise.

Every frame is watermarked. A frame from `render_scenario` says SIMULATED
because the animals are synthetic; a frame from `render_video` says
UNCALIBRATED because the distances depend on camera parameters nobody has
measured for that clip. Neither is allowed to look like a field result.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from . import evidence as ev
from .acoustics import Atmosphere
from .detect import DEMO_SITE, SimpleTracker, Site
from .ledger import Ledger
from .policy import EngineConfig, PolicyEngine
from .scenario import SCENARIOS
from .species import SPECIES, TARGET_KEY, species_for_label

SITE_ATM = Atmosphere(temp_c=32.0, rh_pct=60.0, ambient_spl_db=58.0)

# BGR, tuned to stay legible when a projector crushes the gamma.
INK = (36, 26, 20)
OK = (95, 160, 60)
CRIT = (44, 48, 190)
WARN = (30, 150, 220)
ACCENT = (140, 130, 20)
PAPER = (244, 242, 238)
ROAD = (120, 118, 112)
GRASS = (150, 178, 168)
SKY = (216, 208, 196)


def _cv():
    import cv2  # noqa: PLC0415
    return cv2


def _poly(cv, img, pts, color, thickness=2, closed=True):
    cv.polylines(img, [np.array(pts, np.int32)], closed, color, thickness, cv.LINE_AA)


def _label(cv, img, text, org, bg, fg=(255, 255, 255), scale=0.5, pad=5):
    (w, h), _ = cv.getTextSize(text, cv.FONT_HERSHEY_SIMPLEX, scale, 1)
    x, y = int(org[0]), int(org[1])
    cv.rectangle(img, (x, y - h - 2 * pad), (x + w + 2 * pad, y), bg, -1)
    cv.putText(img, text, (x + pad, y - pad), cv.FONT_HERSHEY_SIMPLEX, scale, fg, 1, cv.LINE_AA)
    return w + 2 * pad


def _backdrop(cv, site: Site, w: int, h: int) -> np.ndarray:
    """Synthetic road scene, for scenario rendering."""
    img = np.zeros((h, w, 3), np.uint8)
    img[: int(site.horizon_y)] = SKY
    img[int(site.horizon_y):] = GRASS
    cw = [list(p) for p in site.carriageway]
    wide = [[cw[0][0] - 70, cw[0][1]], [cw[1][0] + 70, cw[1][1]],
            [cw[2][0] + 90, cw[2][1]], [cw[3][0] - 90, cw[3][1]]]
    cv.fillPoly(img, [np.array(wide, np.int32)], ROAD)
    # centre line
    x0 = int((cw[0][0] + cw[1][0]) / 2)
    x1 = int((cw[2][0] + cw[3][0]) / 2)
    y0, y1 = int(cw[0][1]), int(cw[2][1])
    n = 9
    for i in range(0, n, 2):
        a = (int(x0 + (x1 - x0) * i / n), int(y0 + (y1 - y0) * i / n))
        b = (int(x0 + (x1 - x0) * (i + 1) / n), int(y0 + (y1 - y0) * (i + 1) / n))
        cv.line(img, a, b, (225, 225, 225), 3, cv.LINE_AA)
    return img


def _silhouette(cv, img, xyxy, label, color) -> None:
    """
    Simple filled body so a synthetic actor is visible inside its box.

    Only used for scenario rendering. On real footage the animal is already in
    the pixels and drawing over it would be dishonest.
    """
    x1, y1, x2, y2 = (int(v) for v in xyxy)
    w, h = max(x2 - x1, 2), max(y2 - y1, 2)
    if label == "person":
        cx = x1 + w // 2
        cv.circle(img, (cx, y1 + int(h * 0.12)), max(int(w * 0.30), 3), color, -1, cv.LINE_AA)
        cv.fillPoly(img, [np.array([
            [cx - int(w * .30), y2], [cx - int(w * .22), y1 + int(h * .26)],
            [cx + int(w * .22), y1 + int(h * .26)], [cx + int(w * .30), y2]], np.int32)],
            color, cv.LINE_AA)
        return
    by = y1 + int(h * 0.10)
    bh = int(h * 0.52)
    cv.ellipse(img, (x1 + int(w * .46), by + bh // 2),
               (int(w * .40), max(bh // 2, 2)), 0, 0, 360, color, -1, cv.LINE_AA)
    lw = max(int(w * .07), 2)
    for fx in (.20, .36, .62, .80):
        px = x1 + int(w * fx)
        cv.rectangle(img, (px - lw // 2, by + int(bh * .85)), (px + lw // 2, y2 - int(h * .06)),
                     color, -1)
    cv.ellipse(img, (x1 + int(w * .86), by + int(bh * .34)),
               (max(int(w * .15), 2), max(int(bh * .30), 2)), -15, 0, 360, color, -1, cv.LINE_AA)
    if label == "cow":
        cv.line(img, (x1 + int(w * .88), by + int(bh * .12)),
                (x1 + int(w * .99), by - int(bh * .06)), color, max(int(w * .04), 2), cv.LINE_AA)
        cv.line(img, (x1 + int(w * .79), by + int(bh * .12)),
                (x1 + int(w * .68), by - int(bh * .06)), color, max(int(w * .04), 2), cv.LINE_AA)


def _draw_overlay(cv, img, site: Site, tracks, snap, watermark: str, t: float,
                  silhouettes: bool = False) -> None:
    """Draw zones, tracks, flight vectors and the decision panel."""
    h, w = img.shape[:2]

    _poly(cv, img, site.warning_zone, WARN, 2)
    _poly(cv, img, site.carriageway, CRIT, 2)
    _label(cv, img, "WARNING ZONE", (site.warning_zone[0][0] + 6,
                                     site.warning_zone[0][1] - 6), WARN, scale=0.45)
    _label(cv, img, "CARRIAGEWAY", (site.carriageway[0][0] + 6,
                                    site.carriageway[0][1] + 22), CRIT, scale=0.45)

    acts = snap["actions"]
    emitting = any(a["action"] == "emit" for a in acts)
    denied = any(a["action"] == "denied" for a in acts)
    verdict_col = OK if emitting else (CRIT if denied else WARN)

    # emitter mast + pulse
    ex, ey = int(site.emitter_px[0]), int(site.emitter_px[1])
    cv.line(img, (ex, ey), (ex, ey - 60), INK, 5, cv.LINE_AA)
    cv.circle(img, (ex, ey - 66), 10, INK, -1, cv.LINE_AA)
    cv.circle(img, (ex, ey - 66), 6, ACCENT, -1, cv.LINE_AA)
    if emitting:
        for k in range(3):
            r = ((t * 1.4 + k * 0.33) % 1.0)
            cv.ellipse(img, (ex, ey), (int(r * 560), int(r * 210)),
                       0, 180, 360, ACCENT, 2, cv.LINE_AA)

    for tr in tracks:
        if site.classify_position(tr.foot_point) == "outside":
            continue
        x1, y1, x2, y2 = (int(v) for v in tr.xyxy)
        profiles = species_for_label(tr.label)
        name = profiles[0].name if profiles else tr.label
        target = tr.label == "cow"
        outhears = bool(profiles and profiles[0].hearing_high_hz
                        > SPECIES[TARGET_KEY].hearing_high_hz)
        col = ACCENT if target else CRIT
        if silhouettes:
            _silhouette(cv, img, tr.xyxy, tr.label, INK if target else col)
        cv.rectangle(img, (x1, y1), (x2, y2), col, 2, cv.LINE_AA)
        dist = site.estimate_distance_m(tr.foot_point)
        used = _label(cv, img, f"{name} {dist:.1f}m", (x1, y1), col, scale=0.5)
        if outhears:
            _label(cv, img, "OUT-HEARS TARGET", (x1 + used + 4, y1), CRIT, scale=0.42)

        if target:
            fl = site.flight_assessment(tr.foot_point, ev.get("flight_vector_check_m"))
            vx, vz = fl["flight_vector"]
            fx, fy = int(tr.foot_point[0]), int(tr.foot_point[1])
            ang = np.arctan2(-vz, vx)
            gx, gy = int(fx + np.cos(ang) * 105), int(fy + np.sin(ang) * 105)
            fcol = OK if fl["safe"] else CRIT
            cv.arrowedLine(img, (fx, fy), (gx, gy), fcol, 4, cv.LINE_AA, tipLength=0.3)
            tag = ("ESCAPE CLEAR" if fl["safe"]
                   else ("ALREADY ON ROAD" if fl["already_in_hazard"] else "FLEES ONTO ROAD"))
            _label(cv, img, tag, (gx - 60, gy - 8), fcol, scale=0.45)

    # decision panel
    panel_h = 132
    sub = img[h - panel_h:h, 0:w].copy()
    cv.rectangle(sub, (0, 0), (w, panel_h), (28, 22, 18), -1)
    cv.addWeighted(sub, 0.78, img[h - panel_h:h, 0:w], 0.22, 0, img[h - panel_h:h, 0:w])
    y = h - panel_h + 26

    state = ("EMITTING" if emitting else "REFUSED" if denied
             else "ESCALATED" if any(a["action"] == "escalate" for a in acts)
             else "OUT OF RANGE" if any(a["action"] == "out_of_range" for a in acts)
             else "MONITORING")
    cv.putText(img, state, (18, y), cv.FONT_HERSHEY_SIMPLEX, 0.85, verdict_col, 2, cv.LINE_AA)
    cv.putText(img, f"t={t:5.1f}s", (w - 130, y), cv.FONT_HERSHEY_SIMPLEX,
               0.6, PAPER, 1, cv.LINE_AA)

    line = y + 26
    em = next((a for a in acts if a["action"] == "emit"), None)
    if em:
        txt = (f"{em['carrier_khz']} kHz  {em['level_at_1m_db']} dB@1m  ->  "
               f"{em['received_db']} dB at animal   P(turn) {em['p_response']}")
        cv.putText(img, txt, (18, line), cv.FONT_HERSHEY_SIMPLEX, 0.52, OK, 1, cv.LINE_AA)
        line += 22
    for a in acts:
        if a["action"] == "denied":
            for d in a.get("denials", [])[:3]:
                cv.putText(img, "x  " + d[:88], (18, line),
                           cv.FONT_HERSHEY_SIMPLEX, 0.48, CRIT, 1, cv.LINE_AA)
                line += 20
            break
        if a["action"] in ("escalate", "out_of_range"):
            cv.putText(img, a.get("reason", "")[:92], (18, line),
                       cv.FONT_HERSHEY_SIMPLEX, 0.48, WARN, 1, cv.LINE_AA)
            line += 20
            break

    _label(cv, img, watermark, (16, 30), CRIT, scale=0.5)


def render_scenario(
    name: str,
    out: str = "gaukavach_demo.mp4",
    site: Site = DEMO_SITE,
    atm: Atmosphere = SITE_ATM,
    fps: int = 15,
    size: tuple[int, int] = (1280, 720),
) -> str:
    """Render one synthetic scenario to MP4."""
    cv = _cv()
    if name not in SCENARIOS:
        raise KeyError(f"unknown scenario {name!r}")
    sc = SCENARIOS[name]
    engine = PolicyEngine(site, atm, Ledger(), EngineConfig())
    tracker = SimpleTracker()
    w, h = size
    writer = cv.VideoWriter(out, cv.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    if not writer.isOpened():
        raise RuntimeError(f"could not open {out} for writing")

    repeat = max(int(round(fps / sc.fps)), 1)
    for t, dets in sc.frames():
        tracks = tracker.update(dets)
        snap = engine.step(tracks, t)
        for _ in range(repeat):
            img = _backdrop(cv, site, w, h)
            _draw_overlay(cv, img, site, tracks, snap,
                          "SIMULATED - no hardware, no animals", t, silhouettes=True)
            _label(cv, img, sc.name, (16, h - 148), ACCENT, scale=0.5)
            writer.write(img)
    engine.close()
    writer.release()
    return out


def render_video(
    path: str,
    out: str | None = "gaukavach_overlay.mp4",
    weights: str = "yolov8n.pt",
    conf: float = 0.35,
    stride: int = 1,
    max_frames: int = 0,
    site: Site = DEMO_SITE,
    atm: Atmosphere = SITE_ATM,
    show: bool = False,
) -> str:
    """
    Overlay the live decision loop on real footage.

    The geometry is NOT calibrated for an arbitrary clip, so distances are
    indicative only. The watermark says so on every frame, because a plausible
    number on top of real video is exactly the kind of thing that gets believed.
    """
    cv = _cv()
    from .detect import Perception  # noqa: PLC0415

    per = Perception(weights=weights, conf=conf)
    if not per.available:
        raise RuntimeError(f"YOLO unavailable: {per.error}")

    cap = cv.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {path}")
    fps = cap.get(cv.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))

    engine = PolicyEngine(site, atm, Ledger(), EngineConfig())
    tracker = SimpleTracker()
    writer = None
    if out:
        writer = cv.VideoWriter(out, cv.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % max(stride, 1) == 0:
            dets = per.detect(frame)
            tracks = tracker.update(dets)
            snap = engine.step(tracks, idx / fps)
            _draw_overlay(cv, frame, site, tracks, snap,
                          "UNCALIBRATED - distances indicative only", idx / fps)
            if writer:
                writer.write(frame)
            if show:
                cv.imshow("GauKavach", frame)
                if cv.waitKey(1) & 0xFF == 27:
                    break
        idx += 1
        if max_frames and idx >= max_frames:
            break

    cap.release()
    if writer:
        writer.release()
    if show:
        cv.destroyAllWindows()
    engine.close()
    return out or path


def render_all(outdir: str = "media", fps: int = 15) -> list[str]:
    """Render every scenario. Gives a clip per talking point."""
    Path(outdir).mkdir(parents=True, exist_ok=True)
    made = []
    for name in SCENARIOS:
        p = str(Path(outdir) / f"{name}.mp4")
        render_scenario(name, p, fps=fps)
        made.append(p)
    return made
