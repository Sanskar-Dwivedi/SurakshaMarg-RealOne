# Running it

Three ways to demonstrate this, in order of how likely they are to work in a
room you do not control. Pick one; they show the same rules.

---

## 1. On screen, no hardware — the one to present

Open `hardware/bench.html` and press **Run the demo**. Nine narrated beats,
about a minute, driving itself.

Nothing to install, no cable, no port. Every limit on that page is parsed out
of `hardware/wokwi_esp32/gaukavach_esp32.ino` when the page is generated, so it
enforces the firmware's rules rather than an imitation of them. A test fails if
the two ever disagree.

Regenerate after changing the firmware:

    python tools/make_bench.py

---

## 2. On screen, driving the real board over USB

Web Serial needs a secure origin. A `file://` page is not one and neither is an
embedded frame, but `http://127.0.0.1` is — so the page has to be **served**,
not opened off the disk. That is the only reason the launcher exists.

    cd hardware
    python -m http.server 8765 --bind 127.0.0.1
    # then open http://127.0.0.1:8765/bench.html

Click **Connect the board**, choose the ESP32's COM port, then **Run the demo**.
Chrome or Edge only; Firefox has no Web Serial.

The page sends *inputs* — distance, group size, vetoes. The board reaches its
own verdict from them. Two implementations of one rule set agreeing, not the
screen puppeting the lamps.

---

## 3. The board on its own, typed by hand

The most robust path, and the one to fall back on if anything else misbehaves.

Flash `hardware/wokwi_esp32/gaukavach_esp32.ino` — Board: **ESP32 Dev Module**,
core 3.x, no libraries. Then open the Serial Monitor at **115200** and type:

| Type   | What happens                                    |
| ------ | ----------------------------------------------- |
| `d80`  | detected at 28 m, permitted                      |
| `p`    | person in the cone, refused (type again to clear)|
| `n`    | dog or goat in the cone, refused                 |
| `g5`   | herd of five, refused                            |
| `g1`   | back under the group limit                       |
| `v6`   | six vehicles in the zone, refused                |
| `v0`   | clear road again                                 |
| `d20`  | already at the carriageway, refused              |
| `d160` | beyond the acoustic envelope, refused            |
| `e`    | emergency stop, latched                          |
| `r`    | clear the latches                                |
| `?`    | help                                             |

Leave a target detected for about seven seconds and it escalates on its own.

---

## Only one program may hold the serial port

The Arduino Serial Monitor, a browser tab, and any script all compete for it.
A second one gets `Access is denied` or `Serial port busy`. If **Connect the
board** fails, something else has the port — close that, do not restart
anything else.

This is the single most common way a working rig looks broken.

---

## When parts are missing

The firmware does not assume the rig is complete. Near the top of the sketch:

    #define HAVE_POT      0   // no potentiometer  -> group size typed with g1..g8
    #define HAVE_ESTOP    0   // no working button -> emergency stop typed with e
    #define HAVE_SENSOR   0   // no HC-SR04        -> distance typed with d0..d400
    #define TWO_LAMP_MODE 1   // two working LEDs  -> escalation blinks instead
    #define ONE_LAMP_MODE 0   // one working LED   -> states told apart by rate

Set each to match what is actually soldered. Every one of them prints a line at
boot naming what is simulated, and those lines are meant to be read out loud
before anyone asks:

    DECLARE THIS WHEN YOU DEMONSTRATE:
      the distance input is typed, not sensed
      ...
      the governor rules below are unchanged and are doing the deciding

That last line is the point. Missing parts change the inputs. They do not
change a single rule.

**A floating input is worse than a missing one.** GPIO34-39 have no internal
pull-up anywhere in the silicon, so an unfitted potentiometer does not read
zero, it wanders — and the governor then refuses for a herd size nobody chose,
correctly reasoned from a number that is noise. Turn the flag off rather than
leaving the pin unconnected.

---

## Diagnostics

Under `hardware/wiring_check/`, flash whichever answers the question:

| Sketch            | Answers                                              |
| ----------------- | ---------------------------------------------------- |
| `wiring_check`    | what does every input read, right now                 |
| `pin_probe`       | are any two output pins the same node (a shared column) |
| `find_lamp`       | which pins have working LEDs, on-board LED forced off |
| `count_lamp`      | same, but each pin blinks its own number so the answer is a count, not a position |

`count_lamp` is the one that finally worked. Asking someone to map positions to
colours means holding a sequence in their head while watching a board; asking
"how many times did it blink" is something an eye does by itself.

**A measurement taken through a fault does not survive fixing the fault.** The
LED map here was first read while two GPIOs were shorted into one breadboard
column, so driving either lit the single LED that existed. Once the short was
fixed that reading was false, and hours went into driving a pin with nothing
attached. Re-measure after every repair.

---

## Tests

    python -m pytest tests/ -q

They check the things that fail silently: that the firmware, the diagrams, the
build guides and the on-screen bench all still agree about pin assignments and
governor limits, that no LED in any diagram is reversed, that every wire in the
Wokwi manual is listed exactly once, and that no shipped page contains a byte
above 127 — because these pages are fragments and a browser guessing the
charset renders mojibake, which reads as a broken page.
