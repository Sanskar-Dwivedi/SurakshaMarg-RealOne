"""
Electrical sanity checks on the Wokwi diagrams.

Added after two mistakes in a row on these files: first a stray part reference,
then LED anode and cathode swapped during a layout tidy-up. Both are silent -
the JSON stays valid, the simulator loads, and the LEDs simply never light.

These checks are cheap and they encode what "correct" means for this circuit,
so a future layout change cannot quietly break the electrics again.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIAGRAMS = sorted((ROOT / "hardware").glob("wokwi_*/diagram.json"))
IDS = [d.parent.name for d in DIAGRAMS]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def nets(d: dict) -> list[tuple[str, str]]:
    return [(c[0], c[1]) for c in d["connections"]]


def neighbours(d: dict, pin: str) -> set[str]:
    out = set()
    for a, b in nets(d):
        if a == pin:
            out.add(b)
        if b == pin:
            out.add(a)
    return out


def is_gnd(pin: str) -> bool:
    return pin.split(":")[-1].startswith("GND")


@pytest.mark.parametrize("path", DIAGRAMS, ids=IDS)
def test_diagram_is_valid_json_with_parts_and_connections(path: Path):
    d = load(path)
    assert d["parts"] and d["connections"]
    assert len({p["id"] for p in d["parts"]}) == len(d["parts"]), "duplicate part id"


@pytest.mark.parametrize("path", DIAGRAMS, ids=IDS)
def test_every_connection_names_a_real_part(path: Path):
    d = load(path)
    ids = {p["id"] for p in d["parts"]}
    dangling = [
        ep for a, b in nets(d) for ep in (a, b) if ep.split(":")[0] not in ids
    ]
    assert not dangling, f"connections to non-existent parts: {sorted(set(dangling))}"


@pytest.mark.parametrize("path", DIAGRAMS, ids=IDS)
def test_led_polarity_is_the_right_way_round(path: Path):
    """
    Anode is driven, cathode goes to ground. Reversed, the LED never lights and
    nothing else complains - which is exactly how this slipped through once.
    """
    d = load(path)
    for led in [p["id"] for p in d["parts"] if p["type"] == "wokwi-led"]:
        anode, cathode = neighbours(d, f"{led}:A"), neighbours(d, f"{led}:C")
        assert anode, f"{led} anode is not connected"
        assert cathode, f"{led} cathode is not connected"
        assert not any(is_gnd(n) for n in anode), (
            f"{led} anode is wired to GND - polarity reversed")
        assert any(is_gnd(n) for n in cathode), (
            f"{led} cathode does not reach GND")


@pytest.mark.parametrize("path", DIAGRAMS, ids=IDS)
def test_every_led_has_a_series_resistor(path: Path):
    """A bare LED on a GPIO is the classic way to cook a pin."""
    d = load(path)
    res = {p["id"] for p in d["parts"] if p["type"] == "wokwi-resistor"}
    for led in [p["id"] for p in d["parts"] if p["type"] == "wokwi-led"]:
        feed = neighbours(d, f"{led}:A")
        assert any(n.split(":")[0] in res for n in feed), (
            f"{led} is driven directly from a pin with no series resistor")


@pytest.mark.parametrize("path", DIAGRAMS, ids=IDS)
def test_buzzer_has_a_series_resistor(path: Path):
    d = load(path)
    res = {p["id"] for p in d["parts"] if p["type"] == "wokwi-resistor"}
    for bz in [p["id"] for p in d["parts"] if p["type"] == "wokwi-buzzer"]:
        touching = neighbours(d, f"{bz}:1") | neighbours(d, f"{bz}:2")
        assert any(n.split(":")[0] in res for n in touching), (
            f"{bz} has no series resistor; a piezo is a capacitive load")


@pytest.mark.parametrize("path", DIAGRAMS, ids=IDS)
def test_ultrasonic_sensor_is_present_and_wired(path: Path):
    """Without it the sketch idles forever and no LED ever lights."""
    d = load(path)
    sr = [p["id"] for p in d["parts"] if p["type"] == "wokwi-hc-sr04"]
    assert sr, "no HC-SR04 in the diagram"
    for s in sr:
        for pin in ("VCC", "TRIG", "ECHO", "GND"):
            assert neighbours(d, f"{s}:{pin}"), f"{s}:{pin} is unconnected"


def test_esp32_echo_goes_through_a_divider():
    """ESP32 GPIOs are not 5 V tolerant; ECHO must not reach a pin directly."""
    path = ROOT / "hardware" / "wokwi_esp32" / "diagram.json"
    d = load(path)
    res = {p["id"] for p in d["parts"] if p["type"] == "wokwi-resistor"}
    echo = neighbours(d, "sr04:ECHO")
    assert echo, "ECHO unconnected"
    assert all(n.split(":")[0] in res for n in echo), (
        f"ECHO reaches {echo} directly - it must pass through the divider")


def test_esp32_estop_has_a_pull_up_to_3v3():
    """GPIO34-39 have no internal pull-up, so the E-stop would float."""
    d = load(ROOT / "hardware" / "wokwi_esp32" / "diagram.json")
    res = {p["id"] for p in d["parts"] if p["type"] == "wokwi-resistor"}
    node = neighbours(d, "btnEstop:1.l")
    pull = [n for n in node if n.split(":")[0] in res]
    assert pull, "E-stop has no pull-up resistor"
    other = neighbours(d, f"{pull[0].split(':')[0]}:2") | neighbours(
        d, f"{pull[0].split(':')[0]}:1")
    assert any("3V3" in n for n in other), "E-stop pull-up does not reach 3V3"


def test_esp32_pot_is_on_3v3_not_5v():
    """ESP32 ADC pins are not 5 V tolerant."""
    d = load(ROOT / "hardware" / "wokwi_esp32" / "diagram.json")
    assert any("3V3" in n for n in neighbours(d, "pot:VCC")), \
        "pot VCC must be 3V3 on ESP32"
    assert not any(n.endswith(":5V") for n in neighbours(d, "pot:VCC"))


# Pin names Wokwi actually accepts on board-esp32-devkit-c-v4. GPIO36 and 39 are
# addressed by their silkscreen aliases VP and VN; writing "esp:39" is silently
# ignored - the wire simply does not connect and the sketch sees nothing. That
# cost an hour of debugging a circuit that looked correct.
ESP32_PINS = {
    "3V3", "5V", "EN", "VP", "VN", "GND.1", "GND.2", "GND.3",
    "13", "12", "14", "27", "26", "25", "33", "32", "35", "34",
    "23", "22", "21", "19", "18", "17", "16", "4", "0", "2", "15",
    "TX", "RX", "TX0", "RX0", "D2", "D3", "CMD", "CLK", "SD0", "SD1",
}


def test_esp32_uses_only_pin_names_wokwi_accepts():
    d = load(ROOT / "hardware" / "wokwi_esp32" / "diagram.json")
    used = {ep.split(":", 1)[1] for a, b in nets(d) for ep in (a, b)
            if ep.startswith("esp:")}
    bad = sorted(used - ESP32_PINS)
    assert not bad, (
        f"Wokwi does not accept these ESP32 pin names: {bad}. "
        f"GPIO36/39 must be written as VP/VN - a wrong name is ignored silently, "
        f"the wire never connects, and the sketch just sees nothing."
    )


@pytest.mark.parametrize("path", DIAGRAMS, ids=IDS)
def test_parts_are_laid_out_compactly(path: Path):
    """
    A sprawling layout makes Wokwi route wires across the whole canvas and the
    result is unreadable. Keep everything inside a sane bounding box.
    """
    d = load(path)
    tops = [p["top"] for p in d["parts"]]
    lefts = [p["left"] for p in d["parts"]]
    assert max(tops) - min(tops) <= 700, "parts spread too far vertically"
    assert max(lefts) - min(lefts) <= 700, "parts spread too far horizontally"
