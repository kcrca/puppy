# Contributing

## Dev setup

```
git clone https://github.com/example/puppy
cd puppy
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[test]"
pip install ruff
```

## Running tests

```
pytest
```

## Linting

```
ruff check .
ruff format .   # auto-format
```

## Before submitting a PR

- All tests pass (`pytest`)
- No ruff errors (`ruff check .`)
- New behaviour is covered by tests
