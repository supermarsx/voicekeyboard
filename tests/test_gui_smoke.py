import os
import time

import pytest

from voicekeyboard.settings import settings
from voicekeyboard.window import WindowManager


@pytest.mark.skipif(os.name != "posix", reason="CI xvfb smoke runs on Linux only")
def test_gui_smoke(monkeypatch):
    # Configure for quick auto-close
    monkeypatch.setenv("VOICEKB_AUTOCLOSE_MS", "300")
    # Ensure window is shown (xvfb provides display in CI)
    settings.windowShow = True
    WindowManager.start()
    # Give it time to start and quit
    time.sleep(1)
    # If we reached here, no exception occurred
    assert True
