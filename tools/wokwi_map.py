"""
One picture of the whole Wokwi circuit, with every attachment point named.

Imported by make_wokwi_steps.py; not run on its own.

WHY NOT JUST SCREENSHOT THE CANVAS
----------------------------------
The Wokwi canvas puts pins in the board's physical order, so wires have to cross
the whole board to reach the part they belong to. The picture is faithful and
almost unreadable - which is the complaint that produced this file.

Here the ESP32's pins are drawn as a stack of labelled stubs in the order the
parts need them. That is not the physical pin order and does not pretend to be:
you find a pin in Wokwi by its NAME, which is printed on every stub. In exchange
every wire is a straight line and nothing crosses anything.

Ground and 3V3 are drawn as two buses down the right-hand edge, because that is
what they are - one node each, shared by everything that touches them.
"""

from __future__ import annotations

ROW_H = 78
TOP = 124
X_BOARD, X_PADS = 30, 202       # ESP32 body, and its pin pads
X_JUNC = 322                    # where a branch drops to the row below
X_PL, X_PR = 398, 556           # part terminals, left and right
X_GND, X_3V3 = 792, 872         # the two buses
CANVAS_W = 952

INK, MUTED, FAINT = "#0F141A", "#5D6B79", "#8695A3"
LINE, PAPER, SURF = "#D2DAE1", "#FFFFFF", "#F5F8FA"
ACCENT, OK, WARN, CRIT = "#0E7C86", "#1C7A4B", "#B0850F", "#A9291F"
BOARD, PAD = "#1B3A42", "#D9B44A"
RED, BLACK, LEADS = "#C0392B", "#2C3238", "#9AA0A6"

BANDS = {"10k": ["#8B4513", "#1A1A1A", "#E07000"]}

# row -> (part, pin label, which side the wire leaves, where it goes)
# "left" endpoints are ESP32 pins by name; "right" endpoints are a bus.
ROWS = [
    ("ledG",  "A",    "left",  "GPIO26"),
    ("ledG",  "C",    "right", "GND"),
    ("ledR",  "A",    "left",  "GPIO27"),
    ("ledR",  "C",    "right", "GND"),
    ("ledA",  "A",    "left",  "GPIO14"),
    ("ledA",  "C",    "right", "GND"),
    ("bz",    "1",    "left",  "GPIO25"),
    ("bz",    "2",    "right", "GND"),
    ("btnP",  "1.l",  "left",  "GPIO32"),
    ("btnP",  "2.l",  "right", "GND"),
    ("btnN",  "1.l",  "left",  "GPIO33"),
    ("btnN",  "2.l",  "right", "GND"),
    ("btnE",  "1.l",  "left",  "GPIO35"),
    ("btnE",  "2.l",  "right", "GND"),
    ("r10k",  "1",    "branch", "GPIO35"),
    ("r10k",  "2",    "right", "3V3"),
    ("pot",   "SIG",  "left",  "GPIO34"),
    ("pot",   "VCC",  "right", "3V3"),
    ("pot",   "GND",  "right", "GND"),
    ("sr04",  "TRIG", "left",  "GPIO13"),
    ("sr04",  "ECHO", "left",  "GPIO39 (VN)"),
    ("sr04",  "VCC",  "right", "3V3"),
    ("sr04",  "GND",  "right", "GND"),
]

# part -> (kind, caption, accent, colour)
PARTS = {
    "ledG": ("led",  "PERMIT",      OK,     "#2ECC71"),
    "ledR": ("led",  "REFUSE",      CRIT,   "#E74C3C"),
    "ledA": ("led",  "ESCALATE",    WARN,   "#F1C40F"),
    "bz":   ("bz",   "BUZZER",      ACCENT, "#2B2F33"),
    "btnP": ("btn",  "PERSON",      ACCENT, "#2E86C1"),
    "btnN": ("btn",  "DOG / GOAT",  ACCENT, "#F1C40F"),
    "btnE": ("btn",  "E-STOP",      CRIT,   "#E74C3C"),
    "r10k": ("res",  "10k",         CRIT,   "10k"),
    "pot":  ("pot",  "GROUP SIZE",  WARN,   "#2E5FA3"),
    "sr04": ("sr04", "HC-SR04",     ACCENT, "#1E4C7A"),
}

# each part occupies the rows it appears in, and one physical body is drawn
# across that span - so a four-pin sensor looks like one four-pin sensor.
ORDER = ["ledG", "ledR", "ledA", "bz", "btnP", "btnN", "btnE", "r10k", "pot", "sr04"]


