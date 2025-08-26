import sys
import time
import keyboard
import os
import logging
import numpy
import sounddevice
import torch
import threading
from threading import Lock
from queue import Queue
import subprocess

from silero_vad import get_speech_timestamps

from faster_whisper import WhisperModel

from tkinter import messagebox

from PIL import Image, ImageDraw, ImageFilter

from pystray import Icon, Menu, MenuItem

from configparser import ConfigParser

from PyQt6 import QtCore
from PyQt6.QtWidgets import QMainWindow, QApplication, QLabel
from PyQt6.QtGui import QImage, QPainter, QPixmap
from PyQt6.QtCore import QPoint, QRect, Qt, QSize, QTimer

windowLabel = None
window = None


# Helper object to safely update the window label from worker threads
class LabelUpdater(QtCore.QObject):
    textChanged = QtCore.pyqtSignal(str)


labelUpdater = LabelUpdater()

# Window manager, manages stuff related to window
class WindowManager(QMainWindow):
    # Statup window manager
    def __init__(self):
        super().__init__()

        self.setWindowFlags(self.__initWindowFlagsBuilder())
        self.setFixedSize(self.__initWindowSizeBuilder())
        self.setStyleSheet(self.__initWindowStylesBuilder())
        self.setWindowTitle(settings.windowTitle)
        self.__initSetWindowOpacity()
        self.__initRestoreWindow()

        #self.centralWidget = QWidget()
        if settings.windowDraggable:
            self._isDragging: bool = False
            self._dragStartPosition: QPoint = QtCore.QPoint()

        self.__initWindowMainLabel()
        self.installEventFilter(self)
        self.__initWindowUpdater()

    def __initWindowMainLabel(self):
        global windowLabel
        windowLabel = QLabel(settings.labelWindowWelcome, self);
        windowLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)  # Center the text
        windowLabel.setGeometry(2, 2, 200, 50)
        windowLabel.setStyleSheet(self.__initWindowLabelStyleBuilder())
        labelUpdater.textChanged.connect(windowLabel.setText)

    def __initWindowLabelStyleBuilder(self):
        return """
            background-color: transparent;
            border: none;
        """

    def __initWindowUpdater(self):
        if (settings.windowBlurBackgroundEnabled):
            self.timer: QTimer = QTimer(self)
            self.timer.timeout.connect(self.update)
            self.timer.start(settings.windowBlurBackgroundPeriod)

    def __initRestoreWindow(self):
        if (settings.windowPosRestoreOnStartup):
            x: int = settings.windowPosX
            y: int = settings.windowPosY
            logging.debug(f"Restoring window position to {x}, {y}")
            self.move(x, y)

    def __initSetWindowOpacity(self):
        if (settings.windowOpacityEnabled):
            self.setWindowOpacity(settings.windowOpacity)

    def __initWindowSizeBuilder(self):
        return QSize(
                settings.windowWidth, 
                settings.windowHeight
            )

    def __initWindowBorderBuilder(self):
         return f"{settings.windowBorderWidthPx}px {settings.windowBorderType} {settings.windowBorderColor}" if (settings.windowBorderEnabled) else "none"

    def __initWindowStylesBuilder(self):
        return f"""
            background-color: {settings.windowBackgroundColor};
            border: {self.__initWindowBorderBuilder()};
            border-radius: 1px;
            color: {settings.windowTextColor};
            font-size: {settings.windowTextSizePx}px;
            font-family: {settings.windowTextFontType};
            font-weight: {settings.windowTextFontWeight};
            """

    def __initWindowFlagsBuilder(self):
        windowFlags = Qt.WindowType.X11BypassWindowManagerHint
        if (settings.windowKeepOnTop): windowFlags |= Qt.WindowType.WindowStaysOnTopHint
        if (settings.windowFrameless): windowFlags |= Qt.WindowType.FramelessWindowHint
        return windowFlags

    def applyBlur(self, pixmap):
        image = pixmap.toImage()
        if image.format() != QImage.Format.Format_ARGB32:
            image = image.convertToFormat(QImage.Format.Format_ARGB32)

        width, height = image.width(), image.height()
        imageData: str = image.bits().asstring(width * height * 4)
        imageMode: str = "RGBA"
        pilImage: Image = Image.frombytes(imageMode, (width, height), imageData)
        blurredImage: Image = pilImage.filter(ImageFilter.GaussianBlur(settings.windowBlurBackgroundStrength))
        blurredImageData: bytes = blurredImage.tobytes()
        qimage: QImage = QImage(blurredImageData, width, height, QImage.Format.Format_ARGB32)
        return QPixmap.fromImage(qimage)

    def paintEvent(self, event):
        if (settings.windowBlurBackgroundEnabled):
            painter: QPainter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            screenshot: QPixmap = QApplication.primaryScreen().grabWindow(0)
            pixmap: QPixmap = screenshot.copy(self.geometry())
            blurredPixmap: QPixmap = self.applyBlur(pixmap)
            painter.drawPixmap(0, 0, blurredPixmap)
            #overlay_color = QColor(0, 0, 0, int(255 * settings.windowOpacity))  # Black overlay with opacity
            #painter.fillRect(self.rect(), overlay_color)
            painter.end()


    def eventFilter(self, source, event):
        #logging.debug("Event filter triggered")
        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            self.mousePressEvent(event)
            return True
        return super().eventFilter(source, event)

    def mousePressEvent(self, event):
        logging.debug("Detected mouse press event")
        if settings.windowDraggable:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self._isDragging: bool = True
                self._dragStartPosition: QPoint = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        #logging.debug("Detected mouse move event")
        if settings.windowDraggable:
            if self._isDragging:
                newPosition = event.globalPosition().toPoint() - self._dragStartPosition
                screenGeometry: QRect = QApplication.primaryScreen().availableGeometry()
                if (settings.windowClipToScreenBorder):
                    newPosition.setX(max(screenGeometry.left(), min(newPosition.x(), screenGeometry.right() - self.width())))
                    newPosition.setY(max(screenGeometry.top(), min(newPosition.y(), screenGeometry.bottom() - self.height())))
                    self.move(newPosition)
                else:
                    self.move(event.globalPosition().toPoint() - self._dragStartPosition)
                event.accept()

    def mouseReleaseEvent(self, event):
        logging.debug("Detected mouse release event")
        if settings.windowDraggable:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self._isDragging = False
                windowPosition: QPoint = self.pos()
                settings.windowPosX = windowPosition.x()
                settings.windowPosY = windowPosition.y()
                event.accept()

    @staticmethod
    def run():
        global window
        application: QApplication = QApplication(sys.argv)
        with lock:
            window = WindowManager()
            if (settings.windowShow): window.show()
        application.exec()

    @staticmethod
    def start():
        windowThread = threading.Thread(
            target = WindowManager.run, 
            daemon = settings.windowDaemon
        )
        windowThread.start()

