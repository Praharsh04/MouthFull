# Contributing to VoiceFlow Local

Thank you for your interest in contributing!

## Development Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
pytest --cov=voiceflow
```

## Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check src/ tests/
ruff format src/ tests/
```

## Pull Request Guidelines

1. Create a feature branch from `main`.
2. Write tests for new functionality.
3. Ensure all tests pass and linting is clean.
4. Submit a PR with a clear description of changes.
