"""Core utilities and data models for server modules."""

# Avoid importing heavy dependencies at module import time.  The submodules are
# loaded lazily when accessed via ``core.<name>``.  This keeps ``import core``
# lightweight and prevents import errors during installer execution when
# optional dependencies may not yet be available.

__all__ = [
    "models",
    "ColumnSelection",
    "get_current_user",
    "require_role",
    "user_in_site",
    "get_user_site_ids",
    "get_password_hash",
    "verify_password",
    "issue_token",
    "verify_token",
    "ROLE_CHOICES",
    "ROLE_HIERARCHY",
]


def __getattr__(name):
    if name == "models":
        from . import models as _m

        return _m
    if name == "ColumnSelection":
        from .schemas import ColumnSelection as _c

        return _c
    if name in {
        "get_current_user",
        "require_role",
        "user_in_site",
        "get_user_site_ids",
        "get_password_hash",
        "verify_password",
        "ROLE_CHOICES",
        "ROLE_HIERARCHY",
    }:
        from .utils import auth as _a

        return getattr(_a, name)
    if name in {"issue_token", "verify_token"}:
        from . import auth as _auth

        return getattr(_auth, name)
    raise AttributeError(name)
