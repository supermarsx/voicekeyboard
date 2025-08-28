import logging
import os
import threading
import time
from typing import Callable, Optional

import keyboard

from .settings import settings


class HotkeysManager:
    def __init__(self, start_fn: Callable[[], None], stop_fn: Callable[[], None]):
        self.start_fn: Callable[[], None] = start_fn
        self.stop_fn: Callable[[], None] = stop_fn

    def register_start(self):
        """Register global start-recording hotkey."""
        keyboard.add_hotkey(settings.hotkeyStartRecording, self.start_fn)
        logging.debug(f"Loaded start recording hotkey: {settings.hotkeyStartRecording}")

    def register_stop(self):
        """Register global stop-recording hotkey."""
        keyboard.add_hotkey(settings.hotkeyStopRecording, self.stop_fn)
        logging.debug(f"Loaded stop recording hotkey: {settings.hotkeyStopRecording}")

    def register_push_to_talk(self):
        """Register push-to-talk: press to start, release to stop."""
        keyboard.on_press_key(settings.hotkeyPushToTalk, lambda _e: self.start_fn())
        keyboard.on_release_key(settings.hotkeyPushToTalk, lambda _e: self.stop_fn())
        logging.debug(f"Loaded push-to-talk recording hotkey: {settings.hotkeyPushToTalk}")

    def register_all(self):
        """Register all configured hotkeys with the OS."""
        logging.debug("Loading hotkeys")
        self.register_start()
        self.register_stop()
        self.register_push_to_talk()


class HotkeysService:
    def __init__(self, manager: HotkeysManager):
        self.manager: HotkeysManager = manager
        self._thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()

    def start(self):
        """Start the service thread and register all hotkeys unless disabled."""
        if self._thread and self._thread.is_alive():
            return
        # Optionally disable via env for CI/local opt-out
        if os.getenv("VOICEKB_DISABLE_HOTKEYS", "0") in ("1", "true", "True"):
            logging.info("Hotkeys disabled via VOICEKB_DISABLE_HOTKEYS")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="hotkeys", daemon=True)
        self._thread.start()

    def _run(self):
        """Thread target: register hotkeys and keep the service alive."""
        try:
            self.manager.register_all()
            logging.info("Hotkeys registered and service running")
            while not self._stop_event.is_set():
                time.sleep(0.1)
        except Exception as e:
            logging.error(f"Hotkeys service error: {e}")

    def restart_with_manager(self, manager: HotkeysManager) -> None:
        """Stop the service, swap the manager, and start again."""
        self.stop()
        self.manager = manager
        self.start()

    def stop(self):
        """Stop the service thread and clear registered hotkeys."""
        self._stop_event.set()
        try:
            keyboard.clear_all_hotkeys()
        except Exception:
            pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        self._thread = None
