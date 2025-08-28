import logging
import os
import threading
import time
from typing import Optional

from PIL import Image, ImageFilter
from PyQt6 import QtCore
from PyQt6.QtCore import QPoint, QRect, QSize, Qt, QTimer
from PyQt6.QtGui import QImage, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow

from .settings import settings

windowLabel: Optional[QLabel] = None
window: Optional[QMainWindow] = None


class LabelUpdater(QtCore.QObject):
    """Signal-based helper to update the UI label from worker threads."""

    textChanged = QtCore.pyqtSignal(str)


labelUpdater = LabelUpdater()


class UiInvoker(QtCore.QObject):
    """Lightweight invoker to run arbitrary callables in the Qt UI thread.

    Use :func:`invoke_in_ui` to schedule a function from any thread. The callable
    will be executed on the Qt thread as soon as the event loop processes the signal.
    """

    callRequested = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.callRequested.connect(self._run)

    def _run(self, fn):
        try:
            fn()
        except Exception as e:
            import logging

            logging.error(f"UiInvoker callable error: {e}")


uiInvoker: Optional[UiInvoker] = None


class WindowManager(QMainWindow):
    """Main application window (frameless label overlay) with optional blur."""

    def __init__(self):
        super().__init__()

        self.setWindowFlags(self.__initWindowFlagsBuilder())
        self.setFixedSize(self.__initWindowSizeBuilder())
        self.setStyleSheet(self.__initWindowStylesBuilder())
        self.setWindowTitle(settings.windowTitle)
        self.__initSetWindowOpacity()
        self.__initRestoreWindow()

        if settings.windowDraggable:
            self._isDragging: bool = False
            self._dragStartPosition: QPoint = QtCore.QPoint()

        self.__initWindowMainLabel()
        self.installEventFilter(self)
        self.__initWindowUpdater()

    def __initWindowMainLabel(self):
        """Create and attach the main text label, set default style and binding."""
        global windowLabel
        windowLabel = QLabel(settings.labelWindowWelcome, self)
        windowLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        windowLabel.setGeometry(2, 2, 200, 50)
        windowLabel.setStyleSheet(self.__initWindowLabelStyleBuilder())
        labelUpdater.textChanged.connect(windowLabel.setText)

    def __initWindowLabelStyleBuilder(self):
        return """
            background-color: transparent;
            border: none;
        """

    def __initWindowUpdater(self):
        """Enable periodic repaint when background blur is active."""
        if settings.windowBlurBackgroundEnabled:
            self.timer: QTimer = QTimer(self)
            self.timer.timeout.connect(self.update)
            self.timer.start(settings.windowBlurBackgroundPeriod)

    def __initRestoreWindow(self):
        """Move window to last known position if restore is enabled."""
        if settings.windowPosRestoreOnStartup:
            x: int = settings.windowPosX
            y: int = settings.windowPosY
            logging.debug(f"Restoring window position to {x}, {y}")
            self.move(x, y)

    def __initSetWindowOpacity(self):
        """Apply configured window opacity when enabled."""
        if settings.windowOpacityEnabled:
            self.setWindowOpacity(settings.windowOpacity)

    def __initWindowSizeBuilder(self):
        """Return the desired fixed window size."""
        return QSize(settings.windowWidth, settings.windowHeight)

    def __initWindowBorderBuilder(self):
        """Compose CSS border style or 'none' when disabled."""
        if settings.windowBorderEnabled:
            width = settings.windowBorderWidthPx
            btype = settings.windowBorderType
            color = settings.windowBorderColor
            return f"{width}px {btype} {color}"
        return "none"

    def __initWindowStylesBuilder(self):
        """Compose the complete stylesheet for the window."""
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
        """Build the Qt window flags according to settings."""
        windowFlags = Qt.WindowType.X11BypassWindowManagerHint
        if settings.windowKeepOnTop:
            windowFlags |= Qt.WindowType.WindowStaysOnTopHint
        if settings.windowFrameless:
            windowFlags |= Qt.WindowType.FramelessWindowHint
        return windowFlags

    def applyBlur(self, pixmap):
        """Apply Gaussian blur to the captured background pixmap."""
        image = pixmap.toImage()
        if image.format() != QImage.Format.Format_ARGB32:
            image = image.convertToFormat(QImage.Format.Format_ARGB32)

        width, height = image.width(), image.height()
        imageData: bytes = image.bits().asstring(width * height * 4)
        imageMode: str = "RGBA"
        pilImage = Image.frombytes(imageMode, (width, height), imageData)
        blurredImage = pilImage.filter(
            ImageFilter.GaussianBlur(settings.windowBlurBackgroundStrength)
        )
        blurredImageData: bytes = blurredImage.tobytes()
        qimage: QImage = QImage(blurredImageData, width, height, QImage.Format.Format_ARGB32)
        return QPixmap.fromImage(qimage)

    def paintEvent(self, event):
        if settings.windowBlurBackgroundEnabled:
            painter: QPainter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            screen = QApplication.primaryScreen()
            if screen is None:
                return
            screenshot: QPixmap = screen.grabWindow(0)  # type: ignore[arg-type]
            pixmap: QPixmap = screenshot.copy(self.geometry())
            blurredPixmap: QPixmap = self.applyBlur(pixmap)
            painter.drawPixmap(0, 0, blurredPixmap)
            painter.end()

    def eventFilter(self, source, event):
        """Forward mouse press events so the window can be dragged when enabled."""
        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            self.mousePressEvent(event)
            return True
        return super().eventFilter(source, event)

    def mousePressEvent(self, event):
        """Start drag when left mouse button is pressed on the window."""
        logging.debug("Detected mouse press event")
        if settings.windowDraggable:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self._isDragging = True
                self._dragStartPosition = (
                    event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )
                event.accept()

    def mouseMoveEvent(self, event):
        """Update window position while dragging, optionally clamping to screen."""
        if settings.windowDraggable and self._isDragging:
            newPosition = event.globalPosition().toPoint() - self._dragStartPosition
            screen = QApplication.primaryScreen()
            if screen is None:
                return
            screenGeometry: QRect = screen.availableGeometry()
            if settings.windowClipToScreenBorder:
                newPosition.setX(
                    max(
                        screenGeometry.left(),
                        min(newPosition.x(), screenGeometry.right() - self.width()),
                    )
                )
                newPosition.setY(
                    max(
                        screenGeometry.top(),
                        min(newPosition.y(), screenGeometry.bottom() - self.height()),
                    )
                )
                self.move(newPosition)
            else:
                self.move(event.globalPosition().toPoint() - self._dragStartPosition)
            event.accept()

    def mouseReleaseEvent(self, event):
        """Persist last window position upon releasing the mouse button."""
        logging.debug("Detected mouse release event")
        if settings.windowDraggable and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._isDragging = False
            windowPosition: QPoint = self.pos()
            settings.windowPosX = windowPosition.x()
            settings.windowPosY = windowPosition.y()
            event.accept()

    @staticmethod
    def run():
        """Create Qt application and start the window in the UI thread."""
        global window
        global uiInvoker
        application: QApplication = QApplication([])
        uiInvoker = UiInvoker()
        window = WindowManager()
        if settings.windowShow:
            window.show()

        # Auto-close for CI smoke tests
        try:
            ms = int(os.getenv("VOICEKB_AUTOCLOSE_MS", "0"))
        except ValueError:
            ms = 0
        if ms > 0:
            QTimer.singleShot(ms, application.quit)

        application.exec()

    @staticmethod
    def start():
        """Spawn a daemon thread to run the Qt UI when enabled in settings."""
        if not settings.windowShow:
            return None
        windowThread = threading.Thread(
            target=WindowManager.run,
            daemon=settings.windowDaemon,
        )
        windowThread.start()

    @staticmethod
    def wait_label():
        """Wait until the global label widget is created (used at startup)."""
        global windowLabel
        while True:
            if windowLabel is not None:
                return
            time.sleep(0.1)


def invoke_in_ui(fn) -> None:
    """Invoke ``fn`` on the Qt UI thread if available.

    If the UI thread is not yet initialized, a warning is logged and the
    callable is not executed.
    """
    # Dispatch callable to Qt thread via signal
    if uiInvoker is not None:
        uiInvoker.callRequested.emit(fn)
    else:
        import logging

        logging.warning("UiInvoker not initialized; callable not executed")
