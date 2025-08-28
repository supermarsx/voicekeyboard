import logging
import threading

from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

from .settings import settings


class ImageWrapper:
    """Create a simple placeholder tray icon image using Pillow."""

    @staticmethod
    def createImage():
        try:
            width: int = 64
            height: int = 64
            mode: str = "RGB"
            image = Image.new(mode, (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, width, height), fill=(0, 128, 255))
            draw.ellipse((16, 16, width - 16, height - 16), fill=(255, 255, 0))
        except Exception as error:
            logging.error(f"Failed to create image: {error}")
        else:
            logging.debug("Created image")
            return image


class TrayIconManager:
    """Manage the pystray icon lifecycle and menu wiring."""

    icon = None

    @staticmethod
    def onClick(icon, item):
        """Generic click logger for quick diagnostics."""
        logging.info(f"Menu item '{item}' clicked!")

    @staticmethod
    def setup(icon):
        """Make icon visible once the tray loop starts."""
        icon.visible = True

    @staticmethod
    def menuInit(open_settings_cb, open_preferences_cb, restart_cb, exit_cb, toggle_window_cb=None):
        """Build the tray menu with injected callbacks for actions."""
        if toggle_window_cb is None:

            def toggle_window_cb(*_args, **_kwargs):
                return None

        return Menu(
            MenuItem(text=settings.labelTrayMenuTitle, action=lambda *_: None),
            MenuItem(text=settings.labelTrayMenuDivider1, action=lambda *_: None, enabled=False),
            MenuItem(
                text=settings.labelTrayMenuSettings,
                action=Menu(
                    MenuItem(text=settings.labelTrayMenuToggleWindow, action=toggle_window_cb),
                    MenuItem(text=settings.labelTrayMenuOpenSettings, action=open_settings_cb),
                    MenuItem(text=settings.labelTrayMenuEditHotkeys, action=open_preferences_cb),
                ),
            ),
            MenuItem(text=settings.labelTrayMenuRestart, action=restart_cb),
            MenuItem(text=settings.labelTrayMenuExit, action=exit_cb),
        )

    @staticmethod
    def run(open_settings_cb, open_preferences_cb, restart_cb, exit_cb, toggle_window_cb):
        """Run the tray loop in a blocking manner (to be called on a thread)."""
        menu = TrayIconManager.menuInit(
            open_settings_cb,
            open_preferences_cb,
            restart_cb,
            exit_cb,
            toggle_window_cb,
        )
        TrayIconManager.icon = Icon(
            settings.labelTrayIconTitle,
            ImageWrapper.createImage(),
            settings.labelTrayIconName,
            menu,
        )
        TrayIconManager.icon.run(setup=TrayIconManager.setup)

    @staticmethod
    def start(open_settings_cb, open_preferences_cb, restart_cb, exit_cb, toggle_window_cb):
        """Spawn a daemon thread to start the tray icon if enabled in settings."""
        if not settings.trayIconShow:
            return None
        trayThread = threading.Thread(
            target=TrayIconManager.run,
            args=(open_settings_cb, open_preferences_cb, restart_cb, exit_cb, toggle_window_cb),
            daemon=settings.trayIconDaemon,
        )
        trayThread.start()

    @staticmethod
    def stop():
        """Stop the tray icon if running and swallow errors safely."""
        try:
            logging.debug("Stopping tray icon")
            if TrayIconManager.icon:
                TrayIconManager.icon.stop()
        except Exception as error:
            logging.error(f"Failed to stop with error: {error}")
        else:
            logging.debug("Stopped tray icon")
