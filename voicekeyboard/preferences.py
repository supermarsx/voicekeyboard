"""Preferences dialog for editing hotkeys at runtime.

Provides a simple modal dialog to edit the three hotkey combinations. On save,
changes are persisted via settings.save() and a provided callback is invoked to
reload hotkeys in the running app.
"""

from typing import Callable

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from .settings import settings


class PreferencesDialog(QDialog):
    """Modal dialog that edits start/stop/push-to-talk hotkeys."""

    def __init__(self, on_apply: Callable[[], None]):
        super().__init__()
        self.setWindowTitle("VoiceKeyboard Preferences")
        self.on_apply = on_apply

        layout = QVBoxLayout()

        # Hotkey fields
        self.start_edit = QLineEdit(settings.hotkeyStartRecording)
        self.stop_edit = QLineEdit(settings.hotkeyStopRecording)
        self.ptt_edit = QLineEdit(settings.hotkeyPushToTalk)

        layout.addLayout(self._row("Start hotkey:", self.start_edit))
        layout.addLayout(self._row("Stop hotkey:", self.stop_edit))
        layout.addLayout(self._row("Push-to-talk:", self.ptt_edit))

        # Language (basic choices; free text fallback via line edit kept for simplicity)
        self.lang_edit = QLineEdit(settings.whisperLanguage)
        layout.addLayout(self._row("Language (ISO):", self.lang_edit))

        # Compute device selector (string)
        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cuda", "cpu"])
        # Preselect current if present
        current = (
            settings.whisperDevice.lower() if isinstance(settings.whisperDevice, str) else "auto"
        )
        idx = max(0, self.device_combo.findText(current))
        self.device_combo.setCurrentIndex(idx)
        row = QHBoxLayout()
        row.addWidget(QLabel("Compute device:"))
        row.addWidget(self.device_combo)
        layout.addLayout(row)

        # Audio input device (optional; falls back to system default)
        self.input_combo = QComboBox()
        devices = ["Default"]
        try:
            import sounddevice as sd

            infos = sd.query_devices()
            for i, info in enumerate(infos):
                if info.get("max_input_channels", 0) > 0:
                    name = info.get("name", f"Device {i}")
                    devices.append(name)
        except Exception:
            pass
        self.input_combo.addItems(devices)
        if isinstance(settings.audioInputDevice, str) and settings.audioInputDevice:
            ix = self.input_combo.findText(settings.audioInputDevice)
            if ix >= 0:
                self.input_combo.setCurrentIndex(ix)
        row = QHBoxLayout()
        row.addWidget(QLabel("Input device:"))
        row.addWidget(self.input_combo)
        layout.addLayout(row)

        # Buttons
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self._save)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def _row(self, label: str, line: QLineEdit):
        """Create a labeled row with a QLineEdit control."""
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(line)
        return row

    def _save(self):
        """Persist changes and invoke the supplied reload callback."""
        # Persist new hotkeys
        settings.hotkeyStartRecording = self.start_edit.text().strip()
        settings.hotkeyStopRecording = self.stop_edit.text().strip()
        settings.hotkeyPushToTalk = self.ptt_edit.text().strip()
        settings.whisperLanguage = self.lang_edit.text().strip() or settings.whisperLanguage
        settings.whisperDevice = self.device_combo.currentText()
        choice = self.input_combo.currentText()
        settings.audioInputDevice = None if choice == "Default" else choice
        settings.save()
        # Trigger hotkeys reload
        try:
            self.on_apply()
        finally:
            self.accept()

    @staticmethod
    def show_modal(on_apply: Callable[[], None]):
        """Convenience wrapper to construct and display the dialog modally."""
        dlg = PreferencesDialog(on_apply)
        dlg.exec()
