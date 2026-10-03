"""Small JSON config in ~/Library/Application Support/whispr-local/config.json."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


def config_dir() -> Path:
    path = Path.home() / "Library" / "Application Support" / "whispr-local"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return config_dir() / "config.json"


@dataclass
class Config:
    hotkey: str = "alt_r"
    toggle: bool = False
    model: str = "base.en"
    language: str = "en"
    compute_type: str = "int8"
    sample_rate: int = 16000
    min_seconds: float = 0.35
    sound: bool = True
    restore_clipboard: bool = False
    window_x: int | None = None
    window_y: int | None = None

    @classmethod
    def load(cls) -> "Config":
        path = config_path()
        if not path.exists():
            cfg = cls()
            cfg.save()
            return cfg
        data = json.loads(path.read_text())
        known = {field: data[field] for field in cls.__dataclass_fields__ if field in data}
        return cls(**known)

    def save(self) -> None:
        config_path().write_text(json.dumps(asdict(self), indent=2) + "\n")
