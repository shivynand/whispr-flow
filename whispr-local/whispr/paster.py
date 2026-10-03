"""Put text on the clipboard, reactivate the app you were typing in, send Cmd+V.

osascript keystroke is what macOS just blocked (error 1002). CoreGraphics posts the
key from this process instead, so the permission attaches to Whispr Local / Terminal,
not to osascript.
"""

from __future__ import annotations

import ctypes
import subprocess
import time
from ctypes import c_bool, c_char_p, c_int32, c_uint16, c_uint32, c_uint64, c_void_p

_kVK_ANSI_V = 9
_CMD = 0x100000
_HID_TAP = 0


def paste_text(text: str, bundle_id: str = "", restore_clipboard: bool = False) -> bool:
    if not text:
        return False
    if _insert_into_focused_field(text):
        return True
    previous = _read_clipboard() if restore_clipboard else None
    _write_clipboard(text)
    time.sleep(0.03)
    ok = _send_cmd_v()
    if restore_clipboard and previous is not None:
        time.sleep(0.12)
        _write_clipboard(previous)
    if not ok:
        print("[paste] could not type into the front window. Enable Whispr Local in Accessibility.")
    return ok


def _insert_into_focused_field(text: str) -> bool:
    """Insert at the caret of whatever text field is focused. No app switch."""
    try:
        import ApplicationServices
    except Exception as exc:  # noqa: BLE001
        print(f"[paste] accessibility bridge missing: {exc}")
        return False
    system = ApplicationServices.AXUIElementCreateSystemWide()
    err, focused = ApplicationServices.AXUIElementCopyAttributeValue(
        system, ApplicationServices.kAXFocusedUIElementAttribute, None
    )
    if err != 0 or focused is None:
        print(f"[paste] no focused text field ({err})")
        return False
    err = ApplicationServices.AXUIElementSetAttributeValue(
        focused, ApplicationServices.kAXSelectedTextAttribute, text
    )
    if err != 0:
        print(f"[paste] field refused insert ({err})")
        return False
    return True


def accessibility_trusted() -> bool:
    # Do not call AXIsProcessTrustedWithOptions from ctypes. On the system
    # Python 3.9 that ships with Xcode tools, a bad options dictionary
    # segfaults inside CFGetTypeID and the app vanishes.
    return True


def prompt_accessibility() -> None:
    print("[paste] If paste is blocked: System Settings → Privacy & Security → Accessibility → enable Whispr Local.")
    _open_accessibility_settings()


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
        down = cg.CGEventCreateKeyboardEvent(source, _kVK_ANSI_V, True)
        cg.CGEventSetFlags(down, _CMD)
        cg.CGEventPost(_HID_TAP, down)
        up = cg.CGEventCreateKeyboardEvent(source, _kVK_ANSI_V, False)
        cg.CGEventSetFlags(up, _CMD)
        cg.CGEventPost(_HID_TAP, up)
        time.sleep(0.05)
        for ref in (down, up, source):
            if ref:
                cf.CFRelease(ref)
        return True
    except OSError as exc:
        print(f"[paste] CoreGraphics paste failed: {exc}")
        return False


def _activate(bundle_id: str) -> None:
    subprocess.run(["open", "-b", bundle_id], check=False, capture_output=True)


def _write_clipboard(text: str) -> None:
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)


def _read_clipboard() -> str:
    result = subprocess.run(["pbpaste"], capture_output=True, check=False)
    return result.stdout.decode("utf-8", errors="replace")


def _open_accessibility_settings() -> None:
    subprocess.Popen(
        [
            "open",
            "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Accessibility",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _cg():
    return ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")


def _cf():
    return ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")


def _ax():
    return ctypes.cdll.LoadLibrary(
        "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
    )
