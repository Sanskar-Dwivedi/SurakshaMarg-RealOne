# GauKavach

**An acoustic livestock deterrent that is only permitted to act inside the envelope published evidence supports.**

Livestock on the carriageway is a real traffic problem in India: it blocks lanes,
creates queues that outlast the blockage, and kills both animals and people. The
obvious fix — an ultrasonic emitter that moves the animal — has one serious
problem, which is that the evidence for it barely exists. A 2025 prototype paper
is the *only* direct cattle-ultrasound study, and it reported 142 dB SPL at 1 m,
around 27 dB above the international occupational ceiling for that band.

Most systems built on that literature quietly overclaim. GauKavach encodes the
weakness as engineering constraints instead:

| It refuses to | Because |
|---|---|
| Reproduce the 142 dB prototype level | ~27 dB over the cited occupational ceiling (R13) |
| Emit with a dog, cat, goat, sheep or horse in the cone | Every one of them hears the carrier **better than cattle do** |
| Emit at a group of more than 3 animals | Responses are socially facilitated; a startle cascades into a stampede (R9) |
| Emit when fleeing would take the animal onto the road | It would cause the exact collision it exists to prevent |
| Emit at a juvenile, a downed animal, or one that cannot move | Vulnerable, or physically unable to escape |
| Claim a turn-away rate | No published dose-response curve exists for cattle at 22-30 kHz |
| Act as a containment barrier | Umstatter et al. showed audio cues are not stock-proof (R5) |
| Get louder when an animal ignores it | The level is a computed minimum, not a volume control |
| Keep trying indefinitely | Three attempts, then it stops and escalates to a human |

## The finding that reshaped the design

Ultrasonic deterrents are sold on the premise that the frequency is
species-selective. We checked that against comparative audiograms measured at
the **same 60 dB SPL criterion** as the cattle data. The premise is not merely
unproven — it is backwards.

```
$ gaukavach species --carrier 25000

species          group        limit    octaves inside range
Cat              household   85.0kHz     +1.766   hears it BETTER than the target
Dog              household   45.0kHz     +0.848   hears it BETTER than the target
Sheep            livestock   42.5kHz     +0.766   hears it BETTER than the target
Pig              livestock   40.5kHz     +0.696   hears it BETTER than the target
Goat             livestock   37.0kHz     +0.566   hears it BETTER than the target
Cattle           target      35.0kHz     +0.485   <<< THE TARGET
Horse / donkey   working     33.5kHz     +0.422
Human (adult)    human       17.6kHz     -0.506   inaudible
Chicken          livestock    7.2kHz     -1.796   inaudible

frequency_is_selective  : False
target sensitivity rank : 6 of 7
```

**Cattle are second-least sensitive of every species that can hear the signal.**
Five household and farm animals hear it better than the animal being aimed at.
A goat flock beside the road is not an incidental bystander to this device — it
is a more sensitive receiver than the target.

The consequence is architectural: selectivity cannot come from the frequency, so
it must come from the detector or it does not exist. Every non-target veto in
`welfare.py` traces to this table, and a test locks the finding in place.

The traffic-control response — variable message sign, signal hold, dispatch
ticket — fires immediately and independently, because *that* mechanism is not in
doubt. The acoustic nudge is an adjunct to it, never a replacement.

---

## The working prototype

**Open `dashboard/simulator.html` in any browser.** Self-contained, no server,
no internet. Twelve scenarios, a scrub bar, a draggable sandbox, and a decision
field that paints the governor's verdict for every position on the road at once.

It is not a mock: `gaukavach sim` runs the real Python engine over every
scenario and a 1,412-point grid and embeds the results. The browser replays and
looks up; it contains no decision logic of its own. Full guide in
[docs/PROTOTYPE.md](docs/PROTOTYPE.md).

```bash
python -m gaukavach sim                          # rebuild the simulator
python -m gaukavach render --all --outdir media  # MP4 of every scenario
python -m gaukavach render --video clip.mp4      # overlay on REAL footage
```

---

## Quick start

```bash
pip install -e .                 # numpy only; vision extras are optional
pytest -q                        # 92 tests
python -m gaukavach demo         # the whole argument, in presentation order
```

Individual commands, each answering one sceptical question:

