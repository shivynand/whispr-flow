"""Track the last non-Whispr application so the pill never becomes the target."""

from __future__ import annotations

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
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def start(self) -> None:
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def snapshot(self) -> tuple[str, str]:
        with self._lock:
            return self.bundle_id, self.name

    def _loop(self) -> None:
        while not self._stop.is_set():
            bundle, name = _frontmost()
            if bundle and bundle.lower() not in _IGNORE and "python" not in bundle.lower():
                with self._lock:
                    self.bundle_id = bundle
                    self.name = name
            time.sleep(0.2)


def _frontmost() -> tuple[str, str]:
    try:
        from AppKit import NSWorkspace

        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return "", ""
        bundle = app.bundleIdentifier() or ""
        name = app.localizedName() or ""
        return bundle, name
    except Exception as exc:
        print(f"[focus] could not inspect frontmost app: {exc}")
        return "", ""
