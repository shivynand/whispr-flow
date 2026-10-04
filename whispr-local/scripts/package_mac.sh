#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Python backend is not installed. Run scripts/install_mac.sh first."
  exit 1
fi
npm run build
ARCH="$(uname -m)"
case "$ARCH" in
  arm64|x86_64) ;;
  *) echo "Unsupported Mac architecture: $ARCH"; exit 1 ;;
esac
WHISPR_ARCH="$ARCH" node scripts/package_mac.mjs
APP="$ROOT/release/Whispr Local-darwin-$ARCH/Whispr Local.app"
mkdir -p "$ROOT/Whispr Local.app"
rm -rf "$ROOT/Whispr Local.app"
cp -R "$APP" "$ROOT/Whispr Local.app"
codesign --force --deep --sign - "$ROOT/Whispr Local.app"
echo "Built $ROOT/Whispr Local.app"
