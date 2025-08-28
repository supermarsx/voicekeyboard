# VoiceKeyboard

Simple voice-to-text utility using Faster-Whisper and Silero VAD.

## Development

- Create a virtualenv and install dev deps: `pip install -e .[dev]`
- Enable hooks (optional): `pre-commit install`
- Lint: `make lint` or `python -m ruff check .`
- Format: `make fmt` or `python -m ruff check --fix . && python -m black .`
- Type check: `make type` or `python -m mypy --hide-error-codes --pretty voicekeyboard`
- Tests: `make test` or `python -m pytest -q`
- Docs: `make docs` or `python -m mkdocs build --strict`

Environment flags
- `VOICEKB_DRYRUN=1` to skip heavy model downloads and VAD init during tests/CI.
- `VOICEKB_HEADLESS=1` to skip starting the Qt window and tray icon during tests/CI.
- `VOICEKB_DISABLE_HOTKEYS=1` to avoid registering system-wide hotkeys.

Run
- After install, launch with: `voicekeyboard`

Packaging
- Build with PyInstaller (spec files under `packaging/`):
  - `pip install pyinstaller`
  - `pyinstaller packaging/voicekeyboard.spec`
  - Windows: `pyinstaller packaging/windows.spec`
  - macOS: `pyinstaller packaging/macos.spec`

Type checking
- Run mypy: `python -m mypy --hide-error-codes --pretty voicekeyboard`

Docs
- Local: `python -m mkdocs serve`
- Build: `python -m mkdocs build --strict`

### Optional dependencies

Extras are provided for more granular installs (base install already includes full app deps):

- `pip install .[gui]` — UI/tray libraries (PyQt6, pystray, Pillow)
- `pip install .[ml]` — ML backend (torch, faster-whisper)
- `pip install .[audio]` — Audio capture (sounddevice, numpy)
- `pip install .[docs]` — Docs toolchain (mkdocs, mkdocstrings, etc.)
- `pip install .[dev]` — Dev tools (pytest, ruff, black, mypy, docs)
