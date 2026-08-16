# Wokwi — one-click simulation

**Tinkercad Circuits has no import.** There is no file you can upload that
builds a circuit there; STL/OBJ/SVG go to the 3D editor, not to Circuits. You
have to drag every part by hand.

Wokwi does what you actually want, is free, needs no account to try, and
simulates the same sketch.

## Two minutes, start to running

1. Go to **wokwi.com** → *New Project* → **Arduino Uno**
2. Click the **`diagram.json`** tab, select all, delete, and paste
   [`diagram.json`](diagram.json) from this folder. The circuit wires itself.
3. Click the **`sketch.ino`** tab and paste [`sketch.ino`](sketch.ino)
4. Press **▶** and open the serial monitor at **9600**

For the ESP32 version do the same but pick **ESP32** as the board and use the
files in [`../wokwi_esp32/`](../wokwi_esp32/).

## What is already correct in this file

Everything the screenshot of the hand-built Tinkercad circuit was missing:

- **HC-SR04 fitted** on D9/D10 — without it the sketch idles forever and no LED
  ever lights
- **220 Ω in series with all four LEDs and the piezo**
- LED cathodes to **GND**, not to another pin
- Button far legs to **GND**, matching `INPUT_PULLUP` (pressed reads LOW)
- Pot outers to 5 V and GND, wiper to A0

## Driving it

Click the HC-SR04 in the running simulation and drag its distance slider — that
is your approaching animal. Then:

| Do this | You should see |
|---|---|
| Distance ~80 cm | green LED, `PERMITTED @ 28.6 m` |
| Hold **PERSON** | emission stops mid-burst, red LED, reason in the log |
| Pot past 3 | refused for herd size |
| Distance under ~34 cm | refused: fleeing would cross the carriageway |
| Wait it out | amber latches, `ESCALATED` |
| Press **E-STOP** | dead until reset |

## If you must stay in Tinkercad

Build it by hand from [`../build_steps.html`](../build_steps.html), or set
`#define DISTANCE_FROM_POT 1` at the top of the sketch and wire a second pot to
**A1** instead of the HC-SR04. Fewer parts, and a knob is easier to drive on
stage than a sensor slider. Say "the distance input is a knob" when you show it.
