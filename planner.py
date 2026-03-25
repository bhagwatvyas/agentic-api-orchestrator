from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


ALLOWED_ACTIONS = {
    "inspect_files",
    "propose_patch",
    "apply_patch",
    "run_tests",
    "run_lint",
    "summarize_results",
}


@dataclass(slots=True, frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    retryable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class PlanStep:
    id: str
    action_type: str
    inputs: dict[str, Any]
    depends_on: list[str] = field(default_factory=list)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    expected_artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["retry_policy"] = self.retry_policy.to_dict()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlanStep":
        retry_policy = RetryPolicy(**payload.get("retry_policy", {}))
        return cls(
            id=payload["id"],
            action_type=payload["action_type"],
            inputs=payload.get("inputs", {}),
            depends_on=list(payload.get("depends_on", [])),
            retry_policy=retry_policy,
            expected_artifacts=list(payload.get("expected_artifacts", [])),
        )


@dataclass(slots=True, frozen=True)
class Plan:
    run_id: str
    request: str
    target_repo: str
    created_at: str
    steps: list[PlanStep]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "request": self.request,
            "target_repo": self.target_repo,
            "created_at": self.created_at,
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Plan":
        return cls(
            run_id=payload["run_id"],
            request=payload["request"],
            target_repo=payload["target_repo"],
            created_at=payload["created_at"],
            steps=[PlanStep.from_dict(item) for item in payload.get("steps", [])],
        )


class PlannerError(Exception):
    """Raised when a request cannot be mapped to a supported deterministic plan."""


class MockPlanner:
    """
    Fixture-backed planner for a narrow set of interview-friendly developer tasks.

    V1 deliberately fails closed unless the request matches a supported workflow.
    """

    def create_plan(self, request: str, *, target_repo: str) -> Plan:
        normalized = request.strip()
        if not normalized:
            raise PlannerError("Request cannot be empty.")

        lower = normalized.lower()
        if "--dry-run" in lower and "update tests" in lower:
            return self._build_add_dry_run_plan(request=normalized, target_repo=target_repo)

        raise PlannerError(
            "Unsupported request. V1 only supports deterministic repo changes like "
            "'add a --dry-run flag and update tests'."
        )

    def _build_add_dry_run_plan(self, *, request: str, target_repo: str) -> Plan:
        run_id = f"run_{uuid4().hex[:12]}"
        created_at = datetime.now(UTC).isoformat()

        steps = [
            PlanStep(
                id="inspect_repo",
                action_type="inspect_files",
                inputs={
                    "paths": ["main.py", "tests/test_main.py"],
                },
                expected_artifacts=["file_snapshot"],
            ),
            PlanStep(
                id="propose_patch",
                action_type="propose_patch",
                inputs={
                    "change_kind": "add_dry_run_flag",
                    "targets": "{{steps.inspect_repo.output.discovered_files}}",
                },
                depends_on=["inspect_repo"],
                expected_artifacts=["patch"],
            ),
            PlanStep(
                id="apply_patch",
                action_type="apply_patch",
                inputs={
                    "patch": "{{steps.propose_patch.output.patch}}",
                },
                depends_on=["propose_patch"],
                expected_artifacts=["changed_files"],
            ),
            PlanStep(
                id="run_tests",
                action_type="run_tests",
                inputs={
                    "command": ["pytest", "tests/test_main.py"],
                },
                depends_on=["apply_patch"],
                retry_policy=RetryPolicy(max_attempts=2, retryable=True),
                expected_artifacts=["test_report"],
            ),
            PlanStep(
                id="run_lint",
                action_type="run_lint",
                inputs={
                    "paths": ["main.py", "tests/test_main.py"],
                },
                depends_on=["apply_patch"],
                retry_policy=RetryPolicy(max_attempts=2, retryable=True),
                expected_artifacts=["lint_report"],
            ),
            PlanStep(
                id="summarize_results",
                action_type="summarize_results",
                inputs={
                    "changed_files": "{{steps.apply_patch.output.changed_files}}",
                    "test_summary": "{{steps.run_tests.output.summary}}",
                    "lint_summary": "{{steps.run_lint.output.summary}}",
                },
                depends_on=["run_tests", "run_lint"],
                expected_artifacts=["summary"],
            ),
        ]

        return Plan(
            run_id=run_id,
            request=request,
            target_repo=target_repo,
            created_at=created_at,
            steps=steps,
        )