```bash
python -m gaukavach evidence --full   # every constant, its grade, its source
python -m gaukavach species           # who ELSE hears this - the key finding
python -m gaukavach hazards           # 30-hazard register with residual risk
python -m gaukavach hazards --open-only   # only what we CANNOT mitigate
python -m gaukavach citations         # references still needing verification
python -m gaukavach physics           # propagation validated against published values
python -m gaukavach envelope          # what the physics actually permits
python -m gaukavach refuse            # proof the 142 dB level is unreachable
python -m gaukavach spectrum          # why a hard-gated burst is audible
python -m gaukavach behaviour         # dose-response intervals + field-trial sizing
python -m gaukavach traffic           # queueing impact of a blockage
python -m gaukavach run person-in-cone --verbose
python -m gaukavach video clip.mp4    # real YOLO perception, if you have footage
```

---

## Architecture

```
                    ┌─────────────────────────────────────────┐
   camera ────────► │ detect.py   YOLO + tracker + zone geom  │
                    │             cow / dog / horse / person  │
                    └──────────────┬──────────────────────────┘
                                   │ tracks, distance, approach vector
                    ┌──────────────▼──────────────────────────┐
                    │ policy.py   Detect→Classify→Decide→Emit  │
                    │             →Observe→Stop→Escalate→Log   │
                    └───┬───────────────────┬──────────────┬───┘
      always, any range │                   │              │
          ┌─────────────▼──────┐  ┌─────────▼────────┐  ┌──▼──────────┐
          │ traffic.py         │  │ acoustics.py     │  │ ledger.py   │
          │ VMS · signal hold  │  │ ISO 9613-1 +     │  │ SHA-256     │
          │ dispatch ticket    │  │ L&S link budget  │  │ hash chain  │
          │ PROVEN MECHANISM   │  └─────────┬────────┘  └─────────────┘
          └────────────────────┘            │ required dB @1m
                                  ┌─────────▼────────┐
                                  │ welfare.py       │  ← says NO
                                  │ the governor     │
                                  └─────────┬────────┘
                                            │ signed Authorisation only
                                  ┌─────────▼────────┐
                                  │ emitter.py       │
                                  │ ramped burst +   │
                                  │ spectral self-   │
                                  │ inspection       │
                                  └──────────────────┘
```

| Module | Responsibility |
|---|---|
| `evidence.py` | Every constant, with source and evidence grade. Ungraded numbers cannot be fetched. |
| `species.py` | Comparative audiograms, aggression and flocking profiles, child-audibility curve |
| `hazard.py` | 30-row hazard register: severity, likelihood, mitigation, residual risk |
| `acoustics.py` | ISO 9613-1 and Lawrence & Simmons absorption, link budget, carrier selection |
| `welfare.py` | The governor. Enforces limits, issues or denies signed authorisations |
| `emitter.py` | Waveform synthesis, raised-cosine ramping, FFT self-inspection, anti-habituation scheduler |
| `detect.py` | YOLO perception, IoU tracker, inverse-perspective distance, zone geometry |
| `policy.py` | The closed-loop state machine and escalation |
| `twin.py` | Behavioural prior with Monte Carlo credible intervals, field-trial sizing |
| `traffic.py` | Deterministic queueing impact model, signal response plan |
| `ledger.py` | Append-only hash-chained audit log |
| `scenario.py` | Twelve synthetic scenarios exercising every branch, including every veto |
| `simulate.py` | Exports real engine decisions for the browser simulator |
| `render.py` | OpenCV renderer: scenario MP4s, and overlay on real video |

---

## Six things here that are genuinely uncommon

**1. Every number carries its evidence grade, and the grades are load-bearing.**
`evidence.py` is a registry: a constant that is our own guess is graded
`HEURISTIC` and `Grade.actionable` returns `False` for it. `ev.get()` raises on
any name that was never declared, so a magic number is a crash, not a silent
assumption. This caught a real bug during development — the carrier optimiser
was selecting 20 kHz, contradicting OSHA's own statement that 20 kHz is not
reliably inaudible, because the risk threshold that allowed it was undeclared.

**2. The system computes its own range envelope and refuses outside it.**
Heffner & Heffner define the cattle hearing range at a **60 dB SPL criterion**,
which converts an audiogram into a hard link budget: the signal must *arrive* at
≥60 dB, plus a margin over roadside noise. Working back through spreading and
absorption gives the required emitter level, and whether it is even legal. At
the demo site the answer is ~42.8 m at 22 kHz and ~22.5 m at 30 kHz — the
frequency the one cattle prototype used. Returning "no feasible carrier" is a
first-class outcome that triggers escalation, not a louder emitter.

**3. Two absorption models are carried because they disagree.**
ISO 9613-1 predicts 0.911 dB/m at 30 kHz; Lawrence & Simmons *measured* 0.700.
Range decisions use the pessimistic model, exposure decisions the optimistic
one, so both errors fall on the safe side. ISO 9613-1's stated validity ends at
10 kHz, so every use above that is labelled an extrapolation rather than passed
off as standards compliance.

