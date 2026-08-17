# Cattle-Road Perception MVP

The cattle MVP is an additive, dry-run perception workflow that detects cows, tracks them across frames, determines road-space presence via a road polygon, and selects the nearest covering speaker unit.

> [!IMPORTANT]
> The cattle MVP is purely a software/perception demonstration. It **never activates physical hardware** or acoustic emitters.

```text
camera / image / video
          │
 custom YOLO cow detector
  (models/cow_best.pt)
          │
  ByteTrack identity
          │
multi-frame confirmation
          │
bottom-centre ground point
          │
   road polygon check
          │
   ON_ROAD / OFF_ROAD
          │
speaker coverage filter
          │
 nearest valid speaker
```

## Setup & Dependencies

Install optional vision dependencies in your environment:

```bash
pip install -e ".[vision]"
```

## Bundled Model

The repository bundles a trained cow detection model:

```text
models/cow_best.pt
```

This model file (~5.2 MB) is tracked directly in Git. The `gaukavach cattle` command uses `models/cow_best.pt` automatically by default without requiring a `--weights` argument.

### Overriding the Model

To run inference with a custom model instead of the bundled default:

```bash
python -m gaukavach cattle input.png --scene calibration/legendary_scene.json --weights path/to/custom_model.pt
```

## Running Image Inference

Run cattle perception on an image using the bundled default model:

```bash
python -m gaukavach cattle test_image.png   --scene calibration/legendary_scene.json   --output annotated_result.jpg   --conf 0.25   --confirm-frames 1
```

The annotated output image will show bounding boxes, ground-contact points, track IDs, `ON_ROAD`/`OFF_ROAD` status, and speaker coverage highlights.

## Running Video Inference

Run cattle perception on a video stream or file:

```bash
python -m gaukavach cattle test_video.mp4   --scene calibration/legendary_scene.json   --output annotated_result.mp4   --conf 0.25   --confirm-frames 3
```

## Scene Calibration & Configuration

### Creating a New Scene Calibration

Camera perspective and road geometry vary by installation. To configure a new scene from a reference CCTV frame:

```bash
python -m gaukavach cattle-configure   --image reference_frame.png   --coverage-px 180   --output scene_config.json
```

An interactive GUI window will open:
1. **Road Polygon**: Left-click points outlining the roadway boundary (minimum 3 points). Press `ENTER` when complete. Right-click undoes the last point.
2. **Speaker Locations**: Left-click each speaker mount location. Press `ENTER` when complete.

> [!NOTE]
> The included `calibration/legendary_scene.json` is specific to the reference test camera perspective and scene geometry. New camera placements require creating a scene calibration specific to that angle.

### Road Polygon Meaning

The road polygon defines the active vehicle lane boundary in 2D image coordinates. For each detected cow, its ground-contact point (bottom-centre of the bounding box) is evaluated against the road polygon:
- Ground point **inside** polygon: Marked `ON_ROAD` (triggers speaker selection).
- Ground point **outside** polygon: Marked `OFF_ROAD` (monitored but inactive).

### Speaker Coverage Configuration

Each speaker (`S1`, `S2`, etc.) has a defined position and coverage radius (polygon). When a confirmed cow is `ON_ROAD`:
1. System filters speakers whose coverage polygon contains the cow's ground point.
2. The nearest valid, enabled speaker is selected for targeted activation logic.

## Safety & Integration Boundary

- **No Hardware Activation**: This MVP runs in dry-run/simulation mode only.
- **Safety Pipeline Coexistence**: The cattle MVP remains additive and does not modify GauKavach's core welfare, non-target species veto (dogs, goats, horses), or acoustic governor pipelines.
