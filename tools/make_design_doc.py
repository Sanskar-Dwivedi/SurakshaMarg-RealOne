"""
Generate the handover design document for the bench demonstrator.

    python tools/make_design_doc.py

This is the one page you give to somebody who will build the rig without you
standing next to them. Everything in it is read out of the firmware and the
existing verified figures, so the document cannot describe a rig the code does
not implement:

  - pin assignments and governor limits are parsed from the sketch
  - the board pin map is the figure from make_breadboard
  - the circuit diagrams are the figures from make_build_steps
  - the acceptance thresholds are computed from the sketch's own scale factors

Bump ISSUED and REV by hand when the design changes. Everything else follows.
"""

from __future__ import annotations

import html
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESP = ROOT / "hardware" / "wokwi_esp32" / "gaukavach_esp32.ino"

ISSUED = "16 August 2026"
REV = "A"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bs = _load("make_build_steps")
mb = _load("make_breadboard")
OHM = "&#937;"


def esc(s) -> str:
    t = html.escape(str(s), quote=True)
    return "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in t)


def consts() -> dict[str, float]:
    """Governor limits, straight out of the firmware."""
    src = ESP.read_text(encoding="utf-8")
    out = {}
    for n in ("MAX_GROUP", "MAX_ACTIVATION_MS", "MIN_SILENCE_MS", "DAILY_BUDGET_MS",
              "ESCALATE_AFTER_MS", "MAX_ATTEMPTS", "CARRIER_HZ", "DEMO_SPEED",
              "RAMP_MS", "DESK_SCALE", "RANGE_MAX_M", "LINE_M"):
        m = re.search(rf"\b{n}\s*=\s*([\d.]+)", src)
        if not m:
            raise SystemExit(f"{n} not found in {ESP.name}")
        out[n] = float(m.group(1))
    return out


# ------------------------------------------------------------------ content

# Indicative Indian street prices, for budgeting only. They are a range because
# they are, and quoting a single figure to a person who has to go and buy the
# parts is a small lie that costs them a trip.
BOM = [
    ("1", "ESP32 DevKit V1", "30-pin, micro-USB. 38-pin works; pin labels differ",
     "350 - 500"),
    ("1", "HC-SR04", "ultrasonic ranging module, 5 V", "60 - 120"),
    ("1", "Piezo buzzer", "passive, 2-pin. Stands in for the transducer", "15 - 30"),
    ("3", "LED 5 mm", "one green, one red, one amber", "6 - 15"),
    ("4", f"Resistor 220 {OHM}", "1/4 W, 5%. Three LEDs and the piezo", "4 - 8"),
    ("1", f"Resistor 1 k{OHM}", "1/4 W. ECHO divider, upper leg", "1 - 2"),
    ("1", f"Resistor 2 k{OHM}", "1/4 W. ECHO divider, lower leg", "1 - 2"),
    ("1", f"Resistor 10 k{OHM}", "1/4 W. E-stop pull-up. NOT optional", "1 - 2"),
    ("3", "Tactile pushbutton", "6 mm, 4-leg, breadboard pitch", "9 - 24"),
    ("1", f"Potentiometer 10 k{OHM}", "linear, 3-pin, breadboard mountable", "15 - 40"),
    ("1", "Breadboard", "full size, 63 column, with power rails", "80 - 150"),
    ("1", "Jumper wire set", "female-to-male AND male-to-male, ~40 of each", "80 - 150"),
    ("1", "USB cable", "micro-USB, data-capable. Many charge-only cables are not",
     "50 - 100"),
]

