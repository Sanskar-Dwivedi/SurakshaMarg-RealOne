# Demo script — 7 minutes

The whole pitch inverts the usual hackathon move. Other teams claim their thing
works. You claim you found out **where it stops working**, and built a system
that respects that boundary. Judges cannot attack humility that is backed by
running code — and every one of them has already sat through four demos that
overclaimed.

Run everything from the repo root. Have **`dashboard/simulator.html` open in a
browser** and one terminal ready. The simulator is the demo; the terminal is the
proof. See [PROTOTYPE.md](PROTOTYPE.md) for the simulator controls.

---

## The one-sentence version

> "Cattle on the road is a real traffic problem. The obvious fix is an
> ultrasonic emitter — and when we researched it properly we found the evidence
> for that is one prototype paper running at a sound level 27 dB above the
> occupational safety ceiling. So we built the system that *knows that*: it
> computes what physics permits, refuses what welfare forbids, and calls a human
> when sound stops being justified."

---

## Minute 0:00–0:45 · The problem, and the trap

Say the numbers, then say the trap out loud before a judge finds it.

- Livestock blockages create queues that take longer to clear than the blockage
  lasted. `python -m gaukavach traffic` shows a 120 s blockage costing far more
  than twice a 60 s one.
- "The obvious build is a cow buzzer. We started there. Then we read the
  literature."
- Show the refusal tile on the dashboard: **142 dB refused**.

> "The only published cattle-ultrasound prototype ran at 142 dB SPL at one
> metre. That's about 27 dB above the international occupational ceiling for
> that band — over 500 times the acoustic intensity. Building that would have
> been easy. We built the thing that refuses to."

---

## Minute 0:45–1:45 · The refusal (lead with this)

```bash
python -m gaukavach refuse
```

Point at `"granted": false` twice — once without an ethics token, once with.

> "There is no volume control in this system. The emitted level is solved from
> a link budget for that specific animal at that distance in that weather, so a
> closer animal always gets *less* power. An operator cannot turn it up. And
> even a signed animal-ethics authorisation only raises the ceiling to the top
> of the cited occupational band — the prototype level is unreachable by
> configuration, not by policy."

**Then immediately run the scenario that emits nothing:**

```bash
python -m gaukavach run person-in-cone --verbose
```

> "A pedestrian walks into the exposure cone while a cow approaches. The system
> detects the cow, computes a valid carrier, and emits nothing at all. Total
> emission: zero seconds. Bystander safety isn't a check inside the pipeline —
> it's a precondition of the pipeline."

---

## Minute 1:45–2:45 · The finding that reshaped the design

This is your strongest single moment. Run it and let the table sit on screen.

```bash
python -m gaukavach species
```

> "Every ultrasonic deterrent is sold on the idea that the frequency is
> species-selective — inaudible to people, aversive to the target. We checked
> that against comparative audiograms measured at the *same* 60 dB criterion as
> the cattle data.
>
> It's backwards. Cats hear it, dogs hear it, sheep, pigs and goats hear it —
> and all five hear it **better than the cow does**. Cattle rank sixth of seven.
> The only species less sensitive than our target is the horse.
>
> So a goat flock beside the road isn't an incidental bystander to this device.
> It's a more sensitive receiver than the animal we're aiming at.
>
> That's why every scrap of selectivity in our system lives in the detector.
> The frequency provides none — and we can prove it, not assert it."

Then the consequences, fast:

```bash
python -m gaukavach run goat-flock
python -m gaukavach run flight-into-road
```

> "Goat flock present: zero emission. Above three grouped animals we refuse
> entirely, because responses are socially facilitated — a startle cascades, and
> a flock moving as one body is a worse road hazard than the original blockage.
>
> And this one is the failure mode that scared us most. An animal flees *away*
> from the source. If the emitter sits so 'away' means 'across the road', the
> device causes the exact collision it exists to prevent. So we ray-cast the
> flight vector in metric ground coordinates before the acoustics are even
> consulted. Which produced a finding we didn't set out to make: this is an
> approach deterrent, **not** a road-clearer. A cow already mid-carriageway gets
> refused, because clearing it needs a human — never more volume."

