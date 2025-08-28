import logging
import os
import subprocess
import sys
import time

import keyboard  # noqa: F401

from .hotkeys import HotkeysManager, HotkeysService
from .settings import settings
from .stt import SpeechConverter


class Hotkeys:
    """Backward-compatible facade for registering hotkeys.

    Internally delegates to :class:`HotkeysManager` with the current
    ``speechConverter`` callbacks.
    """

    class Load:
        @staticmethod
        def startRecording():
            Hotkeys._manager().register_start()

        @staticmethod
        def stopRecording():
            Hotkeys._manager().register_stop()

        @staticmethod
        def pushToTalk():
            Hotkeys._manager().register_push_to_talk()

        @staticmethod
        def allKeys():
            logging.debug("Loading hotkeys")
            Hotkeys.Load.startRecording()
            Hotkeys.Load.stopRecording()
            Hotkeys.Load.pushToTalk()

    @staticmethod
    def _manager() -> HotkeysManager:
        # Late import/creation to avoid init order issues
        return HotkeysManager(speechConverter.start, speechConverter.stop)


class Generic:
    """Top-level lifecycle helpers for starting/stopping and utilities."""

    @staticmethod
    def startup():
        """Initialize settings/logging and, unless headless, start UI services."""
        Generic.startupSettings()
        headless = os.getenv("VOICEKB_HEADLESS", "0") in ("1", "true", "True")
        if headless:
            settings.windowShow = False
            settings.trayIconShow = False
        if not headless:
            Generic.startTrayIcon()
            Generic.startWindow()
            Generic.waitWindowLabelVar()

    @staticmethod
    def startupSettings():
        """Load settings from disk and configure logging."""
        settings.load()
        settings.setLogging()

    @staticmethod
    def startWindow():
        """Start the Qt window thread (if enabled)."""
        from .window import WindowManager

        WindowManager.start()

    @staticmethod
    def waitWindowLabelVar():
        """Wait for the UI label to be constructed by the Qt thread."""
        from .window import windowLabel

        while True:
            try:
                if windowLabel is not None:
                    return
            except NameError:
                pass
            time.sleep(0.1)

    @staticmethod
    def openSettings():
        """Open ``settings.ini`` with the OS-default editor/file opener."""
        configFile: str = "settings.ini"
        try:
            if sys.platform.startswith("darwin"):
                subprocess.Popen(["open", configFile])
            elif sys.platform.startswith("linux"):
                subprocess.Popen(["xdg-open", configFile])
            elif os.name == "nt":
                startfile = getattr(os, "startfile", None)
                if callable(startfile):
                    startfile(configFile)
            else:
                logging.warning("Unsupported platform.")
        except Exception as error:
            logging.error(f"Failed to open file with error: {error}")

    @staticmethod
    def startTrayIcon():
        """Start the tray icon on a separate thread with callbacks bound."""
        # Lazy import to avoid hard dependency at module import time
        from .tray import TrayIconManager

        TrayIconManager.start(
            open_settings_cb=lambda *_: Generic.openSettings(),
            open_preferences_cb=lambda *_: Generic.openPreferences(),
            restart_cb=lambda *_: Generic.restart(),
            exit_cb=lambda *_: Generic._exit(),
            toggle_window_cb=lambda *_: Generic.toggleWindow(),
        )

    @staticmethod
    def cleanup():
        """Delete log file on exit when configured to do so."""
        try:
            if settings.logDeleteOnExit:
                os.remove(settings.logFullpath)
        except Exception as error:
            from tkinter import messagebox

            messagebox.showerror(
                "Log cleanup failed",
                f"Failed to do log cleanup with error: {error}",
            )

    @staticmethod
    def wrapup():
        """Stop tray and persist settings before shutdown."""
        # Lazy import to avoid hard dependency at module import time
        try:
            from .tray import TrayIconManager

            TrayIconManager.stop()
        except Exception:
            pass
        settings.save()

    @staticmethod
    def _exit():
        """Terminate the process after gracefully shutting down subsystems."""
        logging.info("Closing application")
        Generic.wrapup()
        logging.debug("Finishing shutting down logging and doing os._exit")
        logging.shutdown()
        Generic.cleanup()
        os._exit(0)

    @staticmethod
    def restart():
        """Restart the application process with the same arguments."""
        logging.info("Restarting application")
        Generic.wrapup()
        settings.save()
        # Re-exec the Python interpreter with the same args
        os.execl(sys.executable, sys.executable, *sys.argv)

    @staticmethod
    def toggleWindow():
        """Toggle visibility of the overlay window without destroying it."""
        from .window import window as _win

        if settings.windowShow:
            if _win is not None:
                _win.hide()
            settings.windowShow = False
        else:
            if _win is not None:
                _win.show()
            settings.windowShow = True

    @staticmethod
    def openPreferences():
        """Open the Preferences dialog, unless running in headless mode."""
        headless = os.getenv("VOICEKB_HEADLESS", "0") in ("1", "true", "True")
        if headless:
            logging.info("Headless mode; preferences dialog not shown")
            return
        # Ensure run inside Qt thread
        from .window import invoke_in_ui

        invoke_in_ui(_show_preferences_dialog)


def main() -> None:
    """Entry point for console script ``voicekeyboard``.

    Instantiates the STT subsystem and starts the hotkeys service, then idles
    until a KeyboardInterrupt is received.
    """
    global speechConverter
    global _hotkeys_service
    speechConverter = SpeechConverter()
    # Start hotkeys in a dedicated service thread
    _hotkeys_service = HotkeysService(Hotkeys._manager())
    _hotkeys_service.start()

    # Main loop; in GUI mode, Qt runs on its own thread
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        try:
            _hotkeys_service.stop()
        finally:
            Generic._exit()


# Global used by hotkeys
speechConverter: SpeechConverter
_hotkeys_service: HotkeysService


def reload_hotkeys_service() -> None:
    """Restart the hotkeys service to apply changed bindings from settings."""
    # Recreate manager using updated settings and restart service safely
    try:
        from .hotkeys import HotkeysService as _HS

        global _hotkeys_service
        if isinstance(_hotkeys_service, _HS):
            _hotkeys_service.restart_with_manager(Hotkeys._manager())
        else:
            # Fallback: create anew if global not initialized
            _hotkeys_service = _HS(Hotkeys._manager())
            _hotkeys_service.start()
    except Exception as e:
        logging.error(f"Failed to reload hotkeys service: {e}")


def _show_preferences_dialog():
    """Show the Preferences dialog modally inside the Qt thread."""
    from .preferences import PreferencesDialog

    PreferencesDialog.show_modal(on_apply=reload_hotkeys_service)
