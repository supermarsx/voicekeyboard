# VoiceKeyboard

VoiceKeyboard is a lightweight voice-to-text utility that listens on hotkeys and transcribes speech using Faster-Whisper and Silero VAD. It provides a small overlay window, a system tray icon, and configurable hotkeys.

Features
- Faster-Whisper transcription with Silero VAD voice activity detection
- Global hotkeys for start/stop and push-to-talk
- Minimal Qt overlay window (frameless, always-on-top)
- System tray icon with quick actions
- Headless and dry-run modes for CI/testing

Quickstart
- Install dev deps: `pip install -r requirements-dev.txt`
- Run: `voicekeyboard`
- Edit hotkeys: tray → Settings → Edit hotkeys…

Environment flags
- `VOICEKB_DRYRUN`: skip heavy model downloads (e.g., `1` in CI/tests)
- `VOICEKB_HEADLESS`: don’t start Qt window or tray (e.g., `1` in CI)
- `VOICEKB_AUTOCLOSE_MS`: auto-close Qt after N ms (GUI smoke)
- `VOICEKB_DISABLE_HOTKEYS`: disable system-wide hotkeys (CI/shared machines)
