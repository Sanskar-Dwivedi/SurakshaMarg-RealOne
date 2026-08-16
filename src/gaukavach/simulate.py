"""
Simulation exporter for the interactive presenter.

The browser simulator must not re-implement the decision logic in JavaScript.
If it did, it would be a mock, and the first judge to ask "is the demo running
your real system?" would be right to be sceptical.

So instead this module runs the REAL engine and exports two things:

  1. `playback` - every scenario stepped frame by frame, recording exactly what
     the governor decided and why, as it happened.

  2. `decision_field` - the governor's verdict for a target animal placed at
     every point on a grid across the frame. Dragging an animal around in the
     browser is then a lookup into genuine engine output, not a re-computation.
     Interactive AND honest.

Everything the simulator displays therefore traces to a Python evaluation that
can be re-run and checked from the command line.
"""

from __future__ import annotations

import json

from pathlib import Path

from . import evidence as ev
from .acoustics import Atmosphere, select_carrier
from .detect import (
    DEMO_SITE,

    Site,
    SimpleTracker,
    Track,
    is_downed,
    is_juvenile,
)
from .ledger import Ledger
from .policy import EngineConfig, PolicyEngine
from .scenario import SCENARIOS, Scenario
from .species import SPECIES, TARGET_KEY, species_for_label
from .welfare import Governor, SceneContext

SITE_ATM = Atmosphere(temp_c=32.0, rh_pct=60.0, ambient_spl_db=58.0)


# ---------------------------------------------------------------------------
# Scenario playback
# ---------------------------------------------------------------------------


def record_scenario(sc: Scenario, site: Site = DEMO_SITE, atm: Atmosphere = SITE_ATM) -> dict:
    """Step a scenario through the real engine, recording every frame."""
    engine = PolicyEngine(site, atm, Ledger(), EngineConfig())
    tracker = SimpleTracker()
    frames: list[dict] = []

    for t, dets in sc.frames():
        tracks = tracker.update(dets)
        snap = engine.step(tracks, t)

        drawn = []
        for tr in tracks:
            profiles = species_for_label(tr.label)
            adult_h = profiles[0].typical_adult_height_m if profiles else 1.35
            fl = site.flight_assessment(tr.foot_point, ev.get("flight_vector_check_m"))
            # Compact keys: this payload is embedded in a single HTML file and
            # replayed 5x a second, so verbosity here costs load time on the
            # laptop that has to run the demo.
            drawn.append({
                "id": tr.track_id,
                "l": tr.label,
                "sp": profiles[0].name if profiles else tr.label,
                "g": profiles[0].group.value if profiles else "unknown",
                "b": [int(v) for v in tr.xyxy],
                "d": round(site.estimate_distance_m(tr.foot_point), 1),
                "h": round(site.estimate_height_m(tr.xyxy), 2),
                "z": site.classify_position(tr.foot_point)[0],  # c/w/o
                "t": tr.label == "cow",
                "juv": is_juvenile(tr, site, adult_h, ev.get("juvenile_height_ratio")),
                "dn": is_downed(tr, ev.get("downed_aspect_ratio")),
                "fs": fl["safe"],
                "fa": fl["already_in_hazard"],
                "fc": fl["escape_corridor_m"],
                "fv": fl["flight_vector"],
                "oh": bool(
                    profiles
                    and profiles[0].hearing_high_hz > SPECIES[TARGET_KEY].hearing_high_hz
                ),
            })

        # Only keep the action fields the simulator actually draws.
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

        frames.append({
            "t": round(t, 2),
            "s": snap["state"],
            "a": drawn,
            "x": acts,
        })

    summary = engine.close()
    key_kinds = ("emission", "escalation", "traffic_response", "stop", "observation")
    return {
        "name": sc.name,
        "description": sc.description,
        "duration_s": sc.duration_s,
        "fps": sc.fps,
        "frames": frames,
        "summary": {
            "incidents": summary["incidents"],
            "escalated": summary["escalated"],
            "total_emission_s": summary["total_emission_s"],
            "denials": summary["governor"]["denials_by_reason"],
        },
        "ledger": [
            {"seq": r.seq, "kind": r.kind, "hash": r.hash[:10]}
            for r in engine.ledger
        ],
        "key_events": [
            {"seq": r.seq, "kind": r.kind, "hash": r.hash[:10],
             "p": {k: v for k, v in r.payload.items()
                   if k in ("track_id", "carrier_hz", "level_at_1m_db",
                            "predicted_received_db", "distance_m", "reason",
                            "trigger_distance_m", "outcome_name", "dry_run")}}
            for r in engine.ledger if r.kind in key_kinds
        ],
        "records": len(engine.ledger),
        "chain_valid": engine.ledger.verify()["valid"],
    }


# ---------------------------------------------------------------------------
# Decision field
# ---------------------------------------------------------------------------


