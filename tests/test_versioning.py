from core.utils.versioning import apply_update

class Dummy:
    def __init__(self):
        self.version = 1
        self.conflict_data = None
        self.sync_state = {"name": "a"}
        self.name = "a"


def test_apply_update_increments_version():
    d = Dummy()
    apply_update(d, {"name": "x"}, incoming_version=1, source="test")
    assert d.version == 2
    assert d.conflict_data is None
    assert d.name == "x"
    assert d.sync_state["name"] == "x"


def test_apply_update_conflict():
    d = Dummy()
    d.name = "b"
    apply_update(d, {"name": "x"}, incoming_version=0, source="test")
    assert d.version == 2
    assert d.conflict_data is not None
    assert d.conflict_data[0]["source"] == "test"
    assert d.conflict_data[0]["field"] == "name"
    assert d.conflict_data[0]["remote_value"] == "x"
    assert d.name == "b"
