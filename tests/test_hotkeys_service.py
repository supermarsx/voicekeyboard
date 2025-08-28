import time

from voicekeyboard.hotkeys import HotkeysManager, HotkeysService


def test_hotkeys_service_start_stop(monkeypatch):
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

    manager = HotkeysManager(lambda: None, lambda: None)
    svc = HotkeysService(manager)
    svc.start()
    time.sleep(0.05)
    svc.stop()

    assert len(calls["add"]) >= 2
    assert len(calls["press"]) == 1
    assert len(calls["release"]) == 1


def test_hotkeys_service_disabled(monkeypatch):
    # Ensure no registration occurs when disabled via env
    import keyboard as kb

    monkeypatch.setenv("VOICEKB_DISABLE_HOTKEYS", "1")

    def _fail(*_a, **_k):
        raise AssertionError()

    monkeypatch.setattr(kb, "add_hotkey", _fail)
    monkeypatch.setattr(kb, "on_press_key", _fail)
    monkeypatch.setattr(kb, "on_release_key", _fail)

    svc = HotkeysService(HotkeysManager(lambda: None, lambda: None))
    svc.start()  # Should no-op
    svc.stop()
