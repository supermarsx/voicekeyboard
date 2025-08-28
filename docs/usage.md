# Usage

Launching
- Command: `voicekeyboard`
- The app starts the tray icon and Qt window (unless headless), initializes the STT pipeline, and listens for hotkeys.

Hotkeys
- Start: configured in `settings.ini` (default `ctrl+shift+a`)
- Stop: configured in `settings.ini` (default `ctrl+shift+b`)
- Push-to-talk: press to start, release to stop (default `alt+p`)

Tray actions
- Toggle window: show/hide the overlay window
- Edit hotkeys: opens a dialog to change keybindings and reloads them immediately
- Open settings: opens `settings.ini`
- Restart/Quit: restart or exit the app

Configuration
- `settings.ini` stores all preferences. Changes take effect on restart, or immediately for hotkeys changed via the dialog.
- Logging is enabled by default and writes to `application.log`.

Testing modes
- Dry run: `VOICEKB_DRYRUN=1` (skips model downloads and VAD init)
- Headless: `VOICEKB_HEADLESS=1` (no window or tray)
- GUI auto-close: `VOICEKB_AUTOCLOSE_MS=500` useful with `xvfb-run` in CI
