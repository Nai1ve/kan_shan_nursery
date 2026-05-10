from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Any


class Tracer:
    """Append-only JSON Lines trace for LLM calls.

    File layout: ``<trace_dir>/YYYY-MM-DD.jsonl``. One line per top-level task
    invocation; ``subCalls`` carries per-persona sub-results in multi_persona
    mode.
    """

    def __init__(self, trace_dir: str | Path) -> None:
        self._dir = Path(trace_dir)

    def emit(self, record: dict[str, Any]) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            path = self._dir / f"{date.today().isoformat()}.jsonl"
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            return


def now_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def now_ms() -> int:
    return int(time.time() * 1000)