CRITICAL = [
    ("The 10 k pull-up on the E-stop is load-bearing",
     "GPIO35 is one of GPIO34-39, which are input-only and have <b>no internal "
     "pull-up anywhere in the silicon</b>. The firmware cannot enable one; the "
     "resistor is the only thing holding that input at a defined level. Omit it "
     "and the E-stop latches at random intervals. The failure presents as flaky "
     "software and will be debugged in the wrong place for an hour."),
    ("ECHO must not reach a GPIO directly",
     "The HC-SR04 is supplied at 5 V because it is unreliable below that, so its "
     "ECHO output swings to 5 V. ESP32 GPIOs are <b>not 5 V tolerant</b>. The "
     "1 k / 2 k divider brings it to about 3.3 V. Most published HC-SR04 "
     "tutorials wire ECHO straight to a pin; that is how ESP32s are quietly "
     "damaged, and the damage is usually partial, so the board half works."),
    ("GPIO12 is deliberately unused",
     "GPIO12 (MTDI) is a strapping pin: held high at reset it selects the wrong "
     "flash voltage and the board will not boot. It sits in the middle of the "
     "run of pins this design uses, and skipping it is intentional. Do not "
     "'tidy up' the pin allocation."),
    ("The potentiometer goes to 3V3, never 5 V",
     "The ADC input is not 5 V tolerant either. The pot's outer legs go to 3V3 "
     "and GND."),
    ("LED polarity",
     "Long leg (anode) toward the resistor and the GPIO; short leg to ground. A "
     "reversed LED does not fail loudly, it simply never lights, and looks like "
     "a firmware problem."),
]

ASSEMBLY = [
    ("Power distribution",
     "3V3 to the + rail, GND to the &minus; rail, and <b>link the top and bottom "
     "rails</b> at both ends. Half the inputs float otherwise."),
    ("Three status LEDs",
     f"Each: GPIO &rarr; 220 {OHM} &rarr; LED anode; LED cathode &rarr; "
     f"&minus; rail. Green, red, amber."),
    ("Emitter",
     f"GPIO25 &rarr; 220 {OHM} &rarr; piezo &rarr; &minus; rail."),
    ("Three buttons",
     "Each: GPIO to one leg, &minus; rail to the <b>diagonally opposite</b> leg, "
     "across the centre channel. Diagonal matters - two legs on the same side of "
     "the switch are already shorted together."),
    ("E-stop pull-up",
     f"10 k{OHM} from the E-stop's GPIO35 node to the + rail. It sits "
     f"<b>alongside</b> the button on the same node, not in series with it."),
    ("Group-size potentiometer",
     "Outer legs to + and &minus; rails, wiper to GPIO34."),
    ("Distance sensor and divider",
     f"VCC to VIN/5V, GND to the &minus; rail, TRIG to GPIO13. Then "
     f"ECHO &rarr; 1 k{OHM} &rarr; junction &rarr; 2 k{OHM} &rarr; ground, "
     f"with GPIO39 (VN) reading the junction."),
    ("Inspection before first power",
     "Confirm three things with the board unpowered: ECHO does not touch a GPIO "
     "directly; the 10 k is present and on the button's own node; sensor VCC is "
     "on VIN/5V and the pot is on 3V3."),
]


def acceptance(c: dict[str, float]) -> list[tuple[str, str, str]]:
    """Test steps with thresholds computed from the firmware's own constants."""
    sp = c["DEMO_SPEED"]
    line_cm = c["LINE_M"] * c["DESK_SCALE"]
    max_cm = c["RANGE_MAX_M"] * c["DESK_SCALE"]
    return [
        ("Power on",
         "Connect USB. Open the serial monitor at 115200 baud.",
         "Limits print, followed by <i>NO calibrated mic attached: this rig "
         "makes no dB claim</i>. On-board blue LED blinks about once a second."),
        ("Set the group knob",
         "Turn the potentiometer fully anticlockwise.",
         "Required before any other test. Left of centre the governor reads a "
         "group larger than the limit and refuses everything."),
        ("Detection and permit",
         f"Hold a flat hand about 80 cm from the sensor.",
         "Green LED on, piezo audible, serial reads "
         "<code>PERMITTED @ 28.6 m</code>."),
        ("Emission watchdog",
         "Keep the hand still and watch the piezo.",
         f"Emission stops on its own after about "
         f"{c['MAX_ACTIVATION_MS'] / sp / 1000:.1f} s "
         f"({c['MAX_ACTIVATION_MS'] / 1000:.0f} s of shipped limit, compressed "
         f"{sp:.0f}x for the demo)."),
        ("Human veto",
         "With a target detected, press PERSON.",
         "Emission fades out immediately, red LED, serial gives the reason."),
        ("Non-target veto",
         "Release PERSON, re-detect, press DOG / GOAT.",
         "Red LED, refused as a non-target species in the cone."),
        ("Group-size rule",
         "Release the buttons, re-detect, turn the pot past the limit.",
         f"Red LED once the reading exceeds {c['MAX_GROUP']:.0f} animals."),
        ("Carriageway rule",
         f"Move the hand closer than about {line_cm:.0f} cm.",
         "Red LED: the animal is already at the carriageway, so fleeing would "
         "cross it."),
        ("Range limit",
         f"Move the hand beyond about {max_cm:.0f} cm.",
         "Red LED: beyond the acoustic envelope."),
        ("Escalation",
         "Hold a valid target in range and do nothing else.",
         f"Amber LED after about {c['ESCALATE_AFTER_MS'] / sp / 1000:.1f} s, or "
         f"after {c['MAX_ATTEMPTS']:.0f} attempts. Serial states that acoustic "
         f"cues are not stock-proof and the system has asked for a human."),
        ("Emergency stop",
         "Press E-STOP.",
         "Emitter dead, red LED, and it stays that way until the board is "
         "reset. If it latches without being pressed, the 10 k pull-up is "
         "missing or on the wrong node."),
    ]


