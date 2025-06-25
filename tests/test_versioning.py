from core.utils.versioning import apply_update

class Dummy:
    def __init__(self):
        self.version = 1
        self.conflict_data = None
        self.sync_state = {"name": "a"}
        self.name = "a"
        self.created_at = None
        self.updated_at = None
        self.deleted_at = None


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
    assert d.conflict_data is None
    assert d.name == "b"


def test_apply_update_conflict_equal_versions():
    d = Dummy()
    d.name = "b"
    apply_update(d, {"name": "x"}, incoming_version=1, source="test")
    assert d.conflict_data is not None
    assert d.conflict_data[0]["field"] == "name"
    assert d.name == "b"


def test_ignore_timestamp_fields():
    d = Dummy()
    apply_update(
        d,
        {
            "updated_at": "2024-01-01T00:00:00Z",
            "created_at": "2024-01-01T00:00:00Z",
        },
        incoming_version=2,
        source="test",
    )
    assert d.conflict_data is None


