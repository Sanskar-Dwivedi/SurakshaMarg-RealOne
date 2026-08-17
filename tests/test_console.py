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
