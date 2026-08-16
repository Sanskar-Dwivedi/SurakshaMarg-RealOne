# Hardware to demonstrate GauKavach live

Organised by **what each tier lets you honestly claim**, because that is the
only thing that matters in a review. Buying parts you cannot validate is worse
than having no parts at all: an un-measured emitter on the table invites exactly
the question you cannot answer.

Prices are indicative Indian street prices and will drift. Verify before buying.

---

## Three traps before you spend anything

**1. The obvious cheap transducer is the wrong part.**
Every ultrasonic module in a hobby shop — HC-SR04 and friends — is a narrowband
resonator at **40 kHz**. Our band is 22–30 kHz, and 40 kHz is above the cattle
audiogram endpoint (35 kHz) entirely. It would be inaudible to the animal *and*
useless. You need **wideband piezo horn tweeters** quoted to 27 kHz, not
ultrasonic ranging transducers. Specific part below.

**2. Most amplifiers stop exactly where we start.**
Audio power amps are designed for a 20 kHz ceiling, and many class-D modules
have an output LC filter that rolls off hard right above it. Check the datasheet
for response at 27 kHz, or use a class-AB part with genuine wide power bandwidth.

**3. Your phone cannot measure this, and neither can a laptop mic.**
Phone microphones and their codecs are low-passed and anti-aliased below 20 kHz.
A phone SPL app pointed at a 25 kHz emitter will read the room noise floor and
tell you nothing. **Any dB number you quote without a calibrated ultrasonic
microphone is fabricated.** This is the single most important line in this file.

---

## Tier 0 — what you have now. ₹0.

Laptop + browser. The decision layer, real footage, closed-loop outcomes.

**Can claim:** the perception, the governor, the refusals, the physics, the
outcome model, the hazard register.
**Cannot claim:** that any sound has ever been produced.

For a two-day hackathon this is the right answer, and the BOM below is your
roadmap slide rather than your demo.

---

## The part that actually covers the band

The workable commodity emitter is a **piezo horn tweeter of the CTS/Motorola
KSN1005A class**, and its published spec settles several design questions at once:

| Spec | Value | Consequence |
|---|---|---|
| Frequency response | **4 kHz – 27 kHz** | covers 22–27 kHz. **Does not reach 30 kHz.** |
| Sensitivity | **94 dB SPL @ 1 W / 1 m** | see the link budget below |
| Power | 50 W RMS / 75 W peak | maxes out at **111 dB @ 1 m** |
| Element | 22 mm ceramic piezo | capacitive load — needs a series resistor |
| Price | roughly ₹400–900 each | an array of four is affordable |

