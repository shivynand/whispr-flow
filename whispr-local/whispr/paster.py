"""Paste dictated text into the application that was focused before recording."""

from __future__ import annotations

import subprocess
import time
from enum import Enum

_kVK_ANSI_V = 9


class PasteResult(str, Enum):
    PASTED = "pasted"
    COPIED = "copied"
    FAILED = "failed"
    NO_TARGET = "no_target"


def paste_text(
    text: str,
    bundle_id: str = "",
    restore_clipboard: bool = False,
) -> PasteResult:
    if not text:
        return PasteResult.FAILED

    try:
        previous = _read_clipboard() if restore_clipboard else None
        _write_clipboard(text)
    except Exception as exc:  # clipboard helpers can fail or time out
        print(f"[paste] clipboard write failed: {exc}")
        return PasteResult.FAILED

    ok = False
    if bundle_id:
        if not _activate(bundle_id):
            print(f"[paste] could not activate target app: {bundle_id}")
        else:
            time.sleep(0.12)
            ok = _send_cmd_v()
    else:
        print("[paste] no target application was captured")
        if restore_clipboard and previous is not None:
            _write_clipboard(previous)
        return PasteResult.NO_TARGET
        return PasteResult.COPIED
    if restore_clipboard and previous is not None:
        time.sleep(0.15)
        try:
            _write_clipboard(previous)
        except (OSError, subprocess.CalledProcessError):
            print("[paste] could not restore previous clipboard contents")

    if not ok:
        print("[paste] keyboard injection failed; Accessibility permission may be missing")
        return PasteResult.COPIED
    return PasteResult.PASTED


def _activate(bundle_id: str) -> bool:
    try:
        from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication

        apps = NSRunningApplication.runningApplicationsWithBundleIdentifier_(bundle_id)
        if apps:
            return bool(apps[0].activateWithOptions_(NSApplicationActivateIgnoringOtherApps))
    except Exception as exc:
        print(f"[paste] AppKit activation failed: {exc}")

    try:
        result = subprocess.run(
            ["open", "-b", bundle_id],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[paste] target activation failed: {exc}")
        return False


def _send_cmd_v() -> bool:
    try:
        from ApplicationServices import AXIsProcessTrusted, AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
        from Quartz import (
            CGEventCreateKeyboardEvent,
            CGEventPost,
            CGEventSetFlags,
            CGEventSourceCreate,
            kCGEventFlagMaskCommand,
            kCGEventSourceStateCombinedSessionState,
            kCGHIDEventTap,
        )

        if not AXIsProcessTrusted():
            print("[paste] Whispr Local needs Accessibility permission")
            try:
                AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
            except Exception as exc:
                print(f"[paste] could not request Accessibility access: {exc}")
            return False

        source = CGEventSourceCreate(kCGEventSourceStateCombinedSessionState)
        if not source:
            return False

        down = CGEventCreateKeyboardEvent(source, _kVK_ANSI_V, True)
        up = CGEventCreateKeyboardEvent(source, _kVK_ANSI_V, False)
        if not down or not up:
            return False

        CGEventSetFlags(down, kCGEventFlagMaskCommand)
        CGEventSetFlags(up, kCGEventFlagMaskCommand)
        CGEventPost(kCGHIDEventTap, down)
        CGEventPost(kCGHIDEventTap, up)
        time.sleep(0.05)
        return True
    except Exception as exc:
        print(f"[paste] CoreGraphics failed: {exc}")
        return False


def _write_clipboard(text: str) -> None:
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True, timeout=5)


def _read_clipboard() -> str:
    result = subprocess.run(["pbpaste"], capture_output=True, check=False, timeout=5)
    return result.stdout.decode("utf-8", errors="replace")


def prompt_accessibility() -> None:
    print("If paste is blocked: System Settings → Privacy & Security → Accessibility → enable Whispr Local.")
