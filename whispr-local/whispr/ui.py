"""Floating matte bar. Menu-bar item shows or hides it. Stays on every Space."""

from __future__ import annotations

from typing import Callable

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSBackingStoreBuffered,
    NSButton,
    NSColor,
    NSFloatingWindowLevel,
    NSFont,
    NSMakeRect,
    NSMenu,
    NSMenuItem,
    NSPanel,
    NSScreen,
    NSStatusBar,
    NSTextField,
    NSVariableStatusItemLength,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from Foundation import NSObject
from PyObjCTools import AppHelper

from whispr.config import Config


class Delegate(NSObject):
    def initWithOwner_(self, owner):
        self = objc.super(Delegate, self).init()
        if self is None:
            return None
        self.owner = owner
        return self

    def togglePanel_(self, _sender) -> None:
        self.owner.toggle_panel()

    def talk_(self, _sender) -> None:
        self.owner.on_toggle()

    def accessibility_(self, _sender) -> None:
        self.owner.open_privacy_settings("Privacy_Accessibility")

    def inputMonitoring_(self, _sender) -> None:
        self.owner.open_privacy_settings("Privacy_ListenEvent")

    def quit_(self, _sender) -> None:
        self.owner.on_quit()
        NSApplication.sharedApplication().terminate_(None)


class Pill:
    def __init__(
        self,
        on_toggle: Callable[[], None],
        on_quit: Callable[[], None],
        config: Config,
        python_path: str,
    ) -> None:
        self.on_toggle = on_toggle
        self.on_quit = on_quit
        self.config = config
        self.python_path = python_path
        self.app = NSApplication.sharedApplication()
        self.app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        self.delegate = Delegate.alloc().initWithOwner_(self)

        self.status = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self.status.button().setTitle_("Whispr")
        menu = NSMenu.alloc().init()
        for title, action in (
            ("Show / hide", "togglePanel:"),
            ("Start / stop", "talk:"),
            ("Accessibility settings…", "accessibility:"),
            ("Input Monitoring settings…", "inputMonitoring:"),
            ("Quit", "quit:"),
        ):
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, "")
            item.setTarget_(self.delegate)
            menu.addItem_(item)
        self.status.setMenu_(menu)

        width, height = 360, 44
        screen = NSScreen.mainScreen().frame()
        x = config.window_x if config.window_x is not None else (screen.size.width - width) / 2
        y = config.window_y if config.window_y is not None else screen.size.height - 90
        style = NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel
        self.window = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, width, height),
            style,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setLevel_(NSFloatingWindowLevel)
        self.window.setFloatingPanel_(True)
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(0.09, 0.09, 0.1, 0.9))
        self.window.setHidesOnDeactivate_(False)
        self.window.setMovableByWindowBackground_(True)
        self.window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
            | NSWindowCollectionBehaviorStationary
        )
        self.window.setHasShadow_(True)

        self.dot = NSTextField.alloc().initWithFrame_(NSMakeRect(16, 10, 18, 24))
        self.dot.setStringValue_("●")
        self.dot.setBezeled_(False)
        self.dot.setDrawsBackground_(False)
        self.dot.setEditable_(False)
        self.dot.setSelectable_(False)
        self.dot.setFont_(NSFont.systemFontOfSize_(14))
        self.dot.setTextColor_(NSColor.colorWithCalibratedWhite_alpha_(0.55, 1))
        self.window.contentView().addSubview_(self.dot)

        self.label = NSTextField.alloc().initWithFrame_(NSMakeRect(36, 10, 230, 24))
        self.label.setStringValue_("Loading…")
        self.label.setBezeled_(False)
        self.label.setDrawsBackground_(False)
        self.label.setEditable_(False)
        self.label.setSelectable_(False)
        self.label.setFont_(NSFont.systemFontOfSize_(13))
        self.label.setTextColor_(NSColor.colorWithCalibratedWhite_alpha_(0.92, 1))
        self.window.contentView().addSubview_(self.label)

        self.hint = NSTextField.alloc().initWithFrame_(NSMakeRect(250, 12, 96, 20))
        self.hint.setStringValue_("hold space")
        self.hint.setAlignment_(1)
        self.hint.setBezeled_(False)
        self.hint.setDrawsBackground_(False)
        self.hint.setEditable_(False)
        self.hint.setSelectable_(False)
        self.hint.setFont_(NSFont.systemFontOfSize_(11))
        self.hint.setTextColor_(NSColor.colorWithCalibratedWhite_alpha_(0.45, 1))
        self.window.contentView().addSubview_(self.hint)
        self.hit = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))
        self.hit.setTitle_("")
        self.hit.setBordered_(False)
        self.hit.setTransparent_(True)
        self.hit.setTarget_(self.delegate)
        self.hit.setAction_("talk:")
        self.window.contentView().addSubview_(self.hit)

        self.window.contentView().setWantsLayer_(True)
        self.window.orderFrontRegardless()
        AppHelper.callAfter(self._ask_for_microphone)

    def toggle_panel(self) -> None:
        if self.window.isVisible():
            self.window.orderOut_(None)
        else:
            self.window.orderFrontRegardless()

    def open_privacy_settings(self, pane: str) -> None:
        import subprocess

        url = f"x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?{pane}"
        subprocess.Popen(["open", url])

    def set_status(self, state: str, detail: str) -> None:
        AppHelper.callAfter(self._apply, state, detail)

    def _apply(self, state: str, detail: str) -> None:
        self.label.setStringValue_(detail[:52])
        if state == "listening":
            self.dot.setTextColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0.32, 0.28, 1))
            self.hint.setStringValue_("release")
            self.status.button().setTitle_("● Whispr")
        elif state == "transcribing":
            self.dot.setTextColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0.78, 0.35, 1))
            self.hint.setStringValue_("working")
            self.status.button().setTitle_("… Whispr")
        elif state == "error":
            self.dot.setTextColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(1, 0.45, 0.4, 1))
            self.hint.setStringValue_("check Settings")
            self.status.button().setTitle_("Whispr")
        else:
            self.dot.setTextColor_(NSColor.colorWithCalibratedWhite_alpha_(0.55, 1))
            self.hint.setStringValue_("hold space")
            self.status.button().setTitle_("Whispr")
        origin = self.window.frame().origin
        self.config.window_x = int(origin.x)
        self.config.window_y = int(origin.y)
        self.config.save()

    def _ask_for_microphone(self) -> None:
        try:
            import AVFoundation
        except Exception as exc:  # noqa: BLE001
            print(f"[mic] {exc}")
            return
        status = AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_("soun")
        print(f"[mic] authorization status {status}")
        if status == 3:
            return

        def done(granted) -> None:
            print(f"[mic] prompt result granted={granted}")
            if not granted:
                AppHelper.callAfter(self._send_user_to_mic_settings)

        AVFoundation.AVCaptureDevice.requestAccessForMediaType_completionHandler_("soun", done)

    def _send_user_to_mic_settings(self) -> None:
        import subprocess

        subprocess.Popen(
            ["open", "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Microphone"]
        )

    def mainloop(self) -> None:
        AppHelper.runEventLoop()
