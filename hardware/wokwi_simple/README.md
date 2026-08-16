# wokwi_simple - the stripped simulator build

Same firmware, same governor, same demo. Eleven parts instead of seventeen and
twenty-three wires instead of thirty, because every component that exists only
to protect real silicon has been removed.

**profile: simulator-only**

This diagram is NOT a wiring reference for hardware. If you build the physical
rig, use `hardware/wokwi_esp32/diagram.json`, which keeps everything below.

## What this omits, and why it is safe here but not on a bench

| Omitted | Present in the hardware build | Why it can go in a simulator |
| --- | --- | --- |
| 3 x 220 Ω LED series resistors | yes | A simulated GPIO has no current limit to exceed. On real hardware a bare LED across a pin draws whatever the diode will pass and degrades the driver. |
| 1 x 220 Ω buzzer series resistor | yes | A simulated piezo has no inrush. A real one is a capacitive load and pulls a current spike at switch-on. |
| 1 kΩ / 2 kΩ divider on ECHO | yes | Here the sensor runs from **3V3**, so ECHO never exceeds a level the pin accepts. On hardware the sensor is unreliable below 5 V, so it runs at 5 V, and ESP32 GPIOs are **not** 5 V tolerant - hence the divider. |

## What is deliberately kept

The **10 kΩ pull-up on GPIO35**. It is not protection, it is function: GPIO34-39
are input-only and have no internal pull-up anywhere in the silicon, simulated
or otherwise. Without it the E-stop input floats and latches at random.

## Firmware

`sketch.ino` is a byte-for-byte copy of `hardware/wokwi_esp32/gaukavach_esp32.ino`.
The pin map is identical, so nothing about the code knows or cares which of the
two diagrams it is running under. A test enforces the copy stays current.
