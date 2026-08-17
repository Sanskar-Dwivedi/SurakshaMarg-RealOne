"""
Hardware acceptance: drive the real board through every rule it has.

    python tools/hw_acceptance.py --port COM5

WHY THIS EXISTS
---------------
The test suite proves the Python governor and the on-screen bench agree with
the firmware SOURCE. It cannot prove the chip on the desk is running that
source, or that the thing running is wired to anything. Those are different
claims and only the board can settle them.

So this talks to the board over USB, provokes each refusal in turn, and checks
the board's own words came back. It asserts nothing about the lamps, because a
serial port cannot see an LED - the lamp column says which one SHOULD be lit,
for a person watching. That split is deliberate: this script reports what it
can actually observe and labels the rest as needing eyes.

READING A FAILURE
-----------------
A rule that does not fire is not necessarily broken firmware. Check in this
order, because it is the order that has actually caught things here:

  1. Is the governor even running? Send `?`; anything but the console help
     means a different sketch is flashed. That has cost a whole afternoon.
  2. Is the Serial Monitor open? It holds the port exclusively.
  3. Only then suspect the rule.
"""

from __future__ import annotations

import argparse
import sys
import time

# Every refusal the firmware can reach, in the order the veto chain tests them.
# The strings are the firmware's, verbatim; if a rule is reworded there and not
# here, this fails loudly, which is the intent.
RULES: list[tuple[str, list[str], float, str, str]] = [
    # id            setup commands        secs  expected fragment            lamp
    ("person",      ["d25", "p"],          4.0, "a person is inside the exposure cone",       "RED"),
    ("non-target",  ["d25", "n"],          4.0, "a non-target species is inside the cone",    "RED"),
    ("herd",        ["d25", "g5"],         4.0, "group large enough that a startle could",    "RED"),
    ("out-of-range", ["d55"],              4.0, "beyond the acoustic envelope",               "YELLOW"),
    ("carriageway", ["d6"],                4.0, "already at the carriageway",                 "RED"),
    ("permitted",   ["d25"],               4.0, "PERMITTED",                                  "GREEN"),
]


def drain(ser, secs: float) -> list[str]:
    out, end = [], time.time() + secs
    while time.time() < end:
        ln = ser.readline().decode("utf-8", "replace").rstrip()
        if ln:
            out.append(ln)
    return out


def send(ser, cmd: str) -> None:
    ser.write((cmd + "\n").encode())
    ser.flush()
    time.sleep(0.25)


def reset(ser) -> None:
    """
    Return the board to a known state between rules.

    `r` clears the latches and the distance override but NOT the typed group
    size, so `g1` is sent explicitly. Found the hard way: `g5` from the herd
    rule leaked into every rule after it, the herd veto out-ranked them in the
    chain, and three good rules reported as broken.

    Anything driving this console has the same problem - group size is
    write-only, so a driver that assumes `r` cleared it is wrong from that
    point on. See the note in the report.
    """
    send(ser, "r")
    send(ser, "g1")
    time.sleep(0.6)
    ser.reset_input_buffer()


