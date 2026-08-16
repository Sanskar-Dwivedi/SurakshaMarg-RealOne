"""
The sketches must compile - on every core they claim to support.

Added after a real failure: the ESP32 sketch used the Arduino-ESP32 core 2.x
LEDC API (`ledcSetup`/`ledcAttachPin`), Wokwi builds against core 3.x where
those were removed, and nobody found out until the simulator refused to build.

A syntax-only compile against stubbed headers catches that in under a second.
It proves the sketch COMPILES, not that it behaves; behaviour is asserted in
test_firmware_consistency.py.

Skipped cleanly when no C++ compiler is on PATH, so this never blocks anyone.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STUB_DIR = Path(__file__).resolve().parent
UNO = ROOT / "hardware" / "tinkercad_uno" / "gaukavach_uno.ino"
ESP = ROOT / "hardware" / "wokwi_esp32" / "gaukavach_esp32.ino"
ESP_COPY = ROOT / "hardware" / "wokwi_esp32" / "sketch.ino"
UNO_COPY = ROOT / "hardware" / "wokwi_uno" / "sketch.ino"

CXX = shutil.which("g++") or shutil.which("clang++")
needs_cxx = pytest.mark.skipif(CXX is None, reason="no C++ compiler on PATH")


def _compile(source: str, defines: list[str]) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as td:
        cpp = Path(td) / "sketch_check.cpp"
        cpp.write_text('#include "arduino_stub.h"\n' + source, encoding="utf-8")
        cmd = [CXX, "-std=gnu++17", "-fsyntax-only", "-Wall",
               f"-I{STUB_DIR}", *[f"-D{d}" for d in defines], str(cpp)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode == 0, r.stderr


@needs_cxx
@pytest.mark.parametrize("core,defines", [("2.x", []), ("3.x", ["FAKE_CORE3"])],
                         ids=["esp32-core2", "esp32-core3"])
def test_esp32_sketch_compiles_on_both_cores(core: str, defines: list[str]):
    """Wokwi ships core 3.x; most local Arduino IDE installs are on 2.x."""
    ok, err = _compile(ESP.read_text(encoding="utf-8"), defines)
    assert ok, f"ESP32 sketch fails to compile on core {core}:\n{err}"


@needs_cxx
@pytest.mark.parametrize("mode", [0, 1], ids=["uno-hcsr04", "uno-pot-distance"])
def test_uno_sketch_compiles_in_both_distance_modes(mode: int):
    """DISTANCE_FROM_POT swaps the HC-SR04 for a knob; both paths must build."""
    src = UNO.read_text(encoding="utf-8").replace(
        "#define DISTANCE_FROM_POT 0", f"#define DISTANCE_FROM_POT {mode}")
    ok, err = _compile(src, [])
    assert ok, f"Uno sketch fails to compile with DISTANCE_FROM_POT={mode}:\n{err}"


@needs_cxx
def test_esp32_sketch_uses_no_raw_ledc_call_outside_the_shim():
    """
    Every LEDC call must go through emitAttach/emitDuty.

    A stray ledcWrite(LEDC_CH, ...) compiles fine on core 2.x and breaks on 3.x,
    which is exactly the failure this file exists to prevent.
    """
    lines = ESP.read_text(encoding="utf-8").splitlines()
    start = next(i for i, l in enumerate(lines) if "LEDC portability shim" in l)
    end = next(i for i, l in enumerate(lines[start:], start) if l.strip() == "#endif")
    outside = [
        l.strip() for i, l in enumerate(lines)
        if not (start <= i <= end)
        and any(c in l for c in ("ledcWrite(", "ledcSetup(", "ledcAttachPin(", "ledcAttach("))
        and not l.strip().startswith("*")
    ]
    assert not outside, "raw LEDC calls outside the shim:\n" + "\n".join(outside)


SIMPLE_COPY = ROOT / "hardware" / "wokwi_simple" / "sketch.ino"


@pytest.mark.parametrize("original,copy",
                         [(ESP, ESP_COPY), (UNO, UNO_COPY), (ESP, SIMPLE_COPY)],
                         ids=["esp32", "uno", "esp32-simple"])
def test_wokwi_sketch_copies_are_current(original: Path, copy: Path):
    """
    Wokwi wants the file called sketch.ino. Those copies must not go stale, or
    the simulator quietly runs old firmware while the repo shows new.
    """
    assert copy.is_file(), f"missing {copy}"
    assert copy.read_text(encoding="utf-8") == original.read_text(encoding="utf-8"), (
        f"{copy.relative_to(ROOT)} has drifted from "
        f"{original.relative_to(ROOT)} - re-copy it"
    )
