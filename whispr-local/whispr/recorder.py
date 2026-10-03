"""Microphone capture. Audio stays in memory; nothing is written unless asked."""

from __future__ import annotations

import threading
from typing import Optional

import numpy as np


class Recorder:
    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate
        self._frames: list[np.ndarray] = []
        self._stream = None
        self._lock = threading.Lock()

    def start(self) -> None:
        import sounddevice as sd

        with self._lock:
            self._frames = []

            def callback(indata, frames, time_info, status) -> None:  # noqa: ANN001
                if status:
                    print(f"[mic] {status}")
                self._frames.append(indata.copy())

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                callback=callback,
            )
            self._stream.start()

    def snapshot(self) -> np.ndarray:
        with self._lock:
            if not self._frames:
                return np.zeros(0, dtype=np.float32)
            return np.concatenate(self._frames, axis=0).reshape(-1)

    def stop(self) -> np.ndarray:
        with self._lock:
            stream = self._stream
            self._stream = None
        if stream is not None:
            stream.stop()
            stream.close()
        if not self._frames:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self._frames, axis=0).reshape(-1)

    @property
    def is_recording(self) -> bool:
        return self._stream is not None


def seconds(audio: np.ndarray, sample_rate: int) -> float:
    if audio.size == 0:
        return 0.0
    return float(audio.size) / float(sample_rate)
