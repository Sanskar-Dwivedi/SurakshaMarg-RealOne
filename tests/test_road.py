"""
Tests for the road occupancy and violation watch.

Synthetic tracks, not video: every threshold here is a duration or a speed, and
both are far easier to state exactly in a fixture than to provoke from footage.
The video path is covered separately.
"""

from __future__ import annotations

import pytest

from gaukavach.detect import Site, Track
from gaukavach.road import (PERSON_IN_LANE, STOPPED_IN_LANE, WRONG_WAY,
                            Incident, RoadWatch, polygon_area_m2)

SITE = Site(
    name="test crossing",
    carriageway=((240, 470), (1040, 470), (1180, 700), (100, 700)),
    warning_zone=((330, 330), (960, 330), (1260, 719), (20, 719)),
    emitter_px=(640, 719),
)


def track(label: str, pts, tid="T1") -> Track:
    """A track whose history is the given image points, ending at the last."""
    x, y = pts[-1]
    return Track(track_id=tid, label=label, xyxy=(x - 20, y - 40, x + 20, y),
                 conf=0.9, history=list(pts))


def run(watch: RoadWatch, tracks, seconds, fps=10.0):
    """Drive the watch for `seconds`, returning the last frame's result."""
    out = {}
    steps = int(seconds * fps)
    for i in range(steps + 1):
        out = watch.step(tracks, now_s=i / fps, fps=fps, frame_index=i)
    return out


def test_polygon_area_is_the_shoelace_area():
    assert polygon_area_m2([(0, 0), (10, 0), (10, 5), (0, 5)]) == pytest.approx(50.0)
    assert polygon_area_m2([(0, 0), (1, 1)]) == 0.0          # degenerate


def test_carriageway_area_is_positive_and_finite():
    area = RoadWatch(site=SITE).carriageway_area_m2()
    assert area > 0 and area < 1e6, f"implausible carriageway area {area}"


# -- crowding ---------------------------------------------------------------

def test_crowd_counts_only_people_actually_on_the_carriageway():
    w = RoadWatch(site=SITE)
    on = track("person", [(640, 600)], tid="P1")
    off = track("person", [(640, 200)], tid="P2")     # above the road, on the verge
    cow = track("cow", [(640, 600)], tid="C1")
    reading = w.crowd([on, off, cow])
    assert reading.count == 1, "only the person inside the polygon counts"


def test_crowd_level_rises_with_the_count():
    w = RoadWatch(site=SITE)
    one = w.crowd([track("person", [(640, 600)], tid="P0")])
    many = w.crowd([track("person", [(500 + i * 12, 600)], tid=f"P{i}")
                    for i in range(60)])
    assert many.per_100m2 > one.per_100m2
    assert (one.level, many.level) != (many.level, one.level)
    assert many.level in {"busy", "crowded"}


def test_an_empty_road_reads_clear():
    assert RoadWatch(site=SITE).crowd([]).level == "clear"


# -- wrong way --------------------------------------------------------------

def _toward_camera(tid="V1"):
    """A vehicle moving DOWN the image, i.e. toward the camera (-Z)."""
    return track("car", [(640, 500), (640, 540), (640, 580), (640, 620)], tid=tid)


def _away_from_camera(tid="V2"):
    """A vehicle moving UP the image, away from the camera (+Z)."""
    return track("car", [(640, 620), (640, 580), (640, 540), (640, 500)], tid=tid)


def test_a_vehicle_against_the_flow_is_flagged():
    w = RoadWatch(site=SITE, flow_dz=1.0)
    out = run(w, [_toward_camera()], seconds=3.0)
    kinds = {e["kind"] for e in out["active"]}
    assert WRONG_WAY in kinds


def test_a_vehicle_with_the_flow_is_not_flagged():
    w = RoadWatch(site=SITE, flow_dz=1.0)
    out = run(w, [_away_from_camera()], seconds=3.0)
    assert not [e for e in out["active"] if e["kind"] == WRONG_WAY]


def test_flow_direction_is_configurable_per_site():
    """The same track is a violation at one site and normal at its mirror."""
    a = run(RoadWatch(site=SITE, flow_dz=1.0), [_toward_camera()], 3.0)
    b = run(RoadWatch(site=SITE, flow_dz=-1.0), [_toward_camera()], 3.0)
    assert bool([e for e in a["active"] if e["kind"] == WRONG_WAY])
    assert not [e for e in b["active"] if e["kind"] == WRONG_WAY]


