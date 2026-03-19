from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

from memory import WorkflowState
from planner import PlanStep
from tools import ToolRegistry


STATE_REF_PATTERN = re.compile(r"\{\{state\.([a-zA-Z0-9_.]+)\}\}")


class ExecutionError(Exception):
    """Raised when a workflow step cannot be executed successfully."""


@dataclass(slots=True)
class StepExecution:
    step: PlanStep
    attempts: int
    output: Any


class WorkflowExecutor:
    def __init__(self, registry: ToolRegistry, *, max_retries: int = 1) -> None:
        self._registry = registry
        self._max_retries = max_retries

    def execute(
        self,
        plan: list[PlanStep],
        *,
        state: WorkflowState | None = None,
        on_step_failure: Callable[[PlanStep, Exception, WorkflowState], list[PlanStep] | None] | None = None,
    ) -> tuple[list[StepExecution], WorkflowState]:
        workflow_state = state or WorkflowState()
        results: list[StepExecution] = []

        step_index = 0
        while step_index < len(plan):
            step = plan[step_index]
            resolved_args = self._resolve_value(step.args, workflow_state)

            last_error: Exception | None = None
            for attempt in range(1, self._max_retries + 2):
                try:
                    output = self._registry.invoke(step.tool, **resolved_args)
                    workflow_state.add_step_result(tool_name=step.tool, args=resolved_args, output=output)
                    results.append(StepExecution(step=step, attempts=attempt, output=output))
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    if attempt > self._max_retries:
                        if on_step_failure:
                            replanned = on_step_failure(step, exc, workflow_state)
                            if replanned:
                                plan = plan[:step_index] + replanned
                                break
                        raise ExecutionError(
                            f"Step {step_index} failed for tool {step.tool!r}: {exc}"
                        ) from exc
            else:
                raise ExecutionError(f"Unexpected executor state for step {step_index}.")

            if last_error and on_step_failure and step_index >= len(results):
                continue

            step_index += 1

        return results, workflow_state

    def _resolve_value(self, value: Any, state: WorkflowState) -> Any:
        if isinstance(value, dict):
            return {key: self._resolve_value(sub_value, state) for key, sub_value in value.items()}
        if isinstance(value, list):
            return [self._resolve_value(item, state) for item in value]
        if isinstance(value, str):
            return self._resolve_string(value, state)
        return value

    def _resolve_string(self, value: str, state: WorkflowState) -> Any:
        full_match = STATE_REF_PATTERN.fullmatch(value)
        if full_match:
            return state.get(full_match.group(1))

        def replace(match: re.Match[str]) -> str:
            resolved = state.get(match.group(1))
            return str(resolved)

        return STATE_REF_PATTERN.sub(replace, value)
