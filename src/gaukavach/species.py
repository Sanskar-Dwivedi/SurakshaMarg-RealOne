"""
Comparative audiogram database and species risk profiles.

This module exists because of a finding that inverts the premise of every
ultrasonic animal deterrent we could find, including the one prototype paper
in the literature.

The pitch for "ultrasonic" deterrence is that the signal is species-selective:
inaudible to people, aversive to the target. The first half is true. The second
half is not just unproven - it is BACKWARDS. Hearing-range endpoints measured
at the same 60 dB SPL criterion (Heffner lab comparative data) put cattle near
the BOTTOM of the affected group:

    at 25 kHz, octaves below each species' upper limit
        cat              +1.77     <-- hears it far better than the cow
        dog              +0.85
        sheep            +0.77
        pig              +0.70
        goat             +0.57
        cattle (target)  +0.49     <-- the animal we are aiming at
        horse            +0.42
        adult human      -0.51     (inaudible)
        chicken          -1.80     (inaudible)

Every household and farm species in that list except the horse hears a 22-30 kHz
tone MORE easily than the cow does. A goat herd beside the road is not an
incidental bystander to this device; it is a more sensitive receiver than the
intended target.

The consequence is architectural and non-negotiable: selectivity CANNOT come
from the frequency. It can only come from the detector. Everything in
`welfare.py` that vetoes on non-target presence exists because of this table.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from enum import Enum


class Group(str, Enum):
    TARGET = "target"
    HOUSEHOLD = "household"        # pets sharing human dwellings
    LIVESTOCK = "livestock"        # owned production animals
    WORKING = "working"            # draught animals, often harnessed to a load
    HUMAN = "human"
    WILDLIFE = "wildlife"


class Aggression(str, Enum):
    """
    Risk that acoustic pressure produces a dangerous response rather than
    withdrawal. Graded qualitatively - there is no quantitative literature for
    ultrasonic provocation specifically, so these are reasoned profiles, not
    measurements, and they only ever make the system MORE restrictive.
    """

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass(frozen=True)
class SpeciesProfile:
    name: str
    coco_label: str | None
    group: Group
    hearing_low_hz: float
    hearing_high_hz: float
    source_key: str
    flocking: bool
    aggression: Aggression
    aggression_note: str
    typical_adult_height_m: float
    juvenile_height_m: float
    notes: str

    def octaves_below_limit(self, carrier_hz: float) -> float:
        """
        How far the carrier sits below this species' hearing-range endpoint,
        in octaves. Larger means the tone lands more comfortably inside the
        animal's range, i.e. it is more readily heard.

        Octaves rather than kHz because auditory sensitivity rolls off roughly
        logarithmically in frequency; a linear margin would flatter the high
        frequencies.
        """
        return math.log2(self.hearing_high_hz / max(carrier_hz, 1.0))

    def audible(self, carrier_hz: float) -> bool:
        return carrier_hz <= self.hearing_high_hz

    def as_dict(self) -> dict:
        d = asdict(self)
        d["group"] = self.group.value
        d["aggression"] = self.aggression.value
        return d


# ---------------------------------------------------------------------------
# The database. Endpoints are at the 60 dB SPL criterion - the SAME criterion
# Heffner & Heffner used for cattle, which is what makes the comparison valid.
# ---------------------------------------------------------------------------

SPECIES: dict[str, SpeciesProfile] = {
    "cow": SpeciesProfile(
        "Cattle", "cow", Group.TARGET, 23.0, 35_000.0, "R1",
        flocking=True, aggression=Aggression.MODERATE,
        aggression_note=(
            "Normally withdraws. Maternal defence with a calf at foot and bull "
            "aggression are the dangerous cases, and neither is distinguishable "
            "from a COCO 'cow' label."
        ),
        typical_adult_height_m=1.35, juvenile_height_m=0.90,
        notes="The intended target. Second-least sensitive of the affected group.",
    ),
    "dog": SpeciesProfile(
        "Dog", "dog", Group.HOUSEHOLD, 67.0, 45_000.0, "R17",
        flocking=False, aggression=Aggression.HIGH,
        aggression_note=(
            "Highest concern in this system. Dogs may orient AT the source "
            "rather than away, and acoustic stress is a documented trigger for "
            "redirected aggression toward nearby people. Free-roaming dogs are "
            "ubiquitous on Indian roads. Absolute veto, never a soft weighting."
        ),
        typical_adult_height_m=0.55, juvenile_height_m=0.25,
        notes="Hears 22-30 kHz roughly twice as far inside its range as cattle.",
    ),
    "cat": SpeciesProfile(
        "Cat", "cat", Group.HOUSEHOLD, 48.0, 85_000.0, "R18",
        flocking=False, aggression=Aggression.MODERATE,
        aggression_note="Flees; risk is bolting into traffic rather than attack.",
        typical_adult_height_m=0.30, juvenile_height_m=0.15,
        notes=(
            "The most acoustically sensitive animal likely to be present. A "
            "25 kHz tone sits nearly two octaves inside its range."
        ),
    ),
    "goat": SpeciesProfile(
        "Goat", "sheep", Group.LIVESTOCK, 78.0, 37_000.0, "R19",
        flocking=True, aggression=Aggression.MODERATE,
        aggression_note=(
            "Strong flocking flight response. The hazard is not attack but "
            "panic propagation through the herd and mass movement in an "
            "unpredictable direction, including onto the carriageway."
        ),
        typical_adult_height_m=0.70, juvenile_height_m=0.35,
        notes=(
            "COCO has no goat class; goats are usually detected as 'sheep' or "
            "missed entirely. This is a KNOWN DETECTION GAP, not a solved case."
        ),
    ),
    "sheep": SpeciesProfile(
        "Sheep", "sheep", Group.LIVESTOCK, 125.0, 42_500.0, "R20",
        flocking=True, aggression=Aggression.LOW,
        aggression_note=(
            "Very strong flocking. Panic cascades faster than in cattle and the "
            "flock moves as one body, so a single wrong nudge can put an entire "
            "flock on the road."
        ),
        typical_adult_height_m=0.75, juvenile_height_m=0.35,
        notes="Hears the band notably better than cattle.",
    ),
    "pig": SpeciesProfile(
        "Pig", None, Group.LIVESTOCK, 42.0, 40_500.0, "R19",
        flocking=True, aggression=Aggression.MODERATE,
        aggression_note="Sows with a litter are defensive. No COCO class.",
        typical_adult_height_m=0.70, juvenile_height_m=0.30,
        notes="No COCO class - undetectable by the current perception stack.",
    ),
    "horse": SpeciesProfile(
        "Horse / donkey", "horse", Group.WORKING, 55.0, 33_500.0, "R1",
        flocking=True, aggression=Aggression.HIGH,
        aggression_note=(
            "The single most dangerous case if harnessed. A bolting draught "
            "animal pulling a cart endangers its handler, the load and every "
            "road user, and the handler is a person standing directly in the "
            "exposure cone. Vetoed unconditionally."
        ),
        typical_adult_height_m=1.50, juvenile_height_m=1.00,
        notes=(
            "The only species less sensitive than cattle in this band - and "
            "still vetoed, because the consequence of being wrong is severe."
        ),
    ),
    "elephant": SpeciesProfile(
        "Elephant", "elephant", Group.WILDLIFE, 17.0, 10_500.0, "R21",
        flocking=True, aggression=Aggression.HIGH,
        aggression_note=(
            "Cannot hear this band at all, so the device offers no benefit - "
            "but an elephant on the road is a severe hazard requiring immediate "
            "human escalation, so detection still matters."
        ),
        typical_adult_height_m=2.80, juvenile_height_m=1.20,
        notes="Infrasound specialist. Ultrasonic deterrence is useless here.",
    ),
    "chicken": SpeciesProfile(
        "Chicken / poultry", None, Group.LIVESTOCK, 9.1, 7_200.0, "R22",
        flocking=True, aggression=Aggression.LOW,
        aggression_note="Not affected by this band.",
        typical_adult_height_m=0.35, juvenile_height_m=0.12,
        notes=(
            "Genuinely unaffected - the carrier is nearly two octaves above "
            "their hearing. Recorded so the system can say which species it "
            "does NOT put at risk, not only which it does."
        ),
    ),
    "human": SpeciesProfile(
        "Human (adult)", "person", Group.HUMAN, 31.0, 17_600.0, "R13",
        flocking=False, aggression=Aggression.LOW,
        aggression_note="n/a",
        typical_adult_height_m=1.65, juvenile_height_m=1.10,
        notes=(
            "Typical ADULT limit. Children and adolescents hear materially "
            "higher - see child_audibility_risk()."
        ),
    ),
}

TARGET_KEY = "cow"

# COCO label -> species keys that label may represent. Deliberately many-to-one
# where the detector cannot separate them, so the ambiguity stays visible.
COCO_TO_SPECIES: dict[str, tuple[str, ...]] = {
    "cow": ("cow",),
    "dog": ("dog",),
    "cat": ("cat",),
    "sheep": ("sheep", "goat"),   # COCO cannot separate these
    "horse": ("horse",),
    "elephant": ("elephant",),
    "person": ("human",),
}

# Species we know are at risk but CANNOT currently detect. Listed so the gap is
# a documented limitation rather than an accidental omission.
UNDETECTABLE_AT_RISK: tuple[str, ...] = ("pig",)

UNDETECTABLE_NOTE = (
    "Rhesus macaques are common on Indian roads, are highly reactive, and have "
    "no COCO class at all - the perception stack cannot see them. Pigs and "
    "poultry are likewise absent from the label set. The system must not be "
    "described as covering species it cannot detect."
)


# ---------------------------------------------------------------------------
# Comparative queries
# ---------------------------------------------------------------------------


def audibility_table(carrier_hz: float) -> list[dict]:
    """Every species ranked by how well it hears this carrier."""
    rows = []
    for key, s in SPECIES.items():
        oct_ = s.octaves_below_limit(carrier_hz)
        rows.append({
            "key": key,
            "name": s.name,
            "group": s.group.value,
            "limit_khz": s.hearing_high_hz / 1000.0,
            "octaves_below_limit": round(oct_, 3),
            "audible": s.audible(carrier_hz),
            "more_sensitive_than_target": (
                s.hearing_high_hz > SPECIES[TARGET_KEY].hearing_high_hz
            ),
            "detectable": s.coco_label is not None,
            "aggression": s.aggression.value,
        })
    return sorted(rows, key=lambda r: -r["octaves_below_limit"])


def more_sensitive_than_target(carrier_hz: float) -> list[str]:
    """Species that hear this carrier better than cattle do."""
    target_hi = SPECIES[TARGET_KEY].hearing_high_hz
    return [
        s.name for k, s in SPECIES.items()
        if k != TARGET_KEY and s.audible(carrier_hz) and s.hearing_high_hz > target_hi
    ]


def selectivity_verdict(carrier_hz: float) -> dict:
    """
    The headline finding, computed rather than asserted.

    Returns the number of non-target species that hear the carrier, how many of
    them beat the target, and the target's rank in the affected group.
    """
    table = [r for r in audibility_table(carrier_hz) if r["audible"]]
    target_rank = next(
        i + 1 for i, r in enumerate(table) if r["key"] == TARGET_KEY
    )
    beats = [r["name"] for r in table if r["more_sensitive_than_target"]]
    return {
        "carrier_khz": round(carrier_hz / 1000.0, 1),
        "species_that_hear_it": len(table),
        "non_target_species_affected": len(table) - 1,
        "more_sensitive_than_target": beats,
        "target_sensitivity_rank": f"{target_rank} of {len(table)}",
        "frequency_is_selective": False,
        "conclusion": (
            f"At {carrier_hz / 1000:.1f} kHz the target ranks {target_rank} of "
            f"{len(table)} species that can hear the signal. {len(beats)} "
            f"non-target species hear it BETTER than the animal we are aiming "
            f"at. Frequency provides no selectivity whatsoever; selectivity "
            f"must be enforced at the detection layer or not at all."
        ),
    }


def species_for_label(coco_label: str) -> tuple[SpeciesProfile, ...]:
    keys = COCO_TO_SPECIES.get(coco_label, ())
    return tuple(SPECIES[k] for k in keys if k in SPECIES)


def label_is_ambiguous(coco_label: str) -> bool:
    """True where one detector label covers more than one real species."""
    return len(COCO_TO_SPECIES.get(coco_label, ())) > 1


def child_audibility_risk(carrier_hz: float) -> float:
    """
    Probability that a child or adolescent perceives the carrier, 0..1.

    Separate from the adult curve because high-frequency hearing declines
    steadily with age (R13), and measurements of thresholds above 16 kHz show
    young listeners detecting tones well beyond the conventional 20 kHz limit
    (R23). Commercial anti-loitering devices exploit exactly this gap, operating
    near 17.4 kHz to be heard by teenagers and not by adults.

    The practical consequence: a 22 kHz carrier chosen because adults cannot
    hear it may still be audible to children. Near a school or dense housing
    the band floor must rise.

    HEURISTIC curve, ours. It only ever restricts operation.
    """
    # Anchor points: essentially certain at 17 kHz, negligible by about 26 kHz.
    lo, hi = 17_000.0, 26_000.0
    midpoint = (lo + hi) / 2.0
    steepness = 6.0 / (hi - lo)
    return 1.0 / (1.0 + math.exp(steepness * (carrier_hz - midpoint)))


def sensitive_receptor_floor_hz(near_school_or_housing: bool) -> float:
    """
    Minimum carrier permitted given nearby sensitive receptors.

    Returns 25 kHz near schools or dense housing rather than the usual 22 kHz
    band floor, because the child-audibility curve is still material at 22 kHz.
    """
    return 25_000.0 if near_school_or_housing else 22_000.0


def bat_echolocation_overlap(carrier_hz: float) -> dict:
    """
    Whether the carrier lands inside the echolocation band of insectivorous bats.

    Not an afterthought: the atmospheric-absorption measurement this system
    depends on (Lawrence & Simmons 1982, R14) is itself a paper about bat
    echolocation, because that is who uses these frequencies in air. Several
    molossid and vespertilionid bats call in the 20-35 kHz region, so a
    continuously operating emitter in this band could mask echolocation for
    foraging bats near the site.

    Mitigation is behavioural rather than spectral: event-triggered operation
    with sub-second bursts and enforced silence means total on-time is a
    negligible fraction of a night. That mitigation is asserted, not measured.
    """
    overlaps = 20_000.0 <= carrier_hz <= 60_000.0
    return {
        "carrier_khz": round(carrier_hz / 1000.0, 1),
        "overlaps_bat_echolocation": overlaps,
        "note": (
            "Some insectivorous bats echolocate in the 20-35 kHz region. "
            "Continuous operation in this band risks masking their calls."
            if overlaps else
            "Below the usual echolocation band for the species of concern."
        ),
        "mitigation": (
            "Event-triggered bursts only, sub-second duration, enforced silence "
            "between activations, and no standby emission. Total nightly on-time "
            "is expected to be seconds, not hours."
        ),
        "residual": (
            "Unquantified. No bat activity survey has been carried out at any "
            "site, and none of this has been measured."
        ),
        "grade": "Hypothesis",
    }


def summary(carrier_hz: float = 25_000.0) -> dict:
    return {
        "selectivity": selectivity_verdict(carrier_hz),
        "table": audibility_table(carrier_hz),
        "child_risk": round(child_audibility_risk(carrier_hz), 4),
        "bats": bat_echolocation_overlap(carrier_hz),
        "undetectable_at_risk": list(UNDETECTABLE_AT_RISK),
        "detection_gap_note": UNDETECTABLE_NOTE,
        "ambiguous_labels": [
            lbl for lbl in COCO_TO_SPECIES if label_is_ambiguous(lbl)
        ],
    }
