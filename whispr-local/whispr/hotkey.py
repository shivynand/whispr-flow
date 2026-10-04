"""Global hold-to-talk. On macOS this needs Input Monitoring permission."""

from __future__ import annotations

import threading
from typing import Callable, Optional

from pynput import keyboard

_SPACE_HOLD_SECONDS = 0.24
_SPACE_KEYCODE = 0x31

# Names you can put in config.json. Fn is not reliably visible to user-space apps.
HOTKEYS = {
    "space": keyboard.Key.space,
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
        self._suppress_space = hotkey == "space"
        self._held = False
        self._space_started = False
        self._space_timer = None
        self._replay_space = False
        self._space_passthrough = False
        self._space_lock = threading.Lock()
        self._listener: Optional[keyboard.Listener] = None

    def run(self) -> None:
        options = {"on_press": self._press, "on_release": self._release}
        if self._suppress_space:
            options["darwin_intercept"] = self._intercept
        self._listener = keyboard.Listener(**options)
        self._listener.start()
        self._listener.join()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()

    def _press(self, key, *extra) -> None:  # noqa: ANN001
        if extra and extra[0]:  # Ignore keys synthesized by this app or another app.
            return
        if key != self.key:
            return
        if self._suppress_space:
            with self._space_lock:
                if self._held:
                    return
                self._held = True
                self._space_started = False
                self._space_passthrough = False
                timer = threading.Timer(_SPACE_HOLD_SECONDS, self._start_space_recording)
                timer.daemon = True
                self._space_timer = timer
            timer.start()
            return
        if self._held:
            return
        self._held = True
        if self.toggle:
            self.on_start()
            return
        self.on_start()

    def _release(self, key, *extra) -> None:  # noqa: ANN001
        if extra and extra[0]:
            return
        if key != self.key:
            return
        if self._suppress_space:
            with self._space_lock:
                if not self._held:
                    return
                self._held = False
                timer = self._space_timer
                self._space_timer = None
                started = self._space_started
                if not started:
                    self._replay_space = True
            if timer is not None:
                timer.cancel()
            if started:
                self.on_stop()
            return
        if not self._held:
            return
        self._held = False
        if self.toggle:
            return
        self.on_stop()

    def _start_space_recording(self) -> None:
        with self._space_lock:
            if not self._held or self._space_started or self._space_passthrough:
                return
            self._space_started = True
        self.on_start()

    def _intercept(self, event_type, event):  # noqa: ANN001
        """Suppress held Space, while preserving quick taps as typed spaces."""
        from Quartz import (
            CGEventCreateKeyboardEvent,
            CGEventGetIntegerValueField,
            CGEventGetFlags,
            CGEventPost,
            CGEventSetFlags,
            CGEventSourceCreate,
            kCGEventFlagMaskAlternate,
            kCGEventFlagMaskCommand,
            kCGEventFlagMaskControl,
            kCGEventSourceStateCombinedSessionState,
            kCGHIDEventTap,
            kCGEventKeyDown,
            kCGEventKeyUp,
            kCGKeyboardEventKeycode,
            kCGEventSourceUnixProcessID,
        )

        if event_type not in (kCGEventKeyDown, kCGEventKeyUp):
            return event
        if CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode) != _SPACE_KEYCODE:
            return event
        if CGEventGetIntegerValueField(event, kCGEventSourceUnixProcessID):
            return event

        if event_type == kCGEventKeyDown and CGEventGetFlags(event) & (
            kCGEventFlagMaskCommand | kCGEventFlagMaskAlternate | kCGEventFlagMaskControl
        ):
            with self._space_lock:
                timer = self._space_timer
                self._space_timer = None
                self._held = False
                self._space_passthrough = True
            if timer is not None:
                timer.cancel()
            return event
        if self._space_passthrough:
            if event_type == kCGEventKeyUp:
                self._space_passthrough = False
            return event

        replay = False
        if event_type == kCGEventKeyUp:
            with self._space_lock:
                replay = self._replay_space
                self._replay_space = False
        if replay:
            flags = CGEventGetFlags(event)
            source = CGEventSourceCreate(kCGEventSourceStateCombinedSessionState)
            down = CGEventCreateKeyboardEvent(source, _SPACE_KEYCODE, True)
            up = CGEventCreateKeyboardEvent(source, _SPACE_KEYCODE, False)
            if down is not None and up is not None:
                CGEventSetFlags(down, flags)
                CGEventSetFlags(up, flags)
                CGEventPost(kCGHIDEventTap, down)
                CGEventPost(kCGHIDEventTap, up)
        return None