---

## Minute 2:45–3:45 · The physics that nobody else did

```bash
python -m gaukavach physics
python -m gaukavach envelope
```

Two things to land:

1. **Validation.** "Our propagation model reproduces the published attenuation
   table to 0.1 dB at every distance. This isn't a plausible-looking number, it
   matches Lawrence & Simmons 1982."

2. **The headline finding.** Show the envelope chart.

> "Absorption rises as roughly frequency squared. 30 kHz — the frequency that
> one prototype used — reaches about 22 metres. 22 kHz reaches about 43. So the
> 'ultrasonic wall across a highway' idea is dead on arrival, and we can show
> you the number rather than the intuition. Beyond the envelope the system
> doesn't get louder, it escalates."

If a judge is technical, add the model disagreement:

> "We carry two absorption models because they disagree — ISO says 0.911 dB/m at
> 30 kHz, the direct measurement says 0.700. Range decisions use the pessimistic
> one, exposure decisions the optimistic one, so both errors land on the safe
> side. And ISO 9613-1 is only specified to 10 kHz, so we label every use above
> that as an extrapolation instead of calling it standards compliance."

---

## Minute 3:45–4:15 · The detail that proves depth

```bash
python -m gaukavach spectrum
```

> "A 25 kHz burst switched on and off abruptly is not a 25 kHz signal. The
> rectangular gate splatters broadband energy across the audible range — the
> device clicks at every activation even though the carrier is ultrasonic. OSHA
> documents exactly this failure mode. So every burst is raised-cosine ramped,
> about 98 dB better in the audible band, and the device FFTs its own buffer and
> refuses to play anything that fails the check. It inspects itself before it
> makes a sound."

This is the moment that separates you from teams who bought a transducer.

---

## Minute 4:15–5:15 · The part other teams delete

```bash
python -m gaukavach behaviour
```

Let the `UNINFORMATIVE` verdicts sit on screen for a beat.

> "Does it work? We don't know, and neither does anyone else — there is no
> published dose-response curve for cattle at these frequencies. So our model
> returns credible intervals over an explicit prior, never a point estimate, and
> it labels its own output uninformative at every level the welfare ceiling
> actually permits.
>
> That's not a gap in the project. That *is* the project. Because the useful
> output isn't a performance claim, it's a specification: 27 approaches per arm,
> 54 total, clustered by herd because responses are socially facilitated. We
> turned 'someone should test this' into a costable two-week protocol."

Then the habituation chart:

> "And we can already tell you the most likely failure. An unconditioned tone
> with no consequence decays — our projection has response dropping to about 0.1
> by day ten. A deterrent that works only on day one isn't a deterrent. That's
> why the escalation path exists."

---

## Minute 5:15–6:00 · It runs, and it is auditable

```bash
python -m gaukavach run persistent-blocker
```

> "A cow settles on the road and doesn't move. Three attempts, then the system
> stops emitting permanently and hands the incident to municipal dispatch. It
> gives up instead of getting louder.
>
> Every run writes a SHA-256 hash-chained ledger. Edit one historical record and
> every record after it becomes invalid."

Show the tamper test:

```bash
pytest tests/ -q -k "tamper or ledger"
```

> "And we scoped that claim honestly — there's a test asserting our own
> documentation doesn't overclaim it. It's a single-writer tamper-*evident* log.
> It is not a blockchain and we don't call it one."

---

## Minute 6:00–7:00 · Close on the limitations

Do not let a judge discover these. Hand them over.

```bash
python -m gaukavach hazards --open-only
```

