#!/usr/bin/env python3
"""Hold a key, speak, get cleaned text pasted into the focused Mac app.

Local only: microphone audio never leaves the machine. The Whisper model is
downloaded once on first run and cached by Hugging Face.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import threading
from pathlib import Path

# Allow `python main.py` from the project root without an install.
sys.path.insert(0, str(Path(__file__).resolve().parent))

LOG_PATH = Path.home() / "Library" / "Logs" / "whispr-local.log"

from whispr.cleanup import clean
from whispr.config import Config, config_path
from whispr.focus import FocusTracker
from whispr.paster import paste_text
from whispr.recorder import Recorder, seconds


class App:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.recorder = Recorder(sample_rate=config.sample_rate)
        self.transcriber = None
        self._busy = threading.Lock()
        self._recording = False
        self._toggle_on = False
        self._status = None
        self.focus = FocusTracker()

    def set_status_handler(self, handler) -> None:  # noqa: ANN001
        self._status = handler

    def status(self, state: str, detail: str) -> None:
        print(f"[{state}] {detail}")
        if self._status is not None:
            self._status(state, detail)

    def load_model(self) -> None:
        from whispr.transcriber import Transcriber

        print(f"[whisper] loading {self.config.model}")
        self.status("loading", "Loading model")
        self.transcriber = Transcriber(
            model_size=self.config.model,
            language=self.config.language or None,
            compute_type=self.config.compute_type,
        )

    def on_start(self) -> None:
        if self.config.toggle:
            self._toggle()
            return
        self._begin()

    def on_stop(self) -> None:
        if self.config.toggle:
            return
        self._end()

    def _toggle(self) -> None:
        if self._toggle_on:
            self._toggle_on = False
            self._end()
        else:
            self._toggle_on = self._begin()

    def _begin(self) -> bool:
        if not self._busy.acquire(blocking=False):
            self.status("transcribing", "Still writing")
            return False
        try:
            self.recorder.start()
        except Exception as exc:  # noqa: BLE001
            self._busy.release()
            self.status("error", "Mic blocked")
            print(f"[mic] failed to start: {exc}")
            print("[mic] Grant Microphone access to this app, then click the pill again.")
            return False
        self._recording = True
        self._pasted = ""
        self._committed = 0
        if self.config.sound:
            _chime("Pop")
        self.status("listening", "Listening…")
        threading.Thread(target=self._stream, daemon=True).start()
        return True

    def _stream(self) -> None:
        import time

        while self._recording:
            time.sleep(0.8)
            if not self._recording:
                break
            self._flush(final=False)
        self._flush(final=True)
        self.status("ready", "Click the bar")
        self._busy.release()

    def _flush(self, final: bool) -> None:
        if self.transcriber is None:
            return
        audio = self.recorder.snapshot()
        if audio is None or audio.size <= self._committed:
            return
        chunk = audio[self._committed :]
        if not final and seconds(chunk, self.config.sample_rate) < 0.7:
            return
        if _level(chunk) < 0.002:
            if final:
                self._committed = audio.size
            return
        try:
            raw = self.transcriber.transcribe(chunk)
        except Exception as exc:  # noqa: BLE001
            print(f"[whisper] {exc}")
            return
        text = clean(raw, final=False).strip(" .")
        self._committed = audio.size
        if not text:
            return
        self._pasted = (self._pasted + " " + text).strip()
        self.status("listening", self._pasted[-42:])
        piece = text + " "
        if not paste_text(piece):
            self.status("error", "Allow Accessibility")
            print("[live] recognized but could not type into the front field")
        else:
            print(f"[live] {text}")

    def _end(self) -> None:
        if not self._recording:
            return
        self._recording = False
        audio = self.recorder.stop()
        duration = seconds(audio, self.config.sample_rate)
        level = _level(audio)
        print(f"[audio] {duration:.1f}s level={level:.5f}")
        if duration < self.config.min_seconds or level < 0.002:
            self.status("ready" if duration < self.config.min_seconds else "error", "Too short" if duration < self.config.min_seconds else "Allow Microphone")
            if level < 0.002:
                _open_privacy("Privacy_Microphone")
            return
        self.status("listening", "Finishing…")

    def _finish(self, audio) -> None:  # noqa: ANN001
        return


def _level(audio) -> float:  # noqa: ANN001
    import numpy as np

    if audio is None or getattr(audio, "size", 0) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio))))


def _request_microphone() -> None:
    try:
        import AVFoundation

        AVFoundation.AVCaptureDevice.requestAccessForMediaType_completionHandler_("soun", lambda granted: None)
    except Exception as exc:  # noqa: BLE001
        print(f"[mic] permission prompt unavailable: {exc}")


def _open_privacy(pane: str) -> None:
    subprocess.Popen(
        ["open", f"x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?{pane}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _chime(name: str) -> None:
    sound = Path(f"/System/Library/Sounds/{name}.aiff")
    if sound.exists():
        subprocess.Popen(["afplay", str(sound)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> None:
    _log_to_file()
    parser = argparse.ArgumentParser(description="Local dictation for macOS")
    parser.add_argument("--toggle", action="store_true", help="Hotkey press starts and stops, instead of hold")
    parser.add_argument("--hotkey", help="Override the hotkey for this run (alt_r, f13, ctrl_r, …)")
    parser.add_argument("--model", help="Whisper model size, e.g. tiny.en, base.en, small.en")
    parser.add_argument("--no-ui", action="store_true", help="Terminal only, no floating pill")
    parser.add_argument("--demo-cleanup", metavar="TEXT", help="Run the cleanup pass on TEXT and exit")
    args = parser.parse_args()

    if args.demo_cleanup:
        print(clean(args.demo_cleanup))
        return

    config = Config.load()
    if args.toggle:
        config.toggle = True
    if args.hotkey:
        config.hotkey = args.hotkey
    if args.model:
        config.model = args.model

    binary = str(Path(sys.executable).resolve())
    print(f"whispr-local  config: {config_path()}")
    print(f"python: {binary}")
    print("Hotkey needs this exact binary in Accessibility and Input Monitoring.")
    print("Until that is granted, click the pill. The warning from pynput is that block.")

    app = App(config)
    app.focus.start()
    if args.no_ui:
        app.load_model()
        app.status("ready", "Hold the key")
        from whispr.hotkey import HoldToTalk

        try:
            HoldToTalk(config.hotkey, app.on_start, app.on_stop, toggle=config.toggle).run()
        except KeyboardInterrupt:
            print("\nbye")
        return

    from whispr.ui import Pill

    pill = Pill(on_toggle=app._toggle, on_quit=lambda: None, config=config, python_path=binary)
    app.set_status_handler(pill.set_status)

    def boot() -> None:
        try:
            app.load_model()
            app.status("ready", "Click to dictate")
        except Exception as exc:  # noqa: BLE001
            app.status("error", "Model failed")
            print(f"[whisper] {exc}")

    def hotkey() -> None:
        try:
            from whispr.hotkey import HoldToTalk

            HoldToTalk(config.hotkey, app.on_start, app.on_stop, toggle=config.toggle).run()
        except Exception as exc:  # noqa: BLE001
            print(f"[hotkey] not available yet: {exc}")

    threading.Thread(target=boot, daemon=True).start()
    threading.Thread(target=hotkey, daemon=True).start()
    try:
        pill.mainloop()
    except Exception as exc:  # noqa: BLE001
        _alert("Whispr Local failed to open", str(exc))
        raise


def _log_to_file() -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        handle = LOG_PATH.open("a", encoding="utf-8")
        sys.stdout = handle
        sys.stderr = handle
    except OSError:
        pass


def _alert(title: str, message: str) -> None:
    script = f'display alert "{title}" message "{message[:200]}"'
    subprocess.run(["osascript", "-e", script], check=False)


if __name__ == "__main__":
    main()
