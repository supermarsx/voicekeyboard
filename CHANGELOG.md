# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0]

- Fixed lint across codebase (Ruff) and applied formatting (Black).
- Resolved all test failures; improved test stability for headless/CI.
- Introduced lazy imports to avoid heavy GUI/tray dependencies at module import time.
- Improved typing; mypy passes cleanly on `voicekeyboard/`.
- Added GitHub Actions CI: lint/type, tests (Windows/Linux with Qt offscreen), and docs build.
- Added pre-commit hooks for ruff, black, mypy.
- Added optional extras in `pyproject.toml` (`gui`, `ml`, `audio`, `docs`, `dev`).
- Added Makefile with common tasks.
- Enhanced README with developer workflow and optional extras.
- Verified docs build using MkDocs.

## [0.1.0]

- Initial release.