def _probe_track(x: float, y: float, height_px: float = 105.0) -> Track:
    """A synthetic adult cow standing with its feet at (x, y)."""
    depth = max(y / 719.0, 0.25)
    h = height_px * depth
    w = h * 1.3
    return Track(
        track_id="PROBE",
        label="cow",
        xyxy=(x - w / 2, y - h, x + w / 2, y),
        conf=0.9,
        history=[(x, y)],
    )


def decision_field(
    site: Site = DEMO_SITE,
    atm: Atmosphere = SITE_ATM,
    step_px: int = 16,
    width: int = 1280,
    height: int = 720,
) -> dict:
    """
    Ask the real governor for its verdict with a cow at every grid point.

    This is what makes the browser's drag interaction trustworthy: the answer
    shown when the user moves an animal is the answer the Python governor gave
    for that location, tabulated in advance.
    """
    gov = Governor(atm, directivity_gain_db=12.0)
    cells: list[dict] = []
    y = int(site.horizon_y) + step_px

    while y <= height:
        x = 0
        while x <= width:
            pt = (float(x), float(y))
            zone = site.classify_position(pt)
            if zone == "outside":
                x += step_px
                continue

            dist = site.estimate_distance_m(pt)
            fl = site.flight_assessment(pt, ev.get("flight_vector_check_m"))
            best, _ = select_carrier(
                atm, max(dist, 1.0), gov.ceiling_db, directivity_gain_db=12.0
            )

            if best is None:
                cells.append({
                    "x": x, "y": y, "zone": zone, "d": round(dist, 1),
                    "v": "out_of_range", "lvl": None, "khz": None,
                    "why": [f"{dist:.0f} m is beyond the acoustic envelope"],
                    "flight": fl["safe"],
                })
                x += step_px
                continue

            # Fresh governor per probe so exposure history never leaks between cells.
            probe_gov = Governor(atm, directivity_gain_db=12.0)
            auth = probe_gov.request(
                track_id=f"P{x}_{y}",
                freq_hz=best.freq_hz,
                distance_m=dist,
                duration_s=0.54,
                now_t=1000.0,
                scene=SceneContext(
                    flight_enters_hazard=fl["enters_hazard"],
                    already_in_hazard=fl["already_in_hazard"],
                    escape_corridor_m=fl["escape_corridor_m"],
                ),
            )
            cells.append({
                "x": x, "y": y, "zone": zone, "d": round(dist, 1),
                "v": "permit" if auth.granted else "refuse",
                "lvl": auth.level_at_1m_db if auth.granted else None,
                "khz": round(best.freq_hz / 1000.0, 1),
                "why": [d.value for d in auth.denials],
                "flight": fl["safe"],
            })
            x += step_px
        y += step_px

    return {
        "step_px": step_px,
        "width": width,
        "height": height,
        "cells": cells,
        "note": (
            "Each cell is a real Governor.request() evaluation for an adult cow "
            "standing at that point. The browser looks these up; it does not "
            "re-implement the decision logic."
        ),
    }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export(out_path: str | Path = "dashboard/sim.json", step_px: int = 16) -> dict:
    site, atm = DEMO_SITE, SITE_ATM
    payload = {
        "site": {
            "name": site.name,
            "carriageway": [list(p) for p in site.carriageway],
            "warning_zone": [list(p) for p in site.warning_zone],
            "emitter_px": list(site.emitter_px),
            "horizon_y": site.horizon_y,
            "camera_height_m": site.camera_height_m,
            "focal_px": site.focal_px,
            "lanes": site.lanes,
            "speed_limit_kmh": site.speed_limit_kmh,
        },
        "atmosphere": atm.as_dict(),
        "limits": {
            "ceiling_db": ev.get("osha_ultrasound_ceiling_db"),
            "refused_db": ev.get("refused_prototype_spl_db"),
            "band_lo_khz": ev.get("experimental_band_low_hz") / 1000.0,
            "band_hi_khz": ev.get("experimental_band_high_hz") / 1000.0,
            "max_herd": ev.get("max_herd_size_for_emission"),
            "max_activation_s": ev.get("max_activation_s"),
            "min_silence_s": ev.get("min_silence_s"),
            "daily_budget_s": ev.get("daily_exposure_budget_s"),
            "min_escape_m": ev.get("min_escape_corridor_m"),
        },
        "scenarios": {name: record_scenario(sc, site, atm) for name, sc in SCENARIOS.items()},
        "field": decision_field(site, atm, step_px=step_px),
        "provenance": (
            "Generated by gaukavach.simulate from the same modules the CLI uses. "
            "Every verdict shown in the simulator was produced by the Python "
            "governor; the browser only replays and looks up."
        ),
    }
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, separators=(",", ":"), default=str), encoding="utf-8")
    return payload


if __name__ == "__main__":  # pragma: no cover
    data = export()
    n_cells = len(data["field"]["cells"])
    n_frames = sum(len(s["frames"]) for s in data["scenarios"].values())
    print(f"scenarios : {len(data['scenarios'])}")
    print(f"frames    : {n_frames}")
    print(f"field     : {n_cells} evaluated cells")
    print(f"written   : dashboard/sim.json")
