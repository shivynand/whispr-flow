"""Paste dictated text into the application that was focused before recording."""

from __future__ import annotations

import subprocess
import time

_kVK_ANSI_V = 9


def paste_text(
    text: str,
    bundle_id: str = "",
    restore_clipboard: bool = False,
) -> bool:
    if not text:
        return False

    try:
        previous = _read_clipboard() if restore_clipboard else None
        _write_clipboard(text)
    except Exception as exc:  # clipboard helpers can fail or time out
        print(f"[paste] clipboard write failed: {exc}")
        return False

    if bundle_id:
        if not _activate(bundle_id):
            print(f"[paste] could not activate target app: {bundle_id}")
            return False
        time.sleep(0.12)
    else:
        print("[paste] no target application was captured")
        return False

    ok = _send_cmd_v()
    if restore_clipboard and previous is not None:
        time.sleep(0.15)
        try:
            _write_clipboard(previous)
        except (OSError, subprocess.CalledProcessError):
            print("[paste] could not restore previous clipboard contents")

    if not ok:
        print("[paste] keyboard injection failed; Accessibility permission may be missing")
    return ok


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
        from ApplicationServices import AXIsProcessTrusted
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
