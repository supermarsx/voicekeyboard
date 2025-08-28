import logging
import os
import threading
import time
from collections import deque
from queue import Queue
from typing import Any, Callable, Deque, Dict, List, Optional

import numpy

from .settings import settings


class RingBuffer:
    """Simple ring buffer for 1-D numpy arrays concatenation.

    Maintains a deque of numpy chunks up to a maximum total length. On append,
    evicts from the left to keep the concatenated length within capacity.
    """

    def __init__(self, capacity: int):
        self.capacity = max(1, int(capacity))
        self._chunks: Deque[numpy.ndarray] = deque()
        self._length = 0

    def clear(self) -> None:
        self._chunks.clear()
        self._length = 0

    def append(self, arr: numpy.ndarray) -> None:
        if arr is None:
            return
        if arr.ndim != 1:
            arr = arr.reshape(-1)
        n = int(arr.shape[0])
        if n <= 0:
            return
        self._chunks.append(arr)
        self._length += n
        # Evict from left if over capacity
        while self._length > self.capacity and self._chunks:
            left = self._chunks[0]
            if self._length - left.shape[0] >= self.capacity:
                self._chunks.popleft()
                self._length -= left.shape[0]
            else:
                # Trim the left chunk to fit capacity
                need = self._length - self.capacity
                if need > 0:
                    self._chunks[0] = left[need:]
                    self._length -= need
                break

    def concat(self) -> numpy.ndarray:
        if not self._chunks:
            return numpy.empty((0,), dtype=numpy.float32)
        return numpy.concatenate(list(self._chunks), axis=0)