def _rows_of(part: str) -> list[int]:
    return [i for i, r in enumerate(ROWS) if r[0] == part]


def y_of(row: int) -> float:
    return TOP + row * ROW_H


def draw(S) -> str:
    """S is make_build_steps.S, the tiny SVG builder."""
    n = len(ROWS)
    h = int(y_of(n - 1) + 96)
    s = S(CANVAS_W, h)

    s.txt(X_BOARD, 34, "Every wire is a straight line. Both ends are named.",
          13, MUTED)
    s.txt(X_BOARD, 56,
          "Pin stubs are stacked in the order the parts need them, not in the "
          "board's physical order - find each one by its label.", 11, FAINT)

    _buses(s, h)
    _board(s, n)
    for part in ORDER:
        _part(s, part, _rows_of(part))
    for i, (part, pin, side, target) in enumerate(ROWS):
        _wire(s, i, part, pin, side, target)
    return s.out("Wokwi connection map")


# ------------------------------------------------------------------ pieces

def _buses(s, h: float) -> None:
    y0, y1 = TOP - 46, h - 40
    for x, col, name in ((X_GND, BLACK, "GND"), (X_3V3, RED, "3V3")):
        s.rect(x - 5, y0, 10, y1 - y0, col, rx=5)
        s.txt(x, y0 - 12, name, 12, col, anchor="middle", weight="700")
        s.txt(x, y1 + 20, name, 12, col, anchor="middle", weight="700")
    s.txt(X_GND, y1 + 38, "any GND pin", 9.5, FAINT, anchor="middle")
    s.txt(X_3V3, y1 + 38, "the 3V3 pin", 9.5, FAINT, anchor="middle")


def _board(s, n: int) -> None:
    y0, y1 = TOP - 46, y_of(n - 1) + 46
    s.rect(X_BOARD, y0, X_PADS - X_BOARD, y1 - y0, BOARD, rx=10)
    s.rect(X_BOARD + 14, y0 + 12, 96, 26, "#122A30", rx=4)
    s.txt(X_BOARD + 62, y0 + 30, "ESP32", 13, "#9FD3D9", anchor="middle",
          weight="700")
    s.rect(X_BOARD + 22, y1 - 40, 54, 26, "#3A4149", rx=4)
    s.txt(X_BOARD + 49, y1 - 22, "USB", 9.5, "#9AA6AE", anchor="middle")

    for i, (_part, _pin, side, target) in enumerate(ROWS):
        if side != "left":
            continue
        y = y_of(i)
        s.rect(X_PADS - 12, y - 11, 12, 22, PAD, rx=2)
        s.txt(X_PADS - 20, y + 4, target, 11.5, "#E7F3F5", anchor="end",
              weight="700")


def _label(s, x: float, y: float, text: str, colour: str, anchor: str) -> None:
    s.txt(x, y - 12, text, 10, colour, anchor=anchor, weight="700")


