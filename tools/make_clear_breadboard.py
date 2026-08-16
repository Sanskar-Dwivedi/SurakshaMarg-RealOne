"""
Generate a single-page clear breadboard attachment map.

    python tools/make_clear_breadboard.py

This is the "where do I attach the wire?" companion to the longer build guide.
It favours large labels, numbered connections, and exact breadboard holes over
photorealism. Pin numbers are parsed from the ESP32 sketch so the diagram stays
in lockstep with the firmware.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESP = ROOT / "hardware" / "wokwi_esp32" / "gaukavach_esp32.ino"
OUT = ROOT / "hardware" / "clear_breadboard.html"

INK = "#101820"
MUTED = "#5D6B79"
PAPER = "#F5F7FA"
CARD = "#FFFFFF"
LINE = "#D7DFE7"
BOARD = "#EEE8DA"
CHANNEL = "#D9D1BE"
HOLE = "#5B5F65"
RED = "#D94136"
BLACK = "#2F343A"
BLUE = "#2E86C1"
GREEN = "#218A52"
AMBER = "#C4941C"
PURPLE = "#8447A8"
TEAL = "#0E7C86"

OHM = "ohm"

COL0 = 21
COL1 = 63
PITCH = 18
X0 = 330
Y0 = 118

ROWS = {
    "+": 0,
    "-": 1,
    "J": 3,
    "I": 4,
    "H": 5,
    "G": 6,
    "F": 7,
    "E": 9,
    "D": 10,
    "C": 11,
    "B": 12,
    "A": 13,
    "+b": 15,
    "-b": 16,
}

ALIAS = {"39": "GPIO39/VN", "36": "GPIO36/VP"}


def safe(s: object) -> str:
    text = html.escape(str(s), quote=True)
    return "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in text)


def pins() -> dict[str, str]:
    src = ESP.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for name in (
        "PIN_TRIG",
        "PIN_ECHO",
        "PIN_EMIT",
        "LED_PERMIT",
        "LED_REFUSE",
        "LED_ESCALATE",
        "BTN_PERSON",
        "BTN_NONTARGET",
        "BTN_ESTOP",
        "POT_GROUP",
    ):
        m = re.search(rf"\b{name}\s*=\s*(\d+)", src)
        if not m:
            raise SystemExit(f"{name} not found in {ESP}")
        out[name] = ALIAS.get(m.group(1), f"GPIO{m.group(1)}")
    return out


def xy(row: str, col: int) -> tuple[int, int]:
    return X0 + (col - COL0) * PITCH, Y0 + ROWS[row] * PITCH


def hole(row: str, col: int) -> str:
    label = "+" if row == "+" else "-" if row == "-" else row
    return f"{label}{col}"


class Svg:
    def __init__(self) -> None:
        self.out: list[str] = []

    def add(self, s: str) -> None:
        self.out.append(s)

    def text(
        self,
        x: float,
        y: float,
        text: str,
        size: int = 13,
        fill: str = INK,
        anchor: str = "start",
        weight: str = "500",
    ) -> None:
        self.add(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" '
            f'font-family="Inter,Segoe UI,Arial,sans-serif">{safe(text)}</text>'
        )

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str,
        stroke: str = "none",
        rx: float = 5,
        sw: float = 1,
    ) -> None:
        self.add(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
        )

    def circ(self, x: float, y: float, r: float, fill: str, stroke: str = "none") -> None:
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{stroke}"/>')

    def line(self, points: list[tuple[float, float]], color: str, width: float = 4) -> None:
        path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
        self.add(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        )

    def badge(self, n: int, x: float, y: float, color: str = TEAL) -> None:
        self.circ(x, y, 12, color, "#FFFFFF")
        self.text(x, y + 5, str(n), 13, "#FFFFFF", "middle", "800")

    def pad(self, row: str, col: int, color: str = TEAL) -> None:
        x, y = xy(row, col)
        self.circ(x, y, 7, color, "#FFFFFF")
        self.text(x, y - 11, hole(row, col), 10, color, "middle", "800")

    def board(self) -> None:
        w = (COL1 - COL0) * PITCH
        self.rect(X0 - 26, Y0 - 38, w + 52, 338, BOARD, "#CFC7B6", 8, 1.4)
        self.rect(X0 - 24, Y0 + ROWS["F"] * PITCH + 8, w + 48, 20, CHANNEL, "none", 3)

        for row, color in (("+", RED), ("-", BLUE), ("+b", RED), ("-b", BLUE)):
            y = Y0 + ROWS[row] * PITCH
            self.line([(X0 - 12, y), (X0 + w + 12, y)], color, 2.5)
            self.text(X0 - 38, y + 5, "+" if row.startswith("+") else "-", 16, color, "middle", "800")

        for c in range(COL0, COL1 + 1):
            for row in ROWS:
                x, y = xy(row, c)
                self.rect(x - 3, y - 3, 6, 6, HOLE, "none", 1)

        for c in range(COL0, COL1 + 1):
            if c % 5 == 0 or c in {21, 22, 23, 24, 30, 36, 42, 50, 55, 60, 63}:
                self.text(xy("+", c)[0], Y0 - 50, str(c), 11, MUTED, "middle", "700")
                self.text(xy("-b", c)[0], Y0 + 321, str(c), 11, MUTED, "middle", "700")

        for row in "JIHGFEDCBA":
            self.text(X0 - 42, xy(row, COL0)[1] + 5, row, 13, MUTED, "middle", "800")
            self.text(X0 + w + 42, xy(row, COL1)[1] + 5, row, 13, MUTED, "middle", "800")

    def component_box(self, x: float, y: float, w: float, h: float, title: str, fill: str) -> None:
        self.rect(x, y, w, h, fill, "#1A1F2430", 6, 1.2)
        self.text(x + w / 2, y + h + 17, title, 12, INK, "middle", "800")


def route(svg: Svg, n: int, label: str, start: tuple[float, float], target: tuple[str, int], color: str, lane: int) -> None:
    x2, y2 = xy(*target)
    ymid = 456 + lane * 15
    svg.line([start, (start[0] + 36, start[1]), (start[0] + 36, ymid), (x2, ymid), (x2, y2)], color, 3.3)
    svg.badge(n, x2 + 15, y2 - 14, color)
    svg.pad(*target, color)
    svg.text(start[0] - 8, start[1] + 5, label, 12, INK, "end", "800")


def render(p: dict[str, str]) -> str:
    svg = Svg()
    svg.rect(0, 0, 1160, 650, "#F8FAFC")
    svg.text(32, 42, "Clear breadboard attachment map", 28, INK, "start", "850")
    svg.text(32, 68, "Use the numbered badges, then confirm each exact hole in the table below.", 14, MUTED)
    svg.board()

    # ESP32 block and pin tabs.
    esp_x, esp_y = 48, 120
    svg.component_box(esp_x, esp_y, 178, 286, "ESP32 DevKit", "#DCE9F7")
    svg.text(esp_x + 89, esp_y + 32, "ESP32", 30, "#35536F", "middle", "850")
    pin_y = {
        "3V3": 176,
        "GND": 202,
        p["PIN_TRIG"]: 230,
        p["PIN_ECHO"]: 258,
        p["PIN_EMIT"]: 286,
        p["LED_PERMIT"]: 314,
        p["LED_REFUSE"]: 342,
        p["LED_ESCALATE"]: 370,
        p["BTN_PERSON"]: 398,
        p["BTN_NONTARGET"]: 426,
        p["BTN_ESTOP"]: 454,
        p["POT_GROUP"]: 482,
        "VIN/5V": 510,
    }

    # Main components.
    svg.component_box(*xy("E", 30), 82, 54, "HC-SR04", "#75AADB")
    svg.text(xy("E", 30)[0] + 41, xy("E", 30)[1] + 31, "HC-SR04", 13, "#FFFFFF", "middle", "800")
    for i, label in enumerate(("VCC", "TRIG", "ECHO", "GND")):
        svg.text(xy("E", 30 + i)[0], xy("E", 30)[1] + 78, label, 9, MUTED, "middle", "800")

    for col, color, name in ((26, GREEN, "PERMIT"), (32, RED, "REFUSE"), (38, AMBER, "ESCALATE")):
        x, y = xy("G", col)
        svg.circ(x + PITCH, y - 34, 15, color, "#333333")
        svg.text(x + PITCH, y - 56, name, 10, INK, "middle", "800")

    for col, name in ((50, "PERSON"), (55, "DOG/GOAT"), (60, "E-STOP")):
        x, y = xy("F", col)
        svg.component_box(x - 8, y - 18, 52, 40, name, "#DADDE3")
        svg.circ(x + 18, y + 2, 12, BLUE if col == 50 else AMBER if col == 55 else RED, "#454B52")

    svg.component_box(*xy("E", 24), 56, 42, "10k pot", "#7FA8D8")
    svg.component_box(*xy("G", 44), 44, 44, "Piezo", "#E9C35B")

    # Board-only jumpers and inline parts.
    fixed = [
        (1, "+ rail link", ("+", 47), ("+b", 47), RED),
        (2, "- rail link", ("-", 48), ("-b", 48), BLACK),
        (14, "green LED cathode to ground", ("J", 28), ("-", 28), BLACK),
        (15, "red LED cathode to ground", ("J", 34), ("-", 34), BLACK),
        (16, "amber LED cathode to ground", ("J", 40), ("-", 40), BLACK),
        (18, "piezo - to ground", ("J", 46), ("-", 46), BLACK),
        (22, "pot left leg to 3V3", ("A", 24), ("+b", 24), RED),
        (24, "pot right leg to ground", ("A", 26), ("-b", 26), BLACK),
        (28, "HC-SR04 GND to ground", ("A", 33), ("-b", 33), BLACK),
        (31, "divider bottom to ground", ("D", 40), ("-b", 40), BLACK),
        (35, "PERSON button ground", ("J", 52), ("-", 52), BLACK),
        (37, "DOG/GOAT button ground", ("J", 57), ("-", 57), BLACK),
        (39, "E-STOP button ground", ("J", 62), ("-", 62), BLACK),
        (41, "E-STOP 10k pull-up", ("B", 56), ("+b", 56), RED),
    ]
    for n, _label, a, b, color in fixed:
        x1, y1 = xy(*a)
        x2, y2 = xy(*b)
        svg.line([(x1, y1), (x1, (y1 + y2) / 2), (x2, (y1 + y2) / 2), (x2, y2)], color, 3.1)
        svg.badge(n, x2 + 13, y2 - 13, color)

    # Resistors shown as explicit spans.
    for n, a, b, value in (
        (11, ("J", 24), ("J", 26), f"220 {OHM}"),
        (12, ("J", 30), ("J", 32), f"220 {OHM}"),
        (13, ("J", 36), ("J", 38), f"220 {OHM}"),
        (17, ("J", 42), ("J", 44), f"220 {OHM}"),
        (29, ("B", 32), ("B", 36), f"1k {OHM}"),
        (30, ("D", 36), ("D", 40), f"2k {OHM}"),
        (40, ("B", 60), ("B", 56), f"10k {OHM}"),
    ):
        x1, y1 = xy(*a)
        x2, y2 = xy(*b)
        svg.line([(x1, y1), (x2, y2)], "#A48A5B", 5)
        svg.rect(min(x1, x2) + 9, y1 - 8, abs(x2 - x1) - 18, 16, "#E8D6AE", "#9C8356", 3)
        svg.text((x1 + x2) / 2, y1 - 12, value, 9, INK, "middle", "800")
        svg.badge(n, x2 + 13, y2 - 13, "#A48A5B")

    # ESP32 and sensor feed wires.
    feeds = [
        (3, "3V3", ("+", 22), RED),
        (4, "GND", ("-", 23), BLACK),
        (5, p["LED_PERMIT"], ("I", 24), GREEN),
        (6, p["LED_REFUSE"], ("H", 30), RED),
        (7, p["LED_ESCALATE"], ("F", 36), AMBER),
        (8, p["PIN_EMIT"], ("I", 42), PURPLE),
        (19, "VIN/5V", ("A", 30), RED),
        (20, p["PIN_TRIG"], ("B", 31), GREEN),
        (21, p["PIN_ECHO"], ("C", 36), TEAL),
        (23, p["POT_GROUP"], ("C", 25), AMBER),
        (34, p["BTN_PERSON"], ("A", 50), BLUE),
        (36, p["BTN_NONTARGET"], ("B", 55), AMBER),
        (38, p["BTN_ESTOP"], ("C", 60), RED),
    ]
    for lane, (n, label, target, color) in enumerate(feeds):
        start = (esp_x + 178, pin_y[label if label in pin_y else str(label)])
        route(svg, n, label, start, target, color, lane)

    return (
        '<svg viewBox="0 0 1160 650" role="img" aria-label="Clear ESP32 breadboard '
        'attachment map">'
        + "".join(svg.out)
        + "</svg>"
    )


def connection_rows(p: dict[str, str]) -> str:
    rows = [
        (1, "Jumper", "+ rail 47", "+ bottom rail 47", "Bridge positive rails."),
        (2, "Jumper", "- rail 48", "- bottom rail 48", "Bridge ground rails."),
        (3, "Jumper", "ESP32 3V3", "+ rail 22", "Power rail, 3.3 V."),
        (4, "Jumper", "ESP32 GND", "- rail 23", "Common ground."),
        (5, "Jumper", p["LED_PERMIT"], "I24", "Green status feed."),
        (6, "Jumper", p["LED_REFUSE"], "H30", "Red status feed."),
        (7, "Jumper", p["LED_ESCALATE"], "F36", "Amber status feed."),
        (8, "Jumper", p["PIN_EMIT"], "I42", "Piezo signal feed."),
        (11, f"220 {OHM}", "J24", "J26", "Green LED resistor."),
        (12, f"220 {OHM}", "J30", "J32", "Red LED resistor."),
        (13, f"220 {OHM}", "J36", "J38", "Amber LED resistor."),
        (14, "Jumper", "J28", "- rail 28", "Green LED cathode to ground."),
        (15, "Jumper", "J34", "- rail 34", "Red LED cathode to ground."),
        (16, "Jumper", "J40", "- rail 40", "Amber LED cathode to ground."),
        (17, f"220 {OHM}", "J42", "J44", "Piezo series resistor."),
        (18, "Jumper", "J46", "- rail 46", "Piezo negative to ground."),
        (19, "Jumper", "ESP32 VIN/5V", "A30", "HC-SR04 VCC."),
        (20, "Jumper", p["PIN_TRIG"], "B31", "HC-SR04 TRIG."),
        (21, "Jumper", p["PIN_ECHO"], "C36", "Read divider junction, not raw ECHO."),
        (22, "Jumper", "A24", "+ bottom rail 24", "Pot left leg to 3V3."),
        (23, "Jumper", p["POT_GROUP"], "C25", "Pot middle/wiper leg."),
        (24, "Jumper", "A26", "- bottom rail 26", "Pot right leg to ground."),
        (28, "Jumper", "A33", "- bottom rail 33", "HC-SR04 GND."),
        (29, f"1k {OHM}", "B32", "B36", "ECHO upper divider resistor."),
        (30, f"2k {OHM}", "D36", "D40", "ECHO lower divider resistor."),
        (31, "Jumper", "D40", "- bottom rail 40", "Divider bottom to ground."),
        (34, "Jumper", p["BTN_PERSON"], "A50", "PERSON button input."),
        (35, "Jumper", "J52", "- rail 52", "PERSON button opposite leg to ground."),
        (36, "Jumper", p["BTN_NONTARGET"], "B55", "DOG/GOAT button input."),
        (37, "Jumper", "J57", "- rail 57", "DOG/GOAT button opposite leg to ground."),
        (38, "Jumper", p["BTN_ESTOP"], "C60", "E-STOP button input."),
        (39, "Jumper", "J62", "- rail 62", "E-STOP opposite leg to ground."),
        (40, f"10k {OHM}", "B60", "B56", "External pull-up for GPIO35."),
        (41, "Jumper", "B56", "+ bottom rail 56", "Pull-up to 3V3."),
    ]
    return "".join(
        f"<tr><td><b>{n}</b></td><td>{kind}</td><td>{frm}</td><td>{to}</td>"
        f"<td>{safe(note)}</td></tr>"
        for n, kind, frm, to, note in rows
    )


def main() -> None:
    p = pins()
    page = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clear ESP32 breadboard attachment map</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:{PAPER};color:{INK};font-family:Inter,Segoe UI,Arial,sans-serif;line-height:1.55}}
header{{padding:28px 24px 18px;background:{CARD};border-bottom:1px solid {LINE}}}
main{{max-width:1220px;margin:0 auto;padding:24px}}
h1{{margin:0;font-size:31px;letter-spacing:0;font-weight:850}}
p{{margin:8px 0 0;color:{MUTED};max-width:86ch}}
.diagram{{margin-top:22px;background:{CARD};border:1px solid {LINE};overflow:auto}}
.diagram svg{{display:block;min-width:1040px;width:100%}}
.note{{margin-top:18px;background:#FFF8E3;border-left:4px solid {AMBER};padding:14px 16px;color:{INK}}}
table{{margin-top:22px;width:100%;border-collapse:collapse;background:{CARD};border:1px solid {LINE};font-size:14px}}
th,td{{padding:10px 12px;border-bottom:1px solid {LINE};text-align:left;vertical-align:top}}
th{{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:{MUTED};background:#F8FAFC}}
td:first-child{{width:54px;text-align:center}}
td b{{display:inline-grid;place-items:center;width:26px;height:26px;border-radius:50%;background:{TEAL};color:white}}
code{{background:#F8FAFC;border:1px solid {LINE};padding:1px 5px;border-radius:4px}}
</style>
<header>
  <h1>Clear ESP32 breadboard attachment map</h1>
  <p>Match each numbered badge on the diagram to the table. The table tells you the
  exact pin or breadboard hole to attach. Use ESP32 silkscreen labels, not pin
  counting, because DevKit boards vary.</p>
</header>
<main>
  <section class="diagram">{render(p)}</section>
  <div class="note"><strong>Important:</strong> HC-SR04 ECHO is 5 V. Do not wire
  ECHO straight to the ESP32. Use the 1k/2k divider: raw ECHO column B32 goes
  through 1k to column 36, GPIO39/VN reads column C36, and 2k goes from D36 to
  ground.</div>
  <table>
    <thead><tr><th>No.</th><th>Part</th><th>From</th><th>To</th><th>Check</th></tr></thead>
    <tbody>{connection_rows(p)}</tbody>
  </table>
  <p>Regenerate this page with <code>python tools/make_clear_breadboard.py</code>.</p>
</main>
</html>
"""
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
