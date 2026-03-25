from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from actions import ActionContext, ActionError, run_action
from memory import RunRecord, resolve_inputs
from planner import Plan


class ExecutionError(Exception):
    """Raised when execution cannot complete successfully."""


class WorkflowExecutor:
    def __init__(self, *, store: "RunStore") -> None:
        self._store = store

    def start(self, plan: Plan) -> RunRecord:
        run = RunRecord(plan=plan, status="pending")
        self._store.save(run)
        return run

    def execute(self, run: RunRecord) -> RunRecord:
        context = ActionContext(repo_path=Path(run.plan.target_repo))
        run.status = "running"
        run.mark_updated()
        self._store.save(run)

        for step in run.plan.steps:
            step_state = run.steps[step.id]
            if step_state.status == "succeeded":
                continue

            inputs = resolve_inputs(step.inputs, run)
            attempts_allowed = step.retry_policy.max_attempts if step.retry_policy.retryable else 1

            step_state.status = "running"
            step_state.started_at = datetime.now(UTC).isoformat()
            step_state.failure_reason = None
            self._store.save(run)

            last_error: Exception | None = None
            for attempt in range(1, attempts_allowed + 1):
                step_state.attempts = attempt
                try:
                    output = run_action(step.action_type, inputs, context)
                    step_state.output = output
                    step_state.status = "succeeded"
                    step_state.finished_at = datetime.now(UTC).isoformat()
                    step_state.failure_reason = None
                    run.mark_updated()
                    self._store.save(run)
                    break
                except ActionError as exc:
                    last_error = exc
                    step_state.failure_reason = str(exc)
                    step_state.finished_at = datetime.now(UTC).isoformat()
                    run.mark_updated()
                    self._store.save(run)
            else:
                step_state.status = "failed"
                run.status = "failed"
                run.mark_updated()
                self._store.save(run)
                raise ExecutionError(f"Step {step.id!r} failed: {last_error}") from last_error

        run.status = "succeeded"
        run.mark_updated()
        self._store.save(run)
        return run


from run_store import RunStore
