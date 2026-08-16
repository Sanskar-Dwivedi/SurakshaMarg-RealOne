"""
The handover document is the artefact somebody else builds from.

Every other page in this project is read by the person who wrote the circuit.
This one is read by a stranger with a soldering iron and no context, so a wrong
number here costs a build rather than a minute. The document is generated from
the firmware, and these checks confirm the generation actually binds.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "tools" / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def dd():
    return _load("make_design_doc")


def test_governor_limits_are_read_from_the_firmware(dd):
    """A spec quoting a number the firmware does not enforce is worse than none."""
    src = (ROOT / "hardware" / "wokwi_esp32" / "gaukavach_esp32.ino").read_text(
        encoding="utf-8")
    for name, value in dd.consts().items():
        text = f"{value:.0f}" if value == int(value) else str(value)
        assert re.search(rf"\b{name}\s*=\s*{re.escape(text)}\b", src), (
            f"{name} in the document does not match the sketch")


def test_every_resistor_in_the_circuit_is_in_the_bill_of_materials(dd):
    """The build stops dead if a one-rupee part is missing from the shopping list."""
    listed = " ".join(item[1] for item in dd.BOM)
    for value in ("220", "1 k", "2 k", "10 k"):
        assert value in listed, f"no {value} resistor on the BOM"


def test_bom_prices_parse_and_total_correctly(dd):
    """The cost in the title block is a sum, not a guess."""
    lo = hi = 0
    for _q, _part, _note, price in dd.BOM:
        a, b = price.split(" - ")
        assert int(a) <= int(b), f"price range {price} is backwards"
        lo, hi = lo + int(a), hi + int(b)
    assert lo > 0 and hi > lo


def test_acceptance_thresholds_follow_the_firmware_scale(dd):
    """The tester's ruler has to agree with the firmware's arithmetic."""
    c = dd.consts()
    steps = {name: expect for name, _do, expect in dd.acceptance(c)}
    line_cm = round(c["LINE_M"] * c["DESK_SCALE"])
    assert "Carriageway rule" in steps
    do = next(d for n, d, _e in dd.acceptance(c) if n == "Carriageway rule")
    assert str(line_cm) in do, (
        f"the carriageway test should say {line_cm} cm, computed from "
        f"LINE_M x DESK_SCALE")


def test_every_wired_pin_appears_in_the_pin_schedule():
    """A pin the builder is never told about is a pin they never connect."""
    page = ROOT / "hardware" / "design.html"
    if not page.exists():
        pytest.skip("run tools/make_design_doc.py first")
    mb = _load("make_breadboard")
    text = page.read_text(encoding="utf-8")
    for name, gpio in mb.pins().items():
        label = mb.silk(gpio)
        assert re.search(rf">{label}<", text), (
            f"{name} (printed {label}) is missing from the pin schedule")


def test_the_document_declares_its_limitations(dd):
    """The honest-scope section is load-bearing for this project, not boilerplate."""
    text = " ".join(h + " " + t for h, t in dd.LIMITS).lower()
    for claim in ("no calibrated microphone", "stand-in", "compressed", "scaled"):
        assert claim in text, f"the limitations section does not mention '{claim}'"


def test_generated_page_is_pure_ascii():
    page = ROOT / "hardware" / "design.html"
    if not page.exists():
        pytest.skip("run tools/make_design_doc.py first")
    bad = {c for c in page.read_text(encoding="utf-8") if ord(c) > 127}
    assert not bad, f"non-ASCII would be mis-decoded by the host: {bad}"


def test_every_shipped_page_opens_correctly_without_a_server():
    """These pages are fragments, so the browser guesses the charset.

    A page full of mojibake is indistinguishable from a page that failed to
    load, and the reader has no way to tell which. Numeric character references
    render the same in every encoding, so the rule is simply: no byte above 127
    in anything we hand to a human.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "ascii_pages", ROOT / "tools" / "ascii_pages.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    dirty = {}
    for rel in mod.PAGES:
        path = ROOT / rel
        if not path.is_file():
            continue
        found = mod.offenders(path.read_text(encoding="utf-8"))
        if found:
            dirty[rel] = sum(found.values())
    assert not dirty, (
        f"these pages would mojibake when opened directly: {dirty}. "
        f"Run: python tools/ascii_pages.py")
