import os

# Base directory of the project repository
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

# Absolute path to the ``static`` directory.
#
# Static assets are always served from ``BASE_DIR/static``.  Earlier versions of
# the application allowed overriding this path via the ``STATIC_DIR``
# environment variable.  That behaviour caused inconsistencies when the
# directory was mounted at a different location.  The path is now fixed to the
# repository's ``static`` folder so all components refer to the same location.
STATIC_DIR = os.path.join(BASE_DIR, "static")