def _part(s, key: str, rows: list[int]) -> None:
    kind, caption, accent, colour = PARTS[key]
    ya, yb = y_of(rows[0]), y_of(rows[-1])
    mid = (ya + yb) / 2

    if kind == "led":
        cx, r = (X_PL + X_PR) / 2, 24
        s.add(f'<path d="M{cx - r},{mid + r * 0.4} a{r},{r} 0 0 1 {2 * r},0 '
              f'l0,{r * 0.55} l{-2 * r},0 z" fill="{colour}" '
              f'stroke="#00000035" stroke-width="1.3"/>')
        s.wire(X_PL, ya, cx - 11, mid + r * 0.9, LEADS, 2.6)
        s.wire(X_PR, yb, cx + 11, mid + r * 0.9, LEADS, 2.6)
        s.txt(cx, mid - r - 12, caption, 12, accent, anchor="middle", weight="700")
        s.txt(cx, mid + r + 26, "LED", 10, FAINT, anchor="middle")

    elif kind == "bz":
        cx = (X_PL + X_PR) / 2
        s.circ(cx, mid, 34, "#25292D", "#111417", 1.6)
        s.circ(cx, mid, 8, "#0C0E10")
        s.wire(X_PL, ya, cx - 24, mid, LEADS, 2.6)
        s.wire(X_PR, yb, cx + 24, mid, LEADS, 2.6)
        s.txt(cx, mid - 46, caption, 12, accent, anchor="middle", weight="700")

    elif kind == "btn":
        cx = (X_PL + X_PR) / 2
        s.rect(cx - 40, mid - 34, 80, 68, "#3A4149", "#252A30", rx=8, sw=1.4)
        s.circ(cx, mid, 23, colour, "#00000040", 1.6)
        s.wire(X_PL, ya, cx - 40, ya, LEADS, 2.6)
        s.wire(X_PR, yb, cx + 40, yb, LEADS, 2.6)
        s.txt(cx, mid - 44, caption, 12, accent, anchor="middle", weight="700")

    elif kind == "res":
        cx, bw = (X_PL + X_PR) / 2, 74
        s.wire(X_PL, ya, X_PR, yb, LEADS, 2.6)
        s.rect(cx - bw / 2, mid - 15, bw, 30, "#E4D5B0", "#B9A67E", rx=5)
        for i, c in enumerate(BANDS[colour]):
            s.rect(cx - bw / 2 + 14 + i * 13, mid - 15, 6, 30, c, rx=1)
        s.txt(cx, mid - 26, caption + " " + "Ω", 12, accent,
              anchor="middle", weight="700")

    elif kind == "pot":
        cx = (X_PL + X_PR) / 2
        s.rect(cx - 46, ya - 20, 92, (yb - ya) + 40, colour, "#1F4478", rx=8, sw=1.4)
        s.circ(cx, mid, 27, "#DEE2E6")
        s.wire(cx, mid, cx + 15, mid - 22, "#4A5058", 3.4)
        s.txt(cx, ya - 30, caption, 12, accent, anchor="middle", weight="700")
        for i in rows:
            y = y_of(i)
            side = ROWS[i][2]
            x = cx - 46 if side == "left" else cx + 46
            s.wire(X_PL if side == "left" else X_PR, y, x, y, LEADS, 2.6)

    elif kind == "sr04":
        cx = (X_PL + X_PR) / 2
        s.rect(cx - 60, ya - 22, 120, (yb - ya) + 44, colour, "#143557", rx=8, sw=1.4)
        for dy in (-34, 34):
            s.circ(cx, mid + dy, 27, "#5A6672", "#39424C", 1.8)
            s.circ(cx, mid + dy, 15, "#333B44")
        s.txt(cx, ya - 32, caption, 12, accent, anchor="middle", weight="700")
        for i in rows:
            y = y_of(i)
            side = ROWS[i][2]
            x = cx - 60 if side == "left" else cx + 60
            s.wire(X_PL if side == "left" else X_PR, y, x, y, LEADS, 2.6)


def _hop(s, x: float, y: float, colour: str) -> None:
    """Standard crossing notation: the wire arcs over the bus it does not join."""
    s.add(f'<path d="M{x - 9},{y} a9,9 0 0 1 18,0" stroke="{colour}" '
          f'stroke-width="3.4" fill="none" stroke-linecap="round"/>')


def _wire(s, row: int, part: str, pin: str, side: str, target: str) -> None:
    y = y_of(row)
    _kind, _cap, accent, _c = PARTS[part]

    if side == "left":
        s.wire(X_PADS, y, X_PL, y, accent, 3.4)
        s.circ(X_PL, y, 4.5, accent)
        _label(s, X_PL - 8, y, pin, MUTED, "end")

    elif side == "branch":
        # the pull-up joins the node one row above rather than a second pin
        above = y_of(row - 2)
        s.wire(X_JUNC, above, X_JUNC, y, accent, 3.4)
        s.wire(X_JUNC, y, X_PL, y, accent, 3.4)
        s.circ(X_JUNC, above, 6, accent)
        s.circ(X_PL, y, 4.5, accent)
        s.txt(X_JUNC + 12, y + 20, "same node as " + target, 9.5, MUTED)
        _label(s, X_PL - 8, y, pin, MUTED, "end")

    else:
        bus = X_GND if target == "GND" else X_3V3
        colour = BLACK if target == "GND" else RED
        s.circ(X_PR, y, 4.5, colour)
        _label(s, X_PR + 8, y, pin, MUTED, "start")
        if bus == X_3V3:
            s.wire(X_PR, y, X_GND - 9, y, colour, 3.4)
            _hop(s, X_GND, y, colour)
            s.wire(X_GND + 9, y, bus, y, colour, 3.4)
        else:
            s.wire(X_PR, y, bus, y, colour, 3.4)
        s.circ(bus, y, 6, colour)
