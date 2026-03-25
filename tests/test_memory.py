from memory import RunRecord, resolve_inputs
from planner import MockPlanner


def test_resolve_inputs_reads_prior_step_outputs(tmp_path) -> None:
    plan = MockPlanner().create_plan("Add a --dry-run flag and update tests", target_repo=str(tmp_path))
    run = RunRecord(plan=plan)
    run.steps["inspect_repo"].output = {"discovered_files": ["main.py", "tests/test_main.py"]}

    resolved = resolve_inputs(plan.steps[1].inputs, run)

    assert resolved["targets"] == ["main.py", "tests/test_main.py"]