def test_a_crawling_vehicle_does_not_get_a_direction():
    """Below min_speed_ms the direction is tracker noise, not travel."""
    w = RoadWatch(site=SITE, flow_dz=1.0, min_speed_ms=50.0)
    out = run(w, [_toward_camera()], seconds=3.0)
    assert not [e for e in out["active"] if e["kind"] == WRONG_WAY]


# -- stopped in lane --------------------------------------------------------

def test_a_stationary_vehicle_in_a_lane_is_flagged():
    w = RoadWatch(site=SITE)
    still = track("car", [(640, 600)] * 6, tid="V3")
    out = run(w, [still], seconds=3.0)
    assert STOPPED_IN_LANE in {e["kind"] for e in out["active"]}


def test_a_stationary_vehicle_off_the_road_is_ignored():
    w = RoadWatch(site=SITE)
    parked = track("car", [(640, 200)] * 6, tid="V4")
    out = run(w, [parked], seconds=3.0)
    assert not out["active"]


# -- people in the lane -----------------------------------------------------

def test_a_person_in_the_lane_is_flagged():
    w = RoadWatch(site=SITE)
    out = run(w, [track("person", [(640, 600)] * 4, tid="P9")], seconds=3.0)
    assert PERSON_IN_LANE in {e["kind"] for e in out["active"]}


def test_a_cow_in_the_lane_is_not_a_road_violation():
    """Cattle are the governor's business, not the violation watch's."""
    w = RoadWatch(site=SITE)
    out = run(w, [track("cow", [(640, 600)] * 4, tid="C9")], seconds=3.0)
    assert not out["active"]


# -- the warn / escalate ladder ---------------------------------------------

def test_nothing_fires_before_the_confirm_window():
    w = RoadWatch(site=SITE, confirm_s=1.5)
    out = run(w, [track("person", [(640, 600)] * 4, tid="P3")], seconds=1.0)
    assert out["active"] == [] and out["warn"] == [] and out["escalate"] == []


def test_a_brief_event_never_warns():
    """Someone crossing normally is in the lane for a moment and then gone."""
    w = RoadWatch(site=SITE, warn_after_s=2.5)
    p = track("person", [(640, 600)] * 4, tid="P4")
    for i in range(15):                       # 1.5 s at 10 fps
        w.step([p], now_s=i / 10.0, fps=10.0, frame_index=i)
    out = w.step([], now_s=1.6, fps=10.0, frame_index=16)   # they leave
    assert out["warn"] == [] and w.incidents == []


def test_warning_comes_before_escalation_and_only_once():
    w = RoadWatch(site=SITE, warn_after_s=2.5, escalate_after_s=8.0)
    p = track("person", [(640, 600)] * 4, tid="P5")
    warns = escalations = 0
    for i in range(121):                      # 12 s at 10 fps
        out = w.step([p], now_s=i / 10.0, fps=10.0, frame_index=i)
        warns += len(out["warn"])
        escalations += len(out["escalate"])
    assert warns == 1, "the speaker must not re-warn every frame"
    assert escalations == 1, "the operator must not get the same event repeatedly"


def test_escalation_carries_evidence():
    w = RoadWatch(site=SITE, escalate_after_s=3.0)
    p = track("person", [(640, 600)] * 4, tid="P6")
    for i in range(61):
        out = w.step([p], now_s=i / 10.0, fps=10.0, frame_index=i)
        if out["escalate"]:
            inc = out["escalate"][0]
            assert inc["evidence_frame"] == i
            assert inc["duration_s"] >= 3.0
            assert inc["detail"]
            return
    pytest.fail("never escalated")


# -- the line this module exists to hold ------------------------------------

def test_an_escalated_incident_is_not_reported_to_anyone():
    w = RoadWatch(site=SITE, escalate_after_s=2.0)
    p = track("person", [(640, 600)] * 4, tid="P7")
    for i in range(61):
        w.step([p], now_s=i / 10.0, fps=10.0, frame_index=i)
    assert w.incidents, "expected an incident to exist"
    assert all(not i.authority_notified for i in w.incidents), (
        "nothing in this module may notify an authority automatically"
    )
    assert all(i.notified_by == "" for i in w.incidents)


def test_only_a_named_person_can_mark_an_incident_notified():
    w = RoadWatch(site=SITE)
    inc = Incident(kind=PERSON_IN_LANE, track_id="P8", label="person",
                   raised_at_s=1.0, duration_s=9.0, detail="x", evidence_frame=3)
    with pytest.raises(ValueError):
        w.mark_notified(inc, "   ")
    assert not inc.authority_notified
    w.mark_notified(inc, "Control room operator 4")
    assert inc.authority_notified and inc.notified_by == "Control room operator 4"


