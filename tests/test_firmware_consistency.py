"""
The bench firmware and the software governor must stay two views of one rule set.

The hardware demo's whole argument is that a second, independent layer enforces
the same limits. That argument dies quietly the moment someone tunes a constant
in evidence.py and forgets the sketches, so it is checked here rather than
trusted to discipline.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from gaukavach import evidence as ev

ROOT = Path(__file__).resolve().parents[1]
SKETCHES = [
    ROOT / "hardware" / "tinkercad_uno" / "gaukavach_uno.ino",
    ROOT / "hardware" / "wokwi_esp32" / "gaukavach_esp32.ino",
]

# firmware constant -> (evidence key, multiplier to reach the firmware's unit)
MIRRORED = {
    "MAX_GROUP": ("max_herd_size_for_emission", 1),
    "MAX_ACTIVATION_MS": ("max_activation_s", 1000),
    "MIN_SILENCE_MS": ("min_silence_s", 1000),
    "DAILY_BUDGET_MS": ("daily_exposure_budget_s", 1000),
    "ESCALATE_AFTER_MS": ("escalation_timeout_s", 1000),
}


def _const(src: str, name: str) -> int:
    m = re.search(rf"\b{name}\s*=\s*(\d+)", src)
    assert m, f"{name} not found in sketch"
    return int(m.group(1))


@pytest.mark.parametrize("sketch", SKETCHES, ids=lambda p: p.parent.name)
def test_sketch_exists(sketch: Path):
    assert sketch.is_file(), f"missing {sketch}"


@pytest.mark.parametrize("sketch", SKETCHES, ids=lambda p: p.parent.name)
@pytest.mark.parametrize("fw_name", sorted(MIRRORED))
def test_firmware_limits_match_the_evidence_registry(sketch: Path, fw_name: str):
    key, mult = MIRRORED[fw_name]
    src = sketch.read_text(encoding="utf-8")
    assert _const(src, fw_name) == int(ev.get(key) * mult), (
        f"{sketch.parent.name}/{fw_name} has drifted from evidence.py:{key}"
    )


@pytest.mark.parametrize("sketch", SKETCHES, ids=lambda p: p.parent.name)
def test_firmware_carrier_is_inside_the_documented_band(sketch: Path):
    src = sketch.read_text(encoding="utf-8")
    carrier = _const(src, "CARRIER_HZ")
    assert ev.get("experimental_band_low_hz") <= carrier <= ev.get(
        "experimental_band_high_hz"
    ), "firmware carrier is outside the documented 22-30 kHz band"


@pytest.mark.parametrize("sketch", SKETCHES, ids=lambda p: p.parent.name)
def test_firmware_states_it_cannot_measure_decibels(sketch: Path):
    """The rig has no calibrated microphone; the sketch must say so at boot."""
    src = sketch.read_text(encoding="utf-8").lower()
    assert "no db claim" in src or "makes no db claim" in src


@pytest.mark.parametrize("sketch", SKETCHES, ids=lambda p: p.parent.name)
def test_firmware_declares_the_demo_time_compression(sketch: Path):
    """Compressed timers are fine; undisclosed compressed timers are not."""
    src = sketch.read_text(encoding="utf-8")
    assert _const(src, "DEMO_SPEED") >= 1
    assert "shipped values shown first" in src


def test_desk_scale_matches_the_readme_demo_thresholds():
    """
    The README quotes bench distances at which each veto fires. If DESK_SCALE
    changes those numbers become wrong, and a demo script that lies about its
    own thresholds is worse than none.
    """
    src = SKETCHES[0].read_text(encoding="utf-8")
    scale = float(re.search(r"DESK_SCALE\s*=\s*([\d.]+)", src).group(1))
    line_m = float(re.search(r"LINE_M\s*=\s*([\d.]+)", src).group(1))
    range_m = float(re.search(r"RANGE_MAX_M\s*=\s*([\d.]+)", src).group(1))

    assert round(line_m * scale) == 34, "README says the carriageway veto fires under ~34 cm"
    assert round(range_m * scale) == 120, "README implies the envelope ends near 120 cm"
    assert round(80 / scale, 1) == 28.6, "README quotes 80 cm as 28.6 m"


def test_esp32_ramps_its_envelope():
    """
    The Uno hard-gates because tone() cannot do otherwise. The ESP32 has no such
    excuse, and our own spectrum analysis says a rectangular gate is the wrong
    waveform, so the ESP32 sketch must ramp.
    """
    src = SKETCHES[1].read_text(encoding="utf-8")
    assert "cosf" in src and "RAMP_MS" in src
    assert "ledcWrite" in src


def test_wiring_check_uses_the_same_pins_as_the_governor():
    """The diagnostic is only trustworthy if it probes the pins under test.

    A wiring check on a different pin map does not fail loudly - it reports a
    perfectly healthy circuit that is not the one you built, which is worse
    than having no diagnostic at all.
    """
    check = ROOT / "hardware" / "wiring_check" / "wiring_check.ino"
    if not check.is_file():
        pytest.skip("no wiring_check sketch in this tree")

    esp = (ROOT / "hardware" / "wokwi_esp32" / "gaukavach_esp32.ino").read_text(
        encoding="utf-8")
    diag = check.read_text(encoding="utf-8")

    names = ("PIN_TRIG", "PIN_ECHO", "PIN_EMIT", "LED_PERMIT", "LED_REFUSE",
             "LED_ESCALATE", "LED_ARMED", "BTN_PERSON", "BTN_NONTARGET",
             "BTN_ESTOP", "POT_GROUP")
    for n in names:
        a = re.search(rf"\b{n}\s*=\s*(\d+)", esp)
        b = re.search(rf"\b{n}\s*=\s*(\d+)", diag)
        assert a, f"{n} missing from the governor sketch"
        assert b, f"{n} missing from the wiring check"
        assert a.group(1) == b.group(1), (
            f"{n} is GPIO{a.group(1)} in the governor but GPIO{b.group(1)} "
            f"in the wiring check")
