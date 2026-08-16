# ESP32 on Wokwi — one-click simulation

**Tinkercad cannot do this one at all.** Tinkercad Circuits simulates Arduino
Uno, ATtiny and micro:bit only — there is no ESP32, and there is no circuit
import either. Wokwi has both.

## Two minutes, start to running

1. **wokwi.com** → *New Project* → choose **ESP32**
2. Open the **`diagram.json`** tab, select all, delete, paste
   [`diagram.json`](diagram.json). The circuit wires itself.
3. Open **`sketch.ino`**, paste [`sketch.ino`](sketch.ino)
4. Press **▶**, open the serial monitor at **115200**

## What this file already gets right

Both ESP32 traps are wired in, and both are things tutorials routinely omit:

| Circuit | Why it is there |
|---|---|
| **10 kΩ from GPIO35 to 3V3** | GPIO34–39 are input-only with **no internal pull-up in the silicon**. Without it the E-stop floats and latches at random. |
| **1 kΩ / 2 kΩ divider on ECHO** | HC-SR04 ECHO swings to 5 V and ESP32 GPIOs are **not** 5 V tolerant. The divider brings it to ~3.3 V. |

Also correct: 220 Ω on all three status LEDs and the emitter, pot on **3V3**
(not 5 V — the ADC is not 5 V tolerant), and the ARMED heartbeat on GPIO2,
which is the LED already on the DevKit.

## Why the ESP32 version is the better demo

The Uno's `tone()` is a hard-gated square wave — exactly the waveform our own
spectrum analysis says not to radiate, because a rectangular gate splatters
broadband energy into the audible band. The ESP32's LEDC peripheral controls
duty independently of frequency, so `emitStart()` ramps the envelope with a
raised cosine over 25 ms. That is `emitter.py` expressed in hardware.

Run `python -m gaukavach spectrum` next to it: the model predicts roughly 98 dB
less audible-band energy from that one change.

## "The red LED is stuck on"

It probably is not stuck &mdash; it is refusing, and the sketch says why. Open the
serial monitor at **115200**; the reason prints every 800 ms.

| Log line | Fix |
|---|---|
| `group large enough that a startle could cascade` | turn the **pot down**; anything above 3 is a permanent herd veto |
| `a person is inside the exposure cone` | release the PERSON button |
| `E-STOP LATCHED` | only a restart clears it, by design |
| `already at the carriageway` | drag the HC-SR04 distance **up**, above ~34 cm |

A steady red with no serial output at all means the board is not running &mdash;
check the sketch actually built.

## ECHO is `esp:VN`, not `esp:39`

Wokwi addresses GPIO36 and GPIO39 by their silkscreen aliases **VP** and **VN**.
Write `esp:39` and Wokwi does not complain - it just silently drops the wire.
ECHO then never reaches the MCU, `pulseIn` times out, the sketch sits in IDLE
and every LED stays dark while the circuit looks perfectly correct on screen.

Verified in the browser: with `esp:39` all three LEDs read brightness 0; with
`esp:VN` the sequence runs properly. A test now rejects any ESP32 pin name
Wokwi will not accept.

## Pin choices avoid the strapping pins

GPIO 0, 2, 5, 12 and 15 are sampled at reset. **ECHO is on GPIO39 (VN)**, not
GPIO12: 12 is MTDI, and if it is high at boot the ESP32 selects 1.8 V flash and
may not start. GPIO39 is input-only, which is all ECHO needs. GPIO2 is the one
deliberate exception &mdash; it is the on-board LED, driven as an output only.

## Driving it

Click the HC-SR04 while it runs and drag the distance slider.

| Do this | You should see |
|---|---|
| Distance ~80 cm | green LED, `PERMITTED @ 28.6 m ... ramped 25 ms` |
| Hold **PERSON** | emission stops mid-burst, red LED, reason logged |
| Pot past 3 | refused for herd size |
| Distance under ~34 cm | refused: fleeing would cross the carriageway |
| Wait it out | amber latches, `ESCALATED` |
| Press **E-STOP** | dead until reset |

## Core 2.x and 3.x both work

The LEDC API changed between Arduino-ESP32 core 2.x and 3.x: `ledcSetup()` and
`ledcAttachPin()` were removed, and `ledcWrite()` now takes a **pin** instead of
a channel. Wokwi builds against **3.x**; most local Arduino IDE installs are
still on **2.x**.

The sketch picks the right one at compile time via `ESP_ARDUINO_VERSION_MAJOR`,
so the same file works in both places with nothing to edit. A test compiles it
against stubs of *both* APIs on every run — this was a real build failure once,
and it is not allowed to happen twice.

## Flashing the real board

Same `sketch.ino`, Arduino IDE, board **ESP32 Dev Module**. Wire it per
[`../build_steps.html`](../build_steps.html) — eight steps, one picture each.
