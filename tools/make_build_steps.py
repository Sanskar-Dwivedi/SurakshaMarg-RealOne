"""
Generate the step-by-step ESP32 build guide.

    python tools/make_build_steps.py

WHY THIS DOES NOT DRAW A BREADBOARD
-----------------------------------
The first version rendered the whole 70-column breadboard eight times, dimming
what was already placed. It was accurate and almost unreadable: at that width
the components are a few pixels tall and thirty jumper wires arc across the
canvas, so finding "the one thing I add now" meant hunting.

This version draws each step as SIGNAL CHAINS instead - one row per circuit,
read left to right exactly the way you wire it:

    [ GPIO26 ] --- [ 220R ] --- [ LED ] --- | GND rail

Each row is one thing you build. Nothing else is on screen competing with it.
Physical hole positions are deliberately absent, because they are the part that
differs between breadboards anyway; what matters is which pin connects to what,
in what order, through which component.

Pin numbers are parsed from the sketch, so the pictures cannot drift from the
firmware. Pins are named by their SILKSCREEN LABEL, never by counting holes -
30-pin and 38-pin DevKits order their headers differently.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESP = ROOT / "hardware" / "wokwi_esp32" / "gaukavach_esp32.ino"

# palette, shared with the rest of the project
INK, BODY, MUTED, FAINT = "#0F141A", "#28323C", "#5D6B79", "#8695A3"
LINE, PAPER, SURF = "#D2DAE1", "#FFFFFF", "#F5F8FA"
ACCENT, OK, WARN, CRIT = "#0E7C86", "#1C7A4B", "#B0850F", "#A9291F"
BOARD = "#1B3A42"
RAIL_POS, RAIL_GND = "#C0392B", "#2C3238"

# resistor colour bands
BANDS = {
    "220": ["#CC2200", "#CC2200", "#8B4513"],
    "1k":  ["#8B4513", "#1A1A1A", "#CC2200"],
    "2k":  ["#CC2200", "#1A1A1A", "#CC2200"],
    "10k": ["#8B4513", "#1A1A1A", "#E07000"],
}

# geometry of one signal-chain row
ROW_H = 76
X_PIN, W_PIN = 34, 118
X_R = 210          # first inline component
X_C = 400          # second inline component
X_RAIL = 852
CANVAS_W = 940


OHM = "Ω"


def ascii_safe(s: str) -> str:
    """Every non-ASCII character becomes a numeric reference.

    The page ships as an HTML fragment, so the charset is whatever the host
    decides. A literal UTF-8 omega read as latin-1 renders as two junk glyphs,
    which is exactly what happened to every resistor label in the last build.
    Numeric references cannot be misdecoded.
    """
    return "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in s)


def esc(s) -> str:
    return ascii_safe(html.escape(str(s), quote=True))


def pins() -> dict[str, str]:
    src = ESP.read_text(encoding="utf-8")
    out = {}
    for n in ("PIN_TRIG", "PIN_ECHO", "PIN_EMIT", "LED_PERMIT", "LED_REFUSE",
              "LED_ESCALATE", "LED_ARMED", "BTN_PERSON", "BTN_NONTARGET",
              "BTN_ESTOP", "POT_GROUP"):
        m = re.search(rf"\b{n}\s*=\s*(\d+)", src)
        if not m:
            raise SystemExit(f"{n} not found in {ESP.name}")
        out[n] = m.group(1)
    return out


# GPIO36/39 are printed VP/VN on the silkscreen; naming them by number alone
# sends people hunting for a pin that is not marked.
ALIAS = {"36": "GPIO36 (VP)", "39": "GPIO39 (VN)"}


def pin_name(g: str) -> str:
    return ALIAS.get(g, f"GPIO{g}")


class S:
    def __init__(self, w: int, h: int):
        self.w, self.h, self.o = w, h, []

    def add(self, x):
        self.o.append(x)

    def rect(self, x, y, w, h, fill, stroke="none", rx=4, sw=1.2):
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                 f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def circ(self, x, y, r, fill, stroke="none", sw=1.0):
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"/>')

    def txt(self, x, y, s, size: float = 12, fill=BODY, anchor="start", weight="400",
            fam="ui-monospace,'DejaVu Sans Mono',Menlo,Consolas,monospace"):
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
                 f'text-anchor="{anchor}" font-weight="{weight}" '
                 f'font-family="{fam}">{esc(s)}</text>')

    def wire(self, x1, y1, x2, y2, col, w=3.4):
        self.add(f'<path d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}" stroke="{col}" '
                 f'stroke-width="{w}" fill="none" stroke-linecap="round"/>')

    def elbow(self, x1, y1, x2, y2, col, w=3.4):
        """Right-angled run: across, then down/up. Reads as a real jumper."""
        r = 8
        dy = 1 if y2 > y1 else -1
        self.add(f'<path d="M{x1:.1f},{y1:.1f} H{x2 - r:.1f} '
                 f'Q{x2:.1f},{y1:.1f} {x2:.1f},{y1 + dy * r:.1f} V{y2:.1f}" '
                 f'stroke="{col}" stroke-width="{w}" fill="none" '
                 f'stroke-linecap="round" stroke-linejoin="round"/>')

    def out(self, title):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                f'width="100%" role="img" aria-label="{esc(title)}">'
                f'<rect width="{self.w}" height="{self.h}" fill="{PAPER}"/>'
                + "".join(self.o) + "</svg>")


# ---------------------------------------------------------------- box chain
#
# Every label lives INSIDE a box, and every box sits on a fixed grid slot, so
# two pieces of text can never land on top of each other. The previous version
# annotated free-floating wires and the annotations collided.

BW, BH = 156, 64          # box size
GAPX, GAPY = 44, 42       # space between boxes
X0, Y0 = 36, 80           # centre of the first slot
STRIDE_X = BW + GAPX
STRIDE_Y = BH + GAPY


def bx(c: float) -> float:
    return X0 + c * STRIDE_X


def by(r: float) -> float:
    return Y0 + r * STRIDE_Y


def icon(s: "S", x: float, y: float, kind: str, colour: str) -> None:
    """26x26 pictogram, vertically centred, at the left edge of a box."""
    if kind == "res":
        s.rect(x - 15, y - 8, 30, 16, "#E4D5B0", "#B9A67E", rx=3)
        for i, c in enumerate(BANDS.get(colour, BANDS["220"])):
            s.rect(x - 9 + i * 6, y - 8, 3, 16, c, rx=1)
    elif kind == "led":
        s.add(f'<path d="M{x - 11},{y + 3} a11,11 0 0 1 22,0 l0,8 l-22,0 z" '
              f'fill="{colour}" stroke="#00000035" stroke-width="1"/>')
        s.wire(x - 6, y + 11, x - 6, y + 16, "#8A8F96", 2)
        s.wire(x + 6, y + 11, x + 6, y + 16, "#8A8F96", 2)
    elif kind == "piezo":
        s.circ(x, y, 13, "#C9A227", "#9A7B15", 1.4)
        s.circ(x, y, 6, "#EEE3AC")
    elif kind == "btn":
        s.rect(x - 13, y - 13, 26, 26, "#3A4149", "#252A30", rx=4)
        s.circ(x, y, 8, colour, "#00000040", 1.2)
    elif kind == "pot":
        s.rect(x - 13, y - 12, 26, 24, "#2E5FA3", "#1F4478", rx=4)
        s.circ(x, y - 2, 8, "#DEE2E6")
        s.wire(x, y - 2, x + 5, y - 7, "#4A5058", 2)
    elif kind == "sr04":
        s.rect(x - 15, y - 10, 30, 20, "#1E4C7A", "#143557", rx=3)
        for dx in (-7, 7):
            s.circ(x + dx, y - 1, 6, "#5A6672", "#39424C", 1)
    elif kind == "node":
        s.circ(x, y, 7, colour)
        s.circ(x, y, 12, "none", colour, 1.6)


def box(s: "S", c: float, r: float, style: str, title: str, sub: str,
        colour: str = ACCENT, ikind: str = "", icolour: str = "") -> None:
    """One grid slot. style: pin | part | rail | node."""
    x, y = bx(c), by(r)
    if style == "pin":
        fill, stroke, tcol, scol = BOARD, "none", "#E4F2F4", "#8FB4BA"
    elif style == "rail":
        fill, stroke, tcol, scol = colour, "none", "#FFFFFF", "#FFFFFFB0"
    else:
        fill, stroke, tcol, scol = SURF, LINE, INK, MUTED
    s.rect(x, y - BH / 2, BW, BH, fill, stroke, rx=8, sw=1.3)
    s.rect(x, y - BH / 2, 4.5, BH, colour, rx=2)

    tx = x + 18
    if ikind:
        icon(s, x + 32, y, ikind, icolour or colour)
        tx = x + 54
    s.txt(tx, y - 2, title, 12.5, tcol, weight="700")
    if sub:
        s.txt(tx, y + 16, sub, 10.5, scol,
              fam="system-ui,-apple-system,'Segoe UI',sans-serif")


def link(s: "S", c0: float, r0: float, c1: float, r1: float, colour: str) -> None:
    """Wire between two horizontally adjacent slots."""
    x0, x1, y = bx(c0) + BW, bx(c1), by(r0)
    s.wire(x0, y, x1, y, colour, 3.6)
    s.circ(x0, y, 4.5, colour)
    s.circ(x1, y, 4.5, colour)


def drop(s: "S", c: float, r0: float, r1: float, colour: str) -> None:
    """Wire from the bottom of one slot to the top of the slot below it."""
    x = bx(c) + BW / 2
    y0, y1 = by(r0) + BH / 2, by(r1) - BH / 2
    s.wire(x, y0, x, y1, colour, 3.6)
    s.circ(x, y0, 4.5, colour)
    s.circ(x, y1, 4.5, colour)


def canvas(nrows: int, caption: str, cap_col: str = MUTED) -> "S":
    s = S(CANVAS_W, int(by(nrows - 1) + BH / 2 + 30))
    s.txt(X0, 34, caption, 13, cap_col)
    return s


# ---------------------------------------------------------------- step art

def draw(step: int, p: dict[str, str]) -> str:

    if step == 1:
        s = canvas(3, "Two supply wires, then one link between the ground rails.")
        box(s, 0, 0, "pin", "3V3", "ESP32 header", RAIL_POS)
        box(s, 1, 0, "rail", "+ RAIL", "red line, top", RAIL_POS)
        link(s, 0, 0, 1, 0, RAIL_POS)
        box(s, 0, 1, "pin", "GND", "ESP32 header", RAIL_GND)
        box(s, 1, 1, "rail", "- RAIL", "blue line, top", RAIL_GND)
        link(s, 0, 1, 1, 1, RAIL_GND)
        box(s, 0, 2, "rail", "- RAIL", "top of board", RAIL_GND)
        box(s, 1, 2, "rail", "- RAIL", "bottom of board", RAIL_GND)
        link(s, 0, 2, 1, 2, RAIL_GND)
        return s.out("Step 1")

    if step == 2:
        specs = [(p["LED_PERMIT"], "#2ECC71", "GREEN LED", "permitted", OK),
                 (p["LED_REFUSE"], "#E74C3C", "RED LED", "refused", CRIT),
                 (p["LED_ESCALATE"], "#F1C40F", "AMBER LED", "escalated", WARN)]
        s = canvas(3, "Three identical chains. Long leg faces the resistor.")
        for r, (g, colour, name, meaning, accent) in enumerate(specs):
            box(s, 0, r, "pin", pin_name(g), "output", accent)
            box(s, 1, r, "part", "220 " + OHM, "series resistor", accent, "res", "220")
            box(s, 2, r, "part", name, "long leg on the left", accent, "led", colour)
            box(s, 3, r, "rail", "- RAIL", "short leg", RAIL_GND)
            for c in range(3):
                link(s, c, r, c + 1, r, accent if c < 2 else RAIL_GND)
        return s.out("Step 2")

    if step == 3:
        s = canvas(1, "The emitter. The series resistor is not optional.")
        box(s, 0, 0, "pin", pin_name(p["PIN_EMIT"]), "LEDC carrier out", ACCENT)
        box(s, 1, 0, "part", "220 " + OHM, "series resistor", ACCENT, "res", "220")
        box(s, 2, 0, "part", "PIEZO +", "marked leg", ACCENT, "piezo")
        box(s, 3, 0, "rail", "- RAIL", "other leg", RAIL_GND)
        for c in range(3):
            link(s, c, 0, c + 1, 0, ACCENT if c < 2 else RAIL_GND)
        return s.out("Step 3")

    if step == 4:
        specs = [(p["BTN_PERSON"], "#2E86C1", "PERSON", "veto: human in cone", ACCENT),
                 (p["BTN_NONTARGET"], "#F1C40F", "DOG / GOAT", "veto: non-target", ACCENT),
                 (p["BTN_ESTOP"], "#E74C3C", "E-STOP", "kills emission", CRIT)]
        s = canvas(3, "Pin on one leg, ground on the leg diagonally opposite.")
        for r, (g, colour, name, meaning, accent) in enumerate(specs):
            box(s, 0, r, "pin", pin_name(g), "input", accent)
            box(s, 1, r, "part", name, meaning, accent, "btn", colour)
            box(s, 2, r, "rail", "- RAIL", "opposite leg", RAIL_GND)
            link(s, 0, r, 1, r, accent)
            link(s, 1, r, 2, r, RAIL_GND)
        return s.out("Step 4")

    if step == 5:
        s = canvas(2, "One extra resistor, sitting beside the button - not in line with it.",
                   CRIT)
        box(s, 0, 0, "pin", pin_name(p["BTN_ESTOP"]), "input only, no pull-up", CRIT)
        box(s, 1, 0, "part", "JUNCTION", "the button's pin leg", CRIT, "node")
        box(s, 2, 0, "part", "10k " + OHM, "pull-up resistor", RAIL_POS, "res", "10k")
        box(s, 3, 0, "rail", "+ RAIL", "3V3", RAIL_POS)
        link(s, 0, 0, 1, 0, CRIT)
        link(s, 1, 0, 2, 0, RAIL_POS)
        link(s, 2, 0, 3, 0, RAIL_POS)
        box(s, 1, 1, "part", "E-STOP", "already wired in step 4", CRIT, "btn", "#E74C3C")
        box(s, 2, 1, "rail", "- RAIL", "opposite leg", RAIL_GND)
        drop(s, 1, 0, 1, CRIT)
        link(s, 1, 1, 2, 1, RAIL_GND)
        return s.out("Step 5")

    if step == 6:
        s = canvas(3, "Three legs. The middle one is the wiper.")
        box(s, 0, 0, "pin", "3V3", "never 5V", RAIL_POS)
        box(s, 1, 0, "part", "POT leg 1", "either outer leg", RAIL_POS, "pot")
        link(s, 0, 0, 1, 0, RAIL_POS)
        box(s, 0, 1, "pin", pin_name(p["POT_GROUP"]), "ADC input", WARN)
        box(s, 1, 1, "part", "POT wiper", "the middle leg", WARN, "pot")
        link(s, 0, 1, 1, 1, WARN)
        box(s, 0, 2, "pin", "GND", "ESP32 header", RAIL_GND)
        box(s, 1, 2, "part", "POT leg 3", "the other outer leg", RAIL_GND, "pot")
        link(s, 0, 2, 1, 2, RAIL_GND)
        return s.out("Step 6")

    if step == 7:
        ECHO = "#2E86C1"
        s = canvas(5, "The sensor runs on 5 V. Its ECHO output must not touch a pin "
                      "directly.", CRIT)
        box(s, 0, 0, "pin", "VIN / 5V", "USB rail, not 3V3", RAIL_POS)
        box(s, 1, 0, "part", "SR04 VCC", "sensor supply", RAIL_POS, "sr04")
        link(s, 0, 0, 1, 0, RAIL_POS)

        box(s, 0, 1, "part", "SR04 GND", "sensor ground", RAIL_GND, "sr04")
        box(s, 1, 1, "rail", "- RAIL", "shared ground", RAIL_GND)
        link(s, 0, 1, 1, 1, RAIL_GND)

        box(s, 0, 2, "pin", pin_name(p["PIN_TRIG"]), "output, 3.3 V is fine", OK)
        box(s, 1, 2, "part", "SR04 TRIG", "trigger input", OK, "sr04")
        link(s, 0, 2, 1, 2, OK)

        box(s, 0, 3, "part", "SR04 ECHO", "swings to 5 V", ECHO, "sr04")
        box(s, 1, 3, "part", "1k " + OHM, "upper leg", ECHO, "res", "1k")
        box(s, 2, 3, "part", "JUNCTION", "about 3.3 V here", ACCENT, "node")
        box(s, 3, 3, "pin", pin_name(p["PIN_ECHO"]), "reads the junction", ACCENT)
        link(s, 0, 3, 1, 3, ECHO)
        link(s, 1, 3, 2, 3, ECHO)
        link(s, 2, 3, 3, 3, ACCENT)

        box(s, 2, 4, "part", "2k " + OHM, "lower leg", ECHO, "res", "2k")
        box(s, 3, 4, "rail", "- RAIL", "divider bottom", RAIL_GND)
        drop(s, 2, 3, 4, ECHO)
        link(s, 2, 4, 3, 4, RAIL_GND)
        return s.out("Step 7")

    # step 8 - the finished map, one line per pin
    items = [
        ("3V3 / GND", "the two rails, linked top to bottom", RAIL_POS),
        ("VIN / 5V", "HC-SR04 VCC", RAIL_POS),
        (pin_name(p["LED_PERMIT"]), "220 " + OHM + "  >  green LED  >  - rail", OK),
        (pin_name(p["LED_REFUSE"]), "220 " + OHM + "  >  red LED  >  - rail", CRIT),
        (pin_name(p["LED_ESCALATE"]), "220 " + OHM + "  >  amber LED  >  - rail", WARN),
        (pin_name(p["PIN_EMIT"]), "220 " + OHM + "  >  piezo  >  - rail", ACCENT),
        (pin_name(p["BTN_PERSON"]), "button  >  - rail", ACCENT),
        (pin_name(p["BTN_NONTARGET"]), "button  >  - rail", ACCENT),
        (pin_name(p["BTN_ESTOP"]), "button  >  - rail    and    10k " + OHM + "  >  + rail",
         CRIT),
        (pin_name(p["POT_GROUP"]), "pot wiper   (outer legs to 3V3 and GND)", WARN),
        (pin_name(p["PIN_TRIG"]), "HC-SR04 TRIG", OK),
        (pin_name(p["PIN_ECHO"]), "1k / 2k divider junction  <  ECHO", CRIT),
        (pin_name(p["LED_ARMED"]), "on-board LED - nothing to wire", MUTED),
    ]
    s = S(CANVAS_W, 96 + len(items) * 30)
    s.txt(X0, 34, "Everything on one page. Walk the list before you plug in USB.", 13, MUTED)
    y = 74
    for name, what, col in items:
        s.rect(X0, y - 14, CANVAS_W - 2 * X0, 28, SURF if (y // 30) % 2 else PAPER, rx=4)
        s.rect(X0, y - 14, 4, 28, col, rx=2)
        s.txt(X0 + 18, y + 5, name, 12, INK, weight="700")
        s.txt(X0 + 190, y + 5, what, 12, MUTED)
        y += 30
    return s.out("Step 8")


# ---------------------------------------------------------------- content

STEPS = [
    (1, "Power the rails", ACCENT,
     ["<b>3V3</b> to the <b>+</b> rail.",
      "<b>GND</b> to the <b>&minus;</b> rail.",
      "Link the top and bottom <b>&minus;</b> rails together."],
     "Find every pin by the label printed on the board, never by counting holes. "
     "The 30-pin and 38-pin DevKits order their headers differently."),

    (2, "Three status LEDs", OK,
     ["220&Omega; from <b>GPIO26</b>, then the green LED, then the <b>&minus;</b> rail.",
      "Same again for <b>GPIO27</b> (red) and <b>GPIO14</b> (amber).",
      "Long leg is the anode and faces the resistor. Short leg goes to ground."],
     "Green = permitted, red = refused, amber = gave up and called a human. "
     "The blue ARMED heartbeat is GPIO2, already soldered to the board."),

    (3, "The emitter", ACCENT,
     ["220&Omega; from <b>GPIO25</b>.",
      "Piezo after it: <b>+</b> to the resistor, <b>&minus;</b> to the rail."],
     "If your transducer is a 40&nbsp;kHz ranging element it is the wrong part &mdash; "
     "40&nbsp;kHz is above the 35&nbsp;kHz cattle audiogram endpoint. Fine as a "
     "signal-chain stand-in; just say so."),

    (4, "The three veto buttons", CRIT,
     ["<b>GPIO32</b> &rarr; PERSON button &rarr; <b>&minus;</b> rail.",
      "<b>GPIO33</b> &rarr; DOG/GOAT, <b>GPIO35</b> &rarr; E-STOP, same pattern.",
      "No resistors needed on the first two &mdash; the sketch uses INPUT_PULLUP."],
     "Press-to-ground is the right way round for a safety input: a broken wire reads "
     "as &lsquo;not pressed&rsquo; rather than as a stuck button."),

    (5, "Pull up the E-stop", CRIT,
     ["10k&Omega; from the <b>GPIO35</b> node to the <b>+</b> rail.",
      "Same node as the button leg &mdash; the resistor sits alongside it, not in series."],
     "GPIO34&ndash;39 are input-only and have <b>no internal pull-up in the silicon</b>. "
     "Without this the input floats and the E-stop latches at random, usually mid-demo. "
     "It looks like flaky software, not a missing resistor."),

    (6, "Group-size potentiometer", WARN,
     ["Outer legs to <b>+</b> and <b>&minus;</b>.",
      "Wiper to <b>GPIO34</b>.",
      "Sets how many animals the governor thinks are grouped, 1 to 8."],
     "The pot goes to <b>3V3, never 5V</b>. ESP32 ADC pins are not 5 V tolerant."),

    (7, "HC-SR04, through a divider", CRIT,
     ["<b>VCC</b> to <b>VIN/5V</b> &mdash; the sensor needs 5 V to be reliable.",
      "<b>GND</b> to the <b>&minus;</b> rail.",
      "<b>TRIG</b> straight to <b>GPIO13</b>. That is an output, so 3.3 V is fine.",
      "<b>ECHO</b> &rarr; 1k&Omega; &rarr; junction &rarr; 2k&Omega; &rarr; ground. "
      "<b>GPIO39 (VN)</b> reads the junction."],
     "ECHO swings to 5 V and ESP32 GPIOs are NOT 5 V tolerant. Most tutorials wire it "
     "straight to a pin; that is how people quietly cook an ESP32."),

    (8, "Power up and check", OK,
     ["Plug in USB. The on-board blue LED blinks about once a second.",
      "Serial monitor at <b>115200</b>: the limits print, then "
      "<i>NO calibrated mic attached: this rig makes no dB claim</i>.",
      "Turn the pot fully <b>left</b> first, or it refuses for herd size straight away.",
      "Hand about 80&nbsp;cm from the sensor &rarr; green, <b>PERMITTED @ 28.6 m</b>."],
     "If the E-stop latches on its own, step 5 is missing or on the wrong node. "
     "If nothing lights at all, check the sensor &mdash; without it the sketch idles forever."),
]

PARTS = [
    ("1", "ESP32 DevKit", "any 30- or 38-pin variant"),
    ("1", "HC-SR04", "ultrasonic sensor"),
    ("1", "Piezo buzzer", "the emitter stand-in"),
    ("3", "LED", "green, red, amber"),
    ("4", "Resistor 220&Omega;", "three LEDs + the piezo"),
    ("1", "Resistor 1k&Omega;", "ECHO divider, upper leg"),
    ("1", "Resistor 2k&Omega;", "ECHO divider, lower leg"),
    ("1", "Resistor 10k&Omega;", "E-stop pull-up"),
    ("3", "Tactile button", "person, dog/goat, e-stop"),
    ("1", "Potentiometer 10k&Omega;", "group size"),
    ("1", "Breadboard + jumpers", ""),
]

PAGE = """<title>GauKavach - ESP32 Build Guide</title>
<style>
:root{{--ground:#EDF0F3;--surface:#FFFFFF;--ink:#0F141A;--body:#28323C;--muted:#5D6B79;
--faint:#8695A3;--line:#D2DAE1;--accent:#0E7C86;--accent-soft:#DBEDEF;--ok:#1C7A4B;
--ok-bg:#E2F1E8;--warn:#93670A;--warn-bg:#F8EFD8;--crit:#A9291F;--crit-bg:#F8E4E2;
--surface-2:#F5F8FA;}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--ground:#0C1116;
--surface:#131A21;--ink:#E9EEF3;--body:#C3CFD9;--muted:#8FA0AE;--faint:#6B7C8A;
--line:#212C36;--accent:#40B9C2;--accent-soft:#10333A;--ok:#5FBF8A;--ok-bg:#12291E;
--warn:#D9A63C;--warn-bg:#2C2314;--crit:#E0776C;--crit-bg:#2E1815;--surface-2:#182028;}}}}
:root[data-theme="dark"]{{--ground:#0C1116;--surface:#131A21;--ink:#E9EEF3;--body:#C3CFD9;
--muted:#8FA0AE;--faint:#6B7C8A;--line:#212C36;--accent:#40B9C2;--accent-soft:#10333A;
--ok:#5FBF8A;--ok-bg:#12291E;--warn:#D9A63C;--warn-bg:#2C2314;--crit:#E0776C;
--crit-bg:#2E1815;--surface-2:#182028;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);color:var(--body);
font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;font-size:15.5px;line-height:1.62}}
h1,h2{{font-family:Charter,"Bitstream Charter",Georgia,serif;color:var(--ink);margin:0;text-wrap:balance}}
.wrap{{max-width:1040px;margin:0 auto;padding:0 24px 80px}}
header{{background:var(--surface);border-bottom:1px solid var(--line);padding:30px 0 26px;margin-bottom:26px}}
.eyebrow{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px;letter-spacing:.14em;
text-transform:uppercase;color:var(--accent)}}
h1{{font-size:32px;letter-spacing:-.015em;margin-top:6px}}
.lede{{max-width:70ch;margin-top:12px;color:var(--muted)}}

.rail{{display:flex;gap:6px;margin:22px 0 0;flex-wrap:wrap}}
.rail a{{flex:1 1 0;min-width:64px;text-decoration:none;border:1px solid var(--line);
background:var(--surface);padding:8px 4px;text-align:center;
font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px;color:var(--muted)}}
.rail a b{{display:block;font-size:16px;color:var(--ink);margin-bottom:2px}}
.rail a:hover{{border-color:var(--accent);color:var(--accent)}}

.step{{background:var(--surface);border:1px solid var(--line);margin-top:30px;overflow:hidden;
scroll-margin-top:14px}}
.shead{{display:flex;gap:18px;align-items:center;padding:18px 24px;border-bottom:1px solid var(--line)}}
.num{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:19px;font-weight:700;color:#fff;
background:var(--accent);width:44px;height:44px;display:grid;place-items:center;flex:none;border-radius:50%}}
.num.crit{{background:var(--crit)}} .num.ok{{background:var(--ok)}} .num.warn{{background:var(--warn)}}
h2{{font-size:23px}}
.body{{padding:20px 24px 24px}}
ol{{margin:0;padding-left:24px;max-width:80ch}} ol li{{margin-bottom:9px}}
ol li::marker{{color:var(--accent);font-weight:700}}
.pic{{margin-top:18px;border:1px solid var(--line);background:#fff;overflow-x:auto}}
.pic svg{{display:block;min-width:720px}}
.note{{margin-top:16px;padding:14px 17px;border-left:3px solid var(--warn);background:var(--warn-bg);
font-size:14px;max-width:88ch}}
.note.crit{{border-left-color:var(--crit);background:var(--crit-bg)}}
.note b{{color:var(--ink)}}

.callout{{border:1px solid var(--line);border-left:3px solid var(--crit);background:var(--crit-bg);
padding:16px 20px;margin-top:22px}}
.callout .lbl{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10.5px;letter-spacing:.1em;
text-transform:uppercase;color:var(--crit);margin-bottom:7px}}
.callout p{{margin:0;max-width:78ch}} .callout p+p{{margin-top:10px}}
table{{border-collapse:collapse;width:100%;font-size:14px;margin-top:14px}}
th{{text-align:left;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10.5px;
letter-spacing:.07em;text-transform:uppercase;color:var(--faint);font-weight:400;padding:10px 13px;
border-bottom:1px solid var(--line);background:var(--surface-2)}}
td{{padding:9px 13px;border-bottom:1px solid var(--line)}}
td.q{{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--ink);white-space:nowrap;width:1%}}
.scroll{{overflow-x:auto;border:1px solid var(--line);background:var(--surface);margin-top:14px}}
code{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.9em;background:var(--surface-2);
padding:1px 5px;border:1px solid var(--line)}}
@media print{{body{{background:#fff}} .step{{break-inside:avoid}} .rail{{display:none}}}}
</style>
<header><div class="wrap">
<div class="eyebrow">ESP32 build guide</div>
<h1>Bench governor &mdash; build it step by step</h1>
<p class="lede">Eight steps. Read every diagram left to right: <strong>each box is one thing
you push into the breadboard</strong>, and <strong>each line between two boxes is one jumper
wire</strong>. Chains start at an ESP32 pin and end at a rail. Where a line drops to the row
below, that is a branch off the same node &mdash; not a new connection in series.</p>
<div class="rail">{rail}</div>
<p style="margin-top:18px;font-size:14px;color:var(--muted)">Want the same circuit placed on an actual board, hole by hole? See the <a href="https://claude.ai/code/artifact/e2084b93-b29b-41e5-b80a-103e3192d09a" style="color:var(--accent)">breadboard build</a>.</p>
</div></header>
<div class="wrap">

<div class="callout">
<div class="lbl">Two steps exist only to protect the board</div>
<p><strong>Step 5</strong> (10k pull-up on the E-stop) and <strong>step 7</strong>
(1k/2k divider on ECHO). Most tutorials skip both. Skipping the first gives you an E-stop that
fires at random; skipping the second puts 5&nbsp;V into a pin that is not 5&nbsp;V tolerant.</p>
<p>Pins are named by their <strong>silkscreen label</strong>. GPIO36 and GPIO39 are printed
<code>VP</code> and <code>VN</code> on most boards &mdash; the diagrams show both.</p>
</div>

<h2 style="margin-top:34px">Parts</h2>
<div class="scroll"><table><thead><tr><th>Qty</th><th>Part</th><th>Notes</th></tr></thead>
<tbody>{parts}</tbody></table></div>

{steps}

<h2 style="margin-top:38px">Every connection, one table</h2>
<div class="scroll"><table><thead><tr><th>Pin</th><th>Goes to</th><th>Why</th></tr></thead>
<tbody>{pinmap}</tbody></table></div>

<p style="color:var(--faint);font-size:13px;margin-top:30px">
Pin numbers are parsed from <code>hardware/wokwi_esp32/gaukavach_esp32.ino</code> at build time, so
these diagrams cannot drift from the firmware. Regenerate with
<code>python tools/make_build_steps.py</code>.</p>
</div>
"""


def main() -> None:
    p = pins()

    rail_html = "".join(
        f'<a href="#s{n}"><b>{n}</b>{esc(t.split(chr(32))[0])}</a>'
        for n, t, _c, _i, _note in STEPS)

    parts_html = "".join(
        f'<tr><td class="q">{q}</td><td>{name}</td>'
        f'<td style="color:var(--muted)">{note}</td></tr>'
        for q, name, note in PARTS)

    cls = {ACCENT: "", CRIT: " crit", OK: " ok", WARN: " warn"}
    blocks = []
    for n, title, colour, items, note in STEPS:
        li = "".join(f"<li>{i}</li>" for i in items)
        ncls = "note crit" if colour == CRIT else "note"
        blocks.append(
            f'<div class="step" id="s{n}"><div class="shead">'
            f'<span class="num{cls[colour]}">{n}</span><h2>{esc(title)}</h2></div>'
            f'<div class="body"><ol>{li}</ol>'
            f'<div class="pic">{draw(n, p)}</div>'
            f'<div class="{ncls}">{note}</div></div></div>')

    rows = [
        ("3V3", "+ rail", "logic supply for the pot and the E-stop pull-up"),
        ("VIN / 5V", "HC-SR04 VCC", "the sensor needs 5 V to be reliable"),
        ("GND", "&minus; rails", "top and bottom rails must be linked"),
        (pin_name(p["LED_PERMIT"]), "220&Omega; + green LED", "permitted / emitting"),
        (pin_name(p["LED_REFUSE"]), "220&Omega; + red LED", "refused"),
        (pin_name(p["LED_ESCALATE"]), "220&Omega; + amber LED", "escalated to dispatch"),
        (pin_name(p["LED_ARMED"]), "on-board LED", "armed heartbeat, nothing to wire"),
        (pin_name(p["PIN_EMIT"]), "220&Omega; + piezo", "LEDC ramped burst"),
        (pin_name(p["BTN_PERSON"]), "button to GND", "person in cone, absolute veto"),
        (pin_name(p["BTN_NONTARGET"]), "button to GND", "dog / goat in cone, absolute veto"),
        (pin_name(p["BTN_ESTOP"]), "button to GND + 10k&Omega; to 3V3",
         "input-only pin, no internal pull-up"),
        (pin_name(p["POT_GROUP"]), "pot wiper", "group size; pot ends to 3V3 and GND"),
        (pin_name(p["PIN_TRIG"]), "HC-SR04 TRIG", "output, 3.3 V is fine"),
        (pin_name(p["PIN_ECHO"]), "1k/2k divider junction", "ECHO is 5 V; never wire it direct"),
    ]
    pinmap = "".join(
        f'<tr><td class="q">{a}</td><td>{b}</td>'
        f'<td style="color:var(--muted)">{c}</td></tr>' for a, b, c in rows)

    out = ROOT / "hardware" / "build_steps.html"
    page = PAGE.format(rail=rail_html, parts=parts_html,
                       steps="".join(blocks), pinmap=pinmap)
    out.write_text(ascii_safe(page), encoding="utf-8")
    print(f"wrote hardware/build_steps.html ({out.stat().st_size / 1024:.0f} KB), "
          f"{len(STEPS)} steps")


if __name__ == "__main__":
    main()
