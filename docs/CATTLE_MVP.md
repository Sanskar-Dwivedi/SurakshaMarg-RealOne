# Cattle-Road Perception MVP

The cattle MVP is an additive, dry-run perception workflow that detects cows, tracks them across frames, determines road-space presence via an operator-selected polygon, and shows the nearest enabled speaker.

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
nearest enabled speaker
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
python -m gaukavach cattle input.png --scene calibration/scene_config.json --camera-id fixed-camera-01 --weights path/to/custom_model.pt
```

## Running Image Inference

Run cattle perception on an image using the bundled default model:

```bash
python -m gaukavach cattle test_image.png --scene calibration/scene_config.json --camera-id fixed-camera-01 --output annotated_result.jpg --conf 0.25 --confirm-frames 1
```

The annotated output image will show bounding boxes, ground-contact points, track IDs, `ON_ROAD`/`OFF_ROAD` status, and the nearest speaker with pixel distance.

## Running Video Inference

Run cattle perception on a video stream or file:

```bash
python -m gaukavach cattle test_video.mp4 --scene calibration/scene_config.json --camera-id fixed-camera-01 --output annotated_result.mp4 --conf 0.25 --confirm-frames 3 --event-log speaker_events.jsonl
```

## Scene Calibration & Configuration

### Creating a New Scene Calibration

Camera perspective and road geometry vary by installation. To configure a new fixed camera from the first frame of a selected video:

```bash
python -m gaukavach cattle-configure --source reference_video.mp4 --camera-id fixed-camera-01 --output calibration/scene_config.json
```

An interactive GUI window will open on the video's first frame:
1. **Road Polygon**: Left-click points outlining the roadway boundary (minimum 3 points). Press `ENTER` when complete. Right-click undoes the last point.
2. **Speaker Locations**: Left-click each speaker mount location. Press `ENTER` when complete.
3. **Review**: Press `S` to save, `R` to redraw, or `ESC` to cancel. Right-click undoes a point and `C` clears the current selection.

> [!NOTE]
> The included `calibration/legendary_scene.json` is specific to the reference test camera perspective and scene geometry. New camera placements require creating a scene calibration specific to that angle.

### Road Polygon Meaning

The road polygon defines the active vehicle lane boundary in 2D image coordinates. For each detected cow, its ground-contact point (bottom-centre of the bounding box) is evaluated against the road polygon:
- Ground point **inside** polygon: Marked `ON_ROAD` and its nearest speaker is highlighted after confirmation.
- Ground point **outside** polygon: Marked `OFF_ROAD`; its nearest speaker is still shown for operator awareness.

### Speaker Selection

Each speaker (`S1`, `S2`, etc.) has a configured image location. The nearest enabled speaker is shown for every detected cow; the saved road polygon alone determines `ON_ROAD` or `OFF_ROAD`.

The nearest-speaker distance is measured in image pixels. For a sharply angled camera, this is not the same as physical ground distance; deployment requiring metric distance needs camera calibration.

## Safety & Integration Boundary

- **No Hardware Activation**: This MVP runs in dry-run/simulation mode only.
- **Safety Pipeline Coexistence**: The cattle MVP remains additive and does not modify GauKavach's core welfare, non-target species veto (dogs, goats, horses), or acoustic governor pipelines.
