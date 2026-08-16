"""
Generate the Wokwi build manual: build the simulation by hand, no breadboard.

    python tools/make_wokwi_steps.py

The parts list and every wire are read out of hardware/wokwi_simple/diagram.json,
so the manual cannot describe a circuit the simulator does not have. If you edit
the diagram, re-run this and the manual follows.

The drawing primitives come from make_build_steps, deliberately: two generators
drawing the same circuit two different ways is how the pictures start
disagreeing with each other.
"""

from __future__ import annotations

import html
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAGRAM = ROOT / "hardware" / "wokwi_simple" / "diagram.json"
SKETCH = ROOT / "hardware" / "wokwi_simple" / "sketch.ino"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bs = _load("make_build_steps")
wmap = _load("wokwi_map")
S, box, link, canvas = bs.S, bs.box, bs.link, bs.canvas
ACCENT, OK, WARN, CRIT = bs.ACCENT, bs.OK, bs.WARN, bs.CRIT
RAIL_GND, RAIL_POS, MUTED = bs.RAIL_GND, bs.RAIL_POS, bs.MUTED
OHM = bs.OHM


def esc(s) -> str:
    t = html.escape(str(s), quote=True)
    return "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in t)


def diagram() -> dict:
    return json.loads(DIAGRAM.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- wire tables

# Wokwi's own names, so what the manual says matches what the "+" menu shows.
CATALOGUE = {
    "board-esp32-devkit-c-v4": "ESP32 DevKit V4 (already on the canvas)",
    "wokwi-hc-sr04": "HC-SR04 Ultrasonic Distance Sensor",
    "wokwi-led": "LED",
    "wokwi-buzzer": "Buzzer",
    "wokwi-pushbutton": "Pushbutton",
    "wokwi-resistor": "Resistor",
    "wokwi-potentiometer": "Potentiometer",
}

PRETTY = {
    "esp:3V3": "ESP32 3V3", "esp:5V": "ESP32 VIN/5V",
    "esp:GND.1": "ESP32 GND", "esp:GND.2": "ESP32 GND", "esp:GND.3": "ESP32 GND",
    "esp:VN": "ESP32 GPIO39 (VN)", "esp:VP": "ESP32 GPIO36 (VP)",
}


def ohms(value: str) -> str:
    """10000 -> 10k. Wokwi wants the raw number typed in; humans do not read it."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{n // 1000}k" if n >= 1000 and n % 1000 == 0 else str(n)


def pretty(ep: str, ids: dict[str, str], kinds: dict[str, str]) -> str:
    if ep in PRETTY:
        return PRETTY[ep]
    part, _, pin = ep.partition(":")
    if part == "esp":
        return f"ESP32 GPIO{pin}"
    name = ids.get(part, part)
    if kinds.get(part) == "wokwi-resistor":
        return f"{name} leg {pin}"
    return f"{name} {pin}"


# Short names for the wire tables. The catalogue names above are what you hunt
# for in Wokwi's part menu; these are what fits in a table cell.
SHORT = {
    "wokwi-hc-sr04": "HC-SR04",
    "wokwi-buzzer": "Buzzer",
    "wokwi-potentiometer": "Potentiometer",
    "wokwi-resistor": "Resistor",
}


def part_kinds(d: dict) -> dict[str, str]:
    return {p["id"]: p["type"] for p in d["parts"]}


def labels(d: dict) -> dict[str, str]:
    out = {}
    for p in d["parts"]:
        a, kind = p.get("attrs", {}), p["type"]
        label = a.get("label")
        if kind == "wokwi-led" and label:
            out[p["id"]] = f"{label} LED"
        elif kind == "wokwi-pushbutton" and label:
            out[p["id"]] = f"{label} button"
        elif kind == "wokwi-resistor":
            out[p["id"]] = f"Resistor {ohms(a.get('value', ''))}"
        else:
            out[p["id"]] = label or SHORT.get(kind) or CATALOGUE.get(kind, kind)
    return out


# Which connections belong to which step, by the part ids they touch.
GROUPS = [
    ("leds", {"ledGreen", "ledRed", "ledAmber"}),
    ("buzzer", {"bz"}),
    ("buttons", {"btnPerson", "btnNonTarget", "btnEstop"}),
    ("pullup", {"rEstop"}),
    ("pot", {"pot"}),
    ("sensor", {"sr04"}),
]


def wires_for(d: dict, ids: set[str], exclude: set[str] | None = None) -> list:
    exclude = exclude or set()
    out = []
    for c in d["connections"]:
        touched = {c[0].split(":")[0], c[1].split(":")[0]}
        if touched & ids and not (touched & exclude):
            out.append((c[0], c[1]))
    return out


# ---------------------------------------------------------------- pictures

def pic_leds(p) -> str:
    spec = [("26", "#2ECC71", "GREEN LED", "PERMIT", OK),
            ("27", "#E74C3C", "RED LED", "REFUSE", CRIT),
            ("14", "#F1C40F", "AMBER LED", "ESCALATE", WARN)]
    s = canvas(3, "Straight from the pin to the LED. No resistor in the simulator.")
    for r, (g, colour, name, meaning, accent) in enumerate(spec):
        box(s, 0, r, "pin", f"GPIO{g}", "ESP32", accent)
        box(s, 1, r, "part", name, f"anode  -  {meaning}", accent, "led", colour)
        box(s, 2, r, "pin", "GND", "cathode", RAIL_GND)
        link(s, 0, r, 1, r, accent)
        link(s, 1, r, 2, r, RAIL_GND)
    return s.out("LEDs")


def pic_buzzer(p) -> str:
    s = canvas(1, "Two wires. The buzzer is the emitter stand-in.")
    box(s, 0, 0, "pin", "GPIO25", "LEDC carrier", ACCENT)
    box(s, 1, 0, "part", "BUZZER 1", "the driven pin", ACCENT, "piezo")
    box(s, 2, 0, "pin", "GND", "BUZZER 2", RAIL_GND)
    link(s, 0, 0, 1, 0, ACCENT)
    link(s, 1, 0, 2, 0, RAIL_GND)
    return s.out("Buzzer")


def pic_buttons(p) -> str:
    spec = [("32", "#2E86C1", "PERSON", "human in cone", ACCENT),
            ("33", "#F1C40F", "DOG / GOAT", "non-target", ACCENT),
            ("35", "#E74C3C", "E-STOP", "kills emission", CRIT)]
    s = canvas(3, "Pin to the left leg, ground to the other left leg.")
    for r, (g, colour, name, meaning, accent) in enumerate(spec):
        box(s, 0, r, "pin", f"GPIO{g}", "input", accent)
        box(s, 1, r, "part", name, meaning, accent, "btn", colour)
        box(s, 2, r, "pin", "GND", "opposite leg", RAIL_GND)
        link(s, 0, r, 1, r, accent)
        link(s, 1, r, 2, r, RAIL_GND)
    return s.out("Buttons")


def pic_pullup(p) -> str:
    s = canvas(2, "The one resistor in the whole project. It is not optional.", CRIT)
    box(s, 0, 0, "pin", "GPIO35", "input only, no pull-up", CRIT)
    box(s, 1, 0, "part", "JUNCTION", "the E-STOP pin leg", CRIT, "node")
    box(s, 2, 0, "part", "10k " + OHM, "pull-up resistor", RAIL_POS, "res", "10k")
    box(s, 3, 0, "pin", "3V3", "ESP32", RAIL_POS)
    for c in range(3):
        link(s, c, 0, c + 1, 0, CRIT if c == 0 else RAIL_POS)
    box(s, 1, 1, "part", "E-STOP", "wired in the last step", CRIT, "btn", "#E74C3C")
    box(s, 2, 1, "pin", "GND", "opposite leg", RAIL_GND)
    bs.drop(s, 1, 0, 1, CRIT)
    link(s, 1, 1, 2, 1, RAIL_GND)
    return s.out("Pull-up")


def pic_pot(p) -> str:
    s = canvas(3, "Three wires. The middle terminal is the wiper.")
    rows = [("3V3", "VCC terminal", RAIL_POS), ("GPIO34", "SIG - the wiper", WARN),
            ("GND", "GND terminal", RAIL_GND)]
    for r, (pin, what, colour) in enumerate(rows):
        box(s, 0, r, "pin", pin, "ESP32", colour)
        box(s, 1, r, "part", "POT " + what.split()[0], what, colour, "pot")
        link(s, 0, r, 1, r, colour)
    return s.out("Potentiometer")


def pic_sensor(p) -> str:
    s = canvas(4, "Four wires. In the simulator the sensor runs on 3V3, so ECHO "
                  "needs no divider.")
    rows = [("3V3", "SR04 VCC", "sensor supply", RAIL_POS),
            ("GND", "SR04 GND", "sensor ground", RAIL_GND),
            ("GPIO13", "SR04 TRIG", "trigger out", OK),
            ("GPIO39 (VN)", "SR04 ECHO", "echo in", ACCENT)]
    for r, (pin, part, what, colour) in enumerate(rows):
        box(s, 0, r, "pin", pin, "ESP32", colour)
        box(s, 1, r, "part", part, what, colour, "sr04")
        link(s, 0, r, 1, r, colour)
    return s.out("Sensor")


# ---------------------------------------------------------------- content

STEPS = [
    ("start", 1, "Open a new ESP32 project", ACCENT, None,
     ["Go to <b>wokwi.com</b> and pick <b>ESP32</b> &rarr; <b>Blank Project</b>. "
      "You do not need an account to run it; you need one to save it.",
      "You get two panes: <code>sketch.ino</code> on the left, an empty canvas "
      "with one ESP32 on the right."],
     "There is no breadboard anywhere in this build. In Wokwi you wire parts "
     "directly to the board, which is why this version is quicker to assemble "
     "than the physical one - and why it cannot teach you breadboard rows."),

    ("code", 2, "Paste the firmware", ACCENT, None,
     ["Select everything in <code>sketch.ino</code> and replace it with the code "
      "below. It is the same firmware as the hardware build, unchanged.",
      "Nothing to install: no libraries, no board manager."],
     "The pin map in the code is what the rest of this manual wires to. If you "
     "change a pin in one place you have to change it in both, so it is easier "
     "not to."),

    ("leds", 3, "Three status LEDs", OK, pic_leds,
     ["Click the blue <b>+</b> on the canvas and add <b>LED</b> three times.",
      "Set their colours to green, red and yellow in the parts panel.",
      "Wire each one: GPIO to the <b>anode</b> (the longer pin, marked A), "
      "cathode to any ESP32 <b>GND</b>."],
     "Green means it decided to emit, red means it refused, amber means it gave "
     "up and asked for a human. Most of your demo happens on the red one."),

    ("buzzer", 4, "The emitter", ACCENT, pic_buzzer,
     ["Add <b>Buzzer</b>. Wire pin 1 to GPIO25 and pin 2 to GND.",
      "Turn its volume down in the parts panel before you present."],
     "The buzzer is a stand-in for the ultrasonic transducer, and audible on "
     "purpose - you need to hear the ramped envelope start and stop. Say that "
     "out loud when you demo it rather than letting someone catch it."),

    ("buttons", 5, "The three veto buttons", CRIT, pic_buttons,
     ["Add <b>Pushbutton</b> three times. Label them PERSON, DOG / GOAT and E-STOP.",
      "Wire each: GPIO to one left leg, GND to the other left leg."],
     "Press-to-ground is the right way round for a safety input: a broken wire "
     "reads as <i>not pressed</i> rather than as a stuck button."),

    ("pullup", 6, "The one resistor", CRIT, pic_pullup,
     ["Add <b>Resistor</b> and set its value to <b>10000</b>.",
      "Wire it from the E-STOP button's GPIO35 leg to <b>3V3</b>.",
      "It sits <b>alongside</b> the button on the same node, not in line with it."],
     "GPIO34&ndash;39 are input-only and have <b>no internal pull-up in the "
     "silicon</b>, and Wokwi models that faithfully. Skip this and the E-stop "
     "latches at random, which looks exactly like a software bug."),

    ("pot", 7, "Group-size knob", WARN, pic_pot,
     ["Add <b>Potentiometer</b>. Wire VCC to 3V3, GND to GND, SIG to GPIO34.",
      "Drag it fully anticlockwise before you start."],
     "This is how you show the herd rule live: turn it past 3 and the governor "
     "refuses, because a startle in a group can cascade into the road."),

    ("sensor", 8, "The distance sensor", OK, pic_sensor,
     ["Add <b>HC-SR04 Ultrasonic Distance Sensor</b>.",
      "Wire VCC to <b>3V3</b>, GND to GND, TRIG to GPIO13, "
      "ECHO to <b>GPIO39</b> &mdash; which Wokwi labels <b>VN</b>.",
      "Click the sensor while the simulation runs to get its distance slider."],
     "Two traps here. <b>VN</b> is the only name Wokwi accepts for GPIO39: type "
     "39 and the wire is silently ignored, the sketch simply never sees a "
     "reading. And the sensor is on 3V3 here only because it is simulated &mdash; "
     "the hardware build runs it at 5&nbsp;V through a 1k/2k divider, because "
     "ESP32 pins are not 5&nbsp;V tolerant."),

    ("run", 9, "Press play and run the demo", OK, None,
     ["Hit the green <b>play</b> button. The serial pane prints the limits, then "
      "<i>NO calibrated mic attached: this rig makes no dB claim</i>.",
      "Click the HC-SR04 and set the distance slider to about <b>80&nbsp;cm</b> "
      "&rarr; green, <b>PERMITTED @ 28.6 m</b>.",
      "Now walk the refusals: PERSON, DOG / GOAT, pot past 3, distance under "
      "34&nbsp;cm. Each one turns the green LED red with a reason in serial.",
      "Leave a target detected for about seven seconds &rarr; amber, escalated."],
     "The refusals are the pitch. Anything can be built to emit; the argument "
     "here is that it mostly decides not to, and says why every time."),
]


PAGE = """<title>GauKavach - Wokwi build manual</title>
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
.wrap{{max-width:1040px;margin:0 auto;padding:0 24px 80px}}
header{{background:var(--surface);border-bottom:1px solid var(--line);padding:30px 0 26px;margin-bottom:26px}}
.eyebrow{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px;letter-spacing:.14em;
text-transform:uppercase;color:var(--accent)}}
h1{{font-size:32px;letter-spacing:-.015em;margin-top:6px}}
.lede{{max-width:72ch;margin-top:12px;color:var(--muted)}}
.rail{{display:flex;gap:6px;margin:22px 0 0;flex-wrap:wrap}}
.rail a{{flex:1 1 0;min-width:60px;text-decoration:none;border:1px solid var(--line);
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
ol{{margin:0;padding-left:24px;max-width:82ch}} ol li{{margin-bottom:9px}}
ol li::marker{{color:var(--accent);font-weight:700}}
.pic{{margin-top:18px;border:1px solid var(--line);background:#fff;overflow-x:auto}}
.pic svg{{display:block;min-width:700px}}
.note{{margin-top:16px;padding:14px 17px;border-left:3px solid var(--warn);
background:var(--warn-bg);font-size:14px;max-width:90ch}}
.note.crit{{border-left-color:var(--crit);background:var(--crit-bg)}}
.note b{{color:var(--ink)}}
.fast{{border:2px solid var(--accent);background:var(--surface);padding:20px 24px;
margin-top:24px}}
.fast h2{{font-size:24px;margin-bottom:4px}}
.fast .tag{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10.5px;
letter-spacing:.1em;text-transform:uppercase;color:var(--accent)}}
.clicks{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
gap:12px;margin-top:16px}}
.click{{border:1px solid var(--line);background:var(--surface-2);padding:12px 14px}}
.click b{{display:block;color:var(--ink);font-size:15px;margin-bottom:3px}}
.click span{{font-size:13px;color:var(--muted)}}
.click i{{font-family:ui-monospace,Menlo,Consolas,monospace;font-style:normal;
color:var(--accent);font-size:11px;letter-spacing:.08em}}
.cp{{position:relative;margin-top:14px}}
.cp button{{position:absolute;top:10px;right:10px;z-index:2;
font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px;letter-spacing:.06em;
text-transform:uppercase;background:#1F2A33;color:#CFE0E4;border:1px solid #3A4954;
padding:6px 12px;cursor:pointer}}
.cp button:hover{{background:#2A3A45;color:#fff}}
.cp button.done{{background:var(--ok);border-color:var(--ok);color:#fff}}
.cp h3{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px;
letter-spacing:.1em;text-transform:uppercase;color:var(--faint);margin:0 0 6px}}
.callout{{border:1px solid var(--line);border-left:3px solid var(--accent);
background:var(--surface);padding:16px 20px;margin-top:22px}}
.callout .lbl{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10.5px;
letter-spacing:.1em;text-transform:uppercase;color:var(--accent);margin-bottom:7px}}
.callout p{{margin:0;max-width:80ch}} .callout p+p{{margin-top:10px}}
table{{border-collapse:collapse;width:100%;font-size:14px;margin-top:14px}}
th{{text-align:left;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10.5px;
letter-spacing:.07em;text-transform:uppercase;color:var(--faint);font-weight:400;
padding:10px 13px;border-bottom:1px solid var(--line);background:var(--surface-2)}}
td{{padding:9px 13px;border-bottom:1px solid var(--line)}}
td.w{{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--ink);white-space:nowrap}}
.scroll{{overflow-x:auto;border:1px solid var(--line);background:var(--surface);margin-top:14px}}
code{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.9em;
background:var(--surface-2);padding:1px 5px;border:1px solid var(--line)}}
pre{{margin:14px 0 0;padding:16px 18px;background:#10161C;color:#D7E1EA;overflow-x:auto;
font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;line-height:1.55;
border:1px solid var(--line);max-height:460px}}
pre.short{{max-height:300px}}
details{{margin-top:16px;border:1px solid var(--line);background:var(--surface-2);padding:12px 16px}}
summary{{cursor:pointer;font-weight:600;color:var(--ink)}}
@media print{{body{{background:#fff}} .step{{break-inside:avoid}} .rail{{display:none}}}}
</style>
<header><div class="wrap">
<div class="eyebrow">Wokwi build manual</div>
<h1>Build the simulation by hand &mdash; no breadboard</h1>
<p class="lede">Nine steps, about fifteen minutes. Add one part, wire it, move on.
Every wire in this manual is read out of the project's own diagram file, so the
instructions cannot describe a circuit that does not exist. If you would rather
not click, step 2's shortcut drops the whole thing in at once.</p>
<div class="rail">{rail}</div>
</div></header>
<div class="wrap">

<div class="fast">
<div class="tag">Fastest route &mdash; about a minute, no wiring</div>
<h2>Paste two things and press play</h2>
<p style="max-width:74ch;margin-top:8px">You do not have to understand Wokwi's
editor to run this. Wokwi keeps the circuit in a text file, so pasting that file
builds every part and every wire for you. Nothing to drag.</p>
<div class="clicks">
<div class="click"><b>1. Open</b><span>Go to <i>wokwi.com/projects/new/esp32</i>
&mdash; no account needed to run it.</span></div>
<div class="click"><b>2. diagram.json</b><span>Tab above the code, next to
<i>sketch.ino</i>. Click it, select all, paste block B.</span></div>
<div class="click"><b>3. sketch.ino</b><span>Back to the first tab. Select all,
paste block A.</span></div>
<div class="click"><b>4. Play</b><span>The green triangle, top left of the
canvas. The serial pane opens underneath.</span></div>
</div>
<div class="cp"><h3>Block A &mdash; paste into sketch.ino</h3>
<button data-copy="blockA">Copy</button><pre id="blockA">{sketch}</pre></div>
<div class="cp"><h3>Block B &mdash; paste into diagram.json</h3>
<button data-copy="blockB">Copy</button><pre class="short" id="blockB">{diagram}</pre></div>
<p style="max-width:74ch;margin-top:16px"><b>Then:</b> click the HC-SR04 in the
canvas while it is running &mdash; a distance slider appears. Set it to about
<b>80&nbsp;cm</b> for a permit, and read the reasons in the serial pane. Step 9
has the full demo script.</p>
<p class="note" style="border-left-color:var(--accent);background:var(--surface-2)">
Everything below this box is the same circuit built by hand, one part at a time.
It is there if you want to know what you pasted &mdash; you do not need it to
run the simulation.</p>
</div>

<h2 style="margin-top:30px">The whole circuit</h2>
<p style="color:var(--muted);max-width:74ch">Ten parts around the ESP32. Read a
row left to right: ESP32 pin, part terminal, and where the other terminal goes.
The two bars on the right are the <b>GND</b> and <b>3V3</b> nodes &mdash; every
wire drawn to a bar is just a wire back to that pin on the ESP32.</p>
<div class="pic">{overview}</div>

<div class="callout">
<div class="lbl">This is the stripped version</div>
<p>Eleven parts and {nwires} wires, against seventeen parts and thirty in the
hardware build. Everything that exists only to protect real silicon is gone: the
three LED series resistors, the buzzer's resistor, and the 1k/2k divider on ECHO.
A simulated pin has no current to exceed and no voltage to survive.</p>
<p><b>One passive stays.</b> The 10&nbsp;k pull-up on GPIO35 is not protection,
it is function &mdash; GPIO34&ndash;39 have no internal pull-up in the silicon and
Wokwi models that. Without it the E-stop floats and latches on its own.</p>
<p><b>Do not build hardware from this page.</b> Use the breadboard guide for that.
The behaviour is identical; the electrics are not.</p>
</div>

{steps}

<h2 style="margin-top:38px">Every wire, one table</h2>
<p style="color:var(--muted);max-width:72ch">Generated from
<code>hardware/wokwi_simple/diagram.json</code>. If the manual and the simulator
ever disagree, this table is what the simulator actually has.</p>
<div class="scroll"><table><thead><tr><th>#</th><th>From</th><th>To</th>
</tr></thead><tbody>{alltable}</tbody></table></div>

<p style="color:var(--faint);font-size:13px;margin-top:30px">
Regenerate with <code>python tools/make_wokwi_steps.py</code>.</p>
</div>
<script>
document.querySelectorAll("button[data-copy]").forEach(function (b) {{
  b.addEventListener("click", function () {{
    var pre = document.getElementById(b.dataset.copy);
    function selectIt() {{
      // clipboard blocked or absent: select it so one keystroke still works
      var r = document.createRange();
      r.selectNodeContents(pre);
      var s = getSelection();
      s.removeAllRanges();
      s.addRange(r);
      b.textContent = "Press Ctrl+C";
    }}
    if (!navigator.clipboard || !navigator.clipboard.writeText) {{
      selectIt();
      return;
    }}
    navigator.clipboard.writeText(pre.innerText).then(function () {{
      b.textContent = "Copied";
      b.classList.add("done");
      setTimeout(function () {{
        b.textContent = "Copy";
        b.classList.remove("done");
      }}, 1600);
    }}, selectIt);
  }});
}});
</script>
"""


def main() -> None:
    d = diagram()
    ids, kinds = labels(d), part_kinds(d)
    sketch = SKETCH.read_text(encoding="utf-8")

    rail_html = "".join(
        f'<a href="#w{n}"><b>{n}</b>{esc(t.split(chr(32))[0])}</a>'
        for _k, n, t, _c, _p, _i, _note in STEPS)

    cls = {ACCENT: "", CRIT: " crit", OK: " ok", WARN: " warn"}
    blocks = []
    for key, n, title, colour, pic, items, note in STEPS:
        li = "".join(f"<li>{i}</li>" for i in items)
        extra = ""

        if key == "code":
            extra = (f'<div class="cp"><button data-copy="sk2">Copy</button>'
                     f'<pre id="sk2">{esc(sketch)}</pre></div>')

        group = dict(GROUPS).get(key)
        if group:
            # The button step must not list the pull-up wire: that resistor
            # does not exist on the canvas yet, and step 6 is where it lands.
            later = {"rEstop"} if key == "buttons" else set()
            rows = "".join(
                f'<tr><td class="w">{esc(pretty(a, ids, kinds))}</td>'
                f'<td class="w">{esc(pretty(b, ids, kinds))}</td></tr>'
                for a, b in wires_for(d, group, later))
            extra += ('<div class="scroll"><table><thead><tr><th>Connect this</th>'
                      f'<th>To this</th></tr></thead><tbody>{rows}</tbody></table></div>')

        svg = f'<div class="pic">{pic(d)}</div>' if pic else ""
        ncls = "note crit" if colour == CRIT else "note"
        blocks.append(
            f'<div class="step" id="w{n}"><div class="shead">'
            f'<span class="num{cls[colour]}">{n}</span><h2>{esc(title)}</h2></div>'
            f'<div class="body"><ol>{li}</ol>{svg}{extra}'
            f'<div class="{ncls}">{note}</div></div></div>')

    alltable = "".join(
        f'<tr><td class="w">{i}</td><td class="w">{esc(pretty(c[0], ids, kinds))}</td>'
        f'<td class="w">{esc(pretty(c[1], ids, kinds))}</td></tr>'
        for i, c in enumerate(d["connections"], 1))

    page = PAGE.format(rail=rail_html, steps="".join(blocks),
                       alltable=alltable, nwires=len(d["connections"]),
                       overview=wmap.draw(S), sketch=esc(sketch),
                       diagram=esc(DIAGRAM.read_text(encoding="utf-8")))
    page = "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in page)
    out = ROOT / "hardware" / "wokwi_steps.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote hardware/wokwi_steps.html ({out.stat().st_size / 1024:.0f} KB), "
          f"{len(STEPS)} steps, {len(d['connections'])} wires")


if __name__ == "__main__":
    main()
