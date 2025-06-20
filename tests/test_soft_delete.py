import importlib
from datetime import datetime, timezone
import importlib
from datetime import datetime, timezone
from unittest import mock
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from core.utils.deletion import soft_delete


def _load_models():
    with mock.patch("sqlalchemy.create_engine"), mock.patch(
        "sqlalchemy.schema.MetaData.create_all"
    ):
        return importlib.import_module("core.models.models")


def test_soft_delete_device_clears_fields():
    models = _load_models()
    now = datetime.now(timezone.utc)
    dev = models.Device(
        id=1,
        uuid=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        hostname="dev",
        ip="1.1.1.1",
        mac="aa",
        asset_tag="at",
        manufacturer="cisco",
        device_type_id=1,
        version=1,
        created_at=now,
        updated_at=now,
    )
    soft_delete(dev, 2, "test")
    assert dev.deleted_at is not None
    assert dev.is_deleted is True
    assert dev.mac == "aa"
    assert dev.asset_tag == "at"
    assert dev.hostname == "dev"


def test_query_filters_deleted():
    models = _load_models()
    engine = sa.create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    import core.utils.database as database
    database.Base.metadata.create_all(bind=engine)
    db = Session()
    now = datetime.now(timezone.utc)
    db.add_all([
        models.Device(
            id=1,
            uuid=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            hostname="d1",
            ip="1.1.1.1",
            manufacturer="cisco",
            device_type_id=1,
            version=1,
            created_at=now,
            updated_at=now,
        ),
        models.Device(
            id=2,
            uuid=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            hostname="d2",
            ip="2.2.2.2",
            manufacturer="cisco",
            device_type_id=1,
            version=1,
            created_at=now,
            updated_at=now,
            deleted_at=now,
        ),
    ])
    db.commit()
    # default should exclude deleted
    res = db.query(models.Device).all()
    assert len(res) == 1
    # including deleted should return both
    res_all = db.query(models.Device).execution_options(include_deleted=True).all()
    assert len(res_all) == 2
