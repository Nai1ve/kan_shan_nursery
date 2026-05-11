"""Make kanshan_shared importable from any service entry point.

Each service's app/main.py (or test setup) calls
``kanshan_shared._bootstrap.ensure_on_path()`` near the top so that
``from kanshan_shared import configure_logging`` works without requiring
``pip install -e ../../packages/shared-python`` at dev time.

In CI / Docker, installing the package is still the cleaner option.
"""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_on_path() -> None:
    here = Path(__file__).resolve().parent  # packages/shared-python/kanshan_shared/
    package_root = here.parent  # packages/shared-python/
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
