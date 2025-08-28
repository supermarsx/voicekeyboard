import logging
import os
from configparser import ConfigParser
from tkinter import messagebox


class SettingsManager:
    """Singleton container for application configuration.

    Values are initialized with reasonable defaults and can be overridden by
    loading from an INI file via :meth:`load`.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SettingsManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self.windowShow: bool = True
        self.windowDaemon: bool = True
        self.windowHeight: int = 50
        self.windowWidth: int = 200
        self.windowPosRestoreOnStartup: bool = True
        self.windowPosX: int = 0
        self.windowPosY: int = 0
        self.windowDraggable: bool = True
        self.windowBackgroundColor: str = "black"
        self.windowBorderEnabled: bool = True
        self.windowBorderColor: str = "grey"
        self.windowBorderWidthPx: int = 1
        self.windowBorderType: str = "solid"
        self.windowTextColor: str = "white"
        self.windowTextSizePx: int = 13
        self.windowTextFontType: str = "'Inconsolata', monospace"
        self.windowTextFontWeight: int = 800
        self.windowOpacityEnabled: bool = True
        self.windowOpacity: float = 0.78
        self.windowBlurBackgroundEnabled: bool = False
        self.windowBlurBackgroundPeriod: int = 100
        self.windowBlurBackgroundStrength: float = 2.0
        self.windowClipToScreenBorder: bool = True
        self.windowKeepOnTop: bool = True
        self.windowFrameless: bool = True
        self.trayIconShow: bool = True
        self.trayIconDaemon: bool = True
        self.pushToTalk: bool = False
        self.hotkeyStartRecording: str = "ctrl+shift+a"
        self.hotkeyStopRecording: str = "ctrl+shift+b"
        self.hotkeyPushToTalk: str = "alt+p"
        self.launchAtStartup: bool = False
        self.log: bool = True
        self.logOverwrite: bool = False
        self.logFilemode: str = ""
        self.logEncoding: str = "utf-8"
        self.logLevel: int = 10
        self.logFilename: str = "application.log"
        from typing import Optional

        self.logFilepath: Optional[str] = None
        self.logFullpath: str = ""
        self.logDeleteOnExit: bool = False
        self.windowTitle: str = "VoiceKeyboard"
        self.labelWindowWelcome: str = "Welcome to Voice Keyboard"
        self.labelTrayIconTitle: str = "VoiceKeyboard"
        self.labelTrayIconName: str = "VoiceKeyboard"
        self.labelTrayMenuTitle: str = "VoiceKeyboard"
        self.labelTrayMenuToggleWindow: str = "Toggle window"
        self.labelTrayMenuOpenSettings: str = "Open settings"
        self.labelTrayMenuEditHotkeys: str = "Edit hotkeys"
        self.labelTrayMenuExit: str = "Quit"
        self.labelTrayMenuSettings: str = "Settings"
        self.labelTrayMenuDivider1: str = "---"
        self.labelTrayMenuRestart: str = "Restart"
        self.settingsJustUseDefaults: bool = True
        self.whisperModel: str = "medium"
        self.whisperDevice: str = "cuda"
        self.whisperComputeType: str = "float16"
        self.whisperCpuThreads: int = 0
        self.whisperNumWorkers: int = 1
        self.whisperLanguage: str = "pt"
        self.audioChannels: int = 1
        self.audioSampleRate: int = 16000
        self.audioChunkDuration: float = 1.0
        self.audioChunkSize: int = int(self.audioSampleRate * self.audioChunkDuration)
        self.audioChunkOverlapDuration: float = 0.2
        self.audioChunkOverlapSize: int = int(self.audioSampleRate * self.audioChunkOverlapDuration)
        # Optional audio input device identifier (name or index); None uses system default
        from typing import Optional

        self.audioInputDevice: Optional[str] = None
        self.vadForceRedownload: bool = False

    def load(self, configFile: str = "settings.ini"):
        """Load settings from an INI file.

        Honors ``settingsJustUseDefaults`` to short-circuit loading when set to
        a truthy value within the file.
        """
        try:
            config: ConfigParser = ConfigParser()

            # Preserve option case
            def _identity(s: str) -> str:
                return s

            from typing import Callable, cast

            config.optionxform = cast(Callable[[str], str], _identity)  # type: ignore[assignment]
            if not os.path.isfile(configFile):
                raise Exception(f"File not found: {configFile}")
            config.read(configFile)
            if "Configuration" in config:
                for key, value in config["Configuration"].items():
                    if (
                        hasattr(self, key)
                        and (key == "settingsJustUseDefaults")
                        and (value.lower() in ("true", "1", "yes"))
                        and (getattr(self, key) is True)
                    ):
                        # Respect file flag only when the current instance also opts in
                        return None
                for key, value in config["Configuration"].items():
                    if hasattr(self, key):
                        current_value = getattr(self, key)
                        if isinstance(current_value, bool):
                            setattr(self, key, value.lower() in ("true", "1", "yes"))
                        elif isinstance(current_value, int):
                            setattr(self, key, int(value))
                        elif isinstance(current_value, float):
                            setattr(self, key, float(value))
                        elif current_value is None:
                            setattr(self, key, None if value.lower() == "none" else value)
                        else:
                            setattr(self, key, value)
            logging.info("Loaded settings from configuration file")
        except Exception as error:
            logging.error("Failed to load settings from configuration file")
            messagebox.showerror("Failed to load settings", f"Failed to load settings: {error}")
        finally:
            # Ensure values are sensible
            self.validate()

    def save(self, configFile="settings.ini"):
        """Persist current settings to an INI file."""
        try:
            logging.debug("Saving settings to configuration file")
            config: ConfigParser = ConfigParser()

            # Preserve option case
            def _identity(s: str) -> str:
                return s

            from typing import Callable, cast

            config.optionxform = cast(Callable[[str], str], _identity)  # type: ignore[assignment]
            config["Configuration"] = {
                key: str(getattr(self, key)) if getattr(self, key) is not None else "None"
                for key in vars(self)
            }
            with open(configFile, "w") as file:
                config.write(file)
            logging.info("Saved settings to configuration file")
        except Exception as error:
            logging.error(f"Failed to save settings: {error}")
        else:
            logging.info("Saved settings successfully")

    def setLogging(self):
        """Configure application logging.

        Creates a file handler (to ``logFullpath``) and a console handler using
        the configured level and encoding.
        """
        try:
            if settings.log is False:
                return
            settings.logFilemode = "w" if settings.logOverwrite else "a"
            settings.logFullpath = (
                os.path.join(settings.logFilepath, settings.logFilename)
                if settings.logFilepath
                else settings.logFilename
            )
            logging.basicConfig(
                level=settings.logLevel,
                format="%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s",
                handlers=[
                    logging.FileHandler(
                        settings.logFullpath,
                        settings.logFilemode,
                        settings.logEncoding,
                    ),
                    logging.StreamHandler(),
                ],
            )
            logging.debug("Debug logging enabled")
            logging.info("Informational logging enabled")
            logging.info("Logging has been set")
        except Exception as error:
            messagebox.showerror(
                "Failed to set logging", f"Failed to set logging with exception: {error}"
            )

    def loadHotkeys(self):
        """Register all hotkeys through the Hotkeys facade."""
        from .app import Hotkeys  # local import to avoid cycles

        try:
            logging.debug("Loading hotkeys")
            Hotkeys.Load.allKeys()
        except Exception as error:
            logging.error(f"Failed to load hotkeys with error: {error}")
        else:
            logging.info("Hotkeys have been loaded")

    def debugDumpToConsole(self):
        """Print all settings and their current values to stdout (debug aid)."""
        print("Dumping settings values to console")
        for key in self.__dict__.keys():
            print(f"{key}: {getattr(self, key)}")

    def validate(self) -> None:
        """Clamp and coerce settings to safe ranges/types."""
        # Window sizes and opacity
        try:
            self.windowWidth = max(50, int(self.windowWidth))
            self.windowHeight = max(20, int(self.windowHeight))
        except Exception:
            self.windowWidth, self.windowHeight = 200, 50
        try:
            opacity = float(self.windowOpacity)
        except Exception:
            opacity = 0.78
        self.windowOpacity = max(0.0, min(1.0, opacity))

        # Audio and STT
        try:
            self.audioSampleRate = max(8000, int(self.audioSampleRate))
        except Exception:
            self.audioSampleRate = 16000
        try:
            self.audioChannels = 1 if int(self.audioChannels) != 2 else 2
        except Exception:
            self.audioChannels = 1
        # Derived sizes
        try:
            self.audioChunkSize = int(self.audioSampleRate * float(self.audioChunkDuration))
            self.audioChunkOverlapSize = int(
                self.audioSampleRate * float(self.audioChunkOverlapDuration)
            )
        except Exception:
            self.audioChunkDuration = 1.0
            self.audioChunkOverlapDuration = 0.2
            self.audioChunkSize = int(self.audioSampleRate * self.audioChunkDuration)
            self.audioChunkOverlapSize = int(self.audioSampleRate * self.audioChunkOverlapDuration)
        # Language default
        if not getattr(self, "whisperLanguage", None):
            self.whisperLanguage = "en"


settings = SettingsManager()
