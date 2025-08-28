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


def test_stt_process_calls_model(monkeypatch):
    # Force non-dry mode semantics but patch out heavy loads
    monkeypatch.setenv("VOICEKB_DRYRUN", "0")

    sc = SpeechConverter()
    # Replace heavy components with fakes
    sc.get_speech_timestamps = lambda audio, *_a, **_k: [{"start": 0, "end": min(160, len(audio))}]
    sc.vadModel = object()
    sc.model = DummyModel()

    # Feed a short audio chunk (0.02s at 16kHz)
    audio = np.zeros(320, dtype=np.float32)
    sc.audioQueue.put(audio)

    # Run processing briefly
    sc._process_flag = [True]
    t = __import__("threading").Thread(target=sc.processAudioStream, daemon=True)
    t.start()
    time.sleep(0.1)
    sc._process_flag[0] = False
    t.join(timeout=1)

    assert sc.model.calls >= 1
