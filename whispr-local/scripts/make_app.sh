#!/bin/bash
# Build a tiny app bundle so macOS can grant permissions to "Whispr Local"
# instead of a random venv Python. Run this from the project on your Mac.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/Whispr Local.app"
PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "No venv yet. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"

cat > "$APP/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>Whispr Local</string>
  <key>CFBundleDisplayName</key>
  <string>Whispr Local</string>
  <key>CFBundleIdentifier</key>
  <string>local.whispr.dictation</string>
  <key>CFBundleVersion</key>
  <string>0.2.0</string>
  <key>CFBundleShortVersionString</key>
  <string>0.2.0</string>
  <key>CFBundleExecutable</key>
  <string>whispr-local</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>LSUIElement</key>
  <true/>
  <key>NSMicrophoneUsageDescription</key>
  <string>Whispr Local uses the microphone to dictate into the focused app.</string>
  <key>NSAppleEventsUsageDescription</key>
  <string>Whispr Local pastes dictated text into the focused app.</string>
</dict>
</plist>
EOF

cat > "$APP/Contents/MacOS/whispr-local" << EOF
#!/bin/bash
cd "$ROOT"
exec "$PYTHON" "$ROOT/main.py"
EOF
chmod +x "$APP/Contents/MacOS/whispr-local"

echo "Built: $APP"
echo "Open it with: open \"$APP\""
echo "Then add Whispr Local (and, if paste fails, $PYTHON) in Accessibility and Input Monitoring."
