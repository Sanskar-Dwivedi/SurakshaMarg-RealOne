"""
Generate the one-page hardware BOM as a PDF.

    python tools/make_hardware_pdf.py

Everything here is drawn with matplotlib primitives rather than plt.table,
because the default table renderer cannot do column alignment, tier grouping or
tabular figures, and a costing sheet that does not line up its digits is hard to
read and easy to distrust.

Prices are indicative Indian street prices, held in ITEMS below so they are
edited in one place. The link-budget column is not decoration: it is why a
cheap part is defensible, and it comes from the same acoustics module the CLI
uses.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

# --- identity, matching the rest of the project ---------------------------
INK = "#0F141A"
BODY = "#28323C"
MUTED = "#5D6B79"
FAINT = "#8695A3"
LINE = "#D2DAE1"
RULE = "#B6C2CC"
ACCENT = "#0E7C86"
ACC_SOFT = "#DBEDEF"
OK = "#1C7A4B"
WARN = "#93670A"
WARN_BG = "#F8EFD8"
CRIT = "#A9291F"
CRIT_BG = "#F8E4E2"
SURF2 = "#F5F8FA"

SERIF = "DejaVu Serif"
SANS = "DejaVu Sans"
MONO = "DejaVu Sans Mono"


@dataclass
class Item:
    name: str
    spec: str
    qty: int
    lo: int
    hi: int

    @property
    def tlo(self) -> int:
        return self.qty * self.lo

    @property
    def thi(self) -> int:
        return self.qty * self.hi


TIERS: list[tuple[str, str, str, list[Item]]] = [
    ("TIER 0", "Present today", "Laptop and a browser. Decision layer, real footage, outcome model.", [
        Item("Laptop + browser", "opens simulator.html, no server needed", 1, 0, 0),
        Item("Python 3.10+ and repo", "optional: proves the browser isn't faking it", 1, 0, 0),
    ]),
    ("TIER 1", "Bench emitter", "Produces a genuine 22-27 kHz carrier. Claims no decibels.", [
        Item("USB audio interface", "192 kHz sample rate (not 48 kHz)", 1, 9000, 14000),
        Item("Piezo horn tweeter", "KSN1005A class, quoted 2.2k-27 kHz", 4, 400, 900),
        Item("Class-AB amplifier module", "real response at 27 kHz", 1, 800, 2000),
        Item("Heterodyne bat detector", "20-40 kHz; makes it audible to the room", 1, 3000, 6000),
        Item("ESP32 + relay module", "hardware watchdog, hazard H23", 1, 700, 1500),
        Item("E-stop mushroom switch", "de-energises the amplifier", 1, 300, 800),
        Item("12 V PSU", "bench supply for the amp", 1, 600, 1200),
        Item("Resistors, wiring, enclosure", "series R: piezos are a capacitive load", 1, 300, 300),
    ]),
    ("TIER 2", "Measurement", "Where predictions become measurements. Highest value per rupee.", [
        Item("Dodotronic UltraMic 192K EVO", "EUR 180 ex-works; landed incl. duty", 1, 17000, 22000),
        Item("Tripod + boom arm", "repeatable mic placement", 1, 1500, 3000),
        Item("Laser distance meter", "SPL-vs-distance needs real distances", 1, 500, 2000),
        Item("Audacity / REW", "free analysis software", 1, 0, 0),
    ]),
    ("TIER 3", "Field prototype", "Nothing here runs near an animal without ethics approval.", [
        Item("Directional horn / tweeter array", "the +12 dB the link budget assumes", 1, 8000, 25000),
        Item("Fixed IP66 camera", "1080p, must not move", 1, 3000, 8000),
        Item("Rigid pole mount", "calibration is void if the mount sways", 1, 3000, 6000),
        Item("Edge compute", "Pi 5 + Hailo-8L, or Jetson Orin Nano", 1, 18000, 45000),
        Item("Solar + MPPT + battery", "event-triggered duty cycle", 1, 12000, 30000),
        Item("Enclosure, cable, surge protection", "monsoon", 1, 6000, 15000),
        Item("Calibration checkerboard", "printed; distances are fiction without it", 1, 200, 200),
        Item("Contingency", "there is always contingency", 1, 5000, 15000),
    ]),
]

NOT_PURCHASABLE = [
    ("Animal ethics approval (IAEC)", "weeks of lead time", "blocks all animal exposure"),
    ("Veterinary supervision", "per trial", "required for formal trials"),
    ("Road authority permission", "per site", "required near any carriageway"),
]

TRAPS = [
    ("40 kHz modules are the WRONG part",
     "HC-SR04 and every hobby ultrasonic module is a narrowband 40 kHz resonator. "
     "Cattle hearing ends at 35 kHz, so it is inaudible to the animal and useless. "
     "Buy wideband piezo horn tweeters quoted to 27 kHz."),
    ("Most amplifiers stop where we start",
     "Audio amps target a 20 kHz ceiling and many class-D modules roll off hard "
     "just above it. Check the datasheet at 27 kHz."),
    ("A phone cannot measure this",
     "Phone mics are low-passed below 20 kHz. Any decibel figure quoted without a "
     "calibrated ultrasonic microphone is fabricated."),
]


def rupees(n: int) -> str:
    if n == 0:
        return "-"
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return "₹" + s


def rng(lo: int, hi: int) -> str:
    if lo == 0 and hi == 0:
        return "included"
    if lo == hi:
        return rupees(lo)
    return f"{rupees(lo)}–{rupees(hi)}"


def link_budget_rows():
    """Watts needed from a 94 dB/W/m tweeter, straight from the acoustics module."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from gaukavach import evidence as ev
    from gaukavach.acoustics import Atmosphere, link_budget

    atm = Atmosphere(temp_c=32.0, rh_pct=60.0, ambient_spl_db=58.0)
    cap = ev.get("osha_ultrasound_ceiling_db")
    out = []
    for d in (10, 15, 25, 40):
        need = link_budget(22000.0, float(d), atm, directivity_gain_db=12.0).required_at_1m_db
        out.append((d, need, 10 ** ((need - 94.0) / 10.0), cap - need))
    return out, cap


