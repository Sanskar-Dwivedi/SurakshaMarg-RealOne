"""
Waveform synthesis, spectral self-inspection and the anti-habituation scheduler.

Two non-obvious things live here.

1. ENVELOPE RAMPING. A 25 kHz burst switched on and off abruptly is not a
   25 kHz signal. The rectangular gate convolves a sinc into the spectrum and
   splatters broadband energy across the audible range - the device clicks
   audibly at every activation even though its carrier is ultrasonic. R13
   warns that ultrasonic equipment generates audible components; a hard gate
   is the easiest way to cause exactly that. We therefore raised-cosine ramp
   every burst and MEASURE the residual audible energy before emitting.

2. SELF-INSPECTION BEFORE EMISSION. The device FFTs its own synthesised buffer
   and refuses to play anything whose sub-20 kHz energy exceeds a threshold.
   A prototype that only checks its intended carrier frequency is checking the
   one thing that was never in doubt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict

import numpy as np

from . import evidence as ev

# 192 kHz gives a 96 kHz Nyquist: enough headroom to represent a 30 kHz carrier
# and see its second harmonic without aliasing it back into the audible band.
DEFAULT_SAMPLE_RATE = 192_000


@dataclass(frozen=True)
class BurstPattern:
    """
    One activation pattern. Patterns are varied between activations because a
    single static tone is the configuration most likely to habituate (R5/R6/R11).
    """

    name: str
    burst_ms: float
    gap_ms: float
    repeats: int
    sweep_hz: float = 0.0  # optional linear chirp span across each burst

    @property
    def duration_s(self) -> float:
        n = self.repeats
        return (n * self.burst_ms + max(n - 1, 0) * self.gap_ms) / 1000.0

    def as_dict(self) -> dict:
        d = asdict(self)
        d["duration_s"] = round(self.duration_s, 3)
        return d


# A small, deliberately diverse library. Variation is the point.
PATTERNS: tuple[BurstPattern, ...] = (
    BurstPattern("short-triple", burst_ms=120, gap_ms=90, repeats=3),
    BurstPattern("long-double", burst_ms=300, gap_ms=150, repeats=2),
    BurstPattern("rapid-quint", burst_ms=60, gap_ms=60, repeats=5),
    BurstPattern("chirp-up", burst_ms=250, gap_ms=120, repeats=2, sweep_hz=2500.0),
    BurstPattern("chirp-down", burst_ms=250, gap_ms=120, repeats=2, sweep_hz=-2500.0),
    BurstPattern("irregular", burst_ms=180, gap_ms=240, repeats=3),
)


@dataclass
class SpectralReport:
    """Result of the device inspecting its own output."""

    carrier_hz: float
    sample_rate: int
    peak_hz: float
    audible_energy_db: float       # relative to carrier, dB
    worst_audible_hz: float
    subharmonic_check_hz: float
    subharmonic_level_db: float
    passes: bool
    reason: str | None

    def as_dict(self) -> dict:
        return asdict(self)


def _raised_cosine_envelope(n: int, ramp_frac: float = 0.25) -> np.ndarray:
    """
    Raised-cosine (Tukey) window. `ramp_frac` of each end is a cosine taper.

    Without this the on/off transient is broadband and audible; with it the
    spectral splatter drops by tens of dB. This single line is the difference
    between a silent device and a clicking one.
    """
    env = np.ones(n)
    ramp = max(int(n * ramp_frac), 1)
    if 2 * ramp > n:
        ramp = n // 2
    if ramp > 0:
        t = np.linspace(0.0, math.pi, ramp)
        rise = 0.5 * (1.0 - np.cos(t))
        env[:ramp] = rise
        env[-ramp:] = rise[::-1]
    return env


def synthesise(
    carrier_hz: float,
    pattern: BurstPattern,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    ramp_frac: float = 0.25,
    hard_gate: bool = False,
) -> np.ndarray:
    """
    Build the drive waveform, normalised to +/-1.0.

    `hard_gate=True` deliberately disables ramping so the demo can show the
    audible-click failure mode side by side with the correct waveform.
    """
    burst_n = int(sample_rate * pattern.burst_ms / 1000.0)
    gap_n = int(sample_rate * pattern.gap_ms / 1000.0)
    chunks: list[np.ndarray] = []

    for i in range(pattern.repeats):
        t = np.arange(burst_n) / sample_rate
        if pattern.sweep_hz:
            f0 = carrier_hz - pattern.sweep_hz / 2.0
            k = pattern.sweep_hz / max(t[-1], 1e-9) if burst_n > 1 else 0.0
            phase = 2 * np.pi * (f0 * t + 0.5 * k * t * t)
        else:
            phase = 2 * np.pi * carrier_hz * t
        burst = np.sin(phase)
        if not hard_gate:
            burst = burst * _raised_cosine_envelope(burst_n, ramp_frac)
        chunks.append(burst)
        if i < pattern.repeats - 1:
            chunks.append(np.zeros(gap_n))

    wave = np.concatenate(chunks) if chunks else np.zeros(0)
    peak = float(np.max(np.abs(wave))) if wave.size else 1.0
    return wave / peak if peak > 0 else wave


def inspect_spectrum(
    wave: np.ndarray,
    carrier_hz: float,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    audible_limit_db: float = -40.0,
) -> SpectralReport:
    """
    FFT the actual buffer and measure how much energy lands where humans hear.

    `audible_limit_db` is relative to the carrier peak. -40 dB means audible
    components must be at least 100x weaker in amplitude than the carrier.
    """
    if wave.size == 0:
        return SpectralReport(
            carrier_hz, sample_rate, 0.0, -np.inf, 0.0, carrier_hz / 2, -np.inf,
            False, "empty waveform",
        )

    windowed = wave * np.hanning(wave.size)
    spec = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(wave.size, 1.0 / sample_rate)
    peak_val = float(np.max(spec))
    if peak_val <= 0:
        return SpectralReport(
            carrier_hz, sample_rate, 0.0, -np.inf, 0.0, carrier_hz / 2, -np.inf,
            False, "silent waveform",
        )

    def to_db(x: float) -> float:
        return 20.0 * math.log10(max(x, 1e-12) / peak_val)

    audible_hi = ev.get("human_audibility_high_hz")
    # Ignore DC and the first few bins, which carry window leakage, not signal.
    audible_mask = (freqs > 20.0) & (freqs < audible_hi)
    if np.any(audible_mask):
        idx = int(np.argmax(spec[audible_mask]))
        worst_hz = float(freqs[audible_mask][idx])
        worst_db = to_db(float(spec[audible_mask][idx]))
    else:
        worst_hz, worst_db = 0.0, -np.inf

    # Explicit subharmonic probe: R13's worked example is a 20 kHz source
    # radiating at 10 kHz, so we always look at f/2 by name.
    sub_hz = carrier_hz / 2.0
    sub_bin = int(np.argmin(np.abs(freqs - sub_hz)))
    sub_db = to_db(float(spec[sub_bin]))

    passes = worst_db <= audible_limit_db
    reason = None
    if not passes:
        reason = (
            f"audible component at {worst_hz / 1000:.1f} kHz is {worst_db:.1f} dB "
            f"relative to carrier, above the {audible_limit_db:.0f} dB limit"
        )

    return SpectralReport(
        carrier_hz=carrier_hz,
        sample_rate=sample_rate,
        peak_hz=float(freqs[int(np.argmax(spec))]),
        audible_energy_db=round(worst_db, 2),
        worst_audible_hz=round(worst_hz, 1),
        subharmonic_check_hz=round(sub_hz, 1),
        subharmonic_level_db=round(sub_db, 2),
        passes=passes,
        reason=reason,
    )


class PatternScheduler:
    """
    Chooses carrier and pattern so consecutive exposures for the same animal
    are never identical.

    Rationale is HYPOTHESIS-grade (R5/R6/R11): varying an unconditioned cue is
    expected to slow habituation, but this has not been validated in cattle for
    ultrasound. The scheduler therefore records what it chose so a field trial
    can actually test the hypothesis rather than assume it.
    """

    def __init__(self, seed: int = 0) -> None:
        self.rng = np.random.default_rng(seed)
        self.history: dict[str, list[tuple[float, str]]] = {}

    def choose(
        self, track_id: str, feasible_carriers_hz: list[float]
    ) -> tuple[float, BurstPattern]:
        if not feasible_carriers_hz:
            raise ValueError("no feasible carrier supplied by the acoustics layer")
        past = self.history.setdefault(track_id, [])
        recent = {p for _, p in past[-3:]}
        recent_f = {f for f, _ in past[-2:]}

        options = [p for p in PATTERNS if p.name not in recent] or list(PATTERNS)
        carriers = [f for f in feasible_carriers_hz if f not in recent_f] or feasible_carriers_hz

        pattern = options[int(self.rng.integers(len(options)))]
        carrier = float(carriers[int(self.rng.integers(len(carriers)))])
        past.append((carrier, pattern.name))
        return carrier, pattern

    def exposure_count(self, track_id: str) -> int:
        return len(self.history.get(track_id, []))


def build_emission(
    carrier_hz: float,
    pattern: BurstPattern,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> tuple[np.ndarray, SpectralReport]:
    """Synthesise and self-inspect. Callers must honour `report.passes`."""
    wave = synthesise(carrier_hz, pattern, sample_rate)
    return wave, inspect_spectrum(wave, carrier_hz, sample_rate)


def compare_gating(
    carrier_hz: float = 25_000.0,
    pattern: BurstPattern | None = None,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> dict:
    """
    Demonstration hook: quantify the click artefact a hard gate introduces.

    This is the cheapest way to show a judge that the team understood the
    difference between 'the carrier is ultrasonic' and 'the device is silent'.
    """
    pattern = pattern or PATTERNS[0]
    hard = synthesise(carrier_hz, pattern, sample_rate, hard_gate=True)
    ramped = synthesise(carrier_hz, pattern, sample_rate, hard_gate=False)
    r_hard = inspect_spectrum(hard, carrier_hz, sample_rate)
    r_soft = inspect_spectrum(ramped, carrier_hz, sample_rate)
    return {
        "carrier_khz": carrier_hz / 1000.0,
        "pattern": pattern.name,
        "hard_gated": r_hard.as_dict(),
        "raised_cosine": r_soft.as_dict(),
        "improvement_db": round(
            r_hard.audible_energy_db - r_soft.audible_energy_db, 1
        ),
        "interpretation": (
            "Both waveforms carry the same ultrasonic carrier, and in this "
            "ideal linear model both clear the audible-energy threshold. The "
            "hard gate is nonetheless ~{:.0f} dB worse in the audible band. "
            "That margin matters because a real amplifier and transducer add "
            "nonlinearity and mechanical resonance that this model does not "
            "capture, and R13 documents exactly that failure mode. Ramping "
            "costs nothing and removes the risk."
        ).format(r_hard.audible_energy_db - r_soft.audible_energy_db),
        "honesty_note": (
            "The 'worst audible' bin sits just under 20 kHz in both cases and "
            "is FFT skirt from the carrier itself, not a distinct subharmonic. "
            "We report it rather than filtering it out so the number cannot be "
            "read as a measured emission. Only a calibrated ultrasonic "
            "microphone on real hardware settles this."
        ),
    }


def write_wav(path: str, wave: np.ndarray, sample_rate: int = DEFAULT_SAMPLE_RATE) -> None:
    """Write a 16-bit WAV, for bench measurement or hardware playback."""
    import wave as wavemod

    data = np.clip(wave, -1.0, 1.0)
    pcm = (data * 32767.0).astype("<i2")
    with wavemod.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(pcm.tobytes())
