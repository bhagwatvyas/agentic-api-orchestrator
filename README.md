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

Generate a plan:

```bash
python3 main.py plan "Add a --dry-run flag and update tests" --repo .
```

Apply it:

```bash
python3 main.py apply "Add a --dry-run flag and update tests" --repo .
```

Inspect a saved run:

```bash
python3 main.py show-run <run_id> --repo .
python3 main.py resume <run_id> --repo .
```

Run state is stored under `.agentic_dev/runs/`.

## Testing

```bash
pytest
```
