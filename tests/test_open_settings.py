import sys

from voicekeyboard.app import Generic


def test_open_settings_posix(monkeypatch):
    calls = []

    def fake_popen(args):
        calls.append(tuple(args))

        class P:
            pass

        return P()

    monkeypatch.setattr(sys, "platform", "linux")
    import subprocess as sp

    monkeypatch.setattr(sp, "Popen", fake_popen)
    Generic.openSettings()
    assert calls and calls[0][0] in ("xdg-open",)
