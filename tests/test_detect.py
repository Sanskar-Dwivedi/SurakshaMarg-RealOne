

def test_class_roles_resolve_by_name_not_by_coco_id():
    """
    Ids are only COCO's on COCO weights. A detector trained on Indian roads
    numbers its classes differently, so filtering on id 19 would drop the cows
    and admit whatever happened to be nineteenth.
    """
    from gaukavach.detect import ROLE_BY_NAME
    assert ROLE_BY_NAME["cattle"] == "cow"
    assert ROLE_BY_NAME["buffalo"] == "cow"
    assert ROLE_BY_NAME["auto rickshaw"] == "autorickshaw"
    assert ROLE_BY_NAME["tuk tuk"] == "autorickshaw"
    # A rider is a person for veto purposes, whatever they are sitting on.
    assert ROLE_BY_NAME["rider"] == "person"
    assert ROLE_BY_NAME["pedestrian"] == "person"


def test_a_non_coco_vocabulary_binds_without_code_changes():
    """Simulates IDD-style weights: different ids, different names."""
    from gaukavach.detect import Perception

    class FakeModel:
        names = {0: "car", 1: "motorcycle", 2: "rider", 3: "autorickshaw",
                 4: "animal", 5: "cow", 6: "traffic sign"}

    p = Perception.__new__(Perception)
    p.model = FakeModel()
    p.classes, p.unmapped, p.vocabulary = {}, [], "coco"
    p._bind_vocabulary()
    assert p.classes[5] == "cow", "cow must bind by name, at ITS id not COCO's"
    assert p.classes[3] == "autorickshaw"
    assert p.classes[2] == "person", "a rider is a person"
    assert p.vocabulary == "custom"
    assert "traffic sign" in p.unmapped, "unknown names are recorded, not dropped"
