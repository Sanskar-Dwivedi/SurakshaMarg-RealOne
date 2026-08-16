"""
The on-screen bench claims to enforce the firmware's rules, so check that it does.

This page is the demo now that the hardware is out of the picture, and its
entire claim to being worth more than an animation is that it is a second
implementation of one rule set. A silent divergence between the JavaScript and
the sketch would turn it back into an animation without anyone noticing.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "hardware" / "bench.html"


@pytest.fixture(scope="module")
def mb():
    spec = importlib.util.spec_from_file_location(
        "make_bench", ROOT / "tools" / "make_bench.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def page_consts() -> dict:
    if not PAGE.exists():
        pytest.skip("run tools/make_bench.py first")
    m = re.search(r"const K = (\{.*?\});", PAGE.read_text(encoding="utf-8"), re.S)
    assert m, "the page does not carry a constants block"
    return json.loads(m.group(1))


def test_page_constants_match_the_firmware(mb):
    """Every limit on the page is the one the sketch compiles with."""
    firmware = mb.consts()
    shipped = page_consts()
    assert set(shipped) == set(firmware), (
        f"page and firmware disagree on which constants exist: "
        f"{set(shipped) ^ set(firmware)}")
    for name, value in firmware.items():
        assert shipped[name] == value, (
            f"{name} is {shipped[name]} on the bench page but {value} in the "
            f"firmware")


def test_every_refusal_reason_is_worded_as_in_the_firmware(mb):
    """The reasons are the product. They must not drift into paraphrase."""
    esp = (ROOT / "hardware" / "wokwi_esp32" / "gaukavach_esp32.ino").read_text(
        encoding="utf-8")
    page = PAGE.read_text(encoding="utf-8")
    reasons = re.findall(r'deny = "([^"]+)"', esp)
    assert len(reasons) >= 6, "did not find the refusal reasons in the sketch"
    for r in reasons:
        assert r in page, f"the bench page never gives the reason: {r!r}"


def test_the_bench_states_are_the_firmware_states(mb):
    """Same state machine, same names, so the two can be compared by eye."""
    esp = (ROOT / "hardware" / "wokwi_esp32" / "gaukavach_esp32.ino").read_text(
        encoding="utf-8")
    page = PAGE.read_text(encoding="utf-8")
    m = re.search(r"enum\s+\w*\s*\{([^}]*)\}", esp)
    if not m:
        pytest.skip("no state enum found in the sketch")
    states = [s.strip() for s in m.group(1).split(",") if s.strip()]
    for s in states:
        assert f'"{s}"' in page, f"the bench page has no {s} state"


def test_no_decibel_claim_appears_anywhere(mb):
    """There is no calibrated microphone in this project, so there is no dB figure."""
    text = PAGE.read_text(encoding="utf-8")
    for bad in re.findall(r"\b\d+(?:\.\d+)?\s?dB\b", text):
        pytest.fail(f"the bench page states a decibel figure: {bad}")
    assert "makes no dB claim" in text, "the page must keep saying so out loud"


def test_generated_page_is_pure_ascii():
    if not PAGE.exists():
        pytest.skip("run tools/make_bench.py first")
    bad = {c for c in PAGE.read_text(encoding="utf-8") if ord(c) > 127}
    assert not bad, f"non-ASCII would be mis-decoded by the host: {bad}"