# Image creator wrapper
class ImageWrapper:
    @staticmethod
    def createImage():
        try:
            width: int = 64
            height: int = 64
            mode: str = "RGB"
            image: Image = Image.new(mode, (width, height), color = (255,255,255))
            draw: ImageDraw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, width, height), fill = (0, 128, 255))
            draw.ellipse((16, 16, width - 16, height - 16), fill = (255, 255, 0))
        except Exception as error:
            logging.error(f"Failed to create image: {error}")
        else:
            logging.debug("Created image")
            return image

# Tray icon management
class TrayIconManager:
    icon = None
    # On click event
    @staticmethod
    def onClick(icon, item):
        print(f"Menu item '{item}' clicked!")
   
    # Initialization
    @staticmethod
    def setup(icon):
        icon.visible: bool = True

    @staticmethod
    def menuInit():
        return Menu(
            MenuItem(text = settings.labelTrayMenuTitle, action = TrayIconManager.onClickNull),
            MenuItem(text = settings.labelTrayMenuDivider1, action = TrayIconManager.onClickNull, enabled = False),
            MenuItem(text = settings.labelTrayMenuSettings, action = TrayIconManager.subMenuWindowInit()),
            #MenuItem("Option 2", TrayIconManager.onClick),
            MenuItem(text = settings.labelTrayMenuRestart, action = Generic.restart),
            MenuItem(text = settings.labelTrayMenuExit, action = Generic._exit)
        )

    @staticmethod
    def subMenuWindowInit():
        return Menu(
            MenuItem(text = settings.labelTrayMenuToggleWindow, action = TrayIconManager.toggleWindow),
            MenuItem(text = settings.labelTrayMenuOpenSettings, action = Generic.openSettings)
        )

    @staticmethod
    def toggleWindow(icon, item):
        if (settings.windowShow):
            with lock:
                window.hide()
            settings.windowShow = False
        else:
            with lock:
                window.show()
            settings.windowShow = True

    # Simple null click passthrough for tests
    @staticmethod
    def onClickNull():
        pass

    @staticmethod
    def run():
        # Create menu items
        menu: Menu = TrayIconManager.menuInit()
        # Create the tray icon
        TrayIconManager.icon = Icon(
            settings.labelTrayIconTitle,
            ImageWrapper.createImage(),
            settings.labelTrayIconName,
            menu
        )
        # Run the icon in a blocking manner
        TrayIconManager.icon.run(setup = TrayIconManager.setup)

    @staticmethod
    def start():
        if not (settings.trayIconShow): return None
        trayThread = threading.Thread(
            target = TrayIconManager.run,
            daemon = settings.trayIconDaemon
        )
        trayThread.start()

    @staticmethod
    def stop():
        try:
            logging.debug("Stopping tray icon")
            TrayIconManager.icon.stop()
        except Exception as error:
            logging.error(f"Failed to stop with error: {error}")
        else:
            logging.debug("Stopped tray icon")

