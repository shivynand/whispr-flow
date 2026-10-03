"""Global hold-to-talk. On macOS this needs Input Monitoring permission."""

from __future__ import annotations

from typing import Callable, Optional

from pynput import keyboard

# Names you can put in config.json. Fn is not reliably visible to user-space apps.
HOTKEYS = {
    "alt_r": keyboard.Key.alt_r,
    "alt_l": keyboard.Key.alt_l,
    "alt": keyboard.Key.alt,
    "ctrl_r": keyboard.Key.ctrl_r,
    "ctrl_l": keyboard.Key.ctrl_l,
    "ctrl": keyboard.Key.ctrl,
    "shift_r": keyboard.Key.shift_r,
    "cmd_r": keyboard.Key.cmd_r,
    "f13": keyboard.Key.f13,
    "f14": keyboard.Key.f14,
    "f15": keyboard.Key.f15,
}


class HoldToTalk:
    def __init__(
        self,
        hotkey: str,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        toggle: bool = False,
    ) -> None:
        if hotkey not in HOTKEYS:
            known = ", ".join(sorted(HOTKEYS))
            raise SystemExit(f"Unknown hotkey {hotkey!r}. Use one of: {known}")
        self.key = HOTKEYS[hotkey]
        self.on_start = on_start
        self.on_stop = on_stop
        self.toggle = toggle
        self._held = False
        self._listener: Optional[keyboard.Listener] = None

    def run(self) -> None:
        self._listener = keyboard.Listener(on_press=self._press, on_release=self._release)
        self._listener.start()
        self._listener.join()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()

    def _press(self, key) -> None:  # noqa: ANN001
        if key != self.key or self._held:
            return
        self._held = True
        if self.toggle:
            self.on_start()
            return
        self.on_start()

    def _release(self, key) -> None:  # noqa: ANN001
        if key != self.key or not self._held:
            return
        self._held = False
        if self.toggle:
            return
        self.on_stop()
