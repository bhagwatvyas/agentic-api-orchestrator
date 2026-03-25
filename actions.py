from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Any


class ActionError(Exception):
    """Raised when an action cannot complete successfully."""


@dataclass(slots=True)
class ActionContext:
    repo_path: Path


def run_action(action_type: str, inputs: dict[str, Any], context: ActionContext) -> Any:
    handlers = {
        "inspect_files": inspect_files,
        "propose_patch": propose_patch,
        "apply_patch": apply_patch_action,
        "run_tests": run_tests,
        "run_lint": run_lint,
        "summarize_results": summarize_results,
    }
    try:
        handler = handlers[action_type]
    except KeyError as exc:
        raise ActionError(f"No handler registered for action {action_type!r}.") from exc
    return handler(inputs, context)


def inspect_files(inputs: dict[str, Any], context: ActionContext) -> dict[str, Any]:
    discovered_files: list[str] = []
    files: dict[str, dict[str, Any]] = {}

    for relative_path in inputs["paths"]:
        path = context.repo_path / relative_path
        if not path.exists():
            raise ActionError(f"Expected file {relative_path!r} to exist in target repo.")
        content = path.read_text()
        discovered_files.append(relative_path)
        files[_key_for_path(relative_path)] = {
            "path": relative_path,
            "line_count": len(content.splitlines()),
            "content": content,
        }

    return {
        "discovered_files": discovered_files,
        "files": files,
    }


def propose_patch(inputs: dict[str, Any], context: ActionContext) -> dict[str, Any]:
    change_kind = inputs["change_kind"]
    if change_kind != "add_dry_run_flag":
        raise ActionError(f"Unsupported change kind {change_kind!r}.")

    targets = list(inputs["targets"])
    if targets != ["main.py", "tests/test_main.py"]:
        raise ActionError(
            "V1 add_dry_run_flag workflow expects targets ['main.py', 'tests/test_main.py']."
        )

    main_path = context.repo_path / "main.py"
    test_path = context.repo_path / "tests/test_main.py"
    original_main = main_path.read_text()
    original_test = test_path.read_text()

    updated_main = _patch_main_for_dry_run(original_main)
    updated_test = _patch_test_for_dry_run(original_test)

    patch = {
        "change_kind": change_kind,
        "files": [
            {
                "path": "main.py",
                "before": original_main,
                "after": updated_main,
            },
            {
                "path": "tests/test_main.py",
                "before": original_test,
                "after": updated_test,
            },
        ],
    }

    return {
        "patch": patch,
        "summary": "Add a --dry-run flag to the CLI and cover it with a test.",
    }


def apply_patch_action(inputs: dict[str, Any], context: ActionContext) -> dict[str, Any]:
    patch = inputs["patch"]
    changed_files: list[str] = []

    for file_change in patch["files"]:
        path = context.repo_path / file_change["path"]
        current_content = path.read_text()
        expected_before = file_change["before"]
        if current_content != expected_before:
            raise ActionError(
                f"Refusing to apply patch for {file_change['path']!r}; file changed since planning."
            )
        updated_content = file_change["after"]
        if current_content != updated_content:
            path.write_text(updated_content)
            changed_files.append(file_change["path"])

    return {
        "changed_files": changed_files,
        "summary": f"Updated {len(changed_files)} files.",
    }


def run_tests(inputs: dict[str, Any], context: ActionContext) -> dict[str, Any]:
    command = _normalize_command(inputs["command"])
    completed = subprocess.run(
        command,
        cwd=context.repo_path,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ActionError(_format_process_failure("Tests", completed))
    return {
        "command": command,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "summary": "Tests passed.",
    }


def run_lint(inputs: dict[str, Any], context: ActionContext) -> dict[str, Any]:
    paths = [str(context.repo_path / relative_path) for relative_path in inputs["paths"]]
    command = [sys.executable, "-m", "py_compile", *paths]
    completed = subprocess.run(
        command,
        cwd=context.repo_path,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ActionError(_format_process_failure("Lint", completed))
    return {
        "command": command,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "summary": "Lint passed.",
    }


def summarize_results(inputs: dict[str, Any], context: ActionContext) -> dict[str, Any]:
    del context
    return {
        "summary": {
            "changed_files": inputs["changed_files"],
            "tests": inputs["test_summary"],
            "lint": inputs["lint_summary"],
        }
    }


def _patch_main_for_dry_run(content: str) -> str:
    if '--dry-run' in content:
        return content

    updated = content
    if "import json" not in updated:
        if "import argparse\n" not in updated:
            raise ActionError("Could not locate argparse import in main.py.")
        updated = updated.replace("import argparse\n", "import argparse\nimport json\n", 1)

    argument_anchor = '    parser.add_argument("request", help="User request.")\n'
    if argument_anchor not in updated:
        raise ActionError("Could not locate request argument definition in main.py.")
    updated = updated.replace(
        argument_anchor,
        argument_anchor
        + '    parser.add_argument("--dry-run", action="store_true", help="Show parsed input and exit.")\n',
        1,
    )

    parse_anchor = "    args = build_parser().parse_args(argv)\n"
    if parse_anchor not in updated:
        raise ActionError("Could not locate argument parsing in main.py.")
    updated = updated.replace(
        parse_anchor,
        parse_anchor
        + '\n'
        + "    if args.dry_run:\n"
        + '        print(json.dumps({"request": args.request, "dry_run": True}, indent=2))\n'
        + "        return\n",
        1,
    )

    return updated


def _patch_test_for_dry_run(content: str) -> str:
    if "test_main_dry_run_prints_payload" in content:
        return content

    addition = (
        "\n\ndef test_main_dry_run_prints_payload(capsys) -> None:\n"
        '    main(["--dry-run", "ship it"])\n'
        "\n"
        "    captured = capsys.readouterr()\n"
        "    payload = json.loads(captured.out)\n"
        "\n"
        '    assert payload == {"request": "ship it", "dry_run": True}\n'
    )
    return content.rstrip() + addition + "\n"


def _key_for_path(relative_path: str) -> str:
    return relative_path.replace("/", "_").replace(".", "_")


def _normalize_command(command: list[str]) -> list[str]:
    if not command:
        raise ActionError("Command cannot be empty.")
    if command[0] == "pytest":
        return [sys.executable, "-m", *command]
    return command


def _format_process_failure(label: str, completed: subprocess.CompletedProcess[str]) -> str:
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    fragments = [f"{label} command failed with exit code {completed.returncode}."]
    if stdout:
        fragments.append(f"stdout:\n{stdout}")
    if stderr:
        fragments.append(f"stderr:\n{stderr}")
    return "\n".join(fragments)
