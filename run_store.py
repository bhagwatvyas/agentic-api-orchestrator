from __future__ import annotations

from pathlib import Path
import json

from memory import RunRecord


class RunStore:
    def __init__(self, base_dir: str | Path) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, run: RunRecord) -> None:
        path = self._path_for_run(run.plan.run_id)
        path.write_text(json.dumps(run.to_dict(), indent=2, sort_keys=True))

    def load(self, run_id: str) -> RunRecord:
        path = self._path_for_run(run_id)
        return RunRecord.from_dict(json.loads(path.read_text()))

    def _path_for_run(self, run_id: str) -> Path:
        return self._base_dir / f"{run_id}.json"
