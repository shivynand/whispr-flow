"""On-device transcription via faster-whisper. Model files are cached locally."""

from __future__ import annotations

from typing import Optional

import numpy as np


class Transcriber:
    def __init__(
        self,
        model_size: str = "base.en",
        language: Optional[str] = "en",
        compute_type: str = "int8",
    ) -> None:
        from faster_whisper import WhisperModel

        # cpu + int8 is the safe default on Intel and Apple Silicon.
        # The first call downloads the model into the Hugging Face cache.
        print(f"[whisper] loading {model_size} ({compute_type}). First run downloads the model.")
        self.model = WhisperModel(model_size, device="cpu", compute_type=compute_type)
        self.language = language
        print("[whisper] ready")

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        segments, _info = self.model.transcribe(
            audio,
            language=self.language,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        parts = [segment.text.strip() for segment in segments if segment.text.strip()]
        return " ".join(parts).strip()