> "We wrote a 30-row hazard register with severity, likelihood, mitigation and
> residual risk for every row. Two of them we cannot close, and they're still in
> there: ultrasonic intermodulation in hearing aids, where we found no
> measurement and aren't competent to assert one; and macaques, which are all
> over Indian roads and have no detector class at all. A register with no open
> rows has been edited, not completed.
>
> What we did not build: there is no hardware. No transducer, no field
> measurement, no cattle exposed to anything. Every emission in this repo is
> marked dry-run and there's a test asserting nothing claims otherwise. The
> camera is uncalibrated so distances carry about ±20% error. And there is no
> cattle-specific welfare threshold anywhere in the literature for this band —
> we borrow a human occupational ceiling and we label that substitution every
> single place it appears.
>
> Two days, no hardware. What we built is the part that would still matter after
> the hardware arrives: the decision layer that keeps it honest."

---

## Answers to the questions they will actually ask

**"This already exists — virtual fencing, Halter, Nofence."**
> Those are collar-based and depend on associative learning with a paired
> electric stimulus, on animals someone owns, inside a fenced property. Stray
> cattle on a public highway have no collar and no owner present. That's a
> different problem, and the collar literature is precisely what tells us an
> *unpaired* tone will be weaker — which is why we don't claim containment.

**"Isn't this cruel?"**
> The system caps exposure below the occupational ceiling, emits the computed
> minimum, enforces a 20-second quiet period and a 120-second daily budget per
> animal, treats a panic response as a stop criterion that disables that animal
> for the session, and refuses entirely if a person or a dog is in the cone. And
> the framing is backwards: the alternative today is a cow hit by a truck.

**"What about dogs and cats? Street dogs are everywhere."**
> That's the question that reshaped our design. Dogs hear to 45 kHz, cats to
> 85 — both hear our carrier better than cattle do, and acoustic stress is a
> documented trigger for redirected aggression toward people. So it's an
> absolute veto, not a weighting. `run non-target-dog` emits zero seconds.

**"Could you cause a stampede?"**
> Above three grouped conspecifics we refuse outright and escalate. Responses
> are socially facilitated, so a startle propagates through the group instead of
> staying with one animal. A flock is a dispatch problem, not an acoustic one.
> That's `run herd-stampede-risk` — five animals, zero emission.

**"Isn't 22 kHz safe because adults can't hear it?"**
> For adults, yes — 0.45% modelled audibility. For children it's 42%, because
> high-frequency hearing declines with age. That's the same gap anti-loitering
> devices exploit at 17.4 kHz. Near a school our band floor rises to 25 kHz.

**"You have no hardware, so what did you actually build?"**
> The decision layer, which is the part that's hard and the part that's missing
> from the existing prototype. Anyone can drive a transducer. Knowing when *not*
> to is the engineering. 58 tests, all passing, all runnable right now.

**"How is this traffic management?"**
> Layer one is pure traffic control and fires at any distance regardless of
> whether sound can reach: variable message sign, signal hold, advisory speed,
> dispatch ticket. That's the half whose mechanism isn't in doubt. It plugs
> straight into the adaptive signal controller we already built.

**"Your behaviour model is made up."**
> Yes — and it says so in its own output, in the constant's evidence grade, in
> the docstring, and on the dashboard. It's a prior, graded `Hypothesis`,
> structurally forbidden from authorising an emission. Its job is to size the
> experiment that would replace it.

**"Why 22 kHz and not 30?"**
> Physics. Absorption at 30 kHz is 0.911 dB/m versus 0.547 at 22, and cattle
> sensitivity falls toward the audiogram endpoint, so 30 kHz costs about half
> the range for no benefit. We'd have picked 20 kHz for even more range, but
> OSHA says 20 kHz isn't reliably inaudible — so the optimiser is constrained to
> refuse it.

---

## If you have any spare time

In rough order of value per hour:

1. **Find one real dashcam clip with a cow on a road** and run
   `python -m gaukavach video clip.mp4`. Real YOLO detections on real footage
   removes the "it's all synthetic" objection at a stroke. COCO already has
   `cow` — no training needed.
2. **Wire layer 1 into your existing adaptive signal controller.** It makes the
   pivot look intentional rather than desperate: you built a traffic OS, and
   this is its first module.
3. **Print the evidence table** as a one-page handout. Judges keep paper.
