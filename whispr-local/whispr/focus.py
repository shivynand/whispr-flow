"""Remember the app you were typing in, so a click on the pill does not steal the paste."""

from __future__ import annotations

import subprocess
import threading
import time

_IGNORE = {
    "com.apple.terminal",
    "com.googlecode.iterm2",
    "com.apple.scripteditor2",
    "org.python.python",
    "org.python.pythonlauncher",
    "local.whispr.dictation",
    "com.apple.systempreferences",
    "com.apple.settings.privacysecurity.extension",
}


class FocusTracker:
    def __init__(self) -> None:
        self.bundle_id = ""
        self.name = ""
        self._stop = threading.Event()

    def start(self) -> None:
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            bundle, name = _frontmost()
            if bundle and bundle.lower() not in _IGNORE and "python" not in bundle.lower():
                self.bundle_id = bundle
                self.name = name
            time.sleep(0.4)


def _frontmost() -> tuple[str, str]:
    # lsappinfo does not need Accessibility. System Events does, and that is what just failed.
    try:
        front = subprocess.run(
            ["lsappinfo", "front"],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        ).stdout.strip()
        if not front:
            return "", ""
        info = subprocess.run(
            ["lsappinfo", "info", "-only", "bundleid", "-only", "name", front],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return "", ""
    bundle = _field(info, "bundleid")
    name = _field(info, "name")
    return bundle, name


def _field(info: str, key: str) -> str:
    for line in info.splitlines():
        if f'"{key}"=' in line or f"{key}=" in line:
            value = line.split("=", 1)[1].strip().strip('"')
            return value
    return ""
