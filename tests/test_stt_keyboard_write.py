import time

import numpy as np

from voicekeyboard.stt import SpeechConverter


class DummyModel:
    def __init__(self):
        self.calls = 0

    def transcribe(self, audio, language=None, vad_filter=False, word_timestamps=False):
        self.calls += 1

        class Seg:
            def __init__(self, text):
                self.text = text

        return [Seg("hello")], None


def test_stt_writes_text_via_keyboard(monkeypatch):
    """Verify that transcribed text is typed via keyboard.write."""
    monkeypatch.setenv("VOICEKB_DRYRUN", "0")

    written = []

    import keyboard as kb

    monkeypatch.setattr(kb, "write", lambda text: written.append(text))

    sc = SpeechConverter()
    sc.get_speech_timestamps = lambda audio, *_a, **_k: [{"start": 0, "end": min(160, len(audio))}]
    sc.vadModel = object()
    sc.model = DummyModel()

    audio = np.zeros(320, dtype=np.float32)
    sc.audioQueue.put(audio)

    sc._process_flag = [True]
    t = __import__("threading").Thread(target=sc.processAudioStream, daemon=True)
    t.start()
    time.sleep(0.2)
    sc._process_flag[0] = False
    t.join(timeout=1)

    assert len(written) >= 1
    assert written[0] == "hello"


def test_stt_updates_label_on_transcription(monkeypatch):
    """Verify that the UI label is updated with the transcribed text."""
    monkeypatch.setenv("VOICEKB_DRYRUN", "0")

    label_updates = []

    import keyboard as kb

    monkeypatch.setattr(kb, "write", lambda text: None)

    sc = SpeechConverter()
    sc._update_label = lambda text: label_updates.append(text)
    sc.get_speech_timestamps = lambda audio, *_a, **_k: [{"start": 0, "end": min(160, len(audio))}]
    sc.vadModel = object()
    sc.model = DummyModel()

    audio = np.zeros(320, dtype=np.float32)
    sc.audioQueue.put(audio)

    sc._process_flag = [True]
    t = __import__("threading").Thread(target=sc.processAudioStream, daemon=True)
    t.start()
    time.sleep(0.2)
    sc._process_flag[0] = False
    t.join(timeout=1)

    # The last label update should contain the transcribed text
    assert any("hello" in update for update in label_updates)