# Speech converter management
class SpeechConverter:
    def _update_label(self, text: str) -> None:
        labelUpdater.textChanged.emit(text)

    # Initialize the speech converter
    def __init__(self):
        try:
            self.stream = None
            self.streamThread = None
            self.transcriptionThread = None
            self._update_label("STT startup\nLoading up settings")
            logging.debug("Setting audio chunk sizes")
            settings.audioChunkSize = int(settings.audioSampleRate * settings.audioChunkDuration)
            settings.audioChunkOverlapSize = int(settings.audioSampleRate * settings.audioChunkOverlapDuration)
            self._update_label("STT startup\nLoading STT model")
            logging.debug("Loading speech to text model")
            self.model = WhisperModel(
                model_size_or_path = settings.whisperModel,
                device = settings.whisperDevice,
                compute_type = settings.whisperComputeType,
                cpu_threads = settings.whisperCpuThreads,
                num_workers = settings.whisperNumWorkers
                )
            logging.debug("Model loaded")
            self._update_label("STT startup\nSetting up audio queue")
            logging.debug("Starting audio queue")
            self.audioQueue = Queue()
            logging.debug("Queue started")
            self._update_label("STT startup\nLoading VAD model")
            logging.debug("Loading vad model")
            self.vadModel, utils = torch.hub.load(
                repo_or_dir = 'snakers4/silero-vad',
                model = 'silero_vad',
                force_reload = settings.vadForceRedownload
                )
            (get_speech_timestamps, _, _, _, _) = utils
            logging.debug("Model loaded")
            self._update_label("Ready!")
        except Exception as error:
            self._update_label("Failed to start STT!\nPlease check logs")
            logging.error(f"Failed to initialize speech converter: {error}")
        else:
            logging.info("Initialized speech converter")

    # Audio callback
    def audioCallback(self, indata, frames, time, status):
        #if (status): logging.info(f"Audio status: {status}")
        if indata.ndim > 1:
            mono_audio = numpy.mean(indata, axis=1)
        else:
            mono_audio = indata

        self.audioQueue.put(mono_audio.copy())
        
    # Process audio stream
    def processAudioStream(self):
        audio_buffer = []
        sample_rate = settings.audioSampleRate
        min_audio_window = int(sample_rate * 2)  # 2 seconds window

        while _isRecording:
            try:
                # Wait for audio data
                chunk = self.audioQueue.get(timeout=1)
                audio_buffer.append(chunk)

                # Flatten the buffer into a single array
                audio_data = numpy.concatenate(audio_buffer, axis=0)

                # Ensure we have at least 2 seconds of audio
                if len(audio_data) < min_audio_window:
                    continue

                # Run VAD on the buffered audio
                speech_timestamps = get_speech_timestamps(
                    audio_data, self.vadModel, sampling_rate=sample_rate
                )

                if speech_timestamps:
                    for segment in speech_timestamps:
                        start = segment['start']
                        end = segment['end']
                        voiced_audio = audio_data[start:end]

                        # Whisper expects float32 and mono
                        voiced_audio = voiced_audio.astype(numpy.float32)

                        # Transcribe with Whisper
                        segments, info = self.model.transcribe(
                            voiced_audio,
                            language=settings.whisperLanguage,
                            vad_filter=False,
                            word_timestamps=False
                        )
                        text = " ".join([seg.text for seg in segments])

                        print(text)
                        if text:
                            logging.info(f"Typing: {text}")
                            #pyautogui.typewrite(text + " ")

                # Reset the buffer to avoid reprocessing old audio
                audio_buffer = []

            #except self.audioQueue.Empty:
            #    continue
            except Exception as e:
                logging.error(f"Error during real-time transcription: {e}")
                continue

    # Run audio stream
    def _run_audio_stream(self):
        with sounddevice.InputStream(
            callback=self.audioCallback,
            channels=settings.audioChannels,
            samplerate=settings.audioSampleRate
        ) as stream:
            self.stream = stream
            while _recordSignal:
                time.sleep(0.1)  # Let callback do the work

    # Start recording audio
    def start(self):
        global _isRecording, _recordSignal
        # SpeechConverter.stop(self)
        _isRecording = True
        _recordSignal = True
        self._update_label("Recording/Processing...")
        logging.info("Started recording")

        # Start transcription in a separate thread
        transcriptionThread = threading.Thread(target=self.processAudioStream, daemon=True)
        transcriptionThread.start()

        # Start persistent input stream
        self.streamThread = threading.Thread(target=self._run_audio_stream, daemon=True)
        self.streamThread.start()

        
        #with sounddevice.InputStream(
        #    callback = self.audioCallback,
        #    channels = settings.audioChannels,
        #    samplerate = settings.audioSampleRate
        #):
        #    transcriptionThread = threading.Thread(
        #        target = self.processAudioStream
        #    )
        #    transcriptionThread.start()
        #    while (_recordSignal == True): pass

        #self._update_label("Stopped recording..")
        #logging.info("Stopped recording")


    # Stop recording
    def stop(self):
        global _recordSignal
        _recordSignal = False
        logging.info("Stopping STT system")

        # Stop audio stream if running
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                logging.info("Audio stream closed")
            except Exception as e:
                logging.warning(f"Failed to stop audio stream: {e}")
            self.stream = None

        # Join audio stream thread
        if self.streamThread and self.streamThread.is_alive():
            self.streamThread.join(timeout=2)
            logging.info("Audio thread joined")
            self.streamThread = None

        # Join transcription thread
        if self.transcriptionThread and self.transcriptionThread.is_alive():
            self.transcriptionThread.join(timeout=2)
            logging.info("Transcription thread joined")
            self.transcriptionThread = None

        self._update_label("Stopped recording..")

