from configparser import ConfigParser

from voicekeyboard.settings import SettingsManager


def test_settings_just_use_defaults(tmp_path):
    cfg = tmp_path / "settings.ini"
    cp = ConfigParser()
    cp.optionxform = str
    cp["Configuration"] = {
        "settingsJustUseDefaults": "true",
        "windowWidth": "9999",  # should be ignored due to defaults flag
    }
    with open(cfg, "w") as f:
        cp.write(f)

    s = SettingsManager()
    s.windowWidth = 200  # default
    s.load(str(cfg))
    assert s.windowWidth == 200
