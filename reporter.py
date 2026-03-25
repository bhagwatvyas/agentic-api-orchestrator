from __future__ import annotations

from memory import RunRecord
from planner import Plan


def render_plan(plan: Plan) -> str:
    lines = [
        f"Plan: {len(plan.steps)} to add, 0 to change, 0 to destroy",
        f"Run ID: {plan.run_id}",
        f"Request: {plan.request}",
        f"Target Repo: {plan.target_repo}",
        "",
    ]

    for step in plan.steps:
        lines.append(f"+ {step.id} [{step.action_type}]")
        lines.extend(_render_step_inputs(step.action_type, step.inputs))

    return "\n".join(lines)


def render_run(run: RunRecord) -> str:
    lines = [
        f"Run {run.plan.run_id}",
        f"Status: {run.status}",
        "",
    ]

    for step in run.plan.steps:
        state = run.steps[step.id]
        lines.append(
            f"- {step.id}: {state.status} "
            f"(attempts={state.attempts}, action={state.action_type})"
        )
        if state.failure_reason:
            lines.append(f"  failure: {state.failure_reason}")
        if state.output and isinstance(state.output, dict) and "summary" in state.output:
            lines.append(f"  summary: {state.output['summary']}")

    return "\n".join(lines)


def _render_step_inputs(action_type: str, inputs: dict[str, object]) -> list[str]:
    if action_type == "inspect_files":
        return [f"  files: {', '.join(inputs['paths'])}"]
    if action_type == "propose_patch":
        return [f"  change: {inputs['change_kind']}"]
    if action_type == "run_tests":
        return [f"  command: {' '.join(inputs['command'])}"]
    if action_type == "run_lint":
        return [f"  files: {', '.join(inputs['paths'])}"]
    return []
