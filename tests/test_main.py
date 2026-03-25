from pathlib import Path

from main import main


def test_main_plan_prints_plan_without_mutating_repo(tmp_path, capsys) -> None:
    _write_sample_repo(tmp_path)

    main(["plan", "Add a --dry-run flag and update tests", "--repo", str(tmp_path)])

    captured = capsys.readouterr()
    assert "Plan:" in captured.out
    assert "--dry-run" not in (tmp_path / "main.py").read_text()


def test_main_apply_persists_run_and_updates_repo(tmp_path, capsys) -> None:
    _write_sample_repo(tmp_path)

    main(["apply", "Add a --dry-run flag and update tests", "--repo", str(tmp_path)])

    captured = capsys.readouterr()
    run_files = list((tmp_path / ".agentic_dev" / "runs").glob("*.json"))

    assert "Status: succeeded" in captured.out
    assert run_files
    assert "--dry-run" in (tmp_path / "main.py").read_text()


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
