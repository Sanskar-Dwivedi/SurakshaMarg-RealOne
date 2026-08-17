# Cattle-road MVP

The cattle MVP is an additive, dry-run perception workflow. It does not
replace GauKavach's evidence-graded policy engine, acoustic governor, emitter,
hardware, dashboard, or scenario pipeline.

```text
camera/image
    ↓
custom YOLO cow detector
    ↓
ByteTrack identity
    ↓
multi-frame confirmation
    ↓
bottom-centre ground-contact point
    ↓
manual road polygon
    ↓
ON_ROAD / OFF_ROAD
    ↓
speaker coverage filtering
    ↓
nearest valid speaker
```

## Setup

Install the optional vision dependencies:

```powershell
pip install -e ".[vision]"
```

Keep the custom cow weights outside Git. The existing local model is:

```text
C:\Users\ashay\runs\detect\train-3\weights\best.pt
```

Create a scene configuration from a reference image. The first window is for
the road polygon; the second is for speaker locations. Speaker IDs are
assigned as `S1`, `S2`, and so on. Coverage circles are image-space MVP zones;
metric seven-metre coverage requires a measured camera calibration.

```powershell
python -m gaukavach cattle-configure `
  --image legendarycowtester.png `
  --coverage-px 500 `
  --output cattle_scene.json
```

Run an image:

```powershell
python -m gaukavach cattle legendarycowtester.png `
  --weights "C:\Users\ashay\runs\detect\train-3\weights\best.pt" `
  --scene cattle_scene.json `
  --confirm-frames 1 `
  --output legendary_cattle_result.jpg
```

Run a video:

```powershell
python -m gaukavach cattle cow4.mp4 `
  --weights "C:\Users\ashay\runs\detect\train-3\weights\best.pt" `
  --scene cattle_scene.json `
  --output cow4_cattle_result.mp4
```

The annotated output contains the cow box, track ID, confidence,
ground-contact point, road polygon, speaker zones, and selected speaker. No
physical speaker is activated.

## Safety boundary

This command is the cow-road/speaker-selection MVP. It does not automatically
invoke the existing acoustic policy engine. The existing GauKavach command
path remains available and continues to enforce its welfare, non-target,
flight-path, exposure, dry-run, and escalation rules.

The MVP currently requires manual scene setup. Camera movement invalidates the
scene configuration. A custom cow-only model does not provide the
person/dog/horse/sheep/vehicle veto coverage of the existing COCO perception
path, so it must not be treated as a replacement for that safety pipeline.
