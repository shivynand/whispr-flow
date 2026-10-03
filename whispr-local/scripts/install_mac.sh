#!/bin/bash
# One-time setup. After this, launch Whispr Local from Applications. No terminal.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt

bash "$ROOT/scripts/make_app.sh"

mkdir -p "$HOME/Applications"
rm -rf "$HOME/Applications/Whispr Local.app"
cp -R "$ROOT/Whispr Local.app" "$HOME/Applications/Whispr Local.app"

PLIST="$HOME/Library/LaunchAgents/local.whispr.dictation.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>local.whispr.dictation</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/open</string>
    <string>-a</string>
    <string>$HOME/Applications/Whispr Local.app</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
</dict>
</plist>
EOF
launchctl bootout "gui/$(id -u)/local.whispr.dictation" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST" || true

echo
echo "Installed: $HOME/Applications/Whispr Local.app"
echo "It will also start at login."
echo
echo "One permission is still required or it cannot type into Mail, Slack, or a browser:"
echo "  System Settings → Privacy & Security → Accessibility → enable Whispr Local"
echo "Then quit and reopen the app."
open "$HOME/Applications/Whispr Local.app"
open "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Accessibility"
