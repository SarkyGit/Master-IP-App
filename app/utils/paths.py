import os

# Base directory of the project repository
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Absolute path to the "static" directory at the project root
STATIC_DIR = os.path.join(BASE_DIR, "static")