# Settings manager 
class SettingsManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SettingsManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    # Initialize all application settings
    def __init__(self):
        self.windowShow: bool = True
        self.windowDaemon: bool = True
        self.windowHeight: int = 50
        self.windowWidth: int = 200
        self.windowPosRestoreOnStartup: bool = True
        self.windowPosX: int = 0
        self.windowPosY: int = 0
        self.windowDraggable: bool = True
        self.windowBackgroundColor: str = 'black'
        self.windowBorderEnabled: bool = True
        self.windowBorderColor: str = 'grey'
        self.windowBorderWidthPx: int = 1
        self.windowBorderType: str = 'solid'
        self.windowTextColor: str = 'white'
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
        self.hotkeyStartRecording: str = 'ctrl+shift+a'
        self.hotkeyStopRecording: str = 'ctrl+shift+b'
        self.hotkeyPushToTalk: str = 'alt+p'
        self.launchAtStartup: bool = False
        self.log: bool = True
        self.logOverwrite: bool = False
        self.logFilemode: str = ''
        self.logEncoding: str = 'utf-8'
        self.logLevel: int = 10
        self.logFilename: str = 'application.log'
        self.logFilepath: any = None
        self.logFullpath: str = ''
        self.logDeleteOnExit: bool = False
        self.windowTitle: str = 'VoiceKeyboard'
        self.labelWindowWelcome: str = 'Welcome to Voice Keyboard'
        self.labelTrayIconTitle: str = 'VoiceKeyboard'
        self.labelTrayIconName: str = 'VoiceKeyboard'
        self.labelTrayMenuTitle: str = 'VoiceKeyboard'
        self.labelTrayMenuToggleWindow: str = 'Toggle window'
        self.labelTrayMenuOpenSettings: str = 'Open settings'
        self.labelTrayMenuExit: str = 'Quit'
        self.labelTrayMenuSettings: str = 'Settings'
        self.labelTrayMenuDivider1: str = '---'
        self.labelTrayMenuRestart: str = 'Restart'
        self.settingsJustUseDefaults: bool = True
        self.whisperModel: str = 'medium'
        self.whisperDevice: str = 'cuda'
        self.whisperComputeType: str = 'float16'
        self.whisperCpuThreads: int = 0
        self.whisperNumWorkers: int = 1
        self.whisperLanguage: str = 'pt'
        self.audioChannels: int = 1
        self.audioSampleRate: int = 16000
        self.audioChunkDuration: float = 1.0
        self.audioChunkSize: int = int(self.audioSampleRate * self.audioChunkDuration)
        self.audioChunkOverlapDuration: float = 0.2
        self.audioChunkOverlapSize: int = int(self.audioSampleRate * self.audioChunkOverlapDuration)
        self.vadForceRedownload: bool = False

    # Load settings from the configuration file
    def load(self, configFile: str = "settings.ini"):
        try:
            config: ConfigParser = ConfigParser()
            config.optionxform = str
            if not os.path.isfile(configFile): raise Exception(f"File not found: {configFile}")
            config.read(configFile)
            if "Configuration" in config:
                for key, value in config["Configuration"].items():
                    if (hasattr(self, key) and (key == "settingsJustUseDefaults") and (value.lower() in ("true", "1", "yes"))):
                        return None
                for key, value in config["Configuration"].items():
                    if hasattr(self, key):
                        # Infer the type of the attribute and cast the value
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

    # Save current settings to configuration file
    def save(self, configFile="settings.ini"):
        try:
            logging.debug("Saving settings to configuration file")
            config: ConfigParser = ConfigParser()
            config.optionxform = str
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

    # Set logging level
    def setLogging(self):
        try:
            if (settings.log == False): return
            settings.logFilemode = 'w' if settings.logOverwrite else 'a'
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
                        settings.logEncoding
                    ),
                    logging.StreamHandler()
                ],
            )
            logging.debug("Debug logging enabled")
            logging.info("Informational logging enabled")
            logging.info("Logging has been set")
        except Exception as error:
            messagebox.showerror("Failed to set logging", f"Failed to set logging with exception: {error}")

    # Load application hotkeys
    def loadHotkeys(self):
        try:
            logging.debug("Loading hotkeys")
            Hotkeys.Load.allKeys()
        except Exception as error:
            logging.error(f"Failed to load hotkeys with error: {error}")
        else:
            logging.info("Hotkeys have been loaded")

    # Debug dump all setting values to console
    def debugDumpToConsole(self):
        print("Dumping settings values to console")
        for key in self.__dict__.keys():
            print(f"{key}: {getattr(self, key)}")

