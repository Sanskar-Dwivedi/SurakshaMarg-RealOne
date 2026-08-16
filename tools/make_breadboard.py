"""
Generate the breadboard build guide: hole-by-hole placement.

    python tools/make_breadboard.py

RELATIONSHIP TO build_steps.html
--------------------------------
build_steps.html answers "what connects to what". This answers "which hole".
Both are generated from the same sketch, so the pin numbers cannot disagree.

WHY THE ESP32 IS NOT DRAWN PIN-BY-PIN
-------------------------------------
38-pin and 30-pin DevKits order their headers differently, and even among
38-pin boards the silkscreen order varies by vendor. Drawing one vendor's pin
order as if it were universal would send half the readers to the wrong hole.

So the module is drawn as a block occupying the low columns, and every wire
that starts at the ESP32 is named by its SILKSCREEN LABEL. That is safe for a
reason worth knowing: all five holes in a column are the same electrical node,
so whichever row the header pin sits in, the free holes in that same column and
same half are already connected to it. Find the label, use its column.

Component-side holes are given exactly, because nothing there is ambiguous.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESP = ROOT / "hardware" / "wokwi_esp32" / "gaukavach_esp32.ino"

INK, BODY, MUTED, FAINT = "#0F141A", "#28323C", "#5D6B79", "#8695A3"
LINE, PAPER, SURF = "#D2DAE1", "#FFFFFF", "#F5F8FA"
ACCENT, OK, WARN, CRIT = "#0E7C86", "#1C7A4B", "#B0850F", "#A9291F"
RED, BLUE, BLACK, GREEN, YELLOW, PURPLE = (
    "#C0392B", "#2E86C1", "#2C3238", "#1E8449", "#C9A227", "#7D3C98")

BOARD_BG, BOARD_EDGE = "#EAE6DB", "#CFC8B6"
CHANNEL = "#DAD4C4"
HOLE = "#5E5A52"

BANDS = {
    "220": ["#CC2200", "#CC2200", "#8B4513"],
    "1k":  ["#8B4513", "#1A1A1A", "#CC2200"],
    "2k":  ["#CC2200", "#1A1A1A", "#CC2200"],
    "10k": ["#8B4513", "#1A1A1A", "#E07000"],
}

OHM = "Ω"

# ------------------------------------------------------------------ placement
#
# One full-size (63 column) breadboard. The ESP32 sits over columns 1-20.
# Everything else lives in the columns below. Top half = rows F..J,
# bottom half = rows A..E; the two halves of a column are separate nodes.

LED_BASE = {"LED_PERMIT": 24, "LED_REFUSE": 30, "LED_ESCALATE": 36}
PIEZO_BASE = 42
POT_COL = 24                     # legs at 24, 25, 26 (bottom half)
SR04_COL = 30                    # VCC 30, TRIG 31, ECHO 32, GND 33 (bottom)
DIV_COL = 36                     # divider junction (bottom half)
BTN_COL = {"BTN_PERSON": 50, "BTN_NONTARGET": 55, "BTN_ESTOP": 60}
LINK_P, LINK_N = 47, 48       # rail links, in the gap between parts

COL_LO, COL_HI = 21, 63

# Entry row for each ESP32 wire. Distinct rows keep the
# feeds from sharing a segment; any free row in the column works.
LED_FEED_ROW = ["I", "H", "F"]
BTN_FEED_ROW = ["A", "B", "C"]

ROW_Y = {"+t": 0.7, "-t": 1.7,
         "J": 3.3, "I": 4.3, "H": 5.3, "G": 6.3, "F": 7.3,
         "E": 9.3, "D": 10.3, "C": 11.3, "B": 12.3, "A": 13.3,
         "+b": 14.9, "-b": 15.9}
BOARD_H = 16.8


def esc(s) -> str:
    t = html.escape(str(s), quote=True)
    return "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in t)


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


ALIAS = {"36": "GPIO36 (VP)", "39": "GPIO39 (VN)"}


def pin_name(g: str) -> str:
    return ALIAS.get(g, f"GPIO{g}")


# ------------------------------------------------------------------ svg canvas

class Board:
    """A breadboard window: columns c0..c1, drawn whole (both halves)."""

    def __init__(self, c0: int, c1: int, width: int = 980, left: int = 150,
                 top: int = 54, maxpitch: float = 27.0):
        self.c0, self.c1 = c0, c1
        n = c1 - c0
        self.p = min(maxpitch, (width - left - 46) / max(n, 1))
        self.x0, self.y0 = left, top
        self.w = int(left + (c1 - c0) * self.p + 46)
        self.h = int(top + BOARD_H * self.p + 46)
        self.o: list[str] = []
        self.show_badges = True

    # -- geometry
    def hx(self, col: float) -> float:
        return self.x0 + (col - self.c0) * self.p

    def hy(self, row: str) -> float:
        return self.y0 + ROW_Y[row] * self.p

    # -- raw svg
    def add(self, s: str) -> None:
        self.o.append(s)

    def rect(self, x, y, w, h, fill, stroke="none", rx: float = 3, sw=1.0):
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                 f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def circ(self, x, y, r, fill, stroke="none", sw=1.0):
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"/>')

    def txt(self, x, y, s, size=11.0, fill=MUTED, anchor="start", weight="400",
            fam="ui-monospace,'DejaVu Sans Mono',Menlo,Consolas,monospace"):
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
                 f'text-anchor="{anchor}" font-weight="{weight}" '
                 f'font-family="{fam}">{esc(s)}</text>')

    def wire(self, pts, col, w=None):
        w = w if w is not None else self.p * 0.17
        d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f} " + " ".join(
            f"L{x:.1f},{y:.1f}" for x, y in pts[1:])
        self.add(f'<path d="{d}" stroke="{col}" stroke-width="{w:.2f}" fill="none" '
                 f'stroke-linecap="round" stroke-linejoin="round"/>')

    # -- the board itself
    def frame(self) -> None:
        p, x0 = self.p, self.hx(self.c0)
        w = (self.c1 - self.c0) * p
        self.rect(x0 - p * 0.9, self.y0 - p * 0.5, w + p * 1.8,
                  BOARD_H * p + p * 0.2, BOARD_BG, BOARD_EDGE, rx=6, sw=1.4)

        # power rail stripes
        for row, col in (("+t", RED), ("-t", BLUE), ("+b", RED), ("-b", BLUE)):
            y = self.hy(row)
            off = -p * 0.62 if row.startswith("+") else p * 0.62
            self.add(f'<path d="M{x0 - p * 0.5:.1f},{y + off:.1f} '
                     f'H{x0 + w + p * 0.5:.1f}" stroke="{col}" stroke-width="1.6" '
                     f'opacity="0.75"/>')
            self.txt(x0 - p * 1.3, y + 4, "+" if row.startswith("+") else "-",
                     12, col, anchor="middle", weight="700")
            self.txt(x0 + w + p * 1.3, y + 4, "+" if row.startswith("+") else "-",
                     12, col, anchor="middle", weight="700")

        # centre channel
        ytop = self.hy("F") + p * 0.5
        self.rect(x0 - p * 0.9, ytop, w + p * 1.8, p, CHANNEL, rx=2)

        # holes
        for c in range(self.c0, self.c1 + 1):
            for row in ROW_Y:
                x, y = self.hx(c), self.hy(row)
                self.rect(x - p * 0.13, y - p * 0.13, p * 0.26, p * 0.26,
                          HOLE, rx=1.2)

        # row letters
        for row in "JIHGFEDCBA":
            for x in (x0 - p * 1.3, x0 + w + p * 1.3):
                self.txt(x, self.hy(row) + 4, row, 10.5, FAINT, anchor="middle")

        # column numbers, every 5
        for c in range(self.c0, self.c1 + 1):
            if c % 5 == 0:
                self.txt(self.hx(c), self.y0 - p * 1.0, str(c), 10, FAINT,
                         anchor="middle")
                self.txt(self.hx(c), self.y0 + BOARD_H * p + p * 0.5, str(c),
                         10, FAINT, anchor="middle")

    def col_marks(self, cols: set[int], colour: str = ACCENT) -> None:
        """Number the columns this step actually uses, above and below."""
        p = self.p
        for c in sorted(cols):
            self.txt(self.hx(c), self.y0 - p * 1.0, str(c), 10.5, colour,
                     anchor="middle", weight="700")
            self.txt(self.hx(c), self.y0 + BOARD_H * p + p * 0.5, str(c),
                     10.5, colour, anchor="middle", weight="700")

    # -- parts
    def leg(self, row: str, col: float, colour: str = "#8A8F96") -> tuple[float, float]:
        x, y = self.hx(col), self.hy(row)
        self.circ(x, y, self.p * 0.15, colour)
        return x, y

    def badge(self, n: int, x: float, y: float) -> None:
        if not self.show_badges:
            return
        self.circ(x, y, 9.5, "#FFFFFF", INK, 1.4)
        self.txt(x, y + 3.6, str(n), 10.5, INK, anchor="middle", weight="700")

    def resistor(self, n: int, row: str, ca: int, cb: int, value: str) -> None:
        p = self.p
        (xa, ya), (xb, yb) = self.leg(row, ca), self.leg(row, cb)
        self.wire([(xa, ya), (xb, yb)], "#9A9EA4", p * 0.09)
        cx, bw, bh = (xa + xb) / 2, abs(xb - xa) * 0.52, p * 0.42
        self.rect(cx - bw / 2, ya - bh / 2, bw, bh, "#E4D5B0", "#B9A67E", rx=3)
        for i, c in enumerate(BANDS[value]):
            self.rect(cx - bw / 2 + bw * (0.22 + i * 0.18), ya - bh / 2,
                      bw * 0.09, bh, c, rx=1)
        self.badge(n, max(xa, xb) + p * 0.55, ya)

    def led(self, n: int, row: str, ca: int, ck: int, colour: str) -> None:
        p = self.p
        (xa, ya), (xk, _) = self.leg(row, ca), self.leg(row, ck)
        cx, r = (xa + xk) / 2, p * 0.36
        self.wire([(xa, ya), (cx - r * 0.5, ya - p * 0.30)], "#9A9EA4", p * 0.09)
        self.wire([(xk, ya), (cx + r * 0.5, ya - p * 0.30)], "#9A9EA4", p * 0.09)
        cy = ya - p * 0.52
        self.add(f'<path d="M{cx - r},{cy + r * 0.35} a{r},{r} 0 0 1 {2 * r},0 '
                 f'l0,{r * 0.5} l{-2 * r},0 z" fill="{colour}" '
                 f'stroke="#00000035" stroke-width="1.1"/>')
        self.txt(xa, ya + p * 0.62, "long", 8.5, MUTED, anchor="middle")
        self.badge(n, xk + p * 0.60, ya)

    def piezo(self, n: int, row: str, cp: int, cm: int) -> None:
        p = self.p
        (xp, yp), (xm, _) = self.leg(row, cp), self.leg(row, cm)
        cx, cy, r = (xp + xm) / 2, self.hy(row) - p * 0.55, p * 0.60
        self.wire([(xp, yp), (cx - r * 0.4, cy)], "#9A9EA4", p * 0.09)
        self.wire([(xm, yp), (cx + r * 0.4, cy)], "#9A9EA4", p * 0.09)
        self.circ(cx, cy, r, "#C9A227", "#9A7B15", 1.4)
        self.circ(cx, cy, r * 0.45, "#EEE3AC")
        self.txt(xp, yp + p * 0.62, "+", 10, MUTED, anchor="middle", weight="700")
        self.badge(n, cx, cy - r - 9)

    def button(self, n: int, col: int, colour: str) -> None:
        """Straddles the channel: legs in E/F at col and col+2."""
        p = self.p
        x, y = self.hx(col), (self.hy("E") + self.hy("F")) / 2
        w = 2 * p
        self.rect(x - p * 0.35, y - p * 1.0, w + p * 0.7, p * 2.0,
                  "#3A4149", "#252A30", rx=4, sw=1.2)
        self.circ(x + w / 2, y, p * 0.45, colour, "#00000040", 1.2)
        for r in ("E", "F"):
            for c in (col, col + 2):
                self.leg(r, c, "#C8CDD3")
        self.badge(n, x + w / 2, y - p * 1.0 - 10)

    def pot(self, n: int, col: int) -> None:
        p = self.p
        x, y = self.hx(col), self.hy("E")
        self.rect(x - p * 0.4, y - p * 1.55, p * 2.8, p * 1.35,
                  "#2E5FA3", "#1F4478", rx=4, sw=1.2)
        self.circ(x + p, y - p * 0.88, p * 0.44, "#DEE2E6")
        self.wire([(x + p, y - p * 0.88), (x + p * 1.3, y - p * 1.2)],
                  "#4A5058", p * 0.10)
        for c in (col, col + 1, col + 2):
            self.leg("E", c, "#C8CDD3")
        self.txt(x + p, y + p * 0.62, "wiper = middle", 8.5, MUTED, anchor="middle")
        self.badge(n, x + p, y - p * 1.55 - 10)

    def sr04(self, n: int, col: int) -> None:
        p = self.p
        x, y = self.hx(col), self.hy("E")
        self.rect(x - p * 0.45, y - p * 2.0, p * 3.9, p * 1.75,
                  "#1E4C7A", "#143557", rx=4, sw=1.2)
        for dx in (1.0, 2.5):
            self.circ(x + p * dx, y - p * 1.15, p * 0.52, "#5A6672", "#39424C", 1.2)
            self.circ(x + p * dx, y - p * 1.15, p * 0.30, "#333B44")
        for c in range(col, col + 4):
            self.leg("E", c, "#C8CDD3")
        for i, lbl in enumerate(("V", "T", "E", "G")):
            self.txt(x + p * i, y + p * 0.62, lbl, 9, MUTED, anchor="middle",
                     weight="700")
        self.badge(n, x + p * 1.7, y - p * 2.0 - 10)

    def jump(self, n: int | None, a: tuple[str, int], b: tuple[str, int],
             colour: str) -> None:
        """Jumper wire between two holes, routed clear of the parts."""
        (ra, ca), (rb, cb) = a, b
        xa, ya = self.leg(ra, ca, colour)
        xb, yb = self.leg(rb, cb, colour)
        if ca == cb:
            pts = [(xa, ya), (xb, yb)]
        else:
            mid = ya + (yb - ya) * 0.5
            pts = [(xa, ya), (xa, mid), (xb, mid), (xb, yb)]
        self.wire(pts, colour)
        if n is not None:
            # toward the destination: that corridor is kept clear of parts
            self.badge(n, xa + self.p * 0.5, ya + (yb - ya) * 0.30)

    def inward(self, row: str) -> int:
        """+1 to move toward the channel, -1 to move toward the near rail."""
        return 1 if row in ("J", "I", "H", "G", "+t", "-t") else -1

    def feed(self, n: int, label: str, to: tuple[str, int], colour: str) -> None:
        """A wire arriving from the ESP32, drawn as a labelled tab on the left.

        Each feed enters on its own row, so the wire is a single straight line
        and no two feeds share a segment. That is legitimate rather than a
        drawing trick: every hole in a column on one side of the channel is the
        same node, so an unused row in the target column is the same connection
        as the row the component sits in.
        """
        row, col = to
        x, y = self.leg(row, col, colour)
        tw, tx = 100, 6
        self.rect(tx, y - 13, tw, 26, "#1B3A42", "none", rx=6)
        self.rect(tx, y - 13, 4, 26, colour, rx=2)
        self.txt(tx + 13, y + 4, label, 10.5, "#DCEEF0", weight="700")
        self.wire([(tx + tw, y), (x, y)], colour)
        self.badge(n, tx + tw + 16, y)

    def out(self, title: str) -> str:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'viewBox="0 0 {self.w} {self.h}" width="100%" role="img" '
                f'aria-label="{esc(title)}"><rect width="{self.w}" '
                f'height="{self.h}" fill="{PAPER}"/>' + "".join(self.o) + "</svg>")


# ------------------------------------------------------------------ the steps

def rails(b: Board) -> list[tuple[int, str, str]]:
    b.feed(1, "3V3", ("+t", 22), RED)
    b.feed(2, "GND", ("-t", 23), BLACK)
    b.jump(3, ("+t", LINK_P), ("+b", LINK_P), RED)
    b.jump(4, ("-t", LINK_N), ("-b", LINK_N), BLACK)
    return [(1, "3V3 wire", "ESP32 3V3 &rarr; top + rail, hole 22"),
            (2, "GND wire", "ESP32 GND &rarr; top &minus; rail, hole 23"),
            (3, "rail link", f"top + rail {LINK_P} &rarr; bottom + rail {LINK_P}"),
            (4, "rail link",
             f"top &minus; rail {LINK_N} &rarr; bottom &minus; rail {LINK_N}")]


def leds(b: Board, p: dict[str, str]) -> list[tuple[int, str, str]]:
    spec = [("LED_PERMIT", "#2ECC71", "green", OK),
            ("LED_REFUSE", "#E74C3C", "red", CRIT),
            ("LED_ESCALATE", "#F1C40F", "amber", WARN)]
    leg, n = [], 1
    for slot, (key, colour, name, accent) in enumerate(spec):
        c = LED_BASE[key]
        b.feed(n, pin_name(p[key]), (LED_FEED_ROW[slot], c), accent)
        leg.append((n, "jumper",
                    f"{pin_name(p[key])} &rarr; "
                    f"<b>{LED_FEED_ROW[slot]}{c}</b> (same column as the resistor)"))
        n += 1
        b.resistor(n, "J", c, c + 2, "220")
        leg.append((n, f"220 {OHM}", f"<b>J{c}</b> to <b>J{c + 2}</b>"))
        n += 1
        b.led(n, "G", c + 2, c + 4, colour)
        leg.append((n, f"{name} LED",
                    f"long leg <b>G{c + 2}</b>, short leg <b>G{c + 4}</b>"))
        n += 1
        b.jump(n, ("J", c + 4), ("-t", c + 4), BLACK)
        leg.append((n, "jumper", f"<b>J{c + 4}</b> &rarr; top &minus; rail"))
        n += 1
    return leg


def emitter(b: Board, p: dict[str, str]) -> list[tuple[int, str, str]]:
    c = PIEZO_BASE
    b.feed(1, pin_name(p["PIN_EMIT"]), ("I", c), ACCENT)
    b.resistor(2, "J", c, c + 2, "220")
    b.piezo(3, "G", c + 2, c + 4)
    b.jump(4, ("J", c + 4), ("-t", c + 4), BLACK)
    return [(1, "jumper", f'{pin_name(p["PIN_EMIT"])} &rarr; <b>I{c}</b>'),
            (2, f"220 {OHM}", f"<b>J{c}</b> to <b>J{c + 2}</b>"),
            (3, "piezo", f"<b>+</b> leg <b>G{c + 2}</b>, other leg <b>G{c + 4}</b>"),
            (4, "jumper", f"<b>J{c + 4}</b> &rarr; top &minus; rail")]


def buttons(b: Board, p: dict[str, str]) -> list[tuple[int, str, str]]:
    spec = [("BTN_PERSON", "#2E86C1", "PERSON", ACCENT),
            ("BTN_NONTARGET", "#F1C40F", "DOG / GOAT", ACCENT),
            ("BTN_ESTOP", "#E74C3C", "E-STOP", CRIT)]
    leg, n = [], 1
    for slot, (key, colour, name, accent) in enumerate(spec):
        c = BTN_COL[key]
        b.button(n, c, colour)
        leg.append((n, name + " button",
                    f"legs in <b>E{c}</b>, <b>E{c + 2}</b>, <b>F{c}</b>, "
                    f"<b>F{c + 2}</b> &mdash; it straddles the channel"))
        n += 1
        b.feed(n, pin_name(p[key]), (BTN_FEED_ROW[slot], c), accent)
        leg.append((n, "jumper",
                    f"{pin_name(p[key])} &rarr; <b>{BTN_FEED_ROW[slot]}{c}</b>"))
        n += 1
        b.jump(n, ("J", c + 2), ("-t", c + 2), BLACK)
        leg.append((n, "jumper",
                    f"<b>J{c + 2}</b> &rarr; top &minus; rail "
                    f"(diagonally opposite leg)"))
        n += 1
    return leg


def pullup(b: Board, p: dict[str, str]) -> list[tuple[int, str, str]]:
    c = BTN_COL["BTN_ESTOP"]
    b.button(1, c, "#E74C3C")
    b.feed(2, pin_name(p["BTN_ESTOP"]), ("A", c), CRIT)
    b.jump(3, ("J", c + 2), ("-t", c + 2), BLACK)
    b.resistor(4, "B", c, c - 4, "10k")
    b.jump(5, ("B", c - 4), ("+b", c - 4), RED)
    return [(1, "E-STOP button", f"already placed in step 4, columns {c}/{c + 2}"),
            (2, "jumper", f'{pin_name(p["BTN_ESTOP"])} &rarr; <b>A{c}</b>'),
            (3, "jumper", f"<b>J{c + 2}</b> &rarr; top &minus; rail"),
            (4, f"10k {OHM}",
             f"<b>B{c}</b> to <b>B{c - 4}</b> &mdash; note <b>B{c}</b> is the "
             f"same column as the pin leg, so it lands on the same node"),
            (5, "jumper", f"<b>B{c - 4}</b> &rarr; bottom + rail")]


def potentiometer(b: Board, p: dict[str, str]) -> list[tuple[int, str, str]]:
    c = POT_COL
    b.pot(1, c)
    b.jump(2, ("A", c), ("+b", c), RED)
    b.feed(3, pin_name(p["POT_GROUP"]), ("C", c + 1), WARN)
    b.jump(4, ("A", c + 2), ("-b", c + 2), BLACK)
    return [(1, "potentiometer",
             f"legs in <b>E{c}</b>, <b>E{c + 1}</b>, <b>E{c + 2}</b>"),
            (2, "jumper", f"<b>A{c}</b> &rarr; bottom + rail"),
            (3, "jumper", f'<b>C{c + 1}</b> (wiper column) &rarr; {pin_name(p["POT_GROUP"])}'),
            (4, "jumper", f"<b>A{c + 2}</b> &rarr; bottom &minus; rail")]


def sensor(b: Board, p: dict[str, str]) -> list[tuple[int, str, str]]:
    c, d = SR04_COL, DIV_COL
    b.sr04(1, c)
    b.feed(2, "VIN / 5V", ("A", c), RED)
    b.feed(3, pin_name(p["PIN_TRIG"]), ("B", c + 1), OK)
    b.jump(4, ("A", c + 3), ("-b", c + 3), BLACK)
    b.resistor(5, "B", c + 2, d, "1k")
    b.resistor(6, "D", d, d + 4, "2k")
    b.jump(7, ("D", d + 4), ("-b", d + 4), BLACK)
    b.feed(8, pin_name(p["PIN_ECHO"]), ("C", d), ACCENT)
    return [(1, "HC-SR04",
             f"pins in <b>E{c}</b>&ndash;<b>E{c + 3}</b>: VCC, TRIG, ECHO, GND"),
            (2, "jumper", f"VIN / 5V &rarr; <b>A{c}</b> (VCC)"),
            (3, "jumper", f'{pin_name(p["PIN_TRIG"])} &rarr; <b>B{c + 1}</b> (TRIG column)'),
            (4, "jumper", f"<b>A{c + 3}</b> (GND) &rarr; bottom &minus; rail"),
            (5, f"1k {OHM}", f"<b>B{c + 2}</b> (ECHO column) to <b>B{d}</b>"),
            (6, f"2k {OHM}", f"<b>D{d}</b> to <b>D{d + 4}</b>"),
            (7, "jumper", f"<b>D{d + 4}</b> &rarr; bottom &minus; rail"),
            (8, "jumper",
             f'<b>C{d}</b> &rarr; {pin_name(p["PIN_ECHO"])} &mdash; column {d} is '
             f"the junction between the two resistors")]


def everything(b: Board, p: dict[str, str]) -> list[tuple[int, str, str]]:
    """The finished board, no badges: this is what it should look like."""
    for key, colour in (("LED_PERMIT", "#2ECC71"), ("LED_REFUSE", "#E74C3C"),
                        ("LED_ESCALATE", "#F1C40F")):
        c = LED_BASE[key]
        b.resistor(0, "J", c, c + 2, "220")
        b.led(0, "G", c + 2, c + 4, colour)
        b.jump(None, ("J", c + 4), ("-t", c + 4), BLACK)
    c = PIEZO_BASE
    b.resistor(0, "J", c, c + 2, "220")
    b.piezo(0, "G", c + 2, c + 4)
    b.jump(None, ("J", c + 4), ("-t", c + 4), BLACK)
    for key, colour in (("BTN_PERSON", "#2E86C1"), ("BTN_NONTARGET", "#F1C40F"),
                        ("BTN_ESTOP", "#E74C3C")):
        cb = BTN_COL[key]
        b.button(0, cb, colour)
        b.jump(None, ("J", cb + 2), ("-t", cb + 2), BLACK)
    ce = BTN_COL["BTN_ESTOP"]
    b.resistor(0, "B", ce, ce - 4, "10k")
    b.jump(None, ("B", ce - 4), ("+b", ce - 4), RED)
    b.pot(0, POT_COL)
    b.jump(None, ("A", POT_COL), ("+b", POT_COL), RED)
    b.jump(None, ("A", POT_COL + 2), ("-b", POT_COL + 2), BLACK)
    b.sr04(0, SR04_COL)
    b.jump(None, ("A", SR04_COL + 3), ("-b", SR04_COL + 3), BLACK)
    b.resistor(0, "B", SR04_COL + 2, DIV_COL, "1k")
    b.resistor(0, "D", DIV_COL, DIV_COL + 4, "2k")
    b.jump(None, ("D", DIV_COL + 4), ("-b", DIV_COL + 4), BLACK)
    b.jump(None, ("+t", LINK_P), ("+b", LINK_P), RED)
    b.jump(None, ("-t", LINK_N), ("-b", LINK_N), BLACK)
    return []


# ------------------------------------------------------------------ page

STEPS = [
    (1, "Power the rails", ACCENT, (21, 63),
     ["Two wires out of the ESP32, then two links so the bottom rails are live too."],
     "Some breadboards <b>split the power rails in the middle</b> &mdash; look for a "
     "break in the red and blue lines around column 30. If yours is split, bridge "
     "the halves as well, or the right-hand end of the board is dead."),

    (2, "Three status LEDs", OK, (21, 45),
     ["Each LED is the same four moves: jumper in, resistor, LED, jumper to ground.",
      "The <b>long leg</b> is the anode and goes in the hole nearer the resistor."],
     "All five holes in a column are one node. That is why the resistor can end at "
     "<b>J26</b> and the LED can start at <b>G26</b> and still be in series."),

    (3, "The emitter", ACCENT, (38, 50),
     ["Same shape as an LED chain: pin, 220&nbsp;" + OHM + ", part, ground."],
     "A piezo is a capacitive load and pulls a current spike at switch-on. The "
     "series resistor is what stops that landing on the pin."),

    (4, "The three veto buttons", CRIT, (46, 63),
     ["The button sits <b>across the centre channel</b> &mdash; that is what keeps "
      "its two contacts apart.",
      "Pin goes to one column in the bottom half; ground leaves from the "
      "<b>diagonally opposite</b> column in the top half."],
     "Diagonal is the rule worth remembering. Wire two legs on the same side of the "
     "switch and you have a permanent short to ground, which reads as a button "
     "nobody can un-press."),

    (5, "Pull up the E-stop", CRIT, (52, 63),
     ["The 10k goes from the button's <b>pin column</b> to the + rail.",
      "It sits <b>beside</b> the button on the same node, not in line with it."],
     "GPIO34&ndash;39 are input-only and have <b>no internal pull-up in the "
     "silicon</b>. Without this resistor the pin floats and the E-stop latches at "
     "random, usually mid-demo, and it looks exactly like a software bug."),

    (6, "Group-size potentiometer", WARN, (21, 34),
     ["Three legs in three consecutive holes, bottom half.",
      "Outer legs to the two rails, middle leg to the ADC pin."],
     "The pot goes to <b>3V3, never 5V</b>. ESP32 ADC pins are not 5&nbsp;V tolerant."),

    (7, "HC-SR04 and its divider", CRIT, (26, 46),
     ["The sensor's four pins go in four consecutive holes: VCC, TRIG, ECHO, GND.",
      "ECHO does not reach a GPIO directly. It goes through 1k to a junction "
      "column, and from that column through 2k to ground.",
      "The ESP32 reads the <b>junction column</b>."],
     "ECHO swings to 5&nbsp;V and ESP32 GPIOs are NOT 5&nbsp;V tolerant. Most "
     "tutorials wire it straight to a pin; that is how people quietly cook an "
     "ESP32. The divider brings it to about 3.3&nbsp;V."),

    (8, "The finished board", OK, (21, 63),
     ["Everything in place. Compare yours hole by hole before you plug in USB."],
     "If the E-stop latches on its own, step 5 is missing or on the wrong column. "
     "If nothing lights at all, check the sensor &mdash; without it the sketch "
     "idles forever waiting for a reading."),
]


def render(n: int, p: dict[str, str]) -> tuple[str, list[tuple[int, str, str]]]:
    c0, c1 = next(s[3] for s in STEPS if s[0] == n)
    b = Board(c0, c1)
    b.show_badges = n != 8
    b.frame()
    fn = {1: rails, 2: leds, 3: emitter, 4: buttons, 5: pullup,
          6: potentiometer, 7: sensor, 8: everything}[n]
    legend = fn(b) if n == 1 else fn(b, p)  # rails needs no pin map
    used: set[int] = set()
    for _n, _what, where in legend:
        for m in re.finditer(r"[A-J](\d\d)\b", where):
            used.add(int(m.group(1)))
    b.col_marks({c for c in used if c0 <= c <= c1})
    return b.out(f"Step {n}"), legend


PAGE = """<title>GauKavach - breadboard build</title>
<style>
:root{{--ground:#EDF0F3;--surface:#FFFFFF;--ink:#0F141A;--body:#28323C;--muted:#5D6B79;
--faint:#8695A3;--line:#D2DAE1;--accent:#0E7C86;--ok:#1C7A4B;--ok-bg:#E2F1E8;
--warn:#93670A;--warn-bg:#F8EFD8;--crit:#A9291F;--crit-bg:#F8E4E2;--surface-2:#F5F8FA;}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--ground:#0C1116;
--surface:#131A21;--ink:#E9EEF3;--body:#C3CFD9;--muted:#8FA0AE;--faint:#6B7C8A;
--line:#212C36;--accent:#40B9C2;--ok:#5FBF8A;--ok-bg:#12291E;--warn:#D9A63C;
--warn-bg:#2C2314;--crit:#E0776C;--crit-bg:#2E1815;--surface-2:#182028;}}}}
:root[data-theme="dark"]{{--ground:#0C1116;--surface:#131A21;--ink:#E9EEF3;
--body:#C3CFD9;--muted:#8FA0AE;--faint:#6B7C8A;--line:#212C36;--accent:#40B9C2;
--ok:#5FBF8A;--ok-bg:#12291E;--warn:#D9A63C;--warn-bg:#2C2314;--crit:#E0776C;
--crit-bg:#2E1815;--surface-2:#182028;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);color:var(--body);
font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;font-size:15.5px;line-height:1.62}}
h1,h2{{font-family:Charter,"Bitstream Charter",Georgia,serif;color:var(--ink);margin:0;text-wrap:balance}}
.wrap{{max-width:1080px;margin:0 auto;padding:0 24px 80px}}
header{{background:var(--surface);border-bottom:1px solid var(--line);padding:30px 0 26px;margin-bottom:26px}}
.eyebrow{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px;letter-spacing:.14em;
text-transform:uppercase;color:var(--accent)}}
h1{{font-size:32px;letter-spacing:-.015em;margin-top:6px}}
.lede{{max-width:72ch;margin-top:12px;color:var(--muted)}}
.rail{{display:flex;gap:6px;margin:22px 0 0;flex-wrap:wrap}}
.rail a{{flex:1 1 0;min-width:64px;text-decoration:none;border:1px solid var(--line);
background:var(--surface);padding:8px 4px;text-align:center;
font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px;color:var(--muted)}}
.rail a b{{display:block;font-size:16px;color:var(--ink);margin-bottom:2px}}
.rail a:hover{{border-color:var(--accent);color:var(--accent)}}
.step{{background:var(--surface);border:1px solid var(--line);margin-top:30px;
overflow:hidden;scroll-margin-top:14px}}
.shead{{display:flex;gap:18px;align-items:center;padding:18px 24px;border-bottom:1px solid var(--line)}}
.num{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:19px;font-weight:700;color:#fff;
background:var(--accent);width:44px;height:44px;display:grid;place-items:center;flex:none;border-radius:50%}}
.num.crit{{background:var(--crit)}} .num.ok{{background:var(--ok)}} .num.warn{{background:var(--warn)}}
h2{{font-size:23px}}
.body{{padding:20px 24px 24px}}
ul{{margin:0;padding-left:22px;max-width:82ch}} ul li{{margin-bottom:8px}}
ul li::marker{{color:var(--accent)}}
.pic{{margin-top:18px;border:1px solid var(--line);background:#fff;overflow-x:auto}}
.pic svg{{display:block;min-width:760px}}
.note{{margin-top:16px;padding:14px 17px;border-left:3px solid var(--warn);
background:var(--warn-bg);font-size:14px;max-width:90ch}}
.note.crit{{border-left-color:var(--crit);background:var(--crit-bg)}}
.note b{{color:var(--ink)}}
.callout{{border:1px solid var(--line);border-left:3px solid var(--accent);
background:var(--surface);padding:16px 20px;margin-top:22px}}
.callout .lbl{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10.5px;
letter-spacing:.1em;text-transform:uppercase;color:var(--accent);margin-bottom:7px}}
.callout p{{margin:0;max-width:80ch}} .callout p+p{{margin-top:10px}}
table{{border-collapse:collapse;width:100%;font-size:14px;margin-top:14px}}
th{{text-align:left;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10.5px;
letter-spacing:.07em;text-transform:uppercase;color:var(--faint);font-weight:400;
padding:10px 13px;border-bottom:1px solid var(--line);background:var(--surface-2)}}
td{{padding:9px 13px;border-bottom:1px solid var(--line);vertical-align:top}}
td.n{{font-family:ui-monospace,Menlo,Consolas,monospace;color:#fff;background:var(--ink);
width:1%;text-align:center;font-size:12px;padding:4px 0}}
td.n div{{width:22px;height:22px;border-radius:50%;background:var(--ink);color:#fff;
display:grid;place-items:center;margin:2px auto}}
td.w{{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--ink);
white-space:nowrap;width:1%}}
td b{{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--accent)}}
.scroll{{overflow-x:auto;border:1px solid var(--line);background:var(--surface);margin-top:14px}}
code{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.9em;
background:var(--surface-2);padding:1px 5px;border:1px solid var(--line)}}
@media print{{body{{background:#fff}} .step{{break-inside:avoid}} .rail{{display:none}}}}
</style>
<header><div class="wrap">
<div class="eyebrow">ESP32 bench governor</div>
<h1>Breadboard build &mdash; hole by hole</h1>
<p class="lede">Same circuit as the wiring guide, but placed on a real board. Every
component is drawn where it goes, and the numbered badges in each picture match the
table underneath, which names the exact hole. Columns used by the current step are
numbered in <span style="color:var(--accent);font-weight:700">teal</span> along the
top and bottom edge.</p>
<div class="rail">{rail}</div>
</div></header>
<div class="wrap">

<div class="callout">
<div class="lbl">Read this before you place anything</div>
<p><b>A column is a node.</b> All five holes in a column on the same side of the
centre channel are the same electrical point. Two component legs in the same column
are connected; the same column on the other side of the channel is a different node.</p>
<p><b>The ESP32 is not drawn pin by pin, on purpose.</b> 30-pin and 38-pin DevKits
order their headers differently, and vendors differ even within 38 pins. Find each
pin by its <b>silkscreen label</b>, then use any free hole in that pin's column on
that side of the board &mdash; it is the same node as the pin. Put the module over
the low columns (roughly 1&ndash;20) so columns {lo}+ stay free for parts.</p>
<p><b>Board size.</b> This layout assumes a full-size 63-column breadboard. On a
half-size 30-column board, put the ESP32 on one board and the parts on a second,
and carry the two rails across with a pair of jumpers.</p>
</div>

<h2 style="margin-top:34px">Parts</h2>
<div class="scroll"><table><thead><tr><th>Qty</th><th>Part</th><th>Where it lands</th>
</tr></thead><tbody>{parts}</tbody></table></div>

{steps}

<p style="color:var(--faint);font-size:13px;margin-top:30px">
Pin numbers are parsed from <code>hardware/wokwi_esp32/gaukavach_esp32.ino</code> at
build time, so this page cannot drift from the firmware. Regenerate with
<code>python tools/make_breadboard.py</code>.</p>
</div>
"""


def main() -> None:
    p = pins()

    parts = [
        ("1", "ESP32 DevKit", "columns 1&ndash;20, straddling the channel"),
        ("1", "HC-SR04", f"E{SR04_COL}&ndash;E{SR04_COL + 3}"),
        ("1", "Piezo buzzer", f"G{PIEZO_BASE + 2} and G{PIEZO_BASE + 4}"),
        ("3", "LED (green, red, amber)",
         "G26/G28, G32/G34, G38/G40"),
        ("4", f"Resistor 220 {OHM}", "J24, J30, J36, J42 &mdash; each spans 2 columns"),
        ("1", f"Resistor 1k {OHM}", f"B{SR04_COL + 2} to B{DIV_COL}"),
        ("1", f"Resistor 2k {OHM}", f"D{DIV_COL} to D{DIV_COL + 4}"),
        ("1", f"Resistor 10k {OHM}",
         f'B{BTN_COL["BTN_ESTOP"]} to B{BTN_COL["BTN_ESTOP"] - 4}'),
        ("3", "Tactile button", "columns 50/52, 55/57, 60/62, across the channel"),
        ("1", f"Potentiometer 10k {OHM}", f"E{POT_COL}&ndash;E{POT_COL + 2}"),
        ("~18", "Jumper wires", "see each step"),
    ]
    parts_html = "".join(
        f'<tr><td class="w">{q}</td><td>{n}</td>'
        f'<td style="color:var(--muted)">{w}</td></tr>' for q, n, w in parts)

    rail_html = "".join(
        f'<a href="#s{n}"><b>{n}</b>{esc(t.split(chr(32))[0])}</a>'
        for n, t, _c, _win, _i, _note in STEPS)

    cls = {ACCENT: "", CRIT: " crit", OK: " ok", WARN: " warn"}
    blocks = []
    for n, title, colour, _win, items, note in STEPS:
        svg, legend = render(n, p)
        li = "".join(f"<li>{i}</li>" for i in items)
        tbl = ""
        if legend:
            rows = "".join(
                f'<tr><td class="n"><div>{i}</div></td><td class="w">{what}</td>'
                f"<td>{where}</td></tr>" for i, what, where in legend)
            tbl = ('<div class="scroll"><table><thead><tr><th></th><th>Part</th>'
                   f"<th>Exact holes</th></tr></thead><tbody>{rows}</tbody>"
                   "</table></div>")
        ncls = "note crit" if colour == CRIT else "note"
        blocks.append(
            f'<div class="step" id="s{n}"><div class="shead">'
            f'<span class="num{cls[colour]}">{n}</span><h2>{esc(title)}</h2></div>'
            f'<div class="body"><ul>{li}</ul>'
            f'<div class="pic">{svg}</div>{tbl}'
            f'<div class="{ncls}">{note}</div></div></div>')

    page = PAGE.format(rail=rail_html, parts=parts_html,
                       steps="".join(blocks), lo=COL_LO)
    page = "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in page)
    out = ROOT / "hardware" / "breadboard.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote hardware/breadboard.html ({out.stat().st_size / 1024:.0f} KB), "
          f"{len(STEPS)} steps")


if __name__ == "__main__":
    main()
