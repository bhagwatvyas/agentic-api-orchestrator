# Agentic Developer Platform

Small Python CLI for turning constrained natural-language developer requests into typed workflow plans, showing the plan before execution, and then deterministically applying local repo changes with validation and durable run state.

## Core Ideas

- Typed action model instead of arbitrary shell planning
- Fail-closed planning and validation
- Terraform-style `plan` output before execution
- Durable run records with `show-run` and `resume`
- Mock planner adapter so architecture is agentic without relying on a real model

## Supported V1 Workflow

V1 intentionally supports one concrete developer task:

- `add a --dry-run flag and update tests`

The generated workflow is:

1. Inspect `main.py` and `tests/test_main.py`
2. Propose a deterministic patch
3. Apply the patch
4. Run tests
5. Run lint-style syntax validation
6. Summarize results

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .[dev]
```

## Demo

This demo uses a throwaway repo in `/tmp` so you can see the full flow without changing this project.

### 1. Create a sample repo

```bash
mkdir -p /tmp/agentic-dev-demo/tests
```

Create `/tmp/agentic-dev-demo/main.py`:

```python
from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sample CLI")
    parser.add_argument("request", help="User request.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    print(args.request)


if __name__ == "__main__":
    main()
```

Create `/tmp/agentic-dev-demo/tests/test_main.py`:

```python
import json

from main import main


def test_main_prints_request(capsys) -> None:
    main(["hello"])

    captured = capsys.readouterr()
    assert captured.out.strip() == "hello"
```

### 2. Generate the execution plan

```bash
python3 main.py plan "Add a --dry-run flag and update tests" --repo /tmp/agentic-dev-demo
```

Expected output:

```bash
Plan: 6 to add, 0 to change, 0 to destroy
Run ID: run_<generated_id>
Request: Add a --dry-run flag and update tests
Target Repo: /private/tmp/agentic-dev-demo

+ inspect_repo [inspect_files]
  files: main.py, tests/test_main.py
+ propose_patch [propose_patch]
  change: add_dry_run_flag
+ apply_patch [apply_patch]
+ run_tests [run_tests]
  command: pytest tests/test_main.py
+ run_lint [run_lint]
  files: main.py, tests/test_main.py
+ summarize_results [summarize_results]
```

What this shows:
- The system mapped the natural-language request into a fixed typed plan.
- Nothing in the target repo changed yet.

### 3. Apply the plan

```bash
python3 main.py apply "Add a --dry-run flag and update tests" --repo /tmp/agentic-dev-demo
```

Expected output:

```bash
Plan: 6 to add, 0 to change, 0 to destroy
Run ID: run_<generated_id>
Request: Add a --dry-run flag and update tests
Target Repo: /private/tmp/agentic-dev-demo

+ inspect_repo [inspect_files]
  files: main.py, tests/test_main.py
+ propose_patch [propose_patch]
  change: add_dry_run_flag
+ apply_patch [apply_patch]
+ run_tests [run_tests]
  command: pytest tests/test_main.py
+ run_lint [run_lint]
  files: main.py, tests/test_main.py
+ summarize_results [summarize_results]

Run run_<generated_id>
Status: succeeded

- inspect_repo: succeeded (attempts=1, action=inspect_files)
- propose_patch: succeeded (attempts=1, action=propose_patch)
  summary: Add a --dry-run flag to the CLI and cover it with a test.
- apply_patch: succeeded (attempts=1, action=apply_patch)
  summary: Updated 2 files.
- run_tests: succeeded (attempts=1, action=run_tests)
  summary: Tests passed.
- run_lint: succeeded (attempts=1, action=run_lint)
  summary: Lint passed.
- summarize_results: succeeded (attempts=1, action=summarize_results)
  summary: {'changed_files': ['main.py', 'tests/test_main.py'], 'tests': 'Tests passed.', 'lint': 'Lint passed.'}
```

What this shows:
- The plan is printed before execution.
- Execution is sequential and deterministic.
- Validation gates success.
- Each step is persisted with status and summary.

### 4. Inspect the changed files

Inspect `/tmp/agentic-dev-demo/main.py`. Expected result:

```python
from __future__ import annotations

import argparse
import json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sample CLI")
    parser.add_argument("request", help="User request.")
    parser.add_argument("--dry-run", action="store_true", help="Show parsed input and exit.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    if args.dry_run:
        print(json.dumps({"request": args.request, "dry_run": True}, indent=2))
        return
    print(args.request)


if __name__ == "__main__":
    main()
```

Inspect `/tmp/agentic-dev-demo/tests/test_main.py`. Expected result:

```python
import json

from main import main


def test_main_prints_request(capsys) -> None:
    main(["hello"])

    captured = capsys.readouterr()
    assert captured.out.strip() == "hello"


def test_main_dry_run_prints_payload(capsys) -> None:
    main(["--dry-run", "ship it"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload == {"request": "ship it", "dry_run": True}
```

### 5. Show the persisted run record

```bash
python3 main.py show-run <run_id> --repo /tmp/agentic-dev-demo
```

Expected output:

```bash
Run run_<generated_id>
Status: succeeded

- inspect_repo: succeeded (attempts=1, action=inspect_files)
- propose_patch: succeeded (attempts=1, action=propose_patch)
  summary: Add a --dry-run flag to the CLI and cover it with a test.
- apply_patch: succeeded (attempts=1, action=apply_patch)
  summary: Updated 2 files.
- run_tests: succeeded (attempts=1, action=run_tests)
  summary: Tests passed.
- run_lint: succeeded (attempts=1, action=run_lint)
  summary: Lint passed.
- summarize_results: succeeded (attempts=1, action=summarize_results)
  summary: {'changed_files': ['main.py', 'tests/test_main.py'], 'tests': 'Tests passed.', 'lint': 'Lint passed.'}
```

Run state is stored under `/tmp/agentic-dev-demo/.agentic_dev/runs/`.

### 6. Resume a run

```bash
python3 main.py resume <run_id> --repo /tmp/agentic-dev-demo
```

Expected behavior:
- If the run already succeeded, the stored step state is reused and no completed step is rerun.
- If a run stopped mid-way, execution resumes from the first incomplete step.

## Simple Use Cases

- Demo deterministic planning:
  - `python3 main.py plan "Add a --dry-run flag and update tests" --repo /tmp/agentic-dev-demo`
- Demo end-to-end execution:
  - `python3 main.py apply "Add a --dry-run flag and update tests" --repo /tmp/agentic-dev-demo`
- Demo persisted execution state:
  - `python3 main.py show-run <run_id> --repo /tmp/agentic-dev-demo`
- Demo resumability:
  - `python3 main.py resume <run_id> --repo /tmp/agentic-dev-demo`
- Demo fail-closed behavior:
  - `python3 main.py plan "Deploy this service to prod" --repo /tmp/agentic-dev-demo`
  - Expected result: planning fails because the request is outside the supported typed workflow.

## Testing

```bash
.venv/bin/python -m pytest
```
