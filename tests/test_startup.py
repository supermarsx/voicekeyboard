from voicekeyboard import app
from voicekeyboard.settings import settings
from voicekeyboard.stt import SpeechConverter


def test_startup_headless_dryrun(monkeypatch):
    monkeypatch.setenv("VOICEKB_DRYRUN", "1")
    monkeypatch.setenv("VOICEKB_HEADLESS", "1")

    # Ensure startup completes without launching Qt/tray
    app.Generic.startup()

    # Basic components should be instantiable
    sc = SpeechConverter()
    assert sc.model is None
    assert sc.vadModel is None

    # Hotkeys should load without raising when keyboard is patched
    app.speechConverter = sc
    # No-op monkeypatches for keyboard to avoid real hooks
    monkeypatch.setattr(app.keyboard, "add_hotkey", lambda *a, **k: None)
    monkeypatch.setattr(app.keyboard, "on_press_key", lambda *a, **k: None)
    monkeypatch.setattr(app.keyboard, "on_release_key", lambda *a, **k: None)
    settings.loadHotkeys()
