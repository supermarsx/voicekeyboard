from voicekeyboard import app
from voicekeyboard.settings import settings


class DummySpeech:
    def __init__(self):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def test_hotkeys_register(monkeypatch):
    # Patch keyboard functions to capture registrations
    calls = {"add": [], "press": [], "release": []}

    def fake_add_hotkey(combo, func):
        calls["add"].append(combo)

    def fake_on_press_key(key, func):
        calls["press"].append(key)

    def fake_on_release_key(key, func):
        calls["release"].append(key)

    monkeypatch.setattr(app.keyboard, "add_hotkey", fake_add_hotkey)
    monkeypatch.setattr(app.keyboard, "on_press_key", fake_on_press_key)
    monkeypatch.setattr(app.keyboard, "on_release_key", fake_on_release_key)

    # Install dummy speech converter global used by hotkeys
    app.speechConverter = DummySpeech()

    app.Hotkeys.Load.allKeys()

    assert settings.hotkeyStartRecording in calls["add"]
    assert settings.hotkeyStopRecording in calls["add"]
    assert settings.hotkeyPushToTalk in calls["press"]
    assert settings.hotkeyPushToTalk in calls["release"]
