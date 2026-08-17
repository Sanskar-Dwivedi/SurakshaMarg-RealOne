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
        Speaker("S1", (0.0, 0.0), (( -10, -10 ), ( 10, -10 ), ( 10, 10 ), ( -10, 10 )), True),
        Speaker("S2", (100.0, 100.0), (( 90, 90 ), ( 110, 90 ), ( 110, 110 ), ( 90, 110 )), True),
    )
    choice = select_speaker((0.0, 0.0), speakers)
    assert choice.speaker_id == "S1"


def test_default_cow_weights_resolution():
    weights_path = Path(_default_cow_weights())
    assert weights_path.is_file()
    assert weights_path.name == "cow_best.pt"
