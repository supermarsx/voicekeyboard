# Development

Environment
- Python 3.9+
- Dev deps: `pip install -r requirements-dev.txt`

Common tasks
- Lint: `ruff check . && black --check .`
- Type check: `mypy .`
- Tests: `VOICEKB_DRYRUN=1 VOICEKB_HEADLESS=1 pytest`
- GUI smoke (Linux): `VOICEKB_DRYRUN=1 VOICEKB_AUTOCLOSE_MS=500 xvfb-run -a pytest -q tests/test_gui_smoke.py`
- Pre-commit: `pre-commit install` to run hooks locally

Docs
- Build and serve docs: `mkdocs serve`
- Build static site: `mkdocs build`

Packaging
- PyInstaller specs in `packaging/` for Linux, Windows, and macOS.

CI
- GitHub Actions run lint, type checks, tests, and GUI smoke tests in xvfb.
