from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from executor import ExecutionError, WorkflowExecutor
from planner import MockPlanner, PlannerError
from reporter import render_plan, render_run
from run_store import RunStore
from validator import PlanValidationError, PlanValidator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agentic Developer Platform")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Generate and validate a plan.")
    plan_parser.add_argument("request", help="Natural language developer request.")
    plan_parser.add_argument("--repo", default=".", help="Target repository path.")

    apply_parser = subparsers.add_parser("apply", help="Generate a plan and execute it.")
    apply_parser.add_argument("request", help="Natural language developer request.")
    apply_parser.add_argument("--repo", default=".", help="Target repository path.")

    resume_parser = subparsers.add_parser("resume", help="Resume an existing run.")
    resume_parser.add_argument("run_id", help="Run identifier.")
    resume_parser.add_argument("--repo", default=".", help="Target repository path.")

    show_run_parser = subparsers.add_parser("show-run", help="Show persisted run details.")
    show_run_parser.add_argument("run_id", help="Run identifier.")
    show_run_parser.add_argument("--repo", default=".", help="Target repository path.")

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    repo_path = Path(args.repo).resolve()
    store = RunStore(repo_path / ".agentic_dev" / "runs")

    if args.command == "show-run":
        run = store.load(args.run_id)
        print(render_run(run))
        return

    executor = WorkflowExecutor(store=store)

    if args.command == "resume":
        run = store.load(args.run_id)
        try:
            updated = executor.execute(run)
        except ExecutionError as exc:
            raise SystemExit(str(exc)) from exc
        print(render_run(updated))
        return

    planner = MockPlanner()
    validator = PlanValidator()

    try:
        plan = planner.create_plan(args.request, target_repo=str(repo_path))
        validator.validate(plan)
    except (PlannerError, PlanValidationError) as exc:
        raise SystemExit(f"Planning failed: {exc}") from exc

    print(render_plan(plan))
    if args.command == "plan":
        return

    run = executor.start(plan)
    try:
        updated = executor.execute(run)
    except ExecutionError as exc:
        raise SystemExit(str(exc)) from exc
    print()
    print(render_run(updated))


if __name__ == "__main__":
    main()
