from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
import re
from typing import Any

from planner import Plan


STATE_REF_PATTERN = re.compile(r"\{\{steps\.([a-zA-Z0-9_-]+)\.output(?:\.([a-zA-Z0-9_.-]+))?\}\}")


@dataclass(slots=True)
class StepRunState:
    step_id: str
    action_type: str
    status: str = "pending"
    attempts: int = 0
    output: Any = None
    failure_reason: str | None = None
    started_at: str | None = None
    finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StepRunState":
        return cls(**payload)


@dataclass(slots=True)
class RunRecord:
    plan: Plan
    status: str = "pending"
    steps: dict[str, StepRunState] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        if not self.steps:
            self.steps = {
                step.id: StepRunState(step_id=step.id, action_type=step.action_type)
                for step in self.plan.steps
            }

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan.to_dict(),
            "status": self.status,
            "steps": {step_id: state.to_dict() for step_id, state in self.steps.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RunRecord":
        record = cls(
            plan=Plan.from_dict(payload["plan"]),
            status=payload["status"],
            steps={key: StepRunState.from_dict(value) for key, value in payload["steps"].items()},
            created_at=payload["created_at"],
            updated_at=payload["updated_at"],
        )
        return record

    def mark_updated(self) -> None:
        self.updated_at = datetime.now(UTC).isoformat()

    def get_step_output(self, step_id: str) -> Any:
        try:
            return self.steps[step_id].output
        except KeyError as exc:
            raise KeyError(f"Unknown step id {step_id!r}") from exc


def resolve_inputs(value: Any, run: RunRecord) -> Any:
    if isinstance(value, dict):
        return {key: resolve_inputs(item, run) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_inputs(item, run) for item in value]
    if isinstance(value, str):
        return _resolve_string(value, run)
    return value


def _resolve_string(value: str, run: RunRecord) -> Any:
    full_match = STATE_REF_PATTERN.fullmatch(value)
    if full_match:
        return _resolve_reference(full_match.group(1), full_match.group(2), run)

    def replace(match: re.Match[str]) -> str:
        resolved = _resolve_reference(match.group(1), match.group(2), run)
        if isinstance(resolved, str):
            return resolved
        return json.dumps(resolved, sort_keys=True)

    return STATE_REF_PATTERN.sub(replace, value)


def _resolve_reference(step_id: str, path: str | None, run: RunRecord) -> Any:
    current = run.get_step_output(step_id)
    if path is None:
        return current

    for part in path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
            continue
        if isinstance(current, dict):
            current = current[part]
            continue
        raise KeyError(f"Cannot resolve path {path!r} from step {step_id!r}")
    return current
