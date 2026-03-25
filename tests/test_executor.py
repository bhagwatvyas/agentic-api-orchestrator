from pathlib import Path

from executor import WorkflowExecutor
from memory import RunRecord
from planner import MockPlanner
from run_store import RunStore


def test_executor_applies_patch_and_runs_validation(tmp_path) -> None:
    _write_sample_repo(tmp_path)
    plan = MockPlanner().create_plan("Add a --dry-run flag and update tests", target_repo=str(tmp_path))
    store = RunStore(tmp_path / ".agentic_dev" / "runs")
    executor = WorkflowExecutor(store=store)

    run = executor.start(plan)
    completed = executor.execute(run)

    assert completed.status == "succeeded"
    assert completed.steps["apply_patch"].output["changed_files"] == ["main.py", "tests/test_main.py"]
    assert "--dry-run" in (tmp_path / "main.py").read_text()
    assert "test_main_dry_run_prints_payload" in (tmp_path / "tests/test_main.py").read_text()


def test_executor_resume_skips_completed_steps(tmp_path) -> None:
    _write_sample_repo(tmp_path)
    plan = MockPlanner().create_plan("Add a --dry-run flag and update tests", target_repo=str(tmp_path))
    store = RunStore(tmp_path / ".agentic_dev" / "runs")
    executor = WorkflowExecutor(store=store)

    partial_run = RunRecord(plan=plan)
    partial_run.steps["inspect_repo"].status = "succeeded"
    partial_run.steps["inspect_repo"].output = {
        "discovered_files": ["main.py", "tests/test_main.py"],
        "files": {},
    }
    partial_run.steps["propose_patch"].status = "succeeded"
    partial_run.steps["propose_patch"].output = {
        "patch": {
            "change_kind": "add_dry_run_flag",
            "files": [
                {
                    "path": "main.py",
                    "before": (tmp_path / "main.py").read_text(),
                    "after": (tmp_path / "main.py").read_text().replace(
                        '    parser.add_argument("request", help="User request.")\n',
                        '    parser.add_argument("request", help="User request.")\n'
                        '    parser.add_argument("--dry-run", action="store_true", help="Show parsed input and exit.")\n',
                    ),
                },
                {
                    "path": "tests/test_main.py",
                    "before": (tmp_path / "tests/test_main.py").read_text(),
                    "after": (tmp_path / "tests/test_main.py").read_text()
                    + '\n\ndef test_placeholder() -> None:\n    assert True\n',
                },
            ],
        },
        "summary": "ready",
    }
    store.save(partial_run)

    resumed = executor.execute(store.load(plan.run_id))

    assert resumed.steps["inspect_repo"].attempts == 0
    assert resumed.steps["propose_patch"].attempts == 0
    assert resumed.steps["apply_patch"].status == "succeeded"


def _write_sample_repo(repo_path: Path) -> None:
    (repo_path / "tests").mkdir(parents=True, exist_ok=True)
    (repo_path / "main.py").write_text(
        "from __future__ import annotations\n"
        "\n"
        "import argparse\n"
        "\n"
        "\n"
        "def build_parser() -> argparse.ArgumentParser:\n"
        '    parser = argparse.ArgumentParser(description="Sample CLI")\n'
        '    parser.add_argument("request", help="User request.")\n'
        "    return parser\n"
        "\n"
        "\n"
        "def main(argv: list[str] | None = None) -> None:\n"
        "    args = build_parser().parse_args(argv)\n"
        '    print(args.request)\n'
        "\n"
        "\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )
    (repo_path / "tests/test_main.py").write_text(
        "import json\n"
        "\n"
        "from main import main\n"
        "\n"
        "\n"
        "def test_main_prints_request(capsys) -> None:\n"
        '    main(["hello"])\n'
        "\n"
        "    captured = capsys.readouterr()\n"
        '    assert captured.out.strip() == "hello"\n'
    )