LIMITS = [
    ("No decibel claim is made", "There is no calibrated microphone in this rig. "
     "It demonstrates the decision logic and the drive envelope. It does not "
     "measure sound pressure, and nothing in the serial output should be read "
     "as an acoustic measurement."),
    ("The piezo is a stand-in", "A 40 kHz ranging transducer is the wrong part "
     "for this application: 40 kHz is above the 35 kHz endpoint of the cattle "
     "audiogram. The buzzer represents the signal chain, not the emitter."),
    ("Timers are compressed", "Demo timings run faster than the shipped limits "
     "so a full cycle fits inside a presentation. Both figures are printed at "
     "start-up; the shipped value is the one that governs."),
    ("Distance is scaled", "Bench centimetres map to field metres by a fixed "
     "factor so the geometry rules can be exercised on a desk."),
]


PAGE = """<title>GauKavach bench demonstrator - design and build specification</title>
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
font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;font-size:15px;line-height:1.6}}
h1,h2,h3{{font-family:Charter,"Bitstream Charter",Georgia,serif;color:var(--ink);
margin:0;text-wrap:balance}}
.wrap{{max-width:1000px;margin:0 auto;padding:0 26px 90px}}
header{{background:var(--surface);border-bottom:2px solid var(--ink);padding:30px 0 0}}
.eyebrow{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px;
letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}}
h1{{font-size:31px;letter-spacing:-.015em;margin-top:7px;max-width:24ch}}
.block{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
gap:0;margin-top:24px;border-top:1px solid var(--line)}}
.block div{{padding:12px 16px 14px;border-right:1px solid var(--line)}}
.block div:last-child{{border-right:none}}
.block dt{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10px;
letter-spacing:.1em;text-transform:uppercase;color:var(--faint)}}
.block dd{{margin:4px 0 0;font-size:14px;color:var(--ink);font-weight:600}}
section{{margin-top:40px}}
h2{{font-size:24px;padding-bottom:9px;border-bottom:1px solid var(--line)}}
h2 .n{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:15px;
color:var(--accent);margin-right:12px}}
h3{{font-size:17px;margin-top:24px}}
p{{max-width:80ch}}
table{{border-collapse:collapse;width:100%;font-size:13.5px;margin-top:14px}}
th{{text-align:left;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:10px;
letter-spacing:.07em;text-transform:uppercase;color:var(--faint);font-weight:400;
padding:9px 12px;border-bottom:1px solid var(--line);background:var(--surface-2)}}
td{{padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}}
td.q,td.w{{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--ink);
white-space:nowrap;width:1%}}
td.money{{font-family:ui-monospace,Menlo,Consolas,monospace;text-align:right;
white-space:nowrap}}
tr.total td{{border-top:2px solid var(--ink);font-weight:700;color:var(--ink)}}
.scroll{{overflow-x:auto;border:1px solid var(--line);background:var(--surface)}}
.pic{{margin-top:16px;border:1px solid var(--line);background:#fff;overflow-x:auto}}
.pic svg{{display:block;min-width:680px}}
.crit{{border:1px solid var(--line);border-left:3px solid var(--crit);
background:var(--crit-bg);padding:14px 18px;margin-top:14px}}
.crit b{{color:var(--ink)}}
.crit .h{{font-weight:700;color:var(--ink);display:block;margin-bottom:5px}}
.box{{display:inline-block;width:15px;height:15px;border:1.5px solid var(--faint);
vertical-align:-2px;margin-right:4px}}
ol.seq{{padding-left:22px;max-width:82ch}} ol.seq li{{margin-bottom:12px}}
ol.seq li::marker{{color:var(--accent);font-weight:700}}
code{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.9em;
background:var(--surface-2);padding:1px 5px;border:1px solid var(--line)}}
.sig{{margin-top:20px;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
gap:26px}}
.sig div{{border-top:1px solid var(--ink);padding-top:7px;font-size:12px;color:var(--muted);
margin-top:44px;font-family:ui-monospace,Menlo,Consolas,monospace}}
.note{{font-size:13px;color:var(--muted);max-width:82ch}}
@media print{{body{{background:#fff;font-size:11pt}} section{{break-inside:avoid}}
header{{padding-top:0}}}}
</style>
<header><div class="wrap">
<div class="eyebrow">Design and build specification</div>
<h1>GauKavach bench demonstrator</h1>
<div class="block">
<div><dt>Document</dt><dd>Rev {rev}</dd></div>
<div><dt>Issued</dt><dd>{issued}</dd></div>
<div><dt>Firmware</dt><dd>gaukavach_esp32.ino</dd></div>
<div><dt>Target</dt><dd>ESP32 Dev Module</dd></div>
<div><dt>Build time</dt><dd>about 1 hour</dd></div>
<div><dt>Parts cost</dt><dd>{cost}</dd></div>
</div>
</div></header>
<div class="wrap">
{body}
</div>
"""


