from core.utils.versioning import apply_update

class Dummy:
    def __init__(self):
        self.version = 1
        self.conflict_data = None


def test_apply_update_increments_version():
    d = Dummy()
    apply_update(d, {"name": "x"}, incoming_version=1, source="test")
    assert d.version == 2
    assert d.conflict_data is None
    assert d.name == "x"


def test_apply_update_conflict():
    d = Dummy()
    apply_update(d, {"name": "x"}, incoming_version=0, source="test")
    assert d.version == 2
    assert d.conflict_data is not None
    assert d.conflict_data["source"] == "test"
    assert "name" in d.conflict_data["conflicting_fields"]
