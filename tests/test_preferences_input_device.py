import os

import pytest


@pytest.mark.skipif(os.name != "posix", reason="Qt offscreen test runs on Linux only")
def test_preferences_lists_input_devices(monkeypatch):
    # Provide a fake sounddevice module
    class FakeSD:
        @staticmethod
        def query_devices():
            return [
                {"name": "Out Speakers", "max_input_channels": 0},
                {"name": "Mic A", "max_input_channels": 1},
                {"name": "Mic B", "max_input_channels": 2},
            ]

    import sys

    monkeypatch.setitem(sys.modules, "sounddevice", FakeSD)
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication
    from voicekeyboard.preferences import PreferencesDialog
    from voicekeyboard.settings import settings

    app = QApplication([])
    dlg = PreferencesDialog(lambda: None)
    # Ensure combo has our devices
    texts = [dlg.input_combo.itemText(i) for i in range(dlg.input_combo.count())]
    assert "Mic A" in texts and "Mic B" in texts

    # Choose Mic B and save
    ix = dlg.input_combo.findText("Mic B")
    dlg.input_combo.setCurrentIndex(ix)
    dlg._save()
    assert settings.audioInputDevice == "Mic B"
    app.quit()