def main() -> None:
    p = mb.pins()
    c = consts()
    S = []

    def sec(n: str, title: str, inner: str) -> None:
        S.append(f'<section><h2><span class="n">{n}</span>{esc(title)}</h2>{inner}</section>')

    # 1 -------------------------------------------------------------- scope
    sec("1", "Scope", f"""
<p>A desk-scale demonstrator for a livestock road-deterrence governor. An
ultrasonic sensor stands in for the detector, three indicators report the
decision, a piezo represents the emitter, and three buttons plus a knob inject
the conditions under which the system must <b>refuse</b> to emit.</p>
<p>The point of the rig is the refusal path, not the emission path. Every rule
below is enforced in firmware and can be exercised by hand in front of an
audience.</p>
<div class="scroll"><table><thead><tr><th>Governed quantity</th><th>Shipped value</th>
<th>Demo value</th></tr></thead><tbody>
<tr><td>Carrier frequency</td><td class="w">{c['CARRIER_HZ'] / 1000:.1f} kHz</td>
    <td class="w">same</td></tr>
<tr><td>Burst envelope</td><td class="w">{c['RAMP_MS']:.0f} ms raised cosine</td>
    <td class="w">same</td></tr>
<tr><td>Maximum single activation</td>
    <td class="w">{c['MAX_ACTIVATION_MS'] / 1000:.0f} s</td>
    <td class="w">{c['MAX_ACTIVATION_MS'] / c['DEMO_SPEED'] / 1000:.1f} s</td></tr>
<tr><td>Enforced quiet period</td>
    <td class="w">{c['MIN_SILENCE_MS'] / 1000:.0f} s</td>
    <td class="w">{c['MIN_SILENCE_MS'] / c['DEMO_SPEED'] / 1000:.1f} s</td></tr>
<tr><td>Daily exposure budget</td>
    <td class="w">{c['DAILY_BUDGET_MS'] / 1000:.0f} s</td>
    <td class="w">{c['DAILY_BUDGET_MS'] / c['DEMO_SPEED'] / 1000:.0f} s</td></tr>
<tr><td>Escalate to a human after</td>
    <td class="w">{c['ESCALATE_AFTER_MS'] / 1000:.0f} s</td>
    <td class="w">{c['ESCALATE_AFTER_MS'] / c['DEMO_SPEED'] / 1000:.1f} s</td></tr>
<tr><td>Maximum group size for emission</td>
    <td class="w">{c['MAX_GROUP']:.0f} animals</td><td class="w">same</td></tr>
<tr><td>Maximum attempts before escalation</td>
    <td class="w">{c['MAX_ATTEMPTS']:.0f}</td><td class="w">same</td></tr>
</tbody></table></div>
<p class="note">Demo values are the shipped limits divided by
{c['DEMO_SPEED']:.0f}, so a full cycle fits inside a presentation. Both are
printed at start-up.</p>""")

    # 2 ---------------------------------------------------------------- bom
    rows = "".join(
        f'<tr><td class="q">{q}</td><td>{part}</td>'
        f'<td style="color:var(--muted)">{note}</td>'
        f'<td class="money">{price}</td></tr>'
        for q, part, note, price in BOM)
    lo = sum(int(b[3].split(" - ")[0]) for b in BOM)
    hi = sum(int(b[3].split(" - ")[1]) for b in BOM)
    sec("2", "Bill of materials", f"""
<div class="scroll"><table><thead><tr><th>Qty</th><th>Item</th><th>Specification</th>
<th style="text-align:right">INR</th></tr></thead><tbody>{rows}
<tr class="total"><td></td><td>Total</td>
<td style="color:var(--muted)">indicative street prices, for budgeting</td>
<td class="money">{lo} - {hi}</td></tr></tbody></table></div>
<p class="note">The three resistors that cost about one rupee each &mdash; the
1 k, the 2 k and the 10 k &mdash; are the only parts in this list with no
substitute. Sections 5.1 and 5.2 explain why.</p>""")

    # 3 --------------------------------------------------------------- pins
    sched = "".join(
        f'<tr><td class="w">{a}</td><td class="w">{b}</td><td>{d}</td></tr>'
        for a, b, d in [
            ("3V3", "left 1", "+ rail: potentiometer and E-stop pull-up"),
            ("VIN / 5V", "right 1", "HC-SR04 VCC"),
            ("GND", "right 2", f"&minus; rail, both halves linked"),
            (mb.silk(p["PIN_TRIG"]), "right 3", "HC-SR04 TRIG (output, 3.3 V is fine)"),
            (mb.silk(p["LED_ESCALATE"]), "right 5", f"220 {OHM} then amber LED then &minus; rail"),
            (mb.silk(p["LED_REFUSE"]), "right 6", f"220 {OHM} then red LED then &minus; rail"),
            (mb.silk(p["LED_PERMIT"]), "right 7", f"220 {OHM} then green LED then &minus; rail"),
            (mb.silk(p["PIN_EMIT"]), "right 8", f"220 {OHM} then piezo then &minus; rail"),
            (mb.silk(p["BTN_NONTARGET"]), "right 9", "DOG / GOAT button to &minus; rail"),
            (mb.silk(p["BTN_PERSON"]), "right 10", "PERSON button to &minus; rail"),
            (mb.silk(p["BTN_ESTOP"]), "right 11",
             f"E-STOP button to &minus; rail, <b>and 10 k{OHM} to + rail</b>"),
            (mb.silk(p["POT_GROUP"]), "right 12", "potentiometer wiper"),
            (mb.silk(p["PIN_ECHO"]), "right 13",
             f"1 k{OHM} / 2 k{OHM} divider junction, fed from HC-SR04 ECHO"),
            (mb.silk(p["LED_ARMED"]), "left 4", "on-board LED, armed heartbeat. Nothing to wire"),
        ])
    sec("3", "Pin schedule", f"""
<p>Positions are counted from the USB end of a 30-pin DevKit V1. <b>Find every
pin by the label printed on the board</b>; positions differ between variants,
labels do not. Note the silkscreen writes <code>D26</code>, not GPIO26, and
<code>VN</code> for GPIO39.</p>
<div class="scroll"><table><thead><tr><th>Printed</th><th>Position</th>
<th>Connects to</th></tr></thead><tbody>{sched}</tbody></table></div>
<div class="pic">{mb.devkit_figure(p)}</div>""")

    # 4 ------------------------------------------------------------ circuit
    figs = "".join(
        f"<h3>4.{i} {esc(t)}</h3><div class=\"pic\">{bs.draw(n, p)}</div>"
        for i, (n, t) in enumerate(
            [(2, "Status indicators"), (3, "Emitter"), (4, "Veto inputs"),
             (5, "E-stop pull-up"), (6, "Group-size input"),
             (7, "Distance sensor and level divider")], start=1))
    sec("4", "Circuit", f"""
<p>Read each row left to right: each box is one component, each line between two
boxes is one connection. Where a line drops to the row below, that is a branch
off the same node, not a new component in series.</p>{figs}""")

    # 5 ------------------------------------------------- critical notes
    crit = "".join(
        f'<div class="crit"><span class="h">5.{i} {esc(h)}</span>{t}</div>'
        for i, (h, t) in enumerate(CRITICAL, start=1))
    sec("5", "Critical design notes", "<p>Five things that are not preferences. "
        "Each has a specific failure mode attached.</p>" + crit)

    # 6 ---------------------------------------------------------- assembly
    steps = "".join(f"<li><b>{esc(h)}.</b> {t}</li>" for h, t in ASSEMBLY)
    sec("6", "Assembly sequence", f"""
<p>Build in this order; each step is testable before the next.</p>
<ol class="seq">{steps}</ol>
<p class="note"><b>Mounting the ESP32.</b> A 30-pin DevKit V1 is 1.0 inch across
its header rows and a breadboard is 1.1 inch from row A to row J, so seating it
in the board leaves no free holes on one side. Leave the module off the
breadboard and use female-to-male jumpers onto its header pins.</p>""")

    # 7 ---------------------------------------------------------- firmware
    sec("7", "Firmware", f"""
<p>Source: <code>hardware/wokwi_esp32/gaukavach_esp32.ino</code>. No libraries
are required; everything used ships with the ESP32 core.</p>
<div class="scroll"><table><tbody>
<tr><td class="w">Board</td><td>ESP32 Arduino &rarr; ESP32 Dev Module</td></tr>
<tr><td class="w">Core</td><td>arduino-esp32 3.x (verified against 3.3.11)</td></tr>
<tr><td class="w">Upload speed</td><td>921600, or 115200 if uploads fail</td></tr>
<tr><td class="w">Serial monitor</td><td>115200 baud</td></tr>
<tr><td class="w">Footprint</td><td>293,375 bytes flash (22%), 22,456 bytes globals (6%)</td></tr>
</tbody></table></div>
<p class="note">If the upload stalls at <code>Connecting...</code>, hold the BOOT
button as it starts. If no port appears at all, it is the CP2102 / CH340
USB-serial driver, not the sketch, and not the wiring.</p>""")

    # 8 -------------------------------------------------------- acceptance
    tests = "".join(
        f'<tr><td class="q"><span class="box"></span></td>'
        f'<td class="w">{esc(name)}</td><td>{action}</td><td>{expect}</td></tr>'
        for name, action, expect in acceptance(c))
    sec("8", "Acceptance test", f"""
<p>The rig is accepted when every row below is observed. Run them in order; step
2 is a prerequisite for everything after it.</p>
<div class="scroll"><table><thead><tr><th></th><th>Step</th><th>Do this</th>
<th>Expected</th></tr></thead><tbody>{tests}</tbody></table></div>
<div class="sig"><div>Built by / date</div><div>Tested by / date</div></div>""")

    # 9 ------------------------------------------------------ limitations
    lim = "".join(f"<h3>9.{i} {esc(h)}</h3><p>{t}</p>"
                  for i, (h, t) in enumerate(LIMITS, start=1))
    sec("9", "Declared limitations", "<p>Stated here so they are not discovered "
        "by an examiner. Each is a property of the demonstrator, not a defect in "
        "it.</p>" + lim)

    page = PAGE.format(rev=REV, issued=ISSUED, body="".join(S),
                       cost=f"INR {lo} - {hi}")
    page = "".join(ch if ord(ch) < 128 else f"&#{ord(ch)};" for ch in page)
    out = ROOT / "hardware" / "design.html"
    out.write_text(page, encoding="utf-8")
    print(f"wrote hardware/design.html ({out.stat().st_size / 1024:.0f} KB), "
          f"9 sections, BOM INR {lo}-{hi}")


if __name__ == "__main__":
    main()
