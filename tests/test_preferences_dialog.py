import os

import pytest


@pytest.mark.skipif(os.name != "posix", reason="Qt offscreen test runs on Linux only")
def test_preferences_dialog_updates_and_applies(monkeypatch):
    # Run Qt in offscreen mode to avoid display
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication

    from voicekeyboard.preferences import PreferencesDialog
    from voicekeyboard.settings import settings

    calls = {"reloaded": 0}

    def reloader():
        calls["reloaded"] += 1

    app = QApplication([])
    dlg = PreferencesDialog(reloader)
    # Simulate editing values
    dlg.start_edit.setText("ctrl+alt+s")
    dlg.stop_edit.setText("ctrl+alt+x")
    dlg.ptt_edit.setText("alt+z")
    # Save
    dlg._save()
    # Verify settings updated and reloader called
    assert settings.hotkeyStartRecording == "ctrl+alt+s"
    assert settings.hotkeyStopRecording == "ctrl+alt+x"
    assert settings.hotkeyPushToTalk == "alt+z"
    assert calls["reloaded"] == 1
    app.quit()
