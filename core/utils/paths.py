import os

# Base directory of the project repository
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

# Absolute path to the ``static`` directory.
#
# Static assets are served from ``BASE_DIR/web-client/static``. Earlier versions
# of the application stored them directly under ``static`` but moving them under
# ``web-client`` keeps all client assets together.
STATIC_DIR = os.path.join(BASE_DIR, "web-client", "static")
