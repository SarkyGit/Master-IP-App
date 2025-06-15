import os

# Base directory of the project repository
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

# Absolute path to the "static" directory.
#
# The application historically assumed that static assets live under the
# repository root, i.e. ``BASE_DIR/static``.  Some deployment setups mount the
# ``static`` directory elsewhere (for example at ``/static``) which caused the
# app to still look under ``/app/static``.  Allow overriding the location via the
# ``STATIC_DIR`` environment variable so these deployments work out of the box.
STATIC_DIR = os.environ.get("STATIC_DIR", os.path.join(BASE_DIR, "static"))
