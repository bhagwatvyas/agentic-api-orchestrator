# Contributing

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .[dev]
```

## Tests

```bash
pytest
```

## Pull requests

- Keep changes focused and documented.
- Add or update tests when behavior changes.
- Run the test suite before opening a PR.
