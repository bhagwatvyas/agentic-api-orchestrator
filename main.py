from __future__ import annotations

import argparse
import json
from typing import Sequence

from executor import WorkflowExecutor
from memory import WorkflowState
from planner import BasicPlanner, PlannerError
from tools import build_default_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agentic API Orchestrator")
    parser.add_argument("request", help="Natural language request to convert into a workflow.")
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Print the generated plan without executing it.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    planner = BasicPlanner()
    registry = build_default_registry()
    executor = WorkflowExecutor(registry, max_retries=1)

    try:
        plan = planner.create_plan(args.request)
    except PlannerError as exc:
        raise SystemExit(f"Planning failed: {exc}") from exc

    if args.plan_only:
        print(json.dumps([step.to_dict() for step in plan], indent=2))
        return

    state = WorkflowState()
    state.set_context("original_request", args.request)
    executions, state = executor.execute(plan, state=state)
    response = {
        "plan": [step.to_dict() for step in plan],
        "executions": [
            {
                "tool": execution.step.tool,
                "attempts": execution.attempts,
                "output": execution.output,
            }
            for execution in executions
        ],
        "state": state.snapshot(),
    }
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
