# The working prototype — what to actually open

*Hardware questions: see [HARDWARE.md](HARDWARE.md).*

Three things exist, in the order you should reach for them.

---

## 1. The live simulator (your main demo)

**`dashboard/simulator.html`** — double-click it. Any browser, no server, no
internet, fully self-contained at 1.5 MB.

What it does:

- **Plays 12 scenarios** frame by frame with a scrub bar, showing the road,
  the detections, the flight vectors and the governor's live verdict.
- **Sandbox mode** lets you drag a cow anywhere on the road and watch the
  verdict change in real time.
- **Decision field** paints the governor's answer for *every* position at once.
  This is the single most persuasive frame in the whole project: green on the
  verge, **solid red across the entire carriageway**.

### Why it is not a mock

The browser does not re-implement any decision logic. `gaukavach sim` runs the
real Python engine over every scenario and over a 1,412-point grid, records what
the governor actually decided, and embeds that. The page replays and looks up.
Every number on screen traces to a Python evaluation you can re-run:

```bash
python -m gaukavach sim          # rebuild everything
python -m gaukavach run goat-flock   # same verdicts, from the CLI
```

If a judge asks "is this really your system?", run those two side by side.

### Driving it

| Control | What it shows |
|---|---|
| Scenario dropdown | 12 situations, each proving one rule |
| Play / Step / scrub | Frame-accurate; pause on the moment that matters |
| **Decision field** | Governor verdict for every position on the road |
| **Sandbox mode** | Drag the cow; verdict updates from real evaluations |
| Flight vectors | Green arrow = escape clear, red = flees onto the road |
| Emitter cone / Range envelope | The 43 m limit, drawn to scale |
| Right panel | Live vetoes, per-animal flags, run totals, hash-chained log |

---

## 2. Rendered video (backup, and for slides)

If the demo laptop misbehaves, or you want clips inside a deck:

```bash
python -m gaukavach render goat-flock --out goat.mp4
python -m gaukavach render --all --outdir media     # all 12 clips
```

Same engine, drawn with OpenCV. Every frame is watermarked
**SIMULATED — no hardware, no animals**.

---

## 3. Real video overlay (the credibility shot)

This is the highest-value thing you can still do before the deadline. Find *one*
dashcam or CCTV clip with a cow on a road — YouTube, a phone, anything:

```bash
python -m gaukavach render --video clip.mp4 --out overlay.mp4
python -m gaukavach render --video clip.mp4 --show      # live window
```

YOLO's COCO vocabulary already contains `cow`, `dog`, `horse`, `sheep` and
`person`, so there is **no training and no dataset needed**. Real detections,
real tracking, real governor decisions, drawn on real footage.

Frames are watermarked **UNCALIBRATED — distances indicative only**, because the
camera geometry is not measured for an arbitrary clip. Say that out loud when
you show it; it costs you nothing and it is the difference between a demo and a
claim.

---

## The five-minute demo path

1. Open the simulator. Scenario: **`person-in-cone`**. Point at
   `emitted 0.00 s`. *"A pedestrian is in the beam. The system sees the cow,
   computes a valid carrier, and emits nothing at all."*

2. Switch to **`goat-flock`**. *"Goats hear this better than cattle do, and
   panic spreads through a flock. Refused three ways at once."*

3. Turn on **Decision field**. Let it land. *"Green is where we're allowed to
   act. Red is the entire road. An animal flees away from the emitter — if the
   emitter is roadside, 'away' means 'across'. So this is an approach deterrent,
   not a road-clearer. The geometry told us that, we didn't decide it."*

4. Hit **Sandbox mode** and drag the cow from the verge onto the road. Verdict
   flips from `PERMITTED — 22 kHz at 97 dB, 13 dB under the ceiling` to
   `REFUSED`. *"Those are real Python evaluations, one per grid cell."*

5. Scenario **`persistent-blocker`**. *"Three attempts, then it stops
   permanently and calls a human. It gives up rather than getting louder."*

Then drop to the terminal for `gaukavach species` and `gaukavach refuse` — the
two findings — and finish on `gaukavach hazards --open-only`.

---

## Rebuilding after any code change

```bash
python -m gaukavach sim      # re-runs the engine, re-injects the page
```

The simulator can never silently drift from the engine, because it has no
independent logic to drift with.
