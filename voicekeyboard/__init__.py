"""VoiceKeyboard package.

Subpackages and modules:
- voicekeyboard.app: application wiring and entrypoint
- voicekeyboard.settings: configuration manager
- voicekeyboard.window: Qt overlay window and UI helpers
- voicekeyboard.tray: system tray integration
- voicekeyboard.stt: audio capture and speech-to-text

Modules are imported directly when needed (no eager imports here) to avoid
pulling in heavy GUI/ML dependencies at package import time.
"""

from typing import List

__all__: List[str] = [
    # Intentionally left minimal to avoid eager imports
]
