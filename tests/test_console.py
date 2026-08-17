"""
The operations console must be rebuildable from the repository.

The built page is ~6.5 MB of data wrapped around ~45 KB of code. For a long
time only the built page existed, and it was gitignored, so the console's
source of truth was a binary sitting on one laptop: edits to it were never
committed, and a clean checkout could not produce the page at all.

The split fixes that - the code is tracked as a template, the payloads are
generated data - and these tests keep it split.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "dashboard" / "simulator_template.html"

PAYLOAD_IDS = ("sim", "foot", "outc")


def test_the_template_is_tracked():
    assert TEMPLATE.is_file(), (
        "dashboard/simulator_template.html is missing - the console cannot be "
        "rebuilt without it, and the built page is gitignored")


def test_the_template_carries_code_not_data():
    """
    A template that has drifted back into holding its payloads is a template
    in name only: it stops being reviewable in a diff and starts being another
    multi-megabyte binary.
    """
    text = TEMPLATE.read_text(encoding="utf-8")
    size_kb = len(text.encode("utf-8")) / 1024
    assert size_kb < 400, (
        f"template is {size_kb:.0f} KB - a payload has been baked back into "
        f"it; run 'gaukavach sim' to inject data at build time instead")

    for pid in PAYLOAD_IDS:
        marker = f'<script id="{pid}" type="application/json">'
        i = text.find(marker)
        assert i >= 0, f"template has no injection point for '{pid}'"
        body = text[i + len(marker): text.find("</script>", i)]
        assert not body.strip(), f"'{pid}' payload is baked into the template"


def test_the_console_can_drive_the_board_with_the_situation_only():
    """
    The board runs its own governor. The bridge must send it inputs, never a
    verdict - otherwise the lamps are just a remote display and agreement
    between the page and the board proves nothing.
    """
    text = TEMPLATE.read_text(encoding="utf-8")
    assert 'id="linkBtn"' in text, "no board link control in the console"

    body = text[text.find("function driveBoard"):]
    body = body[:body.find("\nfunction ")]
    for cmd in ('tx("d"', 'tx("g"', 'tx("v"', 'tx("p")', 'tx("n")'):
        assert cmd in body, f"the bridge never sends {cmd}"

    # 'e' latches the E-stop and 'r' clears every latch. Replaying a scenario
    # must not be able to do either: that would let a scripted playback put a
    # physical safety device into a state nobody asked for.
    for forbidden in ('tx("e")', 'tx("r")'):
        assert forbidden not in body, (
            f"the frame bridge sends {forbidden}; scenario playback must not "
            f"drive the E-stop or clear latches")


def test_vehicles_are_not_labelled_as_non_target_species():
    """
    'Non-target' names a specific veto about species that hear the carrier.
    Applying that word to a car points a reviewer at the wrong rule.
    """
    text = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r"flags\.push\(a\.t\?.*?\);", text)
    assert m, "actor chip logic not found"
    assert "vehicle" in m.group(0), (
        "vehicles still fall through to the non-target chip")


# ---------------------------------------------------------------------------
# A refusal that stops being reported is worse than no refusal at all: the
# panel and the ledger both fall back to looking like an empty road.
# ---------------------------------------------------------------------------


def _record_all():
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from gaukavach.acoustics import Atmosphere
    from gaukavach.detect import DEMO_SITE
    from gaukavach.scenario import SCENARIOS
    from gaukavach.simulate import record_scenario
    atm = Atmosphere()
    return {n: record_scenario(s, DEMO_SITE, atm) for n, s in SCENARIOS.items()}


def test_no_scenario_goes_silent_once_it_has_started_deciding():
    """
    The bug this catches: a person in the cone latched the incident to
    INHIBITED, the per-track loop then skipped that animal silently on every
    later frame, and nothing cleared the latch when the person walked away.
    person-in-cone reported one veto and then nothing for 93 frames, so the
    console showed IDLE / "None active" through the whole encounter - the
    scenario whose entire job is to show the human veto.

    Escalation had the same shape: the engine stayed TRACKING and emitted no
    action, so an outstanding human dispatch looked like a quiet road.
    """
    for name, rec in _record_all().items():
        frames = rec["frames"]
        started = next((i for i, f in enumerate(frames) if f["x"]), None)
        assert started is not None, f"{name}: never took any action at all"
        after = frames[started:]
        silent = sum(1 for f in after if not f["x"])
        assert silent <= len(after) * 0.15, (
            f"{name}: {silent}/{len(after)} frames report no action after the "
            f"first decision - a standing refusal has stopped being reported")


def test_the_human_veto_is_live_not_latched():
    """A person is a passing fact about the scene, so the refusal must track
    their presence rather than pinning the animal permanently."""
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from gaukavach.welfare import Denial

    rec = _record_all()["person-in-cone"]
    human = Denial.HUMAN_PRESENT.value
    hits = sum(1 for f in rec["frames"] for x in f["x"]
               if human in x.get("den", []))
    assert hits > 20, (
        f"the human veto is reported on only {hits} frames - it is latching "
        f"and then falling silent instead of refusing every frame")


def test_the_page_carries_a_build_stamp_marker():
    """
    'gaukavach sim' stamps the build between these markers. Without them the
    stamp silently does not happen, and a 6.6 MB page that is rebuilt many
    times a day gives you no way to tell which build you are looking at - so
    you reload, see the old one, and debug something you already fixed.
    """
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "<!--BUILD-->" in text and "<!--/BUILD-->" in text, (
        "the build stamp markers are gone from the template")


def test_the_local_server_refuses_to_let_the_browser_cache():
    """
    The default 'python -m http.server' sends Last-Modified and nothing else,
    which lets a browser serve the page from cache without revalidating.
    """
    src = (ROOT / "tools" / "serve.py").read_text(encoding="utf-8")
    assert "no-store" in src, "the local server does not send no-store"
    assert 'keyword.lower() == "last-modified"' in src, (
        "the local server still sends Last-Modified, so a reload can be "
        "answered with 304 from cache")
