from configparser import ConfigParser

from voicekeyboard.settings import SettingsManager


def test_settings_roundtrip(tmp_path):
    cfg_path = tmp_path / "settings.ini"
    s = SettingsManager()
    # Tweak a few values
    s.windowShow = False
    s.windowWidth = 321
    s.whisperLanguage = "en"
    s.save(str(cfg_path))

    # Confirm file structured
    cp = ConfigParser()
    cp.read(cfg_path)
    assert "Configuration" in cp

    # Load into a fresh instance
    s2 = SettingsManager()
    s2.settingsJustUseDefaults = False
    s2.load(str(cfg_path))
    assert s2.windowShow is False
    assert s2.windowWidth == 321
    assert s2.whisperLanguage == "en"


def test_set_logging(tmp_path, monkeypatch):
    s = SettingsManager()
    s.logFilename = "test.log"
    s.logFilepath = str(tmp_path)
    s.logOverwrite = True
    s.setLogging()
    # Ensure log file path computed and file can be created
    assert s.logFullpath.endswith("test.log")
