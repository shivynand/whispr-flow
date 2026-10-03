"""On-device transcription via faster-whisper."""

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

        print(f"[whisper] loading {model_size} ({compute_type})")
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type=compute_type,
        )
        self.language = language
        print("[whisper] ready")

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""

        segments, _info = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            temperature=0.0,
            condition_on_previous_text=True,
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": 500,
                "speech_pad_ms": 200,
            },
            without_timestamps=True,
        )
        return " ".join(
            segment.text.strip()
            for segment in segments
            if segment.text.strip()
        ).strip()
