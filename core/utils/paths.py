import os

"""Utility paths used throughout the application."""

# Base directory of the project repository.  When the application is installed
# as a package this points inside ``site-packages`` so writes may fail.
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

# Absolute path to the ``static`` directory.  It can be overridden via the
# ``STATIC_DIR`` environment variable to support deployments where the
# repository location is read-only.
STATIC_DIR = os.environ.get(
    "STATIC_DIR", os.path.join(BASE_DIR, "web-client", "static")
)
