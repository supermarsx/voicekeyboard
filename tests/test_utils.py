from voicekeyboard.stt import SpeechConverter
from voicekeyboard.tray import ImageWrapper


def test_image_wrapper_create_image():
    img = ImageWrapper.createImage()
    assert img is not None
    assert img.size == (64, 64)


def test_speech_converter_dry_run(monkeypatch):
    monkeypatch.setenv("VOICEKB_DRYRUN", "1")
    sc = SpeechConverter()
    assert sc.model is None
    assert sc.vadModel is None
    # Ensure get_speech_timestamps callable exists
    assert callable(sc.get_speech_timestamps)
