"""
Make every shipped HTML page safe to open directly.

    python tools/ascii_pages.py [--check]

WHY
---
These pages are HTML fragments: no <html>, no <head>, because the artifact
host wraps them and supplies the charset. That is fine when they are published
and wrong the moment somebody double-clicks the file, because then the charset
is whatever the browser guesses. It guesses differently per file, so an em dash
becomes three junk glyphs on one page and renders correctly on the next.

A page that looks like that reads as broken, and the reader is not wrong: they
cannot tell mojibake from a page that failed to load.

The fix is to have no bytes above 127 anywhere. Numeric character references
mean the same thing in every encoding, so the page renders identically whether
it is published, served, or opened off the disk with no server at all.

--check exits non-zero instead of writing, for the test suite.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Everything the project hands to a human as a page. Generated pages are listed
# too: their generators already emit ASCII, so they are here as a backstop that
# fails loudly if one ever stops doing that.
PAGES = [
    "dashboard/index.html",
    "dashboard/simulator.html",
    "hardware/bench.html",
    "hardware/handoff.html",
    "hardware/design.html",
    "hardware/breadboard.html",
    "hardware/build_steps.html",
    "hardware/wokwi_steps.html",
    "hardware/wiring.html",
]


def offenders(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for ch in text:
        if ord(ch) > 127:
            out[ch] = out.get(ch, 0) + 1
    return out


def to_ascii(text: str) -> str:
    return "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in text)


def main() -> int:
    check = "--check" in sys.argv
    bad = 0

    for rel in PAGES:
        path = ROOT / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        found = offenders(text)
        if not found:
            print(f"  ok      {rel}")
            continue

        bad += 1
        worst = ", ".join(f"{c!r} x{n}" for c, n in
                          sorted(found.items(), key=lambda kv: -kv[1])[:4])
        if check:
            print(f"  FAIL    {rel}: {sum(found.values())} non-ASCII ({worst})")
        else:
            path.write_text(to_ascii(text), encoding="utf-8")
            print(f"  fixed   {rel}: {sum(found.values())} escaped ({worst})")

    if check and bad:
        print(f"\n{bad} page(s) would render as mojibake when opened directly.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
