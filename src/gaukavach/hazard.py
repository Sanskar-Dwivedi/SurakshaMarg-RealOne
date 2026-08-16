"""
Hazard register.

A systematic enumeration of every way this system could cause harm, written in
the style of a safety case rather than a feature list. Thirty hazards across
six categories, each with severity, likelihood, the detection mechanism that
finds it, the mitigation in code, and - crucially - the RESIDUAL risk that
remains after mitigation.

Three rules were applied while writing it:

  1. A hazard with no mitigation is still listed. Deleting inconvenient rows is
     how safety cases become fiction.
  2. Residual risk is stated even where it is uncomfortable, and several rows
     end in "unquantified" because that is the truth.
  3. Hazards we cannot even DETECT get their own severity band, because an
     undetectable hazard is worse than a detected one and the register must not
     flatter itself by omitting them.

`unmitigated()` and `undetectable()` are the two queries a reviewer should run
first. They are also printed by `gaukavach hazards` so nobody has to go looking.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum


class Severity(str, Enum):
    CATASTROPHIC = "catastrophic"   # death or life-changing injury
    SEVERE = "severe"               # serious injury, animal death
    MODERATE = "moderate"           # distress, minor injury, service failure
    MINOR = "minor"                 # nuisance, inefficiency


class Likelihood(str, Enum):
    LIKELY = "likely"
    POSSIBLE = "possible"
    UNLIKELY = "unlikely"
    RARE = "rare"


class Status(str, Enum):
    MITIGATED = "mitigated in code"
    PARTIAL = "partially mitigated"
    ACCEPTED = "accepted, documented"
    OPEN = "OPEN - no mitigation"
    UNDETECTABLE = "UNDETECTABLE by this system"


_SEV_RANK = {
    Severity.CATASTROPHIC: 4, Severity.SEVERE: 3,
    Severity.MODERATE: 2, Severity.MINOR: 1,
}
_LIK_RANK = {
    Likelihood.LIKELY: 4, Likelihood.POSSIBLE: 3,
    Likelihood.UNLIKELY: 2, Likelihood.RARE: 1,
}


@dataclass(frozen=True)
class Hazard:
    id: str
    category: str
    title: str
    affected: str
    mechanism: str
    severity: Severity
    likelihood: Likelihood
    detection: str
    mitigation: str
    residual: str
    status: Status
    sources: tuple[str, ...] = ()

    @property
    def score(self) -> int:
        return _SEV_RANK[self.severity] * _LIK_RANK[self.likelihood]

    def as_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        d["likelihood"] = self.likelihood.value
        d["status"] = self.status.value
        d["score"] = self.score
        return d


REGISTER: tuple[Hazard, ...] = (

    # ---------------- Household and companion animals -------------------
    Hazard(
        "H01", "Household animals",
        "Dog exposed to the carrier",
        "Free-roaming and pet dogs",
        "Dogs hear to ~45 kHz - roughly twice as far inside their range at "
        "22-30 kHz as cattle are. The tone is louder to a dog than to the "
        "target animal, in every sense that matters.",
        Severity.SEVERE, Likelihood.LIKELY,
        "YOLO COCO 'dog' class, checked across the whole exposure cone before "
        "any authorisation is issued.",
        "Absolute veto. Denial.NON_TARGET blocks every request while a dog is "
        "present. Not a weighting, not a reduction in level - a hard stop.",
        "A dog outside the camera's field of view but inside the acoustic cone "
        "is not detected. Beam geometry and camera FOV are not yet formally "
        "reconciled.",
        Status.PARTIAL, ("R17", "R22"),
    ),
    Hazard(
        "H02", "Household animals",
        "Redirected aggression in dogs",
        "People near an exposed dog",
        "Acoustic stress is a documented trigger for redirected aggression. A "
        "startled dog may bite a bystander rather than flee, turning an animal "
        "welfare issue into a human injury.",
        Severity.SEVERE, Likelihood.POSSIBLE,
        "Same dog detection; no direct behavioural sensing.",
        "Covered by the same absolute dog veto - the system never knowingly "
        "stresses a dog in the first place.",
        "Depends entirely on detection recall. An undetected dog is an "
        "unmitigated hazard.",
        Status.PARTIAL, ("R17",),
    ),
    Hazard(
        "H03", "Household animals",
        "Cat exposed to the carrier",
        "Domestic and community cats",
        "Cats hear to ~85 kHz. A 25 kHz tone sits nearly two octaves inside "
        "their range - the most acoustically over-exposed animal at any site.",
        Severity.MODERATE, Likelihood.POSSIBLE,
        "COCO 'cat' class. Recall on small, low-contrast animals at night is "
        "poor and we have not measured it.",
        "Non-target veto.",
        "Small nocturnal animals are the weakest case for this detector. "
        "Unquantified.",
        Status.PARTIAL, ("R18",),
    ),
    Hazard(
        "H04", "Household animals",
        "Poultry and backyard birds",
        "Chickens, ducks",
        "Checked and found NOT to apply: chicken hearing tops out near 7 kHz, "
        "nearly two octaves below the carrier.",
        Severity.MINOR, Likelihood.RARE,
        "Not needed for this hazard.",
        "None required. Recorded so the register states what the system does "
        "not endanger, not only what it does.",
        "None identified.",
        Status.ACCEPTED, ("R22",),
    ),

    # ---------------- Herd animals and stampede -------------------------
    Hazard(
        "H05", "Herd and stampede",
        "Goat or sheep flock panic cascade",
        "Flocks, their herder, and every road user",
        "Goats hear to ~37 kHz and sheep to ~42.5 kHz, both above cattle. Both "
        "are strong flocking species: R9 showed virtual-fence responses are "
        "socially facilitated, so a startle in one animal propagates. A flock "
        "moving as one body in an unpredictable direction is a far worse road "
        "hazard than the original blockage.",
        Severity.CATASTROPHIC, Likelihood.POSSIBLE,
        "Same-species spatial clustering within a 12 m radius; group size "
        "compared against the emission threshold each frame.",
        "Denial.HERD_SIZE refuses emission entirely above 3 conspecifics and "
        "escalates to human dispatch. A herd is a dispatch problem, not an "
        "acoustic one.",
        "Threshold of 3 is our judgement, not a measured stampede threshold. "
        "No such measurement exists for ultrasonic provocation.",
        Status.MITIGATED, ("R9", "R19", "R20", "R24"),
    ),
    Hazard(
        "H06", "Herd and stampede",
        "Goats misdetected as sheep, or missed entirely",
        "Goat flocks",
        "COCO has no goat class. Goats are detected as 'sheep' when they are "
        "detected at all, so the count driving the herd threshold may be wrong.",
        Severity.SEVERE, Likelihood.LIKELY,
        "Label ambiguity is declared in species.COCO_TO_SPECIES and surfaced "
        "by label_is_ambiguous().",
        "The ambiguous 'sheep' label maps to BOTH species and the more "
        "restrictive profile is applied. Under-counting still triggers the "
        "non-target veto, which fails safe.",
        "Recall on Indian goat breeds with COCO weights is unmeasured. This is "
        "the single highest-value fine-tuning target.",
        Status.PARTIAL, ("R19",),
    ),
    Hazard(
        "H07", "Herd and stampede",
        "Herd breakthrough led by one animal",
        "Road users",
        "R9 found animals follow the reactions of group members. If leaders "
        "continue forward under acoustic pressure, the group follows them onto "
        "the carriageway.",
        Severity.CATASTROPHIC, Likelihood.POSSIBLE,
        "Per-animal attempt counters plus the group-size check.",
        "Attempt cap of 3, then escalation. The system stops rather than "
        "escalating pressure on a group that is already committed.",
        "Cannot be validated without a field trial on real herds.",
        Status.PARTIAL, ("R9",),
    ),

    # ---------------- Flight geometry -----------------------------------
    Hazard(
        "H08", "Flight geometry",
        "Animal driven ONTO the carriageway",
        "The animal and every road user",
        "The single worst failure mode in the whole design. An animal flees "
        "away from an aversive source. If the emitter sits so that 'away' "
        "means 'across the road', the device causes the exact collision it "
        "exists to prevent.",
        Severity.CATASTROPHIC, Likelihood.POSSIBLE,
        "Flight vector computed in metric ground coordinates from the emitter "
        "to the animal, then ray-cast 25 m forward and tested for intersection "
        "with the carriageway polygon.",
        "Denial.FLIGHT_INTO_HAZARD refuses the emission and escalates. This "
        "check alone means GauKavach is an APPROACH deterrent, not a "
        "road-clearer: an animal already mid-carriageway will usually be "
        "refused, which is the correct answer.",
        "Assumes flight is directly away from the source. Real flight paths "
        "depend on terrain, herd position and the animal's prior route. This "
        "is a first-order model.",
        Status.MITIGATED, ("R24",),
    ),
    Hazard(
        "H09", "Flight geometry",
        "Cornered animal with no escape route",
        "The animal",
        "Grandin's handling work is explicit that pressure applied to an "
        "animal with no viable exit produces panic rather than controlled "
        "movement, including attempts to climb or charge through barriers.",
        Severity.SEVERE, Likelihood.POSSIBLE,
        "Clear-corridor test along the flight vector; requires at least 8 m of "
        "ground away from the carriageway.",
        "Denial.NO_ESCAPE_ROUTE.",
        "Walls, ditches and fences are not in the site model - only the "
        "carriageway polygon is. Real obstacles would need surveying.",
        Status.PARTIAL, ("R24",),
    ),
    Hazard(
        "H10", "Flight geometry",
        "Tethered or restrained animal",
        "The animal",
        "A tethered animal cannot leave no matter how aversive the signal. "
        "Continuing to emit is pure distress with zero possible benefit.",
        Severity.SEVERE, Likelihood.POSSIBLE,
        "Displacement after a completed emission; less than 1.5 m of movement "
        "flags possible restraint, injury or illness.",
        "Denial.IMMOBILE_ANIMAL, permanent do-not-emit flag for that animal, "
        "and escalation for human inspection.",
        "Requires one emission to have already occurred before the condition "
        "is detectable. We cannot see a rope.",
        Status.PARTIAL, ("R24",),
    ),
    Hazard(
        "H11", "Flight geometry",
        "Downed, sick or injured animal harassed",
        "The animal",
        "An animal that is recumbent or collapsed cannot respond and must be "
        "rescued, not nudged.",
        Severity.SEVERE, Likelihood.UNLIKELY,
        "Bounding-box aspect ratio above 1.6 flags possible recumbency. Crude, "
        "and deliberately biased toward false positives.",
        "Denial.DOWNED_ANIMAL plus immediate escalation for veterinary or "
        "municipal response.",
        "Aspect ratio confuses a grazing animal with a downed one. We accept "
        "the false positives; the asymmetry of harm justifies it.",
        Status.PARTIAL, ("R24",),
    ),

    # ---------------- Vulnerable individuals ----------------------------
    Hazard(
        "H12", "Vulnerable individuals",
        "Dam with young at foot",
        "People and the calf or kid",
        "Maternal defence is the classic livestock aggression scenario, and "
        "the young animal is itself more vulnerable to acoustic stress.",
        Severity.SEVERE, Likelihood.POSSIBLE,
        "Real-world height estimated from bounding box and range; below 70% of "
        "species-typical adult height the animal is treated as juvenile.",
        "Denial.JUVENILE_PRESENT vetoes emission anywhere in the group.",
        "Height estimation inherits the camera's ~20% calibration error AND "
        "degrades with range - a calf far from the camera can measure as an "
        "adult and be missed. In testing, a calf was only classified correctly "
        "once inside roughly 20 m. Juvenile protection is therefore weakest "
        "exactly where first contact happens.",
        Status.MITIGATED, ("R24",),
    ),
    Hazard(
        "H13", "Vulnerable individuals",
        "Children hear a carrier adults cannot",
        "Children and adolescents near the site",
        "High-frequency hearing declines with age. A 22 kHz carrier selected "
        "because adults cannot hear it may still be plainly audible to a "
        "child - commercial anti-loitering devices exploit exactly this gap "
        "near 17.4 kHz.",
        Severity.MODERATE, Likelihood.LIKELY,
        "Not detectable per-individual. Handled as a SITE property.",
        "sensitive_receptor_floor_hz() raises the band floor to 25 kHz near "
        "schools or dense housing, and a separate child-audibility curve is "
        "reported alongside the adult one rather than hidden inside it.",
        "Site classification is a manual configuration input. Nobody verifies "
        "that the installer set it honestly.",
        Status.PARTIAL, ("R13", "R23"),
    ),
    Hazard(
        "H14", "Vulnerable individuals",
        "Hearing aids and cochlear implants",
        "Hearing-aid and implant users",
        "Ultrasonic energy can intermodulate in a hearing-aid microphone and "
        "front end, producing audible artefacts for a listener who could not "
        "otherwise perceive the carrier at all.",
        Severity.MODERATE, Likelihood.POSSIBLE,
        "Not detectable.",
        "Indirect only: any detected person vetoes emission, and total on-time "
        "is bounded to seconds.",
        "OPEN. We found no measurement of ultrasonic intermodulation in modern "
        "hearing aids and are not competent to assert one. Flagged as a "
        "question for an audiologist before any deployment near people.",
        Status.OPEN, ("R13",),
    ),
    Hazard(
        "H15", "Vulnerable individuals",
        "Hyperacusis, tinnitus, migraine sensitivity",
        "Susceptible bystanders",
        "Some people report discomfort from ultrasonic sources at levels "
        "others do not perceive.",
        Severity.MINOR, Likelihood.POSSIBLE,
        "Not detectable.",
        "Person veto plus bounded on-time. A published complaints channel is "
        "specified as an operational requirement, not a code feature.",
        "Accepted and documented. No individualised protection is possible.",
        Status.ACCEPTED, ("R13",),
    ),

    # ---------------- Working animals -----------------------------------
    Hazard(
        "H16", "Working animals",
        "Draught animal bolts while harnessed",
        "The handler, the animal, the load, other road users",
        "A bolting bullock or horse pulling a cart is among the most dangerous "
        "outcomes imaginable here - and the handler is a person standing "
        "directly inside the exposure cone.",
        Severity.CATASTROPHIC, Likelihood.UNLIKELY,
        "COCO 'horse' class; a person adjacent to a large animal is a strong "
        "cue for a working pairing.",
        "Horses are vetoed unconditionally as non-target, and any person in "
        "the cone independently vetoes emission. Two separate rules must both "
        "fail for this to occur.",
        "A bullock harnessed to a cart is detected as 'cow' - the target class. "
        "The person veto is the only thing standing between us and this "
        "hazard, and it depends on the handler being visible.",
        Status.PARTIAL, ("R1", "R24"),
    ),

    # ---------------- Wildlife ------------------------------------------
    Hazard(
        "H17", "Wildlife",
        "Masking of bat echolocation",
        "Insectivorous bats",
        "Several bats echolocate in the 20-35 kHz region. This is not a "
        "coincidence - the atmospheric absorption measurement this system "
        "depends on (R14) is itself a bat echolocation paper, because bats are "
        "who uses these frequencies in air.",
        Severity.MODERATE, Likelihood.POSSIBLE,
        "Not detectable.",
        "Behavioural rather than spectral: event-triggered sub-second bursts, "
        "enforced silence, no standby emission. Expected nightly on-time is "
        "seconds.",
        "Unquantified. No bat activity survey has been done at any site.",
        Status.PARTIAL, ("R14",),
    ),
    Hazard(
        "H18", "Wildlife",
        "Macaques and other undetectable species",
        "Monkeys, pigs, small wildlife",
        "Rhesus macaques are common on Indian roads and highly reactive. COCO "
        "has no macaque class and no pig class.",
        Severity.SEVERE, Likelihood.POSSIBLE,
        "NONE. The perception stack is blind to these species.",
        "None available. The system must not be described as protecting "
        "species it cannot see.",
        "OPEN and undetectable. Requires a custom-trained detector before any "
        "site with known macaque presence.",
        Status.UNDETECTABLE, ("R22",),
    ),

    # ---------------- System and operational ----------------------------
    Hazard(
        "H19", "System",
        "Misclassification: dog detected as cow",
        "The misclassified animal",
        "A confident wrong label routes a non-target into the target path.",
        Severity.SEVERE, Likelihood.UNLIKELY,
        "Detector confidence threshold; per-class scoring.",
        "Partial: the non-target veto only helps when the label is right. "
        "Confidence floor of 0.35 is a blunt instrument.",
        "No confusion matrix has been measured on Indian road footage. This is "
        "an unquantified failure mode.",
        Status.PARTIAL, (),
    ),
    Hazard(
        "H20", "System",
        "Detection failure creates false confidence",
        "Road users",
        "An operator who believes the site is protected relaxes other "
        "precautions. A missed animal is then worse than no system.",
        Severity.SEVERE, Likelihood.POSSIBLE,
        "Not self-detectable - by definition the system cannot see what it "
        "missed.",
        "The traffic-control layer fires on ANY detection at any range and is "
        "never gated on acoustic feasibility, so the proven mitigation does "
        "not depend on the unproven one. Documentation states plainly that "
        "this is not a containment system.",
        "Irreducible. Any detector has finite recall.",
        Status.ACCEPTED, ("R5",),
    ),
    Hazard(
        "H21", "System",
        "Distance error causes over- or under-exposure",
        "The target animal",
        "Level is solved from estimated range. A range error becomes a level "
        "error directly.",
        Severity.MODERATE, Likelihood.LIKELY,
        "Inverse-perspective mapping with a stated ~20% error band.",
        "Range decisions use the pessimistic absorption model and exposure "
        "decisions the optimistic one, so both errors fall on the safe side. "
        "The ceiling is an absolute backstop regardless of range.",
        "Uncalibrated camera. A measured homography is required before "
        "deployment.",
        Status.PARTIAL, ("R15",),
    ),
    Hazard(
        "H22", "System",
        "Audible artefacts from hardware nonlinearity",
        "Everyone nearby",
        "A hard-gated burst splatters broadband energy into the audible band, "
        "and real amplifiers and transducers add nonlinearity on top.",
        Severity.MODERATE, Likelihood.LIKELY,
        "FFT self-inspection of the synthesised buffer before playback.",
        "Raised-cosine envelope on every burst, roughly 98 dB improvement in "
        "the audible band, plus refusal to play a buffer that fails the check.",
        "The check models a linear chain. Only a calibrated ultrasonic "
        "microphone on real hardware settles this.",
        Status.PARTIAL, ("R13",),
    ),
    Hazard(
        "H23", "System",
        "Stuck-on emitter",
        "Every animal and person in range",
        "A software hang or power fault leaves the emitter radiating "
        "continuously - the worst possible exposure profile.",
        Severity.SEVERE, Likelihood.UNLIKELY,
        "Watchdog timer; maximum activation of 6 s enforced per request.",
        "Hard duration cap in the governor. A hardware watchdog that "
        "de-energises the amplifier is specified as a build requirement.",
        "The hardware watchdog does not exist yet - there is no hardware. "
        "Software alone cannot guarantee this.",
        Status.PARTIAL, ("R16",),
    ),
    Hazard(
        "H24", "System",
        "Habituation produces silent failure",
        "Road users",
        "Response decays with repeated unpaired exposure - our projection puts "
        "it near 0.1 by day ten. The system keeps operating while quietly "
        "ceasing to work.",
        Severity.MODERATE, Likelihood.LIKELY,
        "Per-animal exposure counters and the habituation projection in the "
        "twin.",
        "Pattern and carrier variation between exposures; the ledger records "
        "response rate per animal per day so decay is measurable rather than "
        "assumed.",
        "Variation is a HYPOTHESIS-grade mitigation. It may not work.",
        Status.PARTIAL, ("R5", "R6", "R11"),
    ),
    Hazard(
        "H25", "System",
        "Operator tampers with the record",
        "Regulators, the public",
        "An operator rewrites a night in which something went wrong.",
        Severity.MODERATE, Likelihood.UNLIKELY,
        "SHA-256 hash chain; verify() recomputes the whole ledger.",
        "Any edit or deletion invalidates every subsequent record.",
        "Single-writer log. It detects post-hoc edits but does not prove the "
        "writer was honest at write time. External timestamping would be "
        "needed for that.",
        Status.PARTIAL, (),
    ),

    # ---------------- Misuse and governance -----------------------------
    Hazard(
        "H26", "Misuse",
        "Used as safety-critical containment",
        "Road users",
        "Someone deploys this along a highway or railway boundary and removes "
        "the fence. R5 is explicit that acoustic cues are not stock-proof.",
        Severity.CATASTROPHIC, Likelihood.POSSIBLE,
        "Not technically detectable - this is a governance failure.",
        "Refused in documentation at every level, and the architecture "
        "enforces it: the acoustic layer has a 3-attempt cap and always "
        "escalates, so it structurally cannot behave like a barrier.",
        "A determined operator can ignore all of this. Real mitigation is "
        "contractual and regulatory.",
        Status.PARTIAL, ("R5",),
    ),
    Hazard(
        "H27", "Misuse",
        "Level raised beyond the welfare ceiling",
        "Animals and people",
        "Someone points at the 142 dB prototype paper and asks for more power.",
        Severity.CATASTROPHIC, Likelihood.UNLIKELY,
        "Governor adjudicates every request; nothing reaches the amplifier "
        "without a signed authorisation.",
        "The ceiling is not a configuration value an operator can raise. Even "
        "a signed ethics token only reaches the top of the cited occupational "
        "band, and a test asserts no emission in any scenario exceeds it.",
        "Someone could fork the code. Nothing prevents that.",
        Status.MITIGATED, ("R4", "R13"),
    ),
    Hazard(
        "H28", "Misuse",
        "Emitter aimed at a dwelling or school",
        "Residents, pupils",
        "Poor siting points a directional beam at occupied buildings.",
        Severity.MODERATE, Likelihood.POSSIBLE,
        "Not automatically detectable.",
        "Site configuration carries a sensitive-receptor flag that raises the "
        "band floor; a siting checklist is specified as an install requirement.",
        "Depends entirely on honest installation.",
        Status.PARTIAL, ("R13", "R23"),
    ),
    Hazard(
        "H29", "Misuse",
        "Legal non-compliance on containment standards",
        "The operator",
        "Many jurisdictions specify fencing or containment standards "
        "regardless of what a technical deterrent achieves.",
        Severity.MODERATE, Likelihood.POSSIBLE,
        "n/a",
        "Documented prominently; the system is positioned as a deterrent layer "
        "and never as a legal containment boundary.",
        "Accepted. Legal review is required per jurisdiction.",
        Status.ACCEPTED, (),
    ),
    Hazard(
        "H30", "Misuse",
        "Frequency selectivity misunderstood as species selectivity",
        "Every non-target animal",
        "The most common conceptual error in this entire product category: "
        "believing an ultrasonic carrier only affects the intended species. "
        "The comparative audiogram shows cattle rank second-LAST among "
        "affected species - five household and farm animals hear it better.",
        Severity.SEVERE, Likelihood.LIKELY,
        "species.selectivity_verdict() computes the ranking for any carrier "
        "and returns frequency_is_selective = False.",
        "The finding is stated in the module docstring, the CLI, the README "
        "and the dashboard, and it is the stated architectural reason that all "
        "selectivity lives in the detector.",
        "None. This one is genuinely closed - the finding is computed, not "
        "asserted, and a test locks it in.",
        Status.MITIGATED, ("R1", "R17", "R18", "R19", "R20", "R22"),
    ),
)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def by_score() -> list[Hazard]:
    return sorted(REGISTER, key=lambda h: (-h.score, h.id))


def unmitigated() -> list[Hazard]:
    """Hazards with no mitigation, or none this system can apply."""
    return [h for h in REGISTER if h.status in (Status.OPEN, Status.UNDETECTABLE)]


def undetectable() -> list[Hazard]:
    return [h for h in REGISTER if h.status is Status.UNDETECTABLE]


def catastrophic() -> list[Hazard]:
    return [h for h in REGISTER if h.severity is Severity.CATASTROPHIC]


def by_category() -> dict[str, list[Hazard]]:
    out: dict[str, list[Hazard]] = {}
    for h in REGISTER:
        out.setdefault(h.category, []).append(h)
    return out


def summary() -> dict:
    status_counts: dict[str, int] = {}
    for h in REGISTER:
        status_counts[h.status.value] = status_counts.get(h.status.value, 0) + 1
    sev_counts: dict[str, int] = {}
    for h in REGISTER:
        sev_counts[h.severity.value] = sev_counts.get(h.severity.value, 0) + 1
    return {
        "total_hazards": len(REGISTER),
        "categories": len(by_category()),
        "by_status": status_counts,
        "by_severity": sev_counts,
        "catastrophic": [h.id for h in catastrophic()],
        "open_or_undetectable": [h.id for h in unmitigated()],
        "highest_scoring": [
            {"id": h.id, "title": h.title, "score": h.score} for h in by_score()[:5]
        ],
        "honesty_note": (
            f"{len(unmitigated())} of {len(REGISTER)} hazards are open or "
            f"undetectable and are listed anyway. A register with no open rows "
            f"has been edited, not completed."
        ),
    }


def export() -> list[dict]:
    return [h.as_dict() for h in by_score()]
