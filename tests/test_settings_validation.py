from voicekeyboard.settings import SettingsManager


def test_settings_validate_window_and_opacity():
    s = SettingsManager()
    s.windowWidth = -10  # invalid
    s.windowHeight = 0   # invalid
    s.windowOpacity = 5  # invalid
    s.validate()
    assert s.windowWidth >= 50
    assert s.windowHeight >= 20
    assert 0.0 <= s.windowOpacity <= 1.0


def test_settings_validate_audio_defaults():
    s = SettingsManager()
    s.audioSampleRate = 4000  # too low
    s.audioChannels = 3       # invalid
    s.audioChunkDuration = 0.5
    s.audioChunkOverlapDuration = 0.1
    s.validate()
    assert s.audioSampleRate >= 8000
    assert s.audioChannels in (1, 2)
    # Derived fields consistent
    assert s.audioChunkSize == int(s.audioSampleRate * s.audioChunkDuration)
    assert s.audioChunkOverlapSize == int(s.audioSampleRate * s.audioChunkOverlapDuration)

