# Bench governor — small-scale hardware demo

A hardware mirror of `src/gaukavach/welfare.py`. Every veto the software
governor applies is enforced *again*, independently, by a microcontroller that
does not trust the host.

**That is the demo.** Not "we made a beeper" — two independent safety layers
that must both agree before a transducer is energised, and either of which can
stop it alone. Judges understand defence in depth immediately.

---

## Read this before you open Tinkercad

**Tinkercad Circuits cannot simulate an ESP32.** It supports Arduino Uno,
ATtiny and micro:bit only — no ESP32, no STM32, no Pico. Searching for an ESP32
part will waste an hour; the ESP32 results you find are 3D models, not
simulatable circuits.

So there are two builds here, with identical topology and identical rules:

| Folder | Board | Simulator | Use it for |
|---|---|---|---|
| [`tinkercad_uno/`](tinkercad_uno/) | Arduino Uno | **Tinkercad Circuits** | building and screen-recording the simulation |
| [`wokwi_esp32/`](wokwi_esp32/) | ESP32 DevKit | **Wokwi** (`diagram.json` included) | your actual board, and envelope ramping |

Wire the Uno version in Tinkercad, then flash the ESP32 version to real
hardware. The pin numbers differ; nothing else does.

---

## Parts (all in the Tinkercad library, all in a basic kit)

| Qty | Part | Role in the demo |
|---:|---|---|
| 1 | Arduino Uno *(or ESP32 on real hardware)* | the governor |
| 1 | HC-SR04 ultrasonic sensor | stands in for the camera: how far is the animal |
| 1 | Piezo buzzer / transducer | the emitter |
| 3 | LED — green, red, amber | PERMIT / REFUSE / ESCALATE |
| 1 | LED — blue | armed heartbeat |
| 4 | Resistor 220 Ω | LED current limit + emitter series |
| 3 | Pushbutton | person present · non-target present · **E-STOP** |
| 1 | Potentiometer 10 kΩ | group size, 1–8 animals |
| 1 | Breadboard + jumpers | |

Optional but worth it on real hardware: an NPN transistor (BC547/2N2222) with a
1 kΩ base resistor to drive the transducer harder than a pin can, and a relay
in the emitter supply so the E-stop cuts **power**, not just signal.

---

## Building it for real? Start here

**[build_steps.html](build_steps.html)** — eight steps, each with its own
breadboard picture. Work already done is faded; what you add in that step is
solid. Two of the steps exist purely to stop you damaging the ESP32, and both
are things most tutorials leave out:

| Step | Why it matters |
|---|---|
| **5 — 10 kΩ pull-up on the E-stop** | GPIO34–39 are input-only with **no internal pull-up**. Without it the E-stop floats and latches mid-demo. |
| **7 — 1 k/2 k divider on ECHO** | HC-SR04 ECHO swings to 5 V; ESP32 GPIOs are **not** 5 V tolerant. Wiring it straight to a pin is how people quietly cook a board. |

Pins are named by their **silkscreen label**, never by counting holes — the
30-pin and 38-pin DevKits order their headers differently.

## Visual wiring diagrams

Open **[wiring.html](wiring.html)** — both boards drawn, colour-coded, with pin
maps and the build steps. Prints cleanly to A4 if you want it on the bench.
Standalone SVGs: [wiring_uno.svg](wiring_uno.svg) ·
[wiring_esp32.svg](wiring_esp32.svg).

Pin numbers in those diagrams are **parsed from the sketches at build time**, so
the picture cannot drift from the firmware. Regenerate after any pin change:

```bash
python tools/make_wiring_diagram.py
```

## Wiring — Arduino Uno (Tinkercad)

| Uno pin | Connects to | Via |
|---|---|---|
| D9 | HC-SR04 **TRIG** | — |
| D10 | HC-SR04 **ECHO** | — |
| 5V / GND | HC-SR04 VCC / GND | — |
| D11 | Piezo **+** | 220 Ω in series; piezo − to GND |
| D5 | Green LED anode | 220 Ω; cathode to GND |
| D6 | Red LED anode | 220 Ω; cathode to GND |
| D7 | Amber LED anode | 220 Ω; cathode to GND |
| D8 | Blue LED anode | 220 Ω; cathode to GND |
| D2 | Pushbutton "PERSON" | other leg to GND (uses `INPUT_PULLUP`) |
| D3 | Pushbutton "DOG/GOAT" | other leg to GND |
| D4 | Pushbutton "E-STOP" | other leg to GND |
| A0 | Potentiometer wiper | ends to 5V and GND |

