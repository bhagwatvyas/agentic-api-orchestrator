from __future__ import annotations

from planner import ALLOWED_ACTIONS, Plan


class PlanValidationError(Exception):
    """Raised when a plan is structurally invalid or violates V1 safety rules."""


REQUIRED_INPUTS = {
    "inspect_files": {"paths"},
    "propose_patch": {"change_kind", "targets"},
    "apply_patch": {"patch"},
    "run_tests": {"command"},
    "run_lint": {"paths"},
    "summarize_results": {"changed_files", "test_summary", "lint_summary"},
}


class PlanValidator:
    def validate(self, plan: Plan) -> None:
        seen: set[str] = set()
        step_index: dict[str, int] = {}
        apply_index: int | None = None
        test_index: int | None = None
        lint_index: int | None = None

        for index, step in enumerate(plan.steps):
            if step.id in seen:
                raise PlanValidationError(f"Duplicate step id {step.id!r}.")
            seen.add(step.id)
            step_index[step.id] = index

            if step.action_type not in ALLOWED_ACTIONS:
                raise PlanValidationError(f"Unsupported action type {step.action_type!r}.")

            missing = REQUIRED_INPUTS[step.action_type] - set(step.inputs)
            if missing:
                raise PlanValidationError(
                    f"Step {step.id!r} is missing required inputs: {', '.join(sorted(missing))}."
                )

            for dependency in step.depends_on:
                if dependency not in step_index:
                    raise PlanValidationError(
                        f"Step {step.id!r} depends on unknown or future step {dependency!r}."
                    )

            if step.action_type == "apply_patch":
                apply_index = index
            elif step.action_type == "run_tests":
                test_index = index
            elif step.action_type == "run_lint":
                lint_index = index

        if apply_index is None:
            raise PlanValidationError("Plan must include an apply_patch step.")
        if test_index is None or lint_index is None:
            raise PlanValidationError("Plan must include both run_tests and run_lint steps.")
        if test_index <= apply_index or lint_index <= apply_index:
            raise PlanValidationError("Validation steps must run after apply_patch.")