**4. The emitter inspects its own waveform before playing it.**
A 25 kHz burst switched on and off abruptly is not a 25 kHz signal — the
rectangular gate splatters broadband energy into the audible band and the device
clicks at every activation. OSHA documents exactly this. Every burst is
raised-cosine ramped (a ~98 dB improvement in the audible band in our linear
model) and the device FFTs its own buffer and refuses to play anything failing
the check.

**5. Flight geometry is checked before the acoustics are.**
An animal flees away from an aversive source. If the emitter sits so that
"away" means "across the road", the device causes the exact collision it exists
to prevent. The flight vector is computed in metric ground coordinates and
ray-cast 25 m forward against the carriageway polygon. This check produced a
finding we did not set out to make: **GauKavach is an approach deterrent, not a
road-clearer.** An animal already mid-carriageway is refused, because clearing
it needs a human or a far-side emitter, never more volume.

**6. The behavioural model refuses to give a point estimate.**
No dose-response curve exists for cattle at these frequencies. `twin.py` returns
90% credible intervals over an explicit prior and prints `UNINFORMATIVE - the
prior dominates` at every level the welfare ceiling permits. Its useful output
is not a performance claim but a **field-trial specification**: 27 approaches
per arm, 54 total, clustered by herd because responses are socially facilitated.

---

## Protecting non-target animals

Three layers, in the order they are evaluated:

| Layer | Mechanism |
|---|---|
| **Species veto** | Dog, cat, sheep/goat, horse or person anywhere in the cone -> absolute stop |
| **Group veto** | More than 3 grouped conspecifics -> refuse and escalate; a flock is a dispatch problem |
| **Individual veto** | Juvenile, downed, or immobile-after-emission -> refuse and flag |

Plus two site-level protections:

- **Children.** High-frequency hearing declines with age, so a carrier chosen
  because adults cannot hear it may be plainly audible to a child — our model
  puts child audibility at **42% at 22 kHz** against 0.45% for adults. Near a
  school or dense housing the band floor rises to 25 kHz.
- **Bats.** Several insectivorous bats echolocate at 20-35 kHz. Not a
  coincidence: the atmospheric-absorption paper this system depends on (R14) is
  itself a bat echolocation study. Mitigated by sub-second event-triggered
  bursts only. Residual risk: unquantified.

Declared detection gaps, because a system must not be described as protecting
what it cannot see: **macaques and pigs have no COCO class at all**, and goats
are detected as "sheep" or missed entirely.

## Hazard register

`gaukavach hazards` prints 30 hazards across 8 categories, each with severity,
likelihood, detection mechanism, mitigation and **residual risk**.

```
30 hazards across 8 categories
  OPEN - no mitigation             1
  UNDETECTABLE by this system      1
  accepted, documented             4
  mitigated in code                5
  partially mitigated             19

  Catastrophic severity : H05, H07, H08, H16, H26, H27
  Open or undetectable  : H14, H18
```

The two we cannot close are stated rather than deleted:

- **H14** — ultrasonic intermodulation in hearing aids and cochlear implants.
  We found no measurement and are not competent to assert one. Flagged as a
  question for an audiologist before any deployment near people.
- **H18** — macaques and other species with no detector class. No mitigation
  available; requires a custom-trained detector before any site with known
  macaque presence.

A register with no open rows has been edited, not completed.

## Hardware

A **bench governor** you can build in Tinkercad in ~15 minutes lives in
[hardware/](hardware/): the same vetoes as `welfare.py`, enforced independently
by a microcontroller that does not trust the host. Two layers must agree before
a transducer is energised, and either can stop it alone.

Step-by-step build guide: **[hardware/build_steps.html](hardware/build_steps.html)**.
Reference diagrams: **[hardware/wiring.html](hardware/wiring.html)**
(pin numbers parsed from the sketches, so the picture cannot drift from the code).

> Tinkercad Circuits cannot simulate an ESP32 — Uno only. Both sketches are
> provided; the Wokwi `diagram.json` wires the ESP32 version for you.

A test asserts the firmware limits never drift from `evidence.py`.

The deterrent hardware itself does not exist, and that is stated everywhere. One-page costed BOM:
**[docs/GauKavach_Hardware_BOM.pdf](docs/GauKavach_Hardware_BOM.pdf)**
(regenerate with `python tools/make_hardware_pdf.py`). Full notes in
[docs/HARDWARE.md](docs/HARDWARE.md)
sets out what a live hardware demo would need, tiered by **what each purchase
lets you honestly claim**:

