#!/usr/bin/env python3
"""Local macOS dictation: record once, transcribe once, paste once."""

from __future__ import annotations

import argparse
import subprocess
import sys
import threading
from pathlib import Path

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
        self.focus = FocusTracker()
        self._busy = threading.Lock()
        self._state_lock = threading.RLock()
        self._recording = False
        self._toggle_on = False
        self._target_bundle = ""
        self._target_name = ""
        self._status = None

    def set_status_handler(self, handler) -> None:
        self._status = handler

    def status(self, state: str, detail: str) -> None:
        print(f"[{state}] {detail}")
        if self._status is not None:
            self._status(state, detail)

    def load_model(self) -> None:
        from whispr.transcriber import Transcriber

        self.status("loading", "Loading model…")
        self.transcriber = Transcriber(
            model_size=self.config.model,
            language=self.config.language or None,
            compute_type=self.config.compute_type,
        )

    def on_start(self) -> None:
        if self.config.toggle:
            self._toggle()
        else:
            self._begin()

    def on_stop(self) -> None:
        if not self.config.toggle:
            self._end()

    def _toggle(self) -> None:
        if self._toggle_on:
            self._toggle_on = False
            self._end()
        else:
            self._toggle_on = self._begin()

    def _begin(self) -> bool:
        if self.transcriber is None:
            self.status("loading", "Model is still loading…")
            return False
        if not self._busy.acquire(blocking=False):
            self.status("transcribing", "Finishing previous dictation…")
            return False

        target_bundle, target_name = self.focus.snapshot()
        if not target_bundle:
            self._busy.release()
            self.status("error", "Click a text field first")
            return False

        try:
            self.recorder.start()
        except Exception as exc:
            self._busy.release()
            self.status("error", "Microphone unavailable")
            print(f"[mic] failed to start: {exc}")
            return False

        with self._state_lock:
            self._target_bundle = target_bundle
            self._target_name = target_name or target_bundle
            self._recording = True

        if self.config.sound:
            _chime("Pop")
        self.status("listening", f"Listening for {self._target_name}")
        return True

    def _end(self) -> None:
        with self._state_lock:
            if not self._recording:
                return
            self._recording = False
            target_bundle = self._target_bundle
            target_name = self._target_name

        try:
            audio = self.recorder.stop()
        except Exception as exc:
            self._busy.release()
            self.status("error", "Microphone stopped unexpectedly")
            print(f"[mic] failed to stop: {exc}")
            return

        duration = seconds(audio, self.config.sample_rate)
        level = _level(audio)
        print(f"[audio] {duration:.2f}s level={level:.5f}")

        if duration < self.config.min_seconds:
            self._busy.release()
            self.status("ready", "Too short — try again")
            return

        if level < 0.002:
            self._busy.release()
            self.status("ready", "No speech detected")
            return

        self.status("transcribing", "Transcribing…")
        threading.Thread(
            target=self._finish_recording,
            args=(audio, target_bundle, target_name),
            daemon=True,
        ).start()

    def _finish_recording(self, audio, target_bundle: str, target_name: str) -> None:
        try:
            try:
                raw = self.transcriber.transcribe(audio)
            except Exception as exc:
                self.status("error", "Transcription failed — try again")
                print(f"[whisper] {exc}")
                return

            text = clean(raw, final=True).strip()
            if not text:
                self.status("ready", "Nothing heard")
                return

            insert = text if text.endswith((" ", "\n")) else text + " "
            self.status("transcribing", "Pasting…")
            ok = paste_text(
                insert,
                bundle_id=target_bundle,
                restore_clipboard=self.config.restore_clipboard,
            )
            if ok:
                self.status("ready", f"Sent to {target_name}")
                print(f"[done] {text}")
            else:
                self.status("error", "Copied to clipboard — paste was blocked")
                print("[paste] target activation or keyboard injection failed")
        finally:
            self._busy.release()


def _level(audio) -> float:
    import numpy as np

    if audio is None or getattr(audio, "size", 0) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio))))


def _chime(name: str) -> None:
    sound = Path(f"/System/Library/Sounds/{name}.aiff")
    if sound.exists():
        subprocess.Popen(
            ["afplay", str(sound)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def main() -> None:
    _log_to_file()
    parser = argparse.ArgumentParser(description="Local dictation for macOS")
    parser.add_argument("--toggle", action="store_true", help="Press the hotkey to start/stop")
    parser.add_argument("--hotkey", help="Override the hotkey for this run")
    parser.add_argument("--model", help="Whisper model size, e.g. tiny.en, base.en, small.en")
    parser.add_argument("--no-ui", action="store_true", help="Terminal only, no floating pill")
    parser.add_argument("--demo-cleanup", metavar="TEXT", help="Run cleanup on TEXT and exit")
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

    app = App(config)
    app.focus.start()

    if args.no_ui:
        app.load_model()
        app.status("ready", "Hold the key")
        from whispr.hotkey import HoldToTalk

        try:
            HoldToTalk(
                config.hotkey,
                app.on_start,
                app.on_stop,
                toggle=config.toggle,
            ).run()
        except KeyboardInterrupt:
            print("\nbye")
        return

    from whispr.ui import Pill

    pill = Pill(
        on_toggle=app._toggle,
        on_quit=app.focus.stop,
        config=config,
        python_path=binary,
    )
    app.set_status_handler(pill.set_status)

    def boot() -> None:
        try:
            app.load_model()
            app.status("ready", "Click to dictate")
        except Exception as exc:
            app.status("error", "Model failed to load")
            print(f"[whisper] {exc}")

    def hotkey() -> None:
        try:
            from whispr.hotkey import HoldToTalk

            HoldToTalk(
                config.hotkey,
                app.on_start,
                app.on_stop,
                toggle=config.toggle,
            ).run()
        except Exception as exc:
            print(f"[hotkey] not available: {exc}")

    threading.Thread(target=boot, daemon=True).start()
    threading.Thread(target=hotkey, daemon=True).start()

    try:
        pill.mainloop()
    except Exception as exc:
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
    safe_title = title.replace("\\", "\\\\").replace('"', '\"')
    safe_message = message[:200].replace("\\", "\\\\").replace('"', '\"')
    script = f'display alert "{safe_title}" message "{safe_message}"'
    subprocess.run(["osascript", "-e", script], check=False)


if __name__ == "__main__":
    main()
