#!/bin/bash
# Build a small macOS app wrapper around the local Python backend.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/Whispr Local.app"
PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "No venv yet. Run scripts/install_mac.sh first."
  exit 1
fi

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
cat > "$APP/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Whispr Local</string>
  <key>CFBundleDisplayName</key><string>Whispr Local</string>
  <key>CFBundleIdentifier</key><string>local.whispr.dictation</string>
  <key>CFBundleVersion</key><string>0.3.0</string>
  <key>CFBundleShortVersionString</key><string>0.3.0</string>
  <key>CFBundleExecutable</key><string>whispr-local</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSUIElement</key><true/>
  <key>NSMicrophoneUsageDescription</key>
  <string>Whispr Local uses the microphone to dictate into the focused app.</string>
  <key>NSAppleEventsUsageDescription</key>
  <string>Whispr Local pastes dictated text into the focused app.</string>
  <key>WhisprProjectRoot</key><string>$ROOT</string>
  <key>WhisprPython</key><string>$PYTHON</string>
  <key>WhisprMainScript</key><string>$ROOT/main.py</string>
</dict>
</plist>
EOF

xcrun clang -framework Foundation -O2 "$ROOT/scripts/launcher.m" \
  -o "$APP/Contents/MacOS/whispr-local"
codesign --force --deep --sign - "$APP"
echo "Built $APP"