class SpeechConverter:
    """Coordinates VAD + Whisper transcription and audio streaming."""

    def __init_dry_run_flag(self) -> bool:
        """Return True when VOICEKB_DRYRUN indicates a dry run (skip models)."""
        return os.getenv("VOICEKB_DRYRUN", "0") in ("1", "true", "True")

    def _update_label(self, text: str) -> None:
        """Emit a label change signal on the UI thread, if available."""
        try:
            from .window import labelUpdater  # local import to avoid hard dep

            labelUpdater.textChanged.emit(text)
        except Exception:
            # UI not available; ignore label updates
            logging.debug("Label update skipped (UI not initialized)")

    def __init__(self):
        """Initialize state; heavy model loads happen lazily when needed.

        This avoids importing or downloading large ML dependencies during tests
        or when running in environments without GPU/CT2 installed. When
        ``VOICEKB_DRYRUN`` is set, models are never loaded.
        """
        try:
            self.dry_run: bool = self.__init_dry_run_flag()
            self.stream: Optional[Any] = None
            self.streamThread: Optional[threading.Thread] = None
            self.transcriptionThread: Optional[threading.Thread] = None
            self.model: Optional[Any] = None
            self.vadModel: Optional[Any] = None
            # default VAD is a no-op until models are ensured
            self.get_speech_timestamps: Callable[..., List[Dict[str, int]]] = (
                lambda audio, *_args, **_kwargs: []
            )
            self._update_label("STT startup\nLoading up settings")
            logging.debug("Setting audio chunk sizes")
            settings.audioChunkSize = int(settings.audioSampleRate * settings.audioChunkDuration)
            settings.audioChunkOverlapSize = int(
                settings.audioSampleRate * settings.audioChunkOverlapDuration
            )
            self._update_label("STT startup\nSetting up audio queue")
            logging.debug("Starting audio queue")
            self.audioQueue: Queue = Queue()
            logging.debug("Queue started")
            self._update_label("Ready!")
        except Exception as error:
            self._update_label("Failed to start STT!\nPlease check logs")
            logging.error(f"Failed to initialize speech converter: {error}")
        else:
            logging.info("Initialized speech converter")

    def _ensure_models_loaded(self) -> None:
        """Lazy-load VAD and Whisper models if not in dry-run mode."""
        if self.dry_run:
            return
        if self.model is not None and self.vadModel is not None:
            return
        try:
            self._update_label("STT startup\nLoading models")
            logging.debug("Loading speech-to-text and VAD models lazily")
            # Import heavy deps only when needed
            import torch
            from faster_whisper import WhisperModel

            self.model = WhisperModel(
                model_size_or_path=settings.whisperModel,
                device=settings.whisperDevice,
                compute_type=settings.whisperComputeType,
                cpu_threads=settings.whisperCpuThreads,
                num_workers=settings.whisperNumWorkers,
            )
            self.vadModel, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=settings.vadForceRedownload,
            )
            (self.get_speech_timestamps, _, _, _, _) = utils
            logging.debug("Models loaded")
        except Exception as e:
            logging.error(f"Failed to load models: {e}")
            # Keep placeholders to allow app to continue running
            self.model = None
            self.vadModel = None
            self.get_speech_timestamps = lambda audio, *_a, **_k: []

    def audioCallback(self, indata, frames, time_info, status):
        """Audio callback for sounddevice, pushing mono samples into the queue."""
        if indata.ndim > 1:
            mono_audio = numpy.mean(indata, axis=1)
        else:
            mono_audio = indata

        self.audioQueue.put(mono_audio.copy())

    def processAudioStream(self) -> None:
        """Consume audio, detect voice segments, and transcribe when possible.

        This loop keeps a sliding buffer and runs VAD to find voiced segments.
        For each segment, it invokes the Whisper model to obtain text.
        The loop terminates when ``_process_flag`` is cleared.
        """
        # Ring buffer sized to ~2s of audio for responsiveness without growing unbounded
        ring = RingBuffer(capacity=int(settings.audioSampleRate * 2))
        sample_rate = settings.audioSampleRate
        # Process small windows to improve responsiveness and allow tests to feed short buffers
        min_audio_window = max(160, int(sample_rate * 0.02))  # ~20ms at 16kHz

        # Use a mutable flag set in start()/stop()
        if not hasattr(self, "_process_flag"):
            self._process_flag = [True]
        while self._process_flag[0]:
            try:
                chunk = self.audioQueue.get(timeout=1)
                ring.append(chunk)
                audio_data = ring.concat()
                if len(audio_data) < min_audio_window:
                    continue
                # Ensure heavy models are loaded if needed
                if not self.dry_run and (self.model is None or self.vadModel is None):
                    self._ensure_models_loaded()
                speech_timestamps = self.get_speech_timestamps(
                    audio_data, self.vadModel, sampling_rate=sample_rate
                )
                if speech_timestamps and self.model:
                    for segment in speech_timestamps:
                        start = segment["start"]
                        end = segment["end"]
                        voiced_audio = audio_data[start:end]
                        voiced_audio = voiced_audio.astype(numpy.float32)
                        segments, info = self.model.transcribe(
                            voiced_audio,
                            language=settings.whisperLanguage,
                            vad_filter=False,
                            word_timestamps=False,
                        )
                        text = " ".join([seg.text for seg in segments])
                        if text:
                            logging.info(f"Typing: {text}")
                # Reset buffer after processing a batch to keep latency low
                ring.clear()
            except Exception as e:
                logging.error(f"Error during real-time transcription: {e}")
                continue

    def _run_audio_stream(self, record_flag: List[bool]) -> None:
        """Maintain a persistent audio input stream while ``record_flag`` is True."""
        # Import here to avoid dependency at module import time
        import sounddevice

        # Map configured device choice
        device_choice = settings.audioInputDevice
        if isinstance(device_choice, str) and device_choice in ("", "Default"):
            device_choice = None

        with sounddevice.InputStream(
            callback=self.audioCallback,
            channels=settings.audioChannels,
            samplerate=settings.audioSampleRate,
            device=device_choice,
        ) as stream:
            self.stream = stream
            while record_flag[0]:
                time.sleep(0.1)

    def start(self) -> None:
        """Start audio capture and processing threads."""
        self._update_label("Recording/Processing...")
        logging.info("Started recording")

        self.transcriptionThread = threading.Thread(target=self.processAudioStream, daemon=True)
        self.transcriptionThread.start()

        self._record_flag = [True]
        self._process_flag = [True]
        self.streamThread = threading.Thread(
            target=self._run_audio_stream, args=(self._record_flag,), daemon=True
        )
        self.streamThread.start()

    def stop(self) -> None:
        """Stop audio capture and processing threads and clean up resources."""
        logging.info("Stopping STT system")
        if hasattr(self, "_record_flag"):
            self._record_flag[0] = False
        if hasattr(self, "_process_flag"):
            self._process_flag[0] = False

        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                logging.info("Audio stream closed")
            except Exception as e:
                logging.warning(f"Failed to stop audio stream: {e}")
            self.stream = None

        if self.streamThread and self.streamThread.is_alive():
            self.streamThread.join(timeout=2)
            logging.info("Audio thread joined")
            self.streamThread = None

        if self.transcriptionThread and self.transcriptionThread.is_alive():
            self.transcriptionThread.join(timeout=2)
            logging.info("Transcription thread joined")
            self.transcriptionThread = None

        self._update_label("Stopped recording..")