| Tier | Spend | Unlocks |
|---|---|---|
| 0 | none | decision layer, real footage, outcome model (what exists today) |
| 1 | ~₹12–22k | a genuine 22–30 kHz carrier through a real transducer, plus an E-stop watchdog |
| 2 | +₹25–40k | **measured** SPL and spectrum — where the numbers stop being predictions |
| 3 | +₹60k–1.5L | field prototype, and it goes nowhere without animal-ethics approval |

Three traps worth knowing before spending anything: the cheap hobby ultrasonic
modules are 40 kHz resonators and sit **outside** the cattle audiogram; most
audio amplifiers roll off at 20 kHz, exactly where this band starts; and a phone
microphone physically cannot measure 25 kHz, so any decibel figure quoted without
a calibrated ultrasonic mic is fabricated.

## What this repository does *not* contain

Stated plainly, because being caught by it is worse than admitting it.

- **No hardware.** No transducer, amplifier or field measurement. Every emission
  is marked `dry_run: true`, and a test asserts nothing anywhere claims otherwise.
- **No cattle were exposed to anything.** The behavioural model is a prior.
- **No camera calibration.** Distances use inverse-perspective mapping with
  plausible defaults and carry roughly ±20% error. Deployment needs a measured
  homography.
- **The spectral check is a linear model.** Real amplifiers and transducers add
  nonlinearity it does not capture. Only a calibrated ultrasonic microphone settles it.
- **No cattle-specific welfare threshold exists** for 22-35 kHz anywhere in the
  literature. We substitute a human occupational ceiling and label that
  substitution every time it appears.

---

## Evidence base

All sixteen sources are in `evidence.py` with DOIs. The load-bearing ones:

| Key | Source | Used for |
|---|---|---|
| R1 | Heffner & Heffner (1983), *Behav. Neurosci.* 97(2) | Audiogram, 60 dB SPL criterion |
| R4 | Taddy et al. (2025), *Nigerian J. Physics* 34(4) | The 142 dB figure we refuse |
| R5 | Umstatter et al. (2013), *Appl. Anim. Behav. Sci.* 147 | Audio cues are not stock-proof |
| R9 | Keshavarzi et al. (2020), *Front. Vet. Sci.* 7 | Social facilitation in herds |
| R13 | OSHA Technical Manual III-5, App. C | Human audibility, subharmonics, ceilings |
| R14 | Lawrence & Simmons (1982), *JASA* 71(3) | Measured ultrasonic absorption |
| R15 | ISO 9613-1:1993 | Analytical absorption model |
| R17-R22 | Heffner lab comparative audiograms | Dog, cat, goat, pig, sheep, elephant hearing |
| R23 | Ashihara (2007), *JASA* 122(3) | Hearing thresholds above 16 kHz (child audibility) |
| R24 | Grandin (1997), *J. Anim. Sci.* 75(1) | Flight zone; pressure without an escape route |

Run `gaukavach citations` for the pre-submission checklist of references not yet
personally retrieved. Sources carry a `first_party_verified` flag precisely
because a citation carried from memory is a liability in this kind of review.

---

## Testing

```bash
pytest -q          # 92 passed, 9 skipped
```

Tests are written as **claims**, so the test names read as the assertions the
project makes:

```
test_propagation_reproduces_the_published_table
test_the_142_db_prototype_level_is_unreachable
test_a_person_in_the_cone_blocks_every_emission
test_optimiser_never_selects_below_the_documented_band
test_granted_level_is_the_minimum_sufficient_not_the_maximum
test_twin_admits_the_intervals_are_uninformative
test_tampering_with_history_is_detected
test_no_emission_ever_exceeds_the_ceiling_in_any_scenario
test_all_emissions_are_marked_dry_run
test_persistent_blocker_escalates_instead_of_getting_louder
test_frequency_provides_no_species_selectivity
test_household_animals_are_all_more_sensitive_than_the_target
test_large_group_blocks_emission
test_animal_on_road_is_never_pushed_across_it
test_no_scenario_with_a_nontarget_animal_ever_emits
test_hazard_register_admits_unmitigated_hazards
test_every_hazard_states_a_residual_risk
```

---

## Licence and status

Research prototype. Not veterinary, legal or regulatory approval for a device.
Animal-welfare requirements and livestock-containment law vary by jurisdiction;
safety-critical containment must use methods meeting the applicable legal and
engineering standard for the site.
