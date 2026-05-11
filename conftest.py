"""Repo-level pytest conftest.

Adds ``packages/shared-python`` to ``sys.path`` so every service test
can import ``kanshan_shared`` without first installing the package. The
file applies to ``python -m unittest`` runs as well, because unittest
imports any conftest.py it sees in the parent chain.
"""

import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parent / "packages" / "shared-python"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
