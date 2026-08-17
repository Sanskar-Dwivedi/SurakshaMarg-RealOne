from gaukavach.cattle_mvp import point_in_polygon, ground_contact_point, SceneConfig, select_speaker, Speaker
from gaukavach.cli import _default_cow_weights
from pathlib import Path


def test_point_in_polygon():
    poly = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert point_in_polygon((5, 5), poly) is True
    assert point_in_polygon((15, 15), poly) is False


def test_ground_contact_point():
    bbox = (10, 20, 30, 80)
    assert ground_contact_point(bbox) == (20.0, 80.0)


def test_select_speaker():
    speakers = (
        Speaker("S1", (0.0, 0.0)),
        Speaker("S2", (100.0, 100.0)),
    )
    choice = select_speaker((0.0, 0.0), speakers)
    assert choice.speaker_id == "S1"


def test_scene_config_persists_camera_and_frame_geometry(tmp_path):
    path = tmp_path / "scene.json"
    original = SceneConfig(
        ((0.0, 0.0), (100.0, 0.0), (100.0, 80.0)),
        (Speaker("S1", (25.0, 30.0)),),
        "fixed-camera-01",
        (100, 80),
    )
    original.save(path)
    loaded = SceneConfig.load(path)
    assert loaded == original
    loaded.validate_for_frame("fixed-camera-01", 100, 80)


def test_scene_config_rejects_changed_camera_or_resolution():
    scene = SceneConfig(((0.0, 0.0), (100.0, 0.0), (100.0, 80.0)), (), "fixed-camera-01", (100, 80))
    try:
        scene.validate_for_frame("fixed-camera-02", 100, 80)
    except RuntimeError as error:
        assert "different camera ID" in str(error)
    else:
        raise AssertionError("camera mismatch should fail")
    try:
        scene.validate_for_frame("fixed-camera-01", 120, 80)
    except RuntimeError as error:
        assert "resolution changed" in str(error)
    else:
        raise AssertionError("resolution mismatch should fail")


def test_default_cow_weights_resolution():
    weights_path = Path(_default_cow_weights())
    assert weights_path.is_file()
    assert weights_path.name == "cow_best.pt"