# --------------------------------------------------------------------------


def text(ax, x, y, s, size=8, color=BODY, family=SANS, weight="normal", ha="left", va="baseline"):
    ax.text(x, y, s, size=size, color=color, family=family, weight=weight,
            ha=ha, va=va, transform=ax.transAxes)


def band(ax, y, h, color, x=0.0, w=1.0, alpha=1.0, ec="none"):
    ax.add_patch(Rectangle((x, y), w, h, transform=ax.transAxes,
                           facecolor=color, edgecolor=ec, alpha=alpha, lw=0.7, zorder=0))


def hline(ax, y, color=LINE, lw=0.8, x0=0.0, x1=1.0):
    ax.plot([x0, x1], [y, y], transform=ax.transAxes, color=color, lw=lw, zorder=1)


def page(fig):
    ax = fig.add_axes([0.055, 0.045, 0.89, 0.90])
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    return ax


def build(out_path: str = "docs/GauKavach_Hardware_BOM.pdf") -> str:
    lb_rows, cap = link_budget_rows()
    grand_lo = sum(i.tlo for _, _, _, items in TIERS for i in items)
    grand_hi = sum(i.thi for _, _, _, items in TIERS for i in items)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(out_path) as pdf:
        # ================= PAGE 1 =================
        fig = plt.figure(figsize=(8.27, 11.69))  # A4 portrait
        fig.patch.set_facecolor("white")
        ax = page(fig)
        y = 1.0

        text(ax, 0, y, "GAUKAVACH", size=8.5, color=ACCENT, family=MONO, weight="bold")
        y -= 0.021
        text(ax, 0, y, "Hardware bill of materials", size=19, color=INK, family=SERIF)
        text(ax, 1.0, y, "one page · all tiers", size=8, color=FAINT, family=MONO, ha="right")
        y -= 0.017
        text(ax, 0, y,
             "Ordered by what each purchase lets you honestly claim. Indicative Indian street prices.",
             size=8.5, color=MUTED)
        y -= 0.014
        hline(ax, y, RULE, 1.2)
        y -= 0.028

        # ---- summary strip
        band(ax, y - 0.052, 0.052, SURF2, ec=LINE)
        cells = [
            ("DEMO TODAY", "₹0", OK),
            ("BENCH EMITTER", rng(16300, 29400), INK),
            ("+ MEASUREMENT", rng(19000, 27000), ACCENT),
            ("+ FIELD RIG", rng(55200, 144200), MUTED),
            ("ALL TIERS", rng(grand_lo, grand_hi), INK),
        ]
        xs = [0.012, 0.205, 0.395, 0.585, 0.988]
        for i, (k, v, col) in enumerate(cells):
            last = i == len(cells) - 1
            ha = "right" if last else "left"
            text(ax, xs[i], y - 0.019, k, size=6.3, color=FAINT, family=MONO, ha=ha)
            text(ax, xs[i], y - 0.040, v, size=9.4, color=col, family=MONO,
                 weight="bold", ha=ha)
        y -= 0.075

        # ---- tier tables
        COL_SPEC, COL_QTY, COL_UNIT = 0.300, 0.680, 0.840
        for tag, title, blurb, items in TIERS:
            tlo = sum(i.tlo for i in items)
            thi = sum(i.thi for i in items)

            band(ax, y - 0.030, 0.030, ACC_SOFT, ec=ACCENT)
            text(ax, 0.010, y - 0.021, tag, size=7.2, color=ACCENT, family=MONO, weight="bold")
            text(ax, 0.088, y - 0.021, title, size=10, color=INK, family=SERIF, weight="bold")
            text(ax, 0.310, y - 0.021, blurb, size=7.4, color=MUTED)
            sub = "₹0" if (tlo == 0 and thi == 0) else rng(tlo, thi)
            text(ax, 0.99, y - 0.021, sub, size=9, color=INK, family=MONO,
                 weight="bold", ha="right")
            y -= 0.038

            text(ax, 0.010, y, "ITEM", size=6.2, color=FAINT, family=MONO)
            text(ax, COL_SPEC, y, "WHAT MATTERS", size=6.2, color=FAINT, family=MONO)
            text(ax, COL_QTY, y, "QTY", size=6.2, color=FAINT, family=MONO, ha="right")
            text(ax, COL_UNIT, y, "UNIT", size=6.2, color=FAINT, family=MONO, ha="right")
            text(ax, 0.99, y, "LINE TOTAL", size=6.2, color=FAINT, family=MONO, ha="right")
            y -= 0.008
            hline(ax, y, RULE, 0.9)
            y -= 0.016

            for it in items:
                text(ax, 0.010, y, it.name, size=8, color=INK)
                text(ax, COL_SPEC, y, it.spec, size=7, color=MUTED)
                text(ax, COL_QTY, y, str(it.qty), size=7.6, color=BODY, family=MONO, ha="right")
                text(ax, COL_UNIT, y, rng(it.lo, it.hi), size=7.6, color=BODY,
                     family=MONO, ha="right")
                text(ax, 0.99, y, rng(it.tlo, it.thi), size=7.8, color=INK,
                     family=MONO, ha="right")
                y -= 0.0175
                hline(ax, y + 0.006, LINE, 0.5)
            y -= 0.016

        # ---- grand total
        band(ax, y - 0.032, 0.032, INK)
        text(ax, 0.012, y - 0.021, "EVERYTHING, TIER 0 THROUGH 3", size=7.5,
             color="white", family=MONO, weight="bold")
        text(ax, 0.99, y - 0.021, rng(grand_lo, grand_hi), size=11, color="white",
             family=MONO, weight="bold", ha="right")
        y -= 0.048

        text(ax, 0, y, "Not purchasable, and required before any animal is exposed",
             size=9.5, color=INK, family=SERIF, weight="bold")
        y -= 0.020
        for name, lead, why in NOT_PURCHASABLE:
            text(ax, 0.012, y, "•", size=8, color=CRIT)
            text(ax, 0.032, y, name, size=8, color=INK)
            text(ax, 0.40, y, lead, size=7.4, color=MUTED, family=MONO)
            text(ax, 0.60, y, why, size=7.4, color=MUTED)
            y -= 0.017

        text(ax, 0, 0.008,
             "GauKavach hardware BOM · prices indicative, verify before purchase · "
             "no hardware currently exists; every figure is a plan, not a receipt",
             size=6.4, color=FAINT, family=MONO)
        pdf.savefig(fig, facecolor="white")
        plt.close(fig)

        # ================= PAGE 2 =================
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.patch.set_facecolor("white")
        ax = page(fig)
        y = 1.0

        text(ax, 0, y, "GAUKAVACH", size=8.5, color=ACCENT, family=MONO, weight="bold")
        y -= 0.021
        text(ax, 0, y, "Why a cheap part is the right part", size=19, color=INK, family=SERIF)
        y -= 0.017
        text(ax, 0, y, "Buying decisions checked against the project's own acoustics model.",
             size=8.5, color=MUTED)
        y -= 0.014
        hline(ax, y, RULE, 1.2)
        y -= 0.034

        # ---- chosen part
        text(ax, 0, y, "The emitter: piezo horn tweeter, KSN1005A class",
             size=11, color=INK, family=SERIF, weight="bold")
        y -= 0.024
        specs = [
            ("Frequency response", "4 kHz – 27 kHz", "covers 22–27 kHz. Does NOT reach 30 kHz."),
            ("Sensitivity", "94 dB SPL @ 1 W / 1 m", "drives the watt column below"),
            ("Power handling", "50 W RMS", "maxes out at 111 dB @ 1 m"),
            ("Unit price", "₹400–900", "an array of four is affordable"),
        ]
        for k, v, note in specs:
            text(ax, 0.012, y, k, size=8, color=MUTED)
            text(ax, 0.30, y, v, size=8, color=INK, family=MONO, weight="bold")
            text(ax, 0.56, y, note, size=7.4, color=MUTED)
            y -= 0.0175
        y -= 0.014

        # ---- link budget table
        band(ax, y - 0.026, 0.026, SURF2, ec=LINE)
        text(ax, 0.012, y - 0.018,
             "LINK BUDGET AT 22 kHz, +12 dB HORN, ON THIS EXACT PART",
             size=7.2, color=ACCENT, family=MONO, weight="bold")
        y -= 0.036
        for lbl, xx in (("TARGET", 0.09), ("NEED @ 1 m", 0.34), ("WATTS", 0.56),
                        ("HEADROOM UNDER CEILING", 0.99)):
            text(ax, xx, y, lbl, size=6.2, color=FAINT, family=MONO, ha="right")
        y -= 0.008
        hline(ax, y, RULE, 0.9)
        y -= 0.017
        for d, need, w, head in lb_rows:
            text(ax, 0.09, y, f"{d} m", size=8, color=INK, family=MONO, ha="right")
            text(ax, 0.34, y, f"{need:.1f} dB", size=8, color=BODY, family=MONO, ha="right")
            text(ax, 0.56, y, f"{w:.2f} W", size=8.4, color=ACCENT, family=MONO,
                 weight="bold", ha="right")
            text(ax, 0.99, y, f"{head:.1f} dB", size=8, color=OK, family=MONO, ha="right")
            y -= 0.019
        y -= 0.006
        text(ax, 0.012, y,
             "A single commodity tweeter on half a watt covers the realistic engagement range.",
             size=8, color=BODY)
        y -= 0.030

        # ---- safety property
        band(ax, y - 0.070, 0.070, CRIT_BG, ec=CRIT)
        text(ax, 0.014, y - 0.019, "SAFETY PROPERTY YOU GET FOR FREE", size=6.8,
             color=CRIT, family=MONO, weight="bold")
        text(ax, 0.014, y - 0.038,
             "Reaching the 142 dB the prototype paper reported would need 63,000 W from this",
             size=8, color=INK)
        text(ax, 0.014, y - 0.053,
             "tweeter — 1,262× its 50 W rating. The hardware physically cannot produce the",
             size=8, color=INK)
        text(ax, 0.014, y - 0.065,
             "exposure the governor refuses. Software says no; hardware could not comply anyway.",
             size=8, color=INK)
        y -= 0.092

        # ---- traps
        text(ax, 0, y, "Three traps before you spend anything",
             size=11, color=INK, family=SERIF, weight="bold")
        y -= 0.024
        for i, (head, body) in enumerate(TRAPS, 1):
            words, lines, cur = body.split(), [], ""
            for w in words:
                if len(cur) + len(w) + 1 > 96:
                    lines.append(cur)
                    cur = w
                else:
                    cur = (cur + " " + w).strip()
            lines.append(cur)
            # Height follows the text, so nothing is silently clipped.
            h = 0.026 + len(lines) * 0.0135
            band(ax, y - h, h, WARN_BG, ec=WARN)
            text(ax, 0.014, y - 0.019, f"{i}.  {head}", size=8.6, color=INK, weight="bold")
            for j, ln in enumerate(lines):
                text(ax, 0.014, y - 0.033 - j * 0.0135, ln, size=7.3, color=BODY)
            y -= h + 0.011

        y -= 0.006
        text(ax, 0, y, "Recommendation for a two-day deadline",
             size=11, color=INK, family=SERIF, weight="bold")
        y -= 0.022
        rec = [
            "Do not buy the emitter. You cannot validate it in two days, and an unmeasured",
            "transducer converts your strongest asset — the honesty of the evidence envelope —",
            "into your weakest prop. If you want something physical, buy the bat detector",
            "(₹3,000–6,000, same-day in most metros): it makes the inaudible audible to the room,",
            "and every word you say about it is true. Present this sheet as the roadmap slide.",
        ]
        for ln in rec:
            text(ax, 0.012, y, ln, size=8, color=BODY)
            y -= 0.0155

        text(ax, 0, 0.008,
             "Sources: CTS/GRS piezo datasheets · dodotronic.com · link budget computed by "
             "gaukavach.acoustics · no hardware has been purchased or tested",
             size=6.4, color=FAINT, family=MONO)
        pdf.savefig(fig, facecolor="white")
        plt.close(fig)

        d = pdf.infodict()
        d["Title"] = "GauKavach - Hardware Bill of Materials"
        d["Subject"] = "Tiered hardware costing for an evidence-graded livestock deterrent"
        d["Creator"] = "gaukavach tools/make_hardware_pdf.py"

    return out_path


if __name__ == "__main__":
    p = build(sys.argv[1] if len(sys.argv) > 1 else "docs/GauKavach_Hardware_BOM.pdf")
    print(f"wrote {p}  ({Path(p).stat().st_size / 1024:.0f} KB)")
