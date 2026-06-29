import os

import great_expectations as gx

_context = None

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@postgres:5432/electricity",
)

GX_PROJECT_DIR = os.environ.get(
    "GX_PROJECT_DIR",
    os.path.dirname(os.path.abspath(__file__)),
)


def get_context():
    global _context
    if _context is None:
        _context = gx.get_context(project_root_dir=GX_PROJECT_DIR)
    return _context