# Hotkeys management
class Hotkeys:
    class Load:
        def startRecording():
            keyboard.add_hotkey(
                settings.hotkeyStartRecording,
                speechConverter.start
            )
            logging.debug(f"Loaded start recording hotkey: {settings.hotkeyStartRecording}")

        def stopRecording():
            keyboard.add_hotkey(
                settings.hotkeyStopRecording,
                speechConverter.stop
            )
            logging.debug(f"Loaded stop recording hotkey: {settings.hotkeyStopRecording}")

        def pushToTalk():
            keyboard.on_press_key(
                settings.hotkeyPushToTalk,
                lambda event: speechConverter.start()
            )
            keyboard.on_release_key(
                settings.hotkeyPushToTalk,
                lambda event: speechConverter.stop()
            )
            logging.debug(
                f"Loaded push-to-talk recording hotkey: {settings.hotkeyPushToTalk}"
            )


        def allKeys():
            logging.debug("Loading hotkeys")
            Hotkeys.Load.startRecording()
            Hotkeys.Load.stopRecording()
            Hotkeys.Load.pushToTalk()

# Application lifecycle generic stuff
class Generic:
    # Application start up routine
    def startup():
        Generic.startupSettings()
        Generic.startTrayIcon()
        Generic.startWindow()
        Generic.waitWindowLabelVar()
        
    # Load up all the settings
    def startupSettings():
        settings.load()
        settings.setLogging()

    # Start up the window
    def startWindow():
        WindowManager.start()

    # Wait for window label variable
    def waitWindowLabelVar():
        while 'windowLabel' not in globals():
            time.sleep(0.1)

    # Open settings file
    def openSettings():
        configFile: str = "settings.ini"
        try:
            if sys.platform.startswith('darwin'):
                subprocess.Popen(['open', configFile])
            elif os.name == 'nt':
                os.startfile(configFile)
            elif os.name == 'posix':
                subprocess.Popen(['xdg-open', configFile])
            else:
                logging.warning("Unsupported platform.")
        except Exception as error:
            logging.error(f"Failed to open file with error: {error}")

    # Initialize tray icon
    def startTrayIcon():
        TrayIconManager.start()

    # Final application clean up before exiting
    def cleanup():
        try:
            if (settings.logDeleteOnExit): os.remove(settings.logFullpath)
        except Exception as error:
            messagebox.showerror("Log cleanup failed", f"Failed to do log cleanup with error: {error}")

    # Wrap up task before closing application
    def wrapup():
        TrayIconManager.stop()
        settings.save()

    # Application exit routine
    def _exit():
        logging.info("Closing application")
        Generic.wrapup()
        logging.debug("Finishing shutting down logging and doing os._exit")
        logging.shutdown()
        Generic.cleanup()
        os._exit(0)

    # Application restart routine
    def restart():
        logging.info("Restarting application")
        Generic.wrapup()
        settings.save()
        os.execl(sys.executable, os.path.abspath(__file__), *sys.argv) 

# Main starts here :)
if __name__ == "__main__":
    _isRecording: bool = False
    _recordSignal: bool = False
    lock: Lock = threading.Lock()
    settings: SettingsManager = SettingsManager()

    Generic.startup()

    speechConverter: SpeechConverter = SpeechConverter()

    settings.loadHotkeys()

    # Simulate main program tasks
    try:
        while True:
            #logging.debug("Application is running")
            #try: windowLabel
            #except Exception as error: logging.debug(f"Failed to get Window Label var, {error}")
            #else: labelUpdater.textChanged.emit("OK")
            #time.sleep(2)
            pass
    except KeyboardInterrupt:
        Generic._exit()
