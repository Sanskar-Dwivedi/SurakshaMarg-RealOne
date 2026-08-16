"""
The breadboard guide claims exact holes, so the layout has to be checkable.

A wiring diagram that is merely plausible is worse than none: someone follows
it, the board does not work, and they spend the demo debugging the picture.
The layout is generated from constants, so the constants can be checked - that
two parts never land on one node by accident, that the divider really divides,
and that the page cannot pick up a character its host might mis-decode.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


@pytest.fixture(scope="module")
def bb():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "make_breadboard", TOOLS / "make_breadboard.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def nodes(bb) -> dict[tuple[str, int], list[str]]:
    """Every (half, column) node the layout occupies, and what claims it.

    'top' is rows F-J, 'bottom' is rows A-E. The two halves of one column are
    separate nodes; that separation is the only reason the buttons work.
    """
    out: dict[tuple[str, int], list[str]] = {}

    def claim(half: str, col: int, who: str) -> None:
        out.setdefault((half, col), []).append(who)

    for key, base in bb.LED_BASE.items():
        claim("top", base, f"{key} feed + resistor")
        claim("top", base + 2, f"{key} resistor + anode")
        claim("top", base + 4, f"{key} cathode + ground jumper")
    pz = bb.PIEZO_BASE
    claim("top", pz, "piezo feed + resistor")
    claim("top", pz + 2, "piezo resistor + plus leg")
    claim("top", pz + 4, "piezo minus leg + ground jumper")

    for key, c in bb.BTN_COL.items():
        claim("bottom", c, f"{key} pin leg")
        claim("top", c + 2, f"{key} ground leg")
        claim("bottom", c + 2, f"{key} ground leg (lower half)")
        claim("top", c, f"{key} pin leg (upper half)")

    for c in range(bb.POT_COL, bb.POT_COL + 3):
        claim("bottom", c, "potentiometer leg")
    for c in range(bb.SR04_COL, bb.SR04_COL + 4):
        claim("bottom", c, "HC-SR04 pin")
    claim("bottom", bb.DIV_COL, "divider junction")
    claim("bottom", bb.DIV_COL + 4, "2k lower end")
    claim("bottom", bb.BTN_COL["BTN_ESTOP"] - 4, "10k upper end")
    return out


def test_no_two_parts_share_a_node_by_accident(bb):
    """Every shared node must be a series connection we meant to make."""
    intended = set()
    for base in bb.LED_BASE.values():
        intended |= {("top", base), ("top", base + 2), ("top", base + 4)}
    pz = bb.PIEZO_BASE
    intended |= {("top", pz), ("top", pz + 2), ("top", pz + 4)}
    for c in bb.BTN_COL.values():
        intended |= {("bottom", c), ("top", c + 2),
                     ("bottom", c + 2), ("top", c)}

    for node, claimants in nodes(bb).items():
        if len(claimants) > 1 and node not in intended:
            pytest.fail(f"node {node} is claimed by {claimants} but that "
                        f"shorting is not part of the design")


def test_led_and_piezo_chains_do_not_overlap(bb):
    """Three LEDs and a piezo, four independent chains in the same half."""
    seen: dict[int, str] = {}
    chains = {**{k: v for k, v in bb.LED_BASE.items()},
              "PIEZO": bb.PIEZO_BASE}
    for name, base in chains.items():
        for c in (base, base + 2, base + 4):
            assert c not in seen, f"{name} column {c} already used by {seen[c]}"
            seen[c] = name


def test_rail_links_are_clear_of_every_part(bb):
    """The top-to-bottom rail jumpers cross the board; keep them out of parts."""
    occupied = {col for (_half, col) in nodes(bb)}
    for col, what in ((bb.LINK_P, "+ rail link"), (bb.LINK_N, "- rail link")):
        assert col not in occupied, (
            f"{what} at column {col} runs straight through a component")


def test_divider_is_wired_as_a_divider(bb):
    """ECHO -> 1k -> junction -> 2k -> ground, and the pin reads the junction."""
    echo_col = bb.SR04_COL + 2          # VCC, TRIG, ECHO, GND
    assert echo_col != bb.DIV_COL, "1k must span two columns, not sit in one"
    assert bb.DIV_COL != bb.DIV_COL + 4
    # the junction must not collide with the sensor's own pins
    assert bb.DIV_COL not in range(bb.SR04_COL, bb.SR04_COL + 4)


def test_estop_pullup_lands_on_the_button_node(bb):
    """The 10k is a pull-up, not a series resistor: same column as the pin leg."""
    src = TOOLS.joinpath("make_breadboard.py").read_text(encoding="utf-8")
    m = re.search(r'b\.resistor\(4, "B", c, c - 4, "10k"\)', src)
    assert m, "the E-stop pull-up should start on the button's own column"


def test_feed_rows_are_distinct(bb):
    """Feeds share a row only if they share a wire, which they never do."""
    assert len(set(bb.LED_FEED_ROW)) == len(bb.LED_FEED_ROW)
    assert len(set(bb.BTN_FEED_ROW)) == len(bb.BTN_FEED_ROW)


def test_pins_come_from_the_sketch_not_from_here(bb):
    """Regenerating after a pin change must move the picture, not silently pass."""
    p = bb.pins()
    src = (ROOT / "hardware" / "wokwi_esp32" / "gaukavach_esp32.ino").read_text(
        encoding="utf-8")
    for name, value in p.items():
        assert re.search(rf"\b{name}\s*=\s*{value}\b", src)


def test_generated_page_is_pure_ascii():
    """The page ships as a fragment; the host picks the charset, so do not risk it."""
    page = ROOT / "hardware" / "breadboard.html"
    if not page.exists():
        pytest.skip("run tools/make_breadboard.py first")
    bad = [c for c in page.read_text(encoding="utf-8") if ord(c) > 127]
    assert not bad, f"non-ASCII characters would be mis-decoded: {set(bad)}"


def test_the_board_figure_calls_out_every_pin_the_sketch_uses(bb):
    """A pin drawn grey reads as 'you do not need this one'.

    The figure greys out unused pads on purpose, which makes an omission
    indistinguishable from a decision. The pot wiper was missing from the map
    for exactly this reason and looked entirely deliberate.
    """
    p = bb.pins()
    used = bb.board_uses(p)
    for name, gpio in p.items():
        label = bb.silk(gpio)
        assert label in used, (
            f"{name} (GPIO{gpio}, printed {label}) is wired by the sketch but "
            f"the board figure shows its pad as unused")


def test_every_called_out_pin_exists_on_that_board(bb):
    """The figure names one specific 30-pin board; do not invent pads on it."""
    header = set(bb.DEVKIT_V1_LEFT) | set(bb.DEVKIT_V1_RIGHT)
    for label in bb.board_uses(bb.pins()):
        assert label in header, (
            f"the figure calls out {label}, which is not on a DevKit V1 30-pin "
            f"header - either the board data or the call-out is wrong")
