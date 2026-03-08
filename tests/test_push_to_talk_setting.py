import time

from voicekeyboard.hotkeys import HotkeysManager, HotkeysService


def test_push_to_talk_not_registered_when_disabled(monkeypatch):
    """Push-to-talk hotkeys should NOT be registered when pushToTalk is False."""
    calls = {"add": [], "press": [], "release": []}

    def fake_add_hotkey(combo, func):
        calls["add"].append(combo)

    def fake_on_press_key(key, func):
        calls["press"].append(key)

    def fake_on_release_key(key, func):
        calls["release"].append(key)

    import keyboard as kb

    monkeypatch.setattr(kb, "add_hotkey", fake_add_hotkey)
    monkeypatch.setattr(kb, "on_press_key", fake_on_press_key)
    monkeypatch.setattr(kb, "on_release_key", fake_on_release_key)
    monkeypatch.setenv("VOICEKB_DISABLE_HOTKEYS", "0")

    from voicekeyboard.settings import settings

    monkeypatch.setattr(settings, "pushToTalk", False)

    manager = HotkeysManager(lambda: None, lambda: None)
    svc = HotkeysService(manager)
    svc.start()
    time.sleep(0.05)
    svc.stop()

    # Start/stop hotkeys should be registered
    assert len(calls["add"]) >= 2
    # Push-to-talk should NOT be registered
    assert len(calls["press"]) == 0
    assert len(calls["release"]) == 0


def test_push_to_talk_registered_when_enabled(monkeypatch):
    """Push-to-talk hotkeys should be registered when pushToTalk is True."""
    calls = {"add": [], "press": [], "release": []}

    def fake_add_hotkey(combo, func):
        calls["add"].append(combo)

    def fake_on_press_key(key, func):
        calls["press"].append(key)

    def fake_on_release_key(key, func):
        calls["release"].append(key)

    import keyboard as kb

    monkeypatch.setattr(kb, "add_hotkey", fake_add_hotkey)
    monkeypatch.setattr(kb, "on_press_key", fake_on_press_key)
    monkeypatch.setattr(kb, "on_release_key", fake_on_release_key)
    monkeypatch.setenv("VOICEKB_DISABLE_HOTKEYS", "0")

    from voicekeyboard.settings import settings

    monkeypatch.setattr(settings, "pushToTalk", True)

    manager = HotkeysManager(lambda: None, lambda: None)
    svc = HotkeysService(manager)
    svc.start()
    time.sleep(0.05)
    svc.stop()

    # Start/stop hotkeys should be registered
    assert len(calls["add"]) >= 2
    # Push-to-talk should be registered
    assert len(calls["press"]) == 1
    assert len(calls["release"]) == 1
