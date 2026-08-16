"""
Generate the wiring diagrams as SVG, plus a printable HTML build sheet.

    python tools/make_wiring_diagram.py

Pin numbers are PARSED OUT OF THE SKETCHES rather than typed here, so the
diagram cannot drift from the firmware. If someone moves the E-stop to another
pin, the picture moves with it or the build fails loudly.

Deliberately a connection diagram, not a photorealistic breadboard render. When
you are actually wiring something, "which pin goes where, in what colour" is
the useful information; a picture of jumper wires curving over a breadboard is
harder to read, not easier.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNO = ROOT / "hardware" / "tinkercad_uno" / "gaukavach_uno.ino"
ESP = ROOT / "hardware" / "wokwi_esp32" / "gaukavach_esp32.ino"

# palette, matching the rest of the project
INK = "#0F141A"
BODY = "#28323C"
MUTED = "#5D6B79"
FAINT = "#8695A3"
LINE = "#D2DAE1"
PAPER = "#FFFFFF"
SURF = "#F5F8FA"
ACCENT = "#0E7C86"
OK = "#1C7A4B"
WARN = "#B0850F"
CRIT = "#A9291F"
BOARD = "#16333A"

W_RED, W_BLK = "#C0392B", "#2C3238"


def limits(path: Path) -> dict[str, int]:
    """The governor limits the firmware enforces, read from the sketch."""
    src = path.read_text(encoding="utf-8")
    out: dict[str, int] = {}
    for name in ("MAX_GROUP", "MAX_ACTIVATION_MS", "MIN_SILENCE_MS",
                 "DAILY_BUDGET_MS", "MAX_ATTEMPTS", "CARRIER_HZ", "DEMO_SPEED"):
        m = re.search(rf"{name}\s*=\s*(\d+)", src)
        if m:
            out[name] = int(m.group(1))
    return out


def pins(path: Path) -> dict[str, str]:
    src = path.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for name in ("PIN_TRIG", "PIN_ECHO", "PIN_EMIT", "LED_PERMIT", "LED_REFUSE",
                 "LED_ESCALATE", "LED_ARMED", "BTN_PERSON", "BTN_NONTARGET",
                 "BTN_ESTOP", "POT_GROUP"):
        m = re.search(rf"\b{name}\s*=\s*(A?\d+)", src)
        if not m:
            raise SystemExit(f"{name} not found in {path.name}")
        out[name] = m.group(1)
    return out


@dataclass
class Comp:
    """A component block: title, subtitle, and the stubs facing the board."""

    key: str
    title: str
    sub: str
    stubs: list[tuple[str, str, str]]  # (stub label, wire colour, net note)
    side: str                          # "L" or "R"
    accent: str = MUTED
    h: int = 0
    y: int = 0
    x: int = 0
    stub_y: dict = field(default_factory=dict)


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


class SVG:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.o: list[str] = []

    def add(self, s: str) -> None:
        self.o.append(s)

    def rect(self, x, y, w, h, fill, stroke="none", rx=4, sw=1.2, op=1.0):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"/>')

    def text(self, x, y, s, size=12, fill=BODY, anchor="start", weight="400",
             family="ui-monospace, 'DejaVu Sans Mono', Menlo, Consolas, monospace"):
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
                 f'text-anchor="{anchor}" font-weight="{weight}" '
                 f'font-family="{family}">{esc(s)}</text>')

    def wire(self, pts, color, width=2.6, dash=""):
        d = " ".join(("M" if i == 0 else "L") + f"{x},{y}" for i, (x, y) in enumerate(pts))
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
                 f'stroke-linecap="round" stroke-linejoin="round"{da}/>')

    def dot(self, x, y, color, r=4.0):
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')

    def render(self, title: str) -> str:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                f'width="100%" role="img" aria-label="{esc(title)}">'
                f'<rect width="{self.w}" height="{self.h}" fill="{PAPER}"/>'
                + "".join(self.o) + "</svg>")


def build(board: str, p: dict[str, str], lim: dict[str, int]) -> str:
    esp = board == "ESP32"
    W, H = 1180, 900
    s = SVG(W, H)

    # ---- title ----
    s.text(34, 40, "GAUKAVACH", 13, ACCENT, weight="700")
    s.text(34, 66, f"Bench governor - {board} wiring", 22, INK, weight="600",
           family="Charter, Georgia, 'DejaVu Serif', serif")
    s.text(34, 88, "Pin numbers parsed from the sketch. Buttons use internal pull-ups: pressed = LOW.",
           12, MUTED)
    s.add(f'<line x1="34" y1="102" x2="{W-34}" y2="102" stroke="{LINE}" stroke-width="1.4"/>')

    # ---- component definitions ----
    left = [
        Comp("sr04", "HC-SR04", "stands in for the camera",
             [("VCC", W_RED, "5V" if not esp else "5V"),
              ("TRIG", "#2E86C1", p["PIN_TRIG"]),
              ("ECHO", "#8E44AD", p["PIN_ECHO"]),
              ("GND", W_BLK, "GND")], "L", ACCENT),
        Comp("bp", "Button  PERSON", "person in the exposure cone",
             [("SIG", "#2E86C1", p["BTN_PERSON"]), ("GND", W_BLK, "GND")], "L", CRIT),
        Comp("bn", "Button  DOG / GOAT", "non-target species in the cone",
             [("SIG", "#B7950B", p["BTN_NONTARGET"]), ("GND", W_BLK, "GND")], "L", CRIT),
        # On ESP32 the pull-up is drawn, not just mentioned: GPIO35 has none
        # internally, and a floating E-stop latches at random.
        Comp("be", "Button  E-STOP",
             "latching; 10k pull-up REQUIRED" if esp else "latching; only a reset clears it",
             ([("SIG", CRIT, p["BTN_ESTOP"]), ("10k", W_RED, "3V3"), ("GND", W_BLK, "GND")]
              if esp else
              [("SIG", CRIT, p["BTN_ESTOP"]), ("GND", W_BLK, "GND")]), "L", CRIT),
        Comp("pot", "Potentiometer 10k", "group size, 1 to 8 animals",
             [("VCC", W_RED, "3V3" if esp else "5V"),
              ("WIPER", "#7D3C98", p["POT_GROUP"]),
              ("GND", W_BLK, "GND")], "L", WARN),
    ]
    right = [
        Comp("emit", "Piezo / transducer", "220R in series - the emitter",
             [("+", "#6C3483", p["PIN_EMIT"]), ("-", W_BLK, "GND")], "R", ACCENT),
        Comp("lg", "LED  PERMIT", "green, 220R",
             [("A", OK, p["LED_PERMIT"]), ("K", W_BLK, "GND")], "R", OK),
        Comp("lr", "LED  REFUSE", "red, 220R",
             [("A", CRIT, p["LED_REFUSE"]), ("K", W_BLK, "GND")], "R", CRIT),
        Comp("la", "LED  ESCALATE", "amber, 220R",
             [("A", WARN, p["LED_ESCALATE"]), ("K", W_BLK, "GND")], "R", WARN),
        Comp("lb", "LED  ARMED", "blue heartbeat, 220R",
             [("A", "#2E86C1", p["LED_ARMED"]), ("K", W_BLK, "GND")], "R", "#2E86C1"),
    ]

    # ---- layout ----
    TOP, GAP = 130, 18
    CW_L, CW_R = 210, 210
    XL, XR = 34, W - 34 - CW_R
    for col, x in ((left, XL), (right, XR)):
        y = TOP
        for c in col:
            c.h = 34 + len(c.stubs) * 21
            c.y, c.x = y, x
            y += c.h + GAP

    BX, BW = 430, 320
    BY, BH = TOP, max(left[-1].y + left[-1].h, right[-1].y + right[-1].h) - TOP
    s.rect(BX, BY, BW, BH, BOARD, rx=10)
    s.text(BX + BW / 2, BY + 30, board, 20, "#FFFFFF", anchor="middle", weight="700")
    s.text(BX + BW / 2, BY + 50, "Uno R3 - Tinkercad" if not esp else "DevKit - Wokwi / real",
           11, "#8FC6CB", anchor="middle")

    # The middle of the board is otherwise dead space, and what the firmware
    # enforces is the single most useful thing to have visible while wiring.
    ey = BY + BH - 132
    s.add(f'<line x1="{BX+16}" y1="{ey-16}" x2="{BX+BW-16}" y2="{ey-16}" '
          f'stroke="#2A4A52" stroke-width="1"/>')
    s.text(BX + 16, ey, "ENFORCES, INDEPENDENTLY OF THE HOST", 9.5, "#8FC6CB", weight="700")
    rows_ = [
        f"carrier          {lim.get('CARRIER_HZ', 25000)/1000:.0f} kHz",
        f"max activation   {lim.get('MAX_ACTIVATION_MS', 6000)/1000:.0f} s",
        f"quiet period     {lim.get('MIN_SILENCE_MS', 20000)/1000:.0f} s",
        f"daily budget     {lim.get('DAILY_BUDGET_MS', 120000)/1000:.0f} s",
        f"max group        {lim.get('MAX_GROUP', 3)}",
        f"attempts         {lim.get('MAX_ATTEMPTS', 3)}, then escalate",
    ]
    for i, r in enumerate(rows_):
        s.text(BX + 16, ey + 18 + i * 15, r, 10.5, "#D6E4E7")
    s.text(BX + 16, ey + 18 + len(rows_) * 15 + 4,
           f"demo timers /{lim.get('DEMO_SPEED', 10)}", 9.5, "#7FA8AE")

    # power rails on the board
    rail_y = BY + 78
    s.text(BX + 16, rail_y, "5V" if not esp else "5V / 3V3", 12, "#F0B27A", weight="700")
    s.text(BX + BW - 16, rail_y, "GND", 12, "#AEB6BD", anchor="end", weight="700")

    # ---- draw components and collect stub anchors ----
    for c in left + right:
        s.rect(c.x, c.y, CW_L if c.side == "L" else CW_R, c.h, SURF, LINE, rx=6)
        s.rect(c.x, c.y, 4, c.h, c.accent, rx=2)
        s.text(c.x + 14, c.y + 20, c.title, 12.5, INK, weight="700")
        s.text(c.x + 14, c.y + 34, c.sub, 10, MUTED,
               family="system-ui, -apple-system, 'DejaVu Sans', sans-serif")
        for i, (lbl, col, net) in enumerate(c.stubs):
            sy = c.y + 50 + i * 21
            c.stub_y[lbl] = sy
            if c.side == "L":
                sx = c.x + CW_L
                s.text(c.x + 14, sy + 4, lbl, 10.5, BODY)
                s.text(sx - 12, sy + 4, net, 10.5, col, anchor="end", weight="700")
            else:
                sx = c.x
                s.text(c.x + CW_R - 14, sy + 4, lbl, 10.5, BODY, anchor="end")
                s.text(sx + 12, sy + 4, net, 10.5, col, weight="700")
            s.dot(sx, sy, col, 3.6)

    # ---- route wires through channels so nothing overlaps ----
    def route(c: Comp, lbl: str, col: str, board_y: float, ch: int) -> None:
        sy = c.stub_y[lbl]
        if c.side == "L":
            x0, x1 = c.x + CW_L, BX
            gx = x0 + 18 + ch * 11
        else:
            x0, x1 = c.x, BX + BW
            gx = x0 - 18 - ch * 11
        s.wire([(x0, sy), (gx, sy), (gx, board_y), (x1, board_y)], col)
        s.dot(x1, board_y, col, 4.2)

    used_y: dict[str, float] = {}
    ly = BY + 100
    ry = BY + 100
    ch_l = ch_r = 0
    for c in left:
        for lbl, col, net in c.stubs:
            key = f"L:{net}"
            if net in ("GND", "5V", "3V3") and key in used_y:
                by = used_y[key]
            else:
                by = ly
                ly += 20
                used_y[key] = by
                s.text(BX + 14, by + 4, net, 11, "#E8EDF2", weight="700")
            route(c, lbl, col, by, ch_l)
            ch_l += 1
    for c in right:
        for lbl, col, net in c.stubs:
            key = f"R:{net}"
            if net in ("GND", "5V", "3V3") and key in used_y:
                by = used_y[key]
            else:
                by = ry
                ry += 20
                used_y[key] = by
                s.text(BX + BW - 14, by + 4, net, 11, "#E8EDF2", anchor="end", weight="700")
            route(c, lbl, col, by, ch_r)
            ch_r += 1

    # ---- footnotes ----
    fy = BY + BH + 34
    notes = [
        ("220R on every LED and on the emitter line.", MUTED),
        ("Buttons: one leg to the pin, the other to GND. INPUT_PULLUP, so pressed = LOW.", MUTED),
    ]
    if esp:
        notes.append(("GPIO35 has NO internal pull-up: add 10k from pin 35 to 3V3 "
                      "or the E-stop floats and fires at random.", CRIT))
        notes.append(("Pot goes to 3V3, not 5V - ADC pins are not 5V tolerant.", CRIT))
    else:
        notes.append(("tone() is a hard-gated square wave. That is the waveform our own "
                      "spectrum analysis says not to radiate - the ESP32 sketch ramps it.", WARN))
    notes.append(("No calibrated ultrasonic microphone is attached, so this rig makes no dB claim.", CRIT))
    for i, (t, col) in enumerate(notes):
        s.text(34, fy + i * 17, ("!  " if col in (CRIT, WARN) else "-  ") + t, 11, col,
               family="system-ui, -apple-system, 'DejaVu Sans', sans-serif")

    s.h = int(fy + len(notes) * 17 + 18)   # trim to content, no dead space
    return s.render(f"{board} wiring diagram")


PAGE = """<title>GauKavach - Wiring Diagrams</title>
<style>
:root{{--ground:#EDF0F3;--surface:#FFFFFF;--ink:#0F141A;--body:#28323C;--muted:#5D6B79;
--faint:#8695A3;--line:#D2DAE1;--accent:#0E7C86;--accent-soft:#DBEDEF;--ok:#1C7A4B;
--ok-bg:#E2F1E8;--warn:#93670A;--warn-bg:#F8EFD8;--crit:#A9291F;--crit-bg:#F8E4E2;--surface-2:#F5F8FA;}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--ground:#0C1116;--surface:#131A21;
--ink:#E9EEF3;--body:#C3CFD9;--muted:#8FA0AE;--faint:#6B7C8A;--line:#212C36;--accent:#40B9C2;
--accent-soft:#10333A;--ok:#5FBF8A;--ok-bg:#12291E;--warn:#D9A63C;--warn-bg:#2C2314;
--crit:#E0776C;--crit-bg:#2E1815;--surface-2:#182028;}}}}
:root[data-theme="dark"]{{--ground:#0C1116;--surface:#131A21;--ink:#E9EEF3;--body:#C3CFD9;
--muted:#8FA0AE;--faint:#6B7C8A;--line:#212C36;--accent:#40B9C2;--accent-soft:#10333A;
--ok:#5FBF8A;--ok-bg:#12291E;--warn:#D9A63C;--warn-bg:#2C2314;--crit:#E0776C;--crit-bg:#2E1815;
--surface-2:#182028;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);color:var(--body);
font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;font-size:15px;line-height:1.6}}
h1,h2,h3{{font-family:Charter,"Bitstream Charter",Georgia,serif;color:var(--ink);margin:0;text-wrap:balance}}
.wrap{{max-width:1180px;margin:0 auto;padding:0 24px 70px}}
header{{background:var(--surface);border-bottom:1px solid var(--line);padding:26px 0 22px;margin-bottom:26px}}
.eyebrow{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px;letter-spacing:.14em;
text-transform:uppercase;color:var(--accent)}}
h1{{font-size:30px;letter-spacing:-.015em;margin-top:6px}}
.lede{{max-width:70ch;margin-top:10px;color:var(--muted)}}
.diagram{{background:#fff;border:1px solid var(--line);margin-top:16px;overflow-x:auto}}
.diagram svg{{display:block;min-width:900px}}
h2{{font-size:22px;margin-top:38px}}
.tag{{display:inline-block;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10.5px;
letter-spacing:.05em;padding:3px 8px;border:1px solid currentColor;text-transform:uppercase;
color:var(--accent);background:var(--accent-soft);margin-left:8px;vertical-align:3px}}
table{{border-collapse:collapse;width:100%;font-size:13.5px;margin-top:14px}}
th{{text-align:left;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10.5px;
letter-spacing:.07em;text-transform:uppercase;color:var(--faint);font-weight:400;padding:9px 12px;
border-bottom:1px solid var(--line);background:var(--surface-2)}}
td{{padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:top}}
td.p{{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--ink);white-space:nowrap}}
.scroll{{overflow-x:auto;border:1px solid var(--line);background:var(--surface);margin-top:14px}}
.callout{{border:1px solid var(--line);border-left:3px solid var(--accent);background:var(--surface);
padding:15px 18px;margin-top:20px}}
.callout.crit{{border-left-color:var(--crit);background:var(--crit-bg)}}
.callout.warn{{border-left-color:var(--warn);background:var(--warn-bg)}}
.callout .lbl{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10.5px;letter-spacing:.1em;
text-transform:uppercase;color:var(--muted);margin-bottom:6px}}
.callout.crit .lbl{{color:var(--crit)}} .callout.warn .lbl{{color:var(--warn)}}
.callout p{{margin:0;max-width:74ch}} .callout p+p{{margin-top:9px}}
ol.steps{{max-width:74ch;padding-left:22px}} ol.steps li{{margin-bottom:9px}}
ol.steps li::marker{{color:var(--accent);font-family:ui-monospace,monospace;font-weight:700}}
code{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.9em;background:var(--surface-2);
padding:1px 5px;border:1px solid var(--line)}}
@media print{{body{{background:#fff}} header{{border:0}} .diagram{{break-inside:avoid}}}}
</style>
<header><div class="wrap">
<div class="eyebrow">Hardware build sheet</div>
<h1>Bench governor &mdash; wiring</h1>
<p class="lede">A hardware mirror of the software governor. Every veto is enforced again by a
microcontroller that does not trust the host, so two independent layers must agree before the
transducer is energised &mdash; and either can stop it alone.</p>
</div></header>
<div class="wrap">

<div class="callout crit">
<div class="lbl">Read this before opening Tinkercad</div>
<p><strong>Tinkercad Circuits cannot simulate an ESP32.</strong> It supports Arduino Uno, ATtiny and
micro:bit only. The &ldquo;ESP32&rdquo; results you find there are 3D models, not circuits. Build the
Uno diagram in Tinkercad; use Wokwi for the ESP32, or just flash your real board.</p>
</div>

<h2>Arduino Uno <span class="tag">Tinkercad</span></h2>
<div class="diagram">{uno}</div>
<div class="scroll"><table><thead><tr><th>Pin</th><th>Goes to</th><th>Notes</th></tr></thead>
<tbody>{uno_rows}</tbody></table></div>

<h2>ESP32 DevKit <span class="tag">Wokwi / real hardware</span></h2>
<div class="diagram">{esp}</div>
<div class="scroll"><table><thead><tr><th>Pin</th><th>Goes to</th><th>Notes</th></tr></thead>
<tbody>{esp_rows}</tbody></table></div>

<div class="callout warn">
<div class="lbl">Two ESP32 gotchas that will cost you an evening</div>
<p><strong>GPIO35 has no internal pull-up.</strong> Add a 10&nbsp;k&#8486; resistor from pin 35 to 3V3 or the
E-stop input floats and latches at random. The supplied <code>diagram.json</code> already includes it.</p>
<p><strong>ADC pins are not 5&nbsp;V tolerant.</strong> The potentiometer goes to 3V3, not 5V.</p>
</div>

<h2>Build it in about fifteen minutes</h2>
<ol class="steps">
<li>tinkercad.com &rarr; <strong>Circuits</strong> &rarr; <em>Create new Circuit</em>.</li>
<li>Drag in: Arduino Uno R3, breadboard, HC-SR04, piezo, 4 LEDs, 4&times; 220&#8486;, 3 pushbuttons, potentiometer.</li>
<li>Wire it per the diagram above. Colours in the picture match the colours in the table.</li>
<li><strong>Code &rarr; Text</strong> (not Blocks). Paste <code>gaukavach_uno.ino</code>.</li>
<li><strong>Start Simulation</strong>, open the <strong>Serial Monitor</strong>.</li>
<li>Drag the slider on the HC-SR04 &mdash; that is your approaching animal.</li>
</ol>

<h2>The demo &mdash; five moves, ninety seconds</h2>
<ol class="steps">
<li><strong>Sensor to ~80&nbsp;cm.</strong> Green LED. Serial: <code>PERMITTED @ 28.6 m, carrier 25.0 kHz</code>.</li>
<li><strong>Hold PERSON.</strong> Emission stops mid-burst, red LED:
<em>&ldquo;a person is inside the exposure cone&rdquo;</em>. Release &mdash; it does <em>not</em> resume,
because the quiet period is now running.</li>
<li><strong>Turn the pot past 3.</strong> <em>&ldquo;group large enough that a startle could cascade&rdquo;</em>.
A flock is a dispatch problem, not an acoustic one.</li>
<li><strong>Sensor under ~34&nbsp;cm.</strong> <em>&ldquo;already at the carriageway &mdash; fleeing would
cross it&rdquo;</em>. The system will not push an animal across the road.</li>
<li><strong>Let it run.</strong> After three attempts the amber LED latches: <strong>ESCALATED</strong>.
It gives up rather than getting louder.</li>
</ol>
<p>Then press <strong>E-STOP</strong>. Nothing clears it but a reset.</p>

<div class="callout crit">
<div class="lbl">What this rig does not prove</div>
<p><strong>Any decibel level.</strong> No calibrated ultrasonic microphone is attached, so an SPL claim
about this rig would be fabricated. Both sketches print that warning at boot.</p>
<p><strong>Anything about cattle.</strong> No animal is involved. And if your transducer is a 40&nbsp;kHz
ranging element, note that 40&nbsp;kHz sits <em>above</em> the 35&nbsp;kHz cattle audiogram endpoint &mdash;
it is the wrong part, standing in for the signal chain only.</p>
</div>

<p style="color:var(--faint);font-size:12.5px;margin-top:34px">
Pin numbers in these diagrams are parsed from the sketches at build time, and a test asserts the
firmware limits never drift from <code>evidence.py</code>. Regenerate with
<code>python tools/make_wiring_diagram.py</code>.</p>
</div>
"""


def rows(p: dict[str, str], esp: bool) -> str:
    spec = [
        (p["PIN_TRIG"], "HC-SR04 TRIG", "10 us trigger pulse"),
        (p["PIN_ECHO"], "HC-SR04 ECHO", "timeout returns -1, never 'adjacent'"),
        (p["PIN_EMIT"], "Piezo +, via 220R", "LEDC ramped burst" if esp else "tone(), hard-gated"),
        (p["LED_PERMIT"], "Green LED, via 220R", "permitted / emitting"),
        (p["LED_REFUSE"], "Red LED, via 220R", "refused"),
        (p["LED_ESCALATE"], "Amber LED, via 220R", "escalated to dispatch"),
        (p["LED_ARMED"], "Blue LED, via 220R", "armed heartbeat"),
        (p["BTN_PERSON"], "Button to GND", "person in cone - absolute veto"),
        (p["BTN_NONTARGET"], "Button to GND", "dog / goat in cone - absolute veto"),
        (p["BTN_ESTOP"], "Button to GND",
         "E-stop. NEEDS external 10k pull-up to 3V3" if esp else "E-stop, latching"),
        (p["POT_GROUP"], "Pot wiper", "group size 1-8; ends to 3V3 and GND" if esp
         else "group size 1-8; ends to 5V and GND"),
    ]
    return "".join(
        f'<tr><td class="p">{esc(pin)}</td><td>{esc(to)}</td>'
        f'<td style="color:var(--muted)">{esc(note)}</td></tr>'
        for pin, to, note in spec
    )


def main() -> None:
    up, ep = pins(UNO), pins(ESP)
    ul, el = limits(UNO), limits(ESP)
    uno_svg, esp_svg = build("Arduino Uno", up, ul), build("ESP32", ep, el)

    (ROOT / "hardware" / "wiring_uno.svg").write_text(uno_svg, encoding="utf-8")
    (ROOT / "hardware" / "wiring_esp32.svg").write_text(esp_svg, encoding="utf-8")

    page = PAGE.format(uno=uno_svg, esp=esp_svg,
                       uno_rows=rows(up, False), esp_rows=rows(ep, True))
    out = ROOT / "hardware" / "wiring.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote hardware/wiring_uno.svg   ({len(uno_svg)/1024:.0f} KB)")
    print(f"wrote hardware/wiring_esp32.svg ({len(esp_svg)/1024:.0f} KB)")
    print(f"wrote hardware/wiring.html      ({out.stat().st_size/1024:.0f} KB)")
    print(f"uno  pins: {up}")
    print(f"esp32 pins: {ep}")


if __name__ == "__main__":
    main()
