import os

import pytest


@pytest.mark.skipif(os.name != "posix", reason="Qt offscreen test runs on Linux only")
def test_label_updater_offscreen(monkeypatch):
    # Run Qt in offscreen mode to avoid display
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication

    from voicekeyboard.window import WindowManager, labelUpdater, windowLabel

    app = QApplication([])
    _ = WindowManager()
    # Emit a change
    labelUpdater.textChanged.emit("Hello")
    # Process events
    app.processEvents()
    assert windowLabel is not None and windowLabel.text() == "Hello"
    app.quit()
