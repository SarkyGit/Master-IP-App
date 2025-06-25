from contextlib import contextmanager
from typing import Iterable, Tuple

from sqlalchemy import event

# Mapping of models to their timestamp update hook functions
try:
    from modules.inventory import models as inventory_models
    from modules.network import models as network_models
    from core.models import models as core_models
except Exception:  # pragma: no cover - module import guard
    inventory_models = None
    network_models = None
    core_models = None

MODEL_UPDATE_EVENTS: list[Tuple[object, object]] = []
if inventory_models is not None:
    for m in (inventory_models.Device, inventory_models.DeviceType,
              inventory_models.Location, inventory_models.Tag):
        MODEL_UPDATE_EVENTS.append((m, inventory_models._update_timestamp))
if network_models is not None:
    for m in (
        network_models.VLAN,
        network_models.SSHCredential,
        network_models.SNMPCommunity,
        network_models.ConnectedSite,
    ):
        MODEL_UPDATE_EVENTS.append((m, network_models._update_timestamp))
if core_models is not None:
    for m in (core_models.Site, core_models.User):
        MODEL_UPDATE_EVENTS.append((m, core_models._update_timestamp))


@contextmanager
def suspend_timestamp_updates(models: Iterable[type] | None = None):
    """Temporarily disable before_update timestamp hooks for given models."""
    targets = MODEL_UPDATE_EVENTS
    if models is not None:
        targets = [pair for pair in MODEL_UPDATE_EVENTS if pair[0] in models]
    for model, fn in targets:
        try:
            event.remove(model, "before_update", fn)
        except Exception:  # pragma: no cover - defensive
            pass
    try:
        yield
    finally:
        for model, fn in targets:
            try:
                event.listen(model, "before_update", fn)
            except Exception:  # pragma: no cover - defensive
                pass