Sources: [GRS PZ1005 (KSN1005A equivalent)](https://www.parts-express.com/GRS-PZ1005-3-1-4-Piezo-Horn-Tweeter-Similar-to-KSN1005A-292-442) ·
[CTS piezo tweeter datasheet](https://www.farnell.com/datasheets/29265.pdf) ·
[Goldwood GT-1005 equivalent](https://www.goldwood.com/250-goldwood-sound-gt-1005-piezo-horn-tweeters-75-watts-each-replacement-for-ksn1005a/).
India: [Amazon.in piezo tweeters](https://www.amazon.in/piezo-tweeter/s?k=piezo+tweeter) ·
[IndiaMART horn tweeters](https://dir.indiamart.com/impcat/horn-tweeter.html). Look for a
quoted response of **2.2 k–27 kHz**; anything specified only to 20 kHz is useless here.

### Losing 30 kHz costs us nothing

The part tops out at 27 kHz, and the band we documented runs to 30 kHz. That
sounds like a problem until you check it against the physics the repo already
computed:

```
effective range at 22 kHz : 42.8 m
effective range at 27 kHz : 30.2 m
carrier the optimiser picks: 22.0 kHz
```

The optimiser selects **22 kHz** for margin and range, and 22 kHz sits
comfortably inside what a ₹500 part delivers. The 30 kHz end of the band — the
frequency the one prototype paper used — is simultaneously the worst acoustically
*and* the hardest to source. The cheap part and the correct physics agree.

### The link budget, against this exact part

Electrical power needed to satisfy the full link budget at 22 kHz with a horn's
+12 dB directivity, on a 94 dB/W/m tweeter:

| Target | Need @ 1 m | Watts | Headroom under ceiling |
|---:|---:|---:|---:|
| 10 m | 84.5 dB | **0.11 W** | 25.5 dB |
| 15 m | 90.0 dB | **0.40 W** | 20.0 dB |
| 25 m | 98.3 dB | **2.7 W** | 11.7 dB |
| 40 m | 108.2 dB | 26.6 W | 1.8 dB |

A single commodity tweeter on **half a watt** covers the realistic engagement
range. You do not need exotic hardware; you need the calibration to prove it.

### A safety property worth stating out loud

To reach the **142 dB** the prototype paper reported, this tweeter would need
**63,000 watts** — 1,262× beyond its 50 W rating. The part physically cannot
produce the exposure our governor refuses. The software says no, and the
hardware could not comply even if the software failed. That is defence in depth
you get for free by choosing a sane transducer.

---

## Tier 1 — "it really emits" bench demo. ~₹12,000–22,000.

Enough to produce a genuine 22–27 kHz signal and let a room *perceive* it,
without claiming a single decibel.

| Item | Spec that matters | ~₹ |
|---|---|---|
| USB audio interface | **192 kHz** sample rate, not 48 kHz | 9,000–14,000 |
| Piezo horn tweeters ×4 | quoted to 27 kHz, not 20 kHz | 1,600–3,600 |
| Class-AB amp module | genuine response at 27 kHz | 800–2,000 |
| Series resistors, wiring, enclosure | piezos are capacitive — protect the amp | 300 |
| **Heterodyne bat detector** | tunable ~20–40 kHz | 3,000–6,000 |
| E-stop + relay + ESP32 watchdog | cuts amp power on fault | 1,200–2,500 |

**The bat detector is the demo.** It shifts the ultrasonic carrier down into the
audible range, so the room *hears* that something is being emitted that nobody
can hear directly. It costs a few thousand rupees and it is the difference
between "trust us, it's on" and a sound in the room. It is an indicator, not an
instrument — say so.

**Can claim:** we generate a real 22–27 kHz carrier through a real transducer;
here is the ramped-vs-hard-gated waveform difference in the signal chain; here is
the watchdog cutting power.
**Cannot claim:** any SPL, any range, any spectral purity at the transducer.

> Build the watchdog even at this tier. Hazard **H23** (stuck-on emitter) is in
> our own register, and demonstrating an E-stop that de-energises the amplifier
> is a stronger safety story than any slide.

---

## Tier 2 — measurement, where the numbers become real. +₹20,000–25,000.

| Item | Spec that matters | ~₹ |
|---|---|---|
| [Dodotronic UltraMic 192K EVO](https://www.dodotronic.com/product/ultramic-192k-evo/) | 192 kHz sampling, USB class-compliant, no drivers | **€180** ≈ 17k ex-works; budget **20–25k** landed after shipping and duty |
| [UltraMic UM250K](https://www.dodotronic.com/product/ultramic-um250k/) *(alternative)* | 250 kHz if you also want headroom for bat work | higher |
| Tripod + boom, tape measure | repeatable mic placement | 2,000 |
| Analysis software | free — Audacity, REW, or our own FFT | 0 |

Cheaper than I first estimated. At €180 this is the **single highest-value
purchase in the whole project** — it is the difference between a repo full of
predictions and a repo with measurements. See the
[user guide](https://www.dodotronic.com/wp-content/uploads/2022/11/Ultramic_User_Guide-1.pdf)
for the gain switch settings before you buy.

Honest limitation: it ships with a response curve, **not** a traceable
laboratory calibration certificate. Good enough for a research prototype and for
every comparison in this repo; not good enough to certify a product.

This is the tier that converts the whole project from argument to evidence.
With it you can finally run what the repo has been asking for all along:

- measure the **actual emitted spectrum** and check for audible subharmonics
- confirm the **~98 dB ramping improvement** is real on hardware, not just in a
  linear model (`gaukavach spectrum` predicts it; this measures it)
- measure **SPL versus distance** and test it against our ISO 9613-1 and
  Lawrence & Simmons predictions — the two models disagree by ~4 dB at 20 m, and
  this rig tells you which one is right for your site
- verify the emitter never exceeds the **110 dB ceiling**

**Can claim:** measured levels, measured spectrum, measured range — with the
caveat that a USB ultrasonic mic has a supplied calibration curve, not a
traceable laboratory certificate.
**Cannot claim:** anything about animals.

---

## Tier 3 — field prototype. +₹60,000–1,50,000, plus approvals.

| Item | Why | ~₹ |
|---|---|---|
| Directional array or horn | the +12 dB the link budget assumes | 8,000–25,000 |
| Fixed camera, IP66 | must not move; geometry depends on it | 3,000–8,000 |
| Rigid mount, measured height | calibration is worthless if the pole sways | 3,000–6,000 |
| Edge compute (Jetson Orin Nano, or Pi 5 + Hailo) | YOLO at useful frame rate | 18,000–45,000 |
| Solar panel, charge controller, battery | duty-cycled, event-triggered load | 12,000–30,000 |
| Weatherproof enclosure, cabling, surge | monsoon | 6,000–15,000 |
| Calibration target (checkerboard) | homography for real distances | ~200 |

**Non-negotiable before any animal is exposed:**
- Institutional **animal-ethics approval** (IAEC or your institution's equivalent)
- **Veterinary supervision** for trials
- Road-authority permission for anything near a carriageway
- The **54-approach protocol** the repo already specifies, with the OFF control
  arm, clustered by herd

Without these you have a device, not a study, and the behavioural numbers stay
prior-driven no matter how good the hardware is.

---

## The camera matters more than the emitter

Our real-footage tab shows why. That clip is a moving dashcam, so range, zones
and flight geometry are **disabled** — they would be fiction. Every geometric
claim the system makes depends on:

- camera **height** above the road plane (measured, not estimated)
- **focal length** in pixels (from a checkerboard calibration, not the spec sheet)
- **horizon row** in the image
- a **rigid** mount

A ₹2,000 webcam on a properly measured pole produces better decisions than a
₹40,000 camera on a tripod someone nudges. The flight-vector check — the one that
stops the system pushing an animal onto the road — is pure geometry, so bad
calibration turns a safety feature into a hazard.

---

## Recommendation for a two-day deadline

**Do not buy the emitter.** You cannot validate it in two days, and an
un-measured transducer on the table converts your strongest asset — the honesty
of the evidence envelope — into the weakest kind of prop.

If you want something physical on the table, the highest-value single purchase
is the **heterodyne bat detector** (~₹3,000–6,000, available same-day in most
metros). Pair it with a laptop playing a ramped 22 kHz burst through a 192 kHz
interface and the room hears a click it cannot otherwise perceive. Total spend
under ₹20,000, and every word you say about it is true.

Then put this page on a slide titled *"what we would buy next, and what each
purchase would let us claim"*. Judges respond well to a team that knows the
price of its own uncertainty.
