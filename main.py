from voicekeyboard.app import Generic
from voicekeyboard.app import main as _main

if __name__ == "__main__":
    Generic.startup()
    _main()
"""Thin wrapper to launch the VoiceKeyboard console application.

Delegates to ``voicekeyboard.app.Generic.startup`` and ``voicekeyboard.app.main``.
"""
