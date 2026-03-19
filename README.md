# Agentic API Orchestrator

Small Python scaffold for converting natural language into multi-step API workflows.

## Components

- `planner.py`: plan schema plus a basic planner stub.
- `tools/`: tool definitions, schemas, and registry.
- `executor.py`: sequential executor with state resolution and retry support.
- `memory.py`: workflow state store.
- `main.py`: CLI entrypoint.

## Run

Create an isolated environment first:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .[dev]
```

Then run:

```bash
python3 main.py "Find me flights from San Francisco to Tokyo and hotels there"
```

```bash
python3 main.py --plan-only "What's the weather in Lisbon?"
```

You can also run the installed CLI:

```bash
agentic-api-orchestrator "Find flights from San Francisco to Tokyo and hotels there"
```

## State References

Later steps can consume prior results using `{{state...}}` placeholders.

Examples:

- `{{state.steps.0.output.destination}}`
- `{{state.tool_outputs.search_flights.0.origin}}`

The planner stub already emits this pattern for chained steps like "find flights ... and hotels there".

## VS Code

Open the workspace in VS Code and use:

- `Run and Debug` with `Run Orchestrator` or `Plan Only`
- `Terminal > Run Task` with `Run orchestrator` or `Show plan only`

Recommended extensions are declared in `.vscode/extensions.json`.
The workspace is configured to use `.venv/bin/python` as the default interpreter.

## Testing

Run the test suite with:

```bash
pytest
```

## GitHub Readiness

The repo now includes:

- `pyproject.toml` for packaging and install metadata
- `.github/workflows/ci.yml` for automated test runs
- `LICENSE` and `CONTRIBUTING.md` for standard open-source repo hygiene
