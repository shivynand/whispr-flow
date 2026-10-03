"""Paste dictated text into the application that was focused before recording."""

from __future__ import annotations

import ctypes
import subprocess
import time
from ctypes import c_bool, c_int32, c_uint16, c_uint64, c_void_p

_kVK_ANSI_V = 9
_CMD = 0x100000
_HID_TAP = 0


def paste_text(
    text: str,
    bundle_id: str = "",
    restore_clipboard: bool = False,
) -> bool:
    if not text:
        return False

    previous = _read_clipboard() if restore_clipboard else None
    try:
        _write_clipboard(text)
    except (OSError, subprocess.CalledProcessError) as exc:
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

    result = subprocess.run(
        ["open", "-b", bundle_id],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _send_cmd_v() -> bool:
    try:
        cg = _cg()
        cf = _cf()
        cg.CGEventSourceCreate.restype = c_void_p
        cg.CGEventSourceCreate.argtypes = [c_int32]
        cg.CGEventCreateKeyboardEvent.restype = c_void_p
        cg.CGEventCreateKeyboardEvent.argtypes = [c_void_p, c_uint16, c_bool]
        cg.CGEventSetFlags.argtypes = [c_void_p, c_uint64]
        cg.CGEventPost.argtypes = [c_int32, c_void_p]
        cf.CFRelease.argtypes = [c_void_p]

        source = cg.CGEventSourceCreate(0)
        if not source:
            return False

        down = cg.CGEventCreateKeyboardEvent(source, _kVK_ANSI_V, True)
        up = cg.CGEventCreateKeyboardEvent(source, _kVK_ANSI_V, False)
        if not down or not up:
            for ref in (down, up, source):
                if ref:
                    cf.CFRelease(ref)
            return False

        cg.CGEventSetFlags(down, _CMD)
        cg.CGEventSetFlags(up, _CMD)
        cg.CGEventPost(_HID_TAP, down)
        cg.CGEventPost(_HID_TAP, up)
        time.sleep(0.05)

        for ref in (down, up, source):
            cf.CFRelease(ref)
        return True
    except OSError as exc:
        print(f"[paste] CoreGraphics failed: {exc}")
        return False


def _write_clipboard(text: str) -> None:
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)


def _read_clipboard() -> str:
    result = subprocess.run(["pbpaste"], capture_output=True, check=False)
    return result.stdout.decode("utf-8", errors="replace")


def prompt_accessibility() -> None:
    print("If paste is blocked: System Settings → Privacy & Security → Accessibility → enable Whispr Local.")