def identify(ser) -> bool:
    ser.reset_input_buffer()
    send(ser, "?")
    lines = drain(ser, 2.5)
    return any("g1..g8" in ln for ln in lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", default="COM5")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--budget", action="store_true",
                    help="also exhaust the daily budget (slow: needs 60 s of emission)")
    args = ap.parse_args()

    try:
        import serial
    except ImportError:
        print("pyserial is not installed")
        return 2

    ser = serial.Serial()
    ser.port, ser.baudrate, ser.timeout = args.port, args.baud, 0.2
    ser.dtr = False
    ser.rts = False
    try:
        ser.open()
    except Exception as exc:
        print(f"cannot open {args.port}: {exc}")
        print("The Arduino Serial Monitor holds the port exclusively - close it.")
        return 2
    time.sleep(1.5)

    print(f"GauKavach hardware acceptance on {args.port}")
    print("=" * 70)
    if not identify(ser):
        print("FAIL  the board did not answer '?' with the governor console.")
        print("      Something else is flashed. Nothing below would mean anything.")
        ser.close()
        return 1
    print("ok    governor firmware is running and answering on the console")
    print()
    print(f"{'rule':<14}{'result':<8}{'lamp':<8}what the board said")
    print("-" * 70)

    failures = 0
    for name, setup, secs, expect, lamp in RULES:
        reset(ser)
        for cmd in setup:
            send(ser, cmd)
        lines = drain(ser, secs)
        hit = next((ln.strip() for ln in lines if expect.lower() in ln.lower()), None)
        if hit:
            print(f"{name:<14}{'ok':<8}{lamp:<8}{hit[:60]}")
        else:
            failures += 1
            last = lines[-1].strip()[:52] if lines else "(silence)"
            print(f"{name:<14}{'FAIL':<8}{lamp:<8}expected {expect!r}; last was {last}")

    # -- the two rules that are about time, not geometry ---------------------

    reset(ser)
    send(ser, "d25")
    lines = drain(ser, 12.0)
    quiet = any("enforced quiet period" in ln for ln in lines)
    watchdog = any("WATCHDOG" in ln for ln in lines)
    print(f"{'quiet-period':<14}{'ok' if quiet else 'FAIL':<8}{'-':<8}"
          f"{'silence is enforced between bursts' if quiet else 'never entered cooldown'}")
    print(f"{'watchdog':<14}{'ok' if watchdog else 'FAIL':<8}{'-':<8}"
          f"{'emission self-terminated' if watchdog else 'no max-activation cut'}")
    failures += (not quiet) + (not watchdog)

    reset(ser)
    send(ser, "d25")
    lines = drain(ser, 22.0)
    escalated = any("ESCALATED" in ln for ln in lines)
    print(f"{'escalation':<14}{'ok' if escalated else 'FAIL':<8}{'RED blink':<8}"
          f"{'gave up and asked for a human' if escalated else 'never escalated'}")
    failures += not escalated

    reset(ser)
    send(ser, "e")
    lines = drain(ser, 3.0)
    estop = any("E-STOP" in ln.upper() for ln in lines)
    print(f"{'e-stop':<14}{'ok' if estop else 'FAIL':<8}{'all off':<8}"
          f"{'latched dead until reset' if estop else 'did not latch'}")
    failures += not estop
    reset(ser)

    # -- the live sensor, which no typed command can stand in for ------------

    send(ser, "r")
    time.sleep(0.5)
    ser.reset_input_buffer()
    lines = drain(ser, 5.0)
    sensor = any("DETECTION" in ln or "REFUSED" in ln or "PERMITTED" in ln for ln in lines)
    print(f"{'live sensor':<14}{'ok' if sensor else 'none':<8}{'-':<8}"
          f"{'HC-SR04 is producing ranges' if sensor else 'quiet - nothing in front of it'}")

    if args.budget:
        print()
        print("Exhausting the daily budget. This needs 60 s of real emission,")
        print("so it takes a few minutes of repeated permits.")
        reset(ser)
        seen = False
        end = time.time() + 240
        while time.time() < end and not seen:
            send(ser, "d25")
            for ln in drain(ser, 20.0):
                if "do-not-emit list" in ln:
                    seen = True
                    break
            send(ser, "d80")          # let it re-acquire
            drain(ser, 1.0)
        print(f"{'daily-budget':<14}{'ok' if seen else 'FAIL':<8}{'RED':<8}"
              f"{'budget exhausted, emitter locked out' if seen else 'never exhausted'}")
        failures += not seen
        reset(ser)

    ser.close()
    print("-" * 70)
    print(f"{'ALL RULES PASSED' if not failures else str(failures) + ' RULE(S) FAILED'}")
    print()
    print("The lamp column is what a person should SEE. A serial port cannot")
    print("observe an LED, so this script never claims a lamp lit - watch the")
    print("board, or flash hardware/wiring_check/count_lamp.ino to test pins.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
