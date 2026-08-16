"""
Behavioural digital twin.

This is the part of the project most likely to be attacked, so it is the part
that concedes most loudly.

Nobody has published a dose-response curve for cattle exposed to 22-30 kHz
tones. The report grades that claim LOW-MODERATE on the strength of a single
prototype (R4). Therefore this twin cannot tell you how well GauKavach works,
and it never returns a bare number pretending otherwise.

What it does instead:
  * encodes response probability as an explicit prior with stated parameters,
  * propagates uncertainty by Monte Carlo over those parameters,
  * returns credible intervals, not point estimates,
  * and reports how wide the interval is, so the reader can see that the
    honest answer is "we don't know yet, here is the range and here is the
    experiment that would narrow it".

The correct use of this module is to size a field trial, not to claim a result.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict

import numpy as np

from . import evidence as ev
from .acoustics import Atmosphere, cattle_sensitivity_penalty_db, total_loss_db


@dataclass
class ResponsePrior:
    """
    Prior over the cattle dose-response relationship.

    `sensitivity_spread_db` exists because R3 documents individual and genetic
    variation in auditory sensitivity; a single threshold would be a fiction.
    """

    threshold_db_mean: float = 75.0
    threshold_db_sd: float = 12.0
    slope_per_db_mean: float = 0.09
    slope_per_db_sd: float = 0.035
    max_response_prob_mean: float = 0.72
    max_response_prob_sd: float = 0.15
    sensitivity_spread_db: float = 8.0

    provenance: str = (
        "NOT MEASURED. Threshold centre is anchored to the 60 dB SPL audiogram "
        "criterion (R1) plus a margin for band-edge sensitivity loss (R3); the "
        "ceiling on response probability reflects that even paired virtual-fence "
        "cues do not achieve 100% compliance (R5, R11). Every parameter is a "
        "prior to be updated by field data, not a finding."
    )
    grade: str = "Hypothesis"

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrialOutcome:
    received_db: float
    p_response_median: float
    p_response_lo: float      # 5th percentile
    p_response_hi: float      # 95th percentile
    interval_width: float
    n_samples: int
    habituation_factor: float
    social_boost: float
    verdict: str

    def as_dict(self) -> dict:
        return asdict(self)


class BehaviourTwin:
    """Monte Carlo simulator over an explicit, citable prior."""

    def __init__(
        self,
        prior: ResponsePrior | None = None,
        seed: int = 7,
        n_samples: int = 4000,
    ) -> None:
        self.prior = prior or ResponsePrior()
        self.rng = np.random.default_rng(seed)
        self.n_samples = n_samples

    def _sample_params(self, n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        p = self.prior
        thr = self.rng.normal(p.threshold_db_mean, p.threshold_db_sd, n)
        thr += self.rng.normal(0.0, p.sensitivity_spread_db, n)  # per-animal variation
        slope = np.clip(self.rng.normal(p.slope_per_db_mean, p.slope_per_db_sd, n), 0.005, None)
        ceil = np.clip(
            self.rng.normal(p.max_response_prob_mean, p.max_response_prob_sd, n), 0.05, 0.98
        )
        return thr, slope, ceil

    def response_probability(
        self,
        received_db: float,
        prior_exposures: int = 0,
        conspecific_responded: bool = False,
    ) -> TrialOutcome:
        """
        Credible interval on P(turn away) for one animal at one dose.

        Habituation follows an exponential decay whose half-life is the
        HYPOTHESIS-grade constant from the evidence registry; social
        facilitation applies the MODERATE-grade gain from R9.
        """
        n = self.n_samples
        thr, slope, ceil = self._sample_params(n)

        logistic = 1.0 / (1.0 + np.exp(-slope * (received_db - thr)))
        p = ceil * logistic

        halflife = ev.get("habituation_halflife_exposures")
        hab = float(0.5 ** (prior_exposures / halflife)) if prior_exposures else 1.0
        p = p * hab

        boost = ev.get("social_facilitation_gain") if conspecific_responded else 0.0
        if boost:
            p = p + (1.0 - p) * boost

        lo, med, hi = (float(x) for x in np.percentile(p, [5, 50, 95]))
        width = hi - lo

        if width > 0.45:
            verdict = (
                "UNINFORMATIVE - the prior dominates. This dose cannot be "
                "distinguished from chance without field data."
            )
        elif med < 0.35:
            verdict = "Likely insufficient. Expect most animals to continue."
        elif med > 0.7 and lo > 0.5:
            verdict = "Promising, but the interval reflects a prior, not evidence."
        else:
            verdict = "Marginal. Exactly the regime a field trial must resolve."

        return TrialOutcome(
            received_db=round(received_db, 1),
            p_response_median=round(med, 3),
            p_response_lo=round(lo, 3),
            p_response_hi=round(hi, 3),
            interval_width=round(width, 3),
            n_samples=n,
            habituation_factor=round(hab, 3),
            social_boost=round(boost, 3),
            verdict=verdict,
        )

    # -- experiment design -------------------------------------------------

    def required_sample_size(
        self,
        baseline_rate: float = 0.15,
        target_rate: float = 0.50,
        power: float = 0.80,
        alpha: float = 0.05,
    ) -> dict:
        """
        Approaches needed per arm to detect a turn-away improvement.

        Standard two-proportion normal approximation. This is the single most
        useful output of the twin: it converts 'we should test it' into a
        concrete, costable field protocol.
        """
        from statistics import NormalDist

        z_a = NormalDist().inv_cdf(1.0 - alpha / 2.0)
        z_b = NormalDist().inv_cdf(power)
        p1, p2 = baseline_rate, target_rate
        pbar = (p1 + p2) / 2.0
        num = (
            z_a * math.sqrt(2 * pbar * (1 - pbar))
            + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
        ) ** 2
        n = num / ((p2 - p1) ** 2)
        per_arm = int(math.ceil(n))
        return {
            "baseline_turn_away_rate": p1,
            "target_turn_away_rate": p2,
            "power": power,
            "alpha": alpha,
            "approaches_per_arm": per_arm,
            "total_approaches": per_arm * 2,
            "note": (
                "Two-proportion normal approximation, independent approaches. "
                "Real herds violate independence because responses are socially "
                "facilitated (R9), so treat this as a LOWER BOUND and cluster "
                "by herd in the analysis."
            ),
        }

    def dose_response_curve(
        self, lo_db: float = 50.0, hi_db: float = 110.0, step_db: float = 5.0
    ) -> list[dict]:
        out = []
        d = lo_db
        while d <= hi_db:
            out.append(self.response_probability(d).as_dict())
            d += step_db
        return out

    def habituation_projection(self, received_db: float, days: int = 10) -> list[dict]:
        """
        Project response decay across repeated exposures.

        The report is explicit that a deterrent working only on day one is not
        a deterrent. This makes that failure mode visible before deployment.
        """
        out = []
        for day in range(days):
            exposures = day * 3  # assume ~3 encounters/day
            o = self.response_probability(received_db, prior_exposures=exposures)
            out.append({"day": day + 1, "cumulative_exposures": exposures, **o.as_dict()})
        return out


def received_level_db(
    emitted_1m_db: float,
    distance_m: float,
    freq_hz: float,
    atm: Atmosphere,
    model: str = "lawrence_simmons",
) -> float:
    """
    What the animal actually receives.

    Exposure questions use the OPTIMISTIC (lower-absorption) model so we never
    under-state how loud it is at the ear.
    """
    loss = total_loss_db(distance_m, freq_hz, atm, model)  # type: ignore[arg-type]
    return emitted_1m_db - loss + cattle_sensitivity_penalty_db(freq_hz) * 0.0
