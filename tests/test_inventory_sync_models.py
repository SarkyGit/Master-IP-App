import importlib
from core.models import models as model_module


def get_model_names():
    return {cls.__tablename__ for cls in model_module.Base.__subclasses__()}


def test_workers_import_inventory_models():
    inv = importlib.import_module("modules.inventory.models")
    # Reload workers to trigger imports
    import server.workers.sync_push_worker as push
    import server.workers.sync_pull_worker as pull
    importlib.reload(push)
    importlib.reload(pull)

    names = get_model_names()
    expected = {
        inv.Device.__tablename__,
        inv.DeviceType.__tablename__,
        inv.DeviceEditLog.__tablename__,
        inv.Tag.__tablename__,
        inv.Location.__tablename__,
        inv.DeviceDamage.__tablename__,
    }
    assert expected <= names