def test_the_module_never_sets_the_notified_flag_itself():
    """
    A grep-level guard. If a future edit wires a machine into this field, the
    distinction between an automated accusation and a human one is gone, and
    every claim made about this module stops being true.
    """
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "src" / "gaukavach" / "road.py"
    text = src.read_text(encoding="utf-8")
    setters = [l.strip() for l in text.splitlines()
               if "authority_notified" in l and "=" in l
               and "False" not in l and "def " not in l
               and not l.strip().startswith(("#", "*", '"'))]
    assert setters == ["incident.authority_notified = True"], (
        f"authority_notified is set somewhere unexpected: {setters}"
    )


# -- regressions: bugs the first twenty tests did not catch ------------------

def _rolling(tid, pts_per_frame, frames, start=(640, 600), keep=8):
    """Yield a track whose history rolls forward by pts_per_frame each frame."""
    hist = [start] * keep
    for i in range(frames):
        dx, dy = pts_per_frame
        hist.append((hist[-1][0] + dx, hist[-1][1] + dy))
        x, y = hist[-1]
        yield Track(tid, "car", (x - 20, y - 40, x + 20, y), 0.9,
                    history=list(hist[-keep:]))


def test_an_event_clears_when_its_condition_stops_not_when_the_track_leaves():
    """
    A car stops, is flagged, then drives off while staying in shot.

    The first version keyed the clear-up on whether the TRACK was still
    visible, so the car stayed listed as stopped for as long as it remained on
    camera, with a frozen duration.
    """
    w = RoadWatch(site=SITE)
    still = track("car", [(640, 600)] * 8, tid="V10")
    for i in range(40):
        out = w.step([still], now_s=i / 10.0, fps=10.0, frame_index=i)
    assert STOPPED_IN_LANE in {e["kind"] for e in out["active"]}

    for i, t in enumerate(_rolling("V10", (40, 0), 40), start=40):
        out = w.step([t], now_s=i / 10.0, fps=10.0, frame_index=i)
    assert w.ground_speed_ms(t, 10.0) > 1.0, "fixture is not actually moving"
    assert not out["active"], "the event outlived the condition that raised it"


def test_stopping_twice_does_not_escalate_on_the_second_stop():
    """
    The dangerous form of the same bug: because the event was never cleared,
    a later `_observe` advanced last_seen_s against the ORIGINAL first_seen_s,
    so duration jumped straight past escalate_after_s and put a human onto a
    car that had merely braked twice.
    """
    w = RoadWatch(site=SITE, escalate_after_s=8.0)
    escalations = 0
    still = track("car", [(640, 600)] * 8, tid="V11")
    for i in range(40):                                   # 4 s stopped
        escalations += len(w.step([still], i / 10.0, 10.0, i)["escalate"])
    for i, t in enumerate(_rolling("V11", (40, 0), 40), start=40):
        escalations += len(w.step([t], i / 10.0, 10.0, i)["escalate"])
    again = track("car", [(300, 600)] * 8, tid="V11")
    for i in range(80, 110):                              # 3 s stopped again
        escalations += len(w.step([again], i / 10.0, 10.0, i)["escalate"])
    assert escalations == 0, "neither stop lasted 8 s; nobody should be called"


def test_speed_is_read_from_a_bounded_window_not_the_whole_track_life():
    """
    History belongs to the caller's tracker and may cover the whole life of the
    track. Measured end to end, a vehicle that drove in and then parked keeps
    reporting the speed of its arrival and never reads as stopped.
    """
    w = RoadWatch(site=SITE, speed_window=6)
    arrived_then_parked = [(200 + i * 40, 600) for i in range(10)] + [(600, 600)] * 10
    t = track("car", arrived_then_parked, tid="V12")
    assert w.ground_speed_ms(t, 10.0) < w.stopped_speed_ms, (
        "a parked car is still being credited with the speed it arrived at"
    )


def test_direction_and_speed_agree_about_which_interval_they_describe():
    """Wrong-way reads the same trailing window as the speed gate before it."""
    w = RoadWatch(site=SITE, flow_dz=1.0, speed_window=4)
    reversed_recently = [(640, 640)] * 6 + [(640, 620), (640, 600), (640, 580)]
    t = track("car", reversed_recently, tid="V13")
    pts = w._window(t)
    assert len(pts) == 4, "the window is not the size it claims"
    assert pts == reversed_recently[-4:]