Buttons use the internal pull-ups, so **pressed = LOW**. No external resistors
needed on the buttons.

### ESP32 pin map (real hardware / Wokwi)

TRIG 13 · ECHO 12 · EMIT 25 · green 26 · red 27 · amber 14 · blue 2 ·
person 32 · non-target 33 · E-stop 35 · pot 34.

> **GPIO35 has no internal pull-up.** Add a 10 kΩ resistor from pin 35 to 3V3
> or the E-stop will float and trigger randomly. The Wokwi diagram already
> includes it.

---

## Build it in Tinkercad in ~15 minutes

1. tinkercad.com → **Circuits** → *Create new Circuit*
2. Drag in: Arduino Uno R3, breadboard, HC-SR04, piezo, 4 LEDs, 4× 220 Ω,
   3 pushbuttons, potentiometer
3. Wire per the table above
4. **Code → Text** (not Blocks), paste
   [`tinkercad_uno/gaukavach_uno.ino`](tinkercad_uno/gaukavach_uno.ino)
5. **Start Simulation**, open **Serial Monitor**
6. Drag the slider on the HC-SR04 to change distance — that is your approaching
   animal

Wokwi is faster if you want the ESP32: create a project, paste the `.ino`, then
paste [`wokwi_esp32/diagram.json`](wokwi_esp32/diagram.json) into the diagram
tab. It wires itself.

---

## The demo script — five presses, ninety seconds

1. **Slide HC-SR04 to ~80 cm.** Green LED. Serial prints
   `PERMITTED @ 28.6 m, attempt 1/3, carrier 25.0 kHz`.
2. **Hold PERSON.** Green dies instantly, red on, emission stops mid-burst:
   *"a person is inside the exposure cone."* Release — it does **not** resume,
   because the quiet period is now running.
3. **Turn the pot past 3.** Red: *"group large enough that a startle could
   cascade."* A flock is a dispatch problem, not an acoustic one.
4. **Slide the sensor very close (under ~34 cm).** Red: *"already at the
   carriageway — fleeing would cross it."* This is the flight-geometry veto:
   the system will not push an animal across the road.
5. **Let it run.** After three attempts the amber LED latches:
   *"ESCALATED → traffic warning + human dispatch."* It gives up rather than
   getting louder.

Then hit **E-STOP** and note that nothing clears it but a reset.

---

## What this rig honestly proves — and what it does not

**Proves:** the distance gate, the four absolute vetoes, the 6 s watchdog, the
enforced quiet period, the daily exposure budget with its do-not-emit latch,
the escalation path, and a hard E-stop — all running on hardware that enforces
them independently of the laptop.

**Does not prove:**

- **Any decibel level.** No calibrated ultrasonic microphone is attached, so any
  SPL claim about this rig would be fabricated. The sketch prints that warning
  at boot so you cannot forget.
- **Any acoustic performance.** A piezo buzzer at 25 kHz is a signal-chain
  stand-in, nothing more.
- **Anything about cattle.** No animal is involved.

### If your transducer is a 40 kHz module

It is the wrong part, and this is worth saying out loud rather than hiding.
HC-SR04-style ultrasonic elements are narrowband resonators at **40 kHz**.
Cattle hearing ends at **35 kHz** — so 40 kHz is inaudible to the target animal
and useless as a deterrent. Driven at 25 kHz, well off resonance, such an
element is also tens of dB down.

Use it as a **signal-chain stand-in** and say so. The right part is a wideband
piezo horn tweeter quoted to 27 kHz — see
[`../docs/HARDWARE.md`](../docs/HARDWARE.md).

### Why the ESP32 sketch is the better one

The Uno's `tone()` is a hard-gated square wave — precisely the waveform our own
spectrum analysis says *not* to radiate, because the rectangular gate splatters
broadband energy into the audible band and the device clicks at every
activation. The ESP32's LEDC peripheral controls duty independently of
frequency, so `emitStart()` ramps the envelope with a raised cosine over 25 ms,
which is the hardware expression of `emitter.py`. Run
`python -m gaukavach spectrum` alongside it: the model predicts ~98 dB less
audible-band energy from exactly that change.

---

## Keeping it honest

The limits in both sketches are copied from `src/gaukavach/evidence.py` and are
listed at the top of each file. If you change one, change both — otherwise the
hardware and the software stop being two views of the same rule set, which is
the entire point of building this.

Demo timers are compressed by `DEMO_SPEED = 10` because nobody will wait 20 s
between bursts on stage. Both sketches print the **real** value next to the
compressed one at boot, so the compression is disclosed rather than hidden.
