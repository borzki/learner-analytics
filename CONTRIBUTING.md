# Contributing

Thanks for helping improve **learner-analytics**.

## Development setup

```bash
git clone https://github.com/borzki/learner-analytics.git
cd learner-analytics
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Workflow

1. Open an issue describing the bug or feature (templates are provided).
2. Create a branch from `main`: `git switch -c feature/short-name`.
3. Make small, focused commits with clear messages (imperative mood: "Add ...", "Fix ...").
4. Before pushing, run the same checks as CI:
   ```bash
   ruff check . && ruff format --check .
   pytest --cov=learner_analytics
   ```
5. Open a pull request that references the issue (`Closes #N`). CI must be green before merging.

## Code style

- Formatting and linting: [ruff](https://docs.astral.sh/ruff/) (line length 100).
- Public functions have type hints and NumPy-style docstrings.
- New behaviour needs a test; keep coverage above 90 %.
- Never commit real student data — use `learner-analytics simulate` for examples.
