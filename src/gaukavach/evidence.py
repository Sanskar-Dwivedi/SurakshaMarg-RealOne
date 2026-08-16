"""
Evidence registry.

Every physical constant, threshold and behavioural assumption used anywhere in
GauKavach must be declared here with a source and an evidence grade. Code that
uses an ungraded magic number is a bug; the constant-audit test will fail.

Grades follow Appendix B of the source report:
    HIGH        - replicated peer-reviewed measurement / official standard
    MODERATE    - repeatedly demonstrated, some heterogeneity
    LOW         - single study or prototype, replication needed
    HYPOTHESIS  - proposed engineering compromise, not validated
    HEURISTIC   - our own modelling choice, no external source claimed
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Grade(str, Enum):
    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"
    HYPOTHESIS = "Hypothesis"
    HEURISTIC = "Heuristic (ours, unvalidated)"

    @property
    def actionable(self) -> bool:
        """May a constant of this grade authorise emission on its own?"""
        return self in (Grade.HIGH, Grade.MODERATE)


@dataclass(frozen=True)
class Source:
    key: str
    citation: str
    url: str
    note: str
    # Whether a team member has personally retrieved and read the source, as
    # opposed to citing it from a secondary reference or from memory. Anything
    # left False must be checked before this work is presented or published.
    # Recording the distinction is cheaper than being caught by it.
    #
    # Only a person may set this. It is a claim about scholarship: that someone
    # read the thing and confirmed it says what we say it says.
    first_party_verified: bool = False

    # A weaker, machine-made claim, kept deliberately separate: on this date the
    # citation's year, volume and pages were compared against the publisher's
    # own record via CrossRef or PubMed, and agreed. Re-runnable with
    # tools/check_citations.py.
    #
    # This catches the error that actually gets caught in review - a volume that
    # has drifted, a transposed page range - and catches nothing else. It says
    # nothing about whether the source supports the claim drawn from it. Folding
    # the two together would let a lookup pass itself off as reading, which is
    # the exact substitution this registry exists to prevent.
    metadata_checked: str = ""


SOURCES: dict[str, Source] = {
    "R1": Source(
        "R1",
        "Heffner, R.S. & Heffner, H.E. (1983). Hearing in large mammals: horses "
        "and cattle. Behavioral Neuroscience 97(2), 299-309.",
        "https://doi.org/10.1037/0735-7044.97.2.299",
        "Primary behavioural audiogram. Cattle 23 Hz - 35 kHz, best sensitivity "
        "near 8 kHz. Range endpoints are defined at a 60 dB SPL criterion - the "
        "single most load-bearing fact in the whole system.",
        metadata_checked="2026-08-16",
    ),
    "R2": Source(
        "R2",
        "Olczak, K. et al. (2023). The Role of Sound in Livestock Farming. "
        "Animals 13(14), 2307.",
        "https://doi.org/10.3390/ani13142307",
        "Livestock acoustics review; cattle hearing and adverse noise effects.",
        metadata_checked="2026-08-16",
    ),
    "R3": Source(
        "R3",
        "Moreira, S.M. et al. (2023). Auditory sensitivity in beef cattle of "
        "different genetic origin. J. Vet. Behavior 59, 67-72.",
        "https://doi.org/10.1016/j.jveb.2022.10.004",
        "Individual and breed variation in auditory sensitivity - the reason we "
        "carry a per-animal response prior rather than one global threshold.",
        metadata_checked="2026-08-16",
    ),
    "R4": Source(
        "R4",
        "Taddy, E.N. et al. (2025). Design and Construction of an Ultrasonic "
        "Cattle Deterrent Device. Nigerian Journal of Physics 34(4), 154-160.",
        "https://njp.nipngr.org/index.php/njp/article/view/462",
        "The only direct cattle-ultrasound prototype. Reports 30 kHz avoidance "
        "at 142 dB SPL @ 1 m. We cite it as motivation and explicitly REFUSE to "
        "reproduce its exposure level. See welfare.HARD_REFUSAL_DB.",
        metadata_checked="2026-08-16",
    ),
    "R5": Source(
        "R5",
        "Umstatter, C. et al. (2013). Can the location of cattle be managed "
        "using broadcast audio cues? Appl. Anim. Behav. Sci. 147, 34-42.",
        "https://doi.org/10.1016/j.applanim.2013.04.019",
        "Audio cues shift cattle location but do NOT give stock-proof "
        "containment. Basis for our 'deterrent layer, never a barrier' rule.",
        metadata_checked="2026-08-16",
    ),
    "R6": Source(
        "R6",
        "Lee, C. et al. (2009). Associative learning by cattle to enable "
        "effective and ethical virtual fences. Appl. Anim. Behav. Sci. 119, 15-22.",
        "https://doi.org/10.1016/j.applanim.2009.03.010",
        "Cattle learn audio cue -> consequence. Unconditioned tones are weaker.",
        metadata_checked="2026-08-16",
    ),
    "R9": Source(
        "R9",
        "Keshavarzi, H. et al. (2020). Virtual Fence Responses Are Socially "
        "Facilitated in Beef Cattle. Front. Vet. Sci. 7, 543158.",
        "https://doi.org/10.3389/fvets.2020.543158",
        "Social facilitation: herd members copy responders. Basis for our herd "
        "model and the leader-breakthrough failure mode.",
        metadata_checked="2026-08-16",
    ),
    "R11": Source(
        "R11",
        "Wilms, L. et al. (2024). How do grazing beef and dairy cattle respond "
        "to virtual fences? A review. J. Anim. Sci. 102, skae108.",
        "https://doi.org/10.1093/jas/skae108",
        "Review of cattle learning, response and welfare evidence.",
        metadata_checked="2026-08-16",
    ),
    "R13": Source(
        "R13",
        "OSHA Technical Manual, Section III Ch.5: Noise, Appendix C - Ultrasound.",
        "https://www.osha.gov/otm/section-3-health-hazards/chapter-5",
        "Human audibility 15-20 kHz and not a fixed boundary; ultrasonic sources "
        "generate audible subharmonics; 6 dB per distance doubling; "
        "international ceiling recommendations ~105-115 dB in the 20-40 kHz band.",
        metadata_checked="2026-08-16",
    ),
    "R14": Source(
        "R14",
        "Lawrence, B.D. & Simmons, J.A. (1982). Measurements of atmospheric "
        "attenuation at ultrasonic frequencies. JASA 71(3), 585-590.",
        "https://doi.org/10.1121/1.387529",
        "Measured approximately 0.7 dB/m at 30 kHz, 25 C, 50% RH.",
        metadata_checked="2026-08-16",
    ),
    "R15": Source(
        "R15",
        "ISO 9613-1:1993. Acoustics - Attenuation of sound during propagation "
        "outdoors - Part 1: absorption of sound by the atmosphere.",
        "https://www.iso.org/standard/17426.html",
        "Analytical absorption model. NOTE: the standard's stated validity "
        "extends to 10 kHz; use at 22-35 kHz is documented extrapolation, not "
        "compliance. GauKavach reports this caveat on every prediction.",
    ),
    "R16": Source(
        "R16",
        "Dimov, D. et al. (2023). Importance of Noise Hygiene in Dairy Cattle "
        "Farming - A Review. Acoustics 5, 1036-1045.",
        "https://doi.org/10.3390/acoustics5040059",
        "Avoid excessive or sudden noise; adverse responses at elevated levels.",
        metadata_checked="2026-08-16",
    ),
    # -- comparative audiograms -------------------------------------------
    # All measured at the SAME 60 dB SPL criterion as R1, which is what makes
    # the cross-species comparison in species.py legitimate rather than a
    # collage of incompatible methods.
    "R17": Source(
        "R17",
        "Heffner, H.E. (1983). Hearing in large and small dogs: absolute "
        "thresholds and size of the tympanic membrane. Behavioral "
        "Neuroscience, 97(2), 310-318.",
        "https://doi.org/10.1037/0735-7044.97.2.310",
        "Dog hearing to approximately 45 kHz. Companion paper to R1 in the "
        "same issue. Basis for the absolute dog veto.",
        metadata_checked="2026-08-16",
    ),
    "R18": Source(
        "R18",
        "Heffner, R.S. & Heffner, H.E. (1985). Hearing range of the domestic "
        "cat. Hearing Research, 19(1), 85-88.",
        "https://doi.org/10.1016/0378-5955(85)90100-5",
        "Cat hearing to approximately 85 kHz - the most sensitive receiver "
        "likely to be present at any deployment site.",
        metadata_checked="2026-08-16",
    ),
    "R19": Source(
        "R19",
        "Heffner, R.S. & Heffner, H.E. (1990). Hearing in domestic pigs "
        "(Sus scrofa) and goats (Capra hircus). Hearing Research, 48, 231-240.",
        "https://doi.org/10.1016/0378-5955(90)90063-U",
        "Goat to approximately 37 kHz, pig to approximately 40.5 kHz. Both "
        "above cattle. Directly supports the user-raised goat-herd hazard.",
        metadata_checked="2026-08-16",
    ),
    "R20": Source(
        "R20",
        "Wollack, C.H. (1963). The auditory acuity of the sheep (Ovis aries). "
        "Journal of Auditory Research, 3, 121-132.",
        "",
        "Sheep hearing to approximately 42.5 kHz. Older study; retained "
        "because it is the standard reference for ovine hearing range.",
    ),
    "R21": Source(
        "R21",
        "Heffner, R.S. & Heffner, H.E. (1982). Hearing in the elephant "
        "(Elephas maximus): absolute sensitivity, frequency discrimination, "
        "and sound localization. Journal of Comparative and Physiological "
        "Psychology, 96(6), 926-944.",
        "https://doi.org/10.1037/0735-7036.96.6.926",
        "Elephant hearing tops out near 10.5 kHz - an ultrasonic deterrent is "
        "simply inapplicable, which is worth stating explicitly.",
        metadata_checked="2026-08-16",
    ),
    "R22": Source(
        "R22",
        "Heffner, H.E. & Heffner, R.S. (2007). Hearing ranges of laboratory "
        "animals. Journal of the American Association for Laboratory Animal "
        "Science, 46(1), 20-22.",
        "https://pubmed.ncbi.nlm.nih.gov/17203911/",
        "Consolidated comparative table at a common 60 dB SPL criterion. The "
        "spine of species.py.",
        metadata_checked="2026-08-16",
    ),
    "R23": Source(
        "R23",
        "Ashihara, K. (2007). Hearing thresholds for pure tones above 16 kHz. "
        "Journal of the Acoustical Society of America, 122(3), EL52-EL57.",
        "https://doi.org/10.1121/1.2761883",
        "Thresholds above 16 kHz in young listeners. Supports the separate "
        "child-audibility curve: a carrier inaudible to adults is not "
        "automatically inaudible to children.",
        metadata_checked="2026-08-16",
    ),
    "R24": Source(
        "R24",
        "Grandin, T. (1997). Assessment of stress during handling and "
        "transport. Journal of Animal Science, 75(1), 249-257.",
        "https://doi.org/10.2527/1997.751249x",
        "Flight zone, point of balance and the consequences of applying "
        "pressure from the wrong angle. The conceptual basis for refusing to "
        "emit when the animal's flight path leads into the carriageway.",
        metadata_checked="2026-08-16",
    ),
    "OURS": Source(
        "OURS",
        "GauKavach engineering assumption (this work).",
        "",
        "No external evidence claimed. Must be validated before field use.",
        first_party_verified=True,
    ),
}


def unverified_sources() -> list[str]:
    """
    Sources nobody on the team has personally retrieved yet.

    Printed as a pre-submission checklist. A citation carried from memory is a
    liability in exactly the kind of review this project invites.
    """
    return sorted(k for k, s in SOURCES.items() if not s.first_party_verified)


@dataclass(frozen=True)
class Constant:
    """A number the system is allowed to use, with its provenance attached."""

    name: str
    value: Any
    unit: str
    grade: Grade
    sources: tuple[str, ...]
    rationale: str
    tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for s in self.sources:
            if s not in SOURCES:
                raise KeyError(f"{self.name} cites unknown source {s!r}")

    def cite(self) -> str:
        return "; ".join(SOURCES[s].citation for s in self.sources)

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "grade": self.grade.value,
            "actionable": self.grade.actionable,
            "sources": [
                {
                    "key": k,
                    "citation": SOURCES[k].citation,
                    "url": SOURCES[k].url,
                    "note": SOURCES[k].note,
                }
                for k in self.sources
            ],
            "rationale": self.rationale,
            "tags": list(self.tags),
        }


REGISTRY: dict[str, Constant] = {}


def declare(c: Constant) -> Constant:
    if c.name in REGISTRY:
        raise ValueError(f"duplicate constant {c.name}")
    REGISTRY[c.name] = c
    return c


def get(name: str) -> Any:
    """Fetch a declared value. Raises if the constant was never graded."""
    if name not in REGISTRY:
        raise KeyError(
            f"{name!r} is not in the evidence registry. Every number that "
            f"influences emission must be declared in evidence.py."
        )
    return REGISTRY[name].value


def grade_of(name: str) -> Grade:
    return REGISTRY[name].grade


def audit() -> dict:
    by_grade: dict[str, list[str]] = {}
    for c in REGISTRY.values():
        by_grade.setdefault(c.grade.value, []).append(c.name)
    return {
        "total_constants": len(REGISTRY),
        "by_grade": {k: len(v) for k, v in sorted(by_grade.items())},
        "non_actionable": sorted(
            c.name for c in REGISTRY.values() if not c.grade.actionable
        ),
        "sources": len(SOURCES),
    }


def export() -> list[dict]:
    return [c.as_dict() for c in REGISTRY.values()]


# ---------------------------------------------------------------------------
# Declarations. Nothing below this line is a "magic number".
# ---------------------------------------------------------------------------

declare(Constant(
    "cattle_hearing_low_hz", 23.0, "Hz", Grade.HIGH, ("R1",),
    "Lower endpoint of the cattle behavioural audiogram.",
    ("audiogram",)))

declare(Constant(
    "cattle_hearing_high_hz", 35_000.0, "Hz", Grade.HIGH, ("R1", "R2"),
    "Upper endpoint of the cattle behavioural audiogram. An ENDPOINT, not a "
    "frequency of useful sensitivity.",
    ("audiogram",)))

declare(Constant(
    "cattle_best_sensitivity_hz", 8_000.0, "Hz", Grade.HIGH, ("R1",),
    "Region of best cattle sensitivity - squarely human-audible, hence "
    "unusable for a covert deterrent.",
    ("audiogram",)))

declare(Constant(
    "audiogram_criterion_db", 60.0, "dB SPL", Grade.HIGH, ("R1",),
    "Heffner & Heffner define hearing-range endpoints at a 60 dB SPL "
    "criterion. Therefore a signal near the top of the range must arrive at "
    "the animal at >= 60 dB SPL to be assumed detectable at all. This converts "
    "an audiogram into a hard link-budget requirement.",
    ("audiogram", "linkbudget")))

declare(Constant(
    "human_audibility_low_hz", 15_000.0, "Hz", Grade.HIGH, ("R13",),
    "Below this, assume essentially every bystander hears the signal.",
    ("human",)))

declare(Constant(
    "human_audibility_high_hz", 20_000.0, "Hz", Grade.HIGH, ("R13",),
    "OSHA: the upper limit of human audibility is ~15-20 kHz and is NOT fixed. "
    "20 kHz is therefore not a guaranteed silent frequency.",
    ("human",)))

declare(Constant(
    "spreading_db_per_doubling", 6.0, "dB", Grade.HIGH, ("R13",),
    "Free-field point-source geometric spreading.",
    ("propagation",)))

declare(Constant(
    "ls_alpha_30k_db_per_m", 0.7, "dB/m", Grade.HIGH, ("R14",),
    "Measured atmospheric attenuation at 30 kHz, 25 C, 50% RH.",
    ("propagation",)))

declare(Constant(
    "osha_ultrasound_ceiling_db", 110.0, "dB SPL", Grade.HIGH, ("R13",),
    "Midpoint of the ~105-115 dB international occupational ceiling band for "
    "20-40 kHz. A HUMAN occupational reference, not a cattle welfare limit - "
    "we adopt it as the emitter cap precisely because no cattle-specific limit "
    "exists, and we say so.",
    ("welfare", "human")))

declare(Constant(
    "osha_ultrasound_ceiling_max_db", 115.0, "dB SPL", Grade.HIGH, ("R13",),
    "Upper edge of the cited international band. Absolute ceiling; "
    "unreachable without a signed ethics authorisation token.",
    ("welfare",)))

declare(Constant(
    "refused_prototype_spl_db", 142.0, "dB SPL @ 1 m", Grade.LOW, ("R4",),
    "The level reported by the only direct cattle-ultrasound prototype. About "
    "27 dB above the occupational ceiling, i.e. >500x the acoustic intensity. "
    "GauKavach treats any configuration approaching this as a fault condition, "
    "not a setting.",
    ("welfare", "refusal")))

declare(Constant(
    "experimental_band_low_hz", 22_000.0, "Hz", Grade.HYPOTHESIS,
    ("R1", "R4", "R13"),
    "Lower edge of the proposed test band: above most adult hearing, well "
    "inside the cattle audiogram. An engineering compromise, NOT a validated "
    "optimum.",
    ("band",)))

declare(Constant(
    "experimental_band_high_hz", 30_000.0, "Hz", Grade.HYPOTHESIS, ("R1", "R4"),
    "Upper edge of the proposed test band; beyond this cattle sensitivity "
    "falls and usable range collapses under absorption.",
    ("band",)))

declare(Constant(
    "max_human_audibility_risk", 0.02, "probability", Grade.HEURISTIC, ("OURS", "R13"),
    "Largest modelled probability of a bystander perceiving the carrier that we "
    "will accept. Set at 2% rather than a looser figure because R13 states "
    "explicitly that 20 kHz is NOT a guaranteed silent frequency; a permissive "
    "threshold lets the optimiser drift down to 20 kHz and quietly contradict "
    "the source.",
    ("human", "band")))

declare(Constant(
    "enforce_band_floor", True, "bool", Grade.HYPOTHESIS, ("R1", "R4", "R13"),
    "Refuse to select a carrier below experimental_band_low_hz even when the "
    "link budget would allow it. The band floor is a documented compromise, so "
    "leaving it must be a deliberate, logged override - not an optimiser "
    "side-effect.",
    ("band", "guard")))

declare(Constant(
    "masking_margin_db", 15.0, "dB", Grade.HEURISTIC, ("OURS",),
    "Signal-to-ambient margin required on top of the audiogram criterion. "
    "Chosen by analogy with speech-detectability margins; NOT measured in "
    "cattle. Tunable, and logged with every activation.",
    ("linkbudget",)))

declare(Constant(
    "max_activation_s", 6.0, "s", Grade.HEURISTIC, ("OURS", "R16"),
    "Hard watchdog limit on any single emission. Noise-hygiene reviews advise "
    "against sustained or sudden noise, and short bursts limit habituation; "
    "the specific value is ours.",
    ("welfare", "watchdog")))

declare(Constant(
    "min_silence_s", 20.0, "s", Grade.HEURISTIC, ("OURS",),
    "Enforced quiet period after any emission, per animal track.",
    ("welfare",)))

declare(Constant(
    "daily_exposure_budget_s", 120.0, "s", Grade.HEURISTIC, ("OURS",),
    "Per-animal cumulative daily exposure cap. Beyond this the animal is "
    "placed on a do-not-emit list and the site escalates to human dispatch.",
    ("welfare",)))

declare(Constant(
    "habituation_halflife_exposures", 12.0, "exposures", Grade.HYPOTHESIS,
    ("R5", "R6", "R11"),
    "Assumed decay in response probability for an unconditioned tone with no "
    "paired consequence. Derived by analogy from virtual-fencing literature "
    "where the cue IS paired; an unpaired cue should decay at least this fast. "
    "Drives the digital twin only - never a live emission decision.",
    ("behaviour",)))

declare(Constant(
    "social_facilitation_gain", 0.35, "fraction", Grade.MODERATE, ("R9",),
    "Increase in response probability for a herd member once a conspecific has "
    "responded. The magnitude is our fit; the effect itself is established.",
    ("behaviour", "herd")))

declare(Constant(
    "max_herd_size_for_emission", 3, "animals", Grade.HYPOTHESIS, ("R9", "R24"),
    "Above this many conspecifics in the zone, emission is refused outright "
    "and the incident escalates. Rationale: R9 established that virtual-fence "
    "responses are socially facilitated, so a startle propagates through a "
    "group rather than staying with one animal. A flock moving as one body in "
    "an unpredictable direction is a worse road hazard than the original "
    "blockage. The specific threshold is ours.",
    ("welfare", "herd", "stampede")))

declare(Constant(
    "herd_grouping_radius_m", 12.0, "m", Grade.HEURISTIC, ("OURS",),
    "Animals of the same species within this distance of each other are "
    "counted as one social group for the stampede check.",
    ("herd",)))

declare(Constant(
    "min_escape_corridor_m", 8.0, "m", Grade.HEURISTIC, ("OURS", "R24"),
    "An animal must have at least this much clear ground along its likely "
    "flight vector, away from the carriageway, before any emission is "
    "permitted. Grandin's handling literature is explicit that pressure "
    "applied without a viable escape route produces panic rather than "
    "controlled movement. The distance is ours.",
    ("welfare", "escape")))

declare(Constant(
    "flight_vector_check_m", 25.0, "m", Grade.HYPOTHESIS, ("R24",),
    "Distance along the predicted flight vector that is tested for "
    "intersection with the carriageway. If the animal would flee ONTO the "
    "road, the system must not emit - it would cause the collision it exists "
    "to prevent.",
    ("welfare", "escape", "geometry")))

declare(Constant(
    "juvenile_height_ratio", 0.7, "fraction", Grade.HEURISTIC, ("OURS",),
    "An animal shorter than this fraction of its species' typical adult "
    "height is treated as juvenile. Emission is then refused: young animals "
    "are more vulnerable, and a dam with offspring at foot is the classic "
    "maternal-aggression case. Estimated from monocular height, so it "
    "inherits the camera's calibration error.",
    ("welfare", "juvenile")))

declare(Constant(
    "immobile_displacement_m", 1.5, "m", Grade.HEURISTIC, ("OURS", "R24"),
    "If an animal moves less than this after a completed emission, it is "
    "treated as possibly tethered, trapped, sick or injured, and further "
    "emission is refused for that animal. Continuing to press an animal that "
    "cannot leave is pure distress with no possible benefit.",
    ("welfare", "restraint")))

declare(Constant(
    "downed_aspect_ratio", 1.6, "w/h", Grade.HEURISTIC, ("OURS",),
    "Bounding-box width-to-height ratio above which an animal is flagged as "
    "possibly recumbent or collapsed. Crude, and deliberately biased toward "
    "false positives: the cost of wrongly sparing a standing animal is one "
    "missed nudge, while the cost of harassing a downed animal is severe.",
    ("welfare", "posture")))

declare(Constant(
    "child_audibility_band_floor_hz", 25_000.0, "Hz", Grade.HYPOTHESIS,
    ("R13", "R23"),
    "Minimum carrier near a school or dense housing. High-frequency hearing "
    "declines with age, so a 22 kHz tone chosen because adults cannot hear it "
    "may still be audible to children. Commercial anti-loitering devices "
    "exploit precisely this gap near 17.4 kHz.",
    ("human", "band", "child")))

declare(Constant(
    "escalation_timeout_s", 25.0, "s", Grade.HEURISTIC, ("OURS", "R5"),
    "If the carriageway is not cleared within this window, stop acoustic "
    "attempts and hand off to human dispatch. Follows directly from R5: "
    "acoustic cues are not stock-proof, so the system must have a defined "
    "give-up point.",
    ("escalation",)))
