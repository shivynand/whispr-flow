#!/bin/bash
ROOT="$(cd "$(dirname "$0")/../Resources" && pwd)"
SUPPORT="$HOME/Library/Application Support/whispr-local"
LOG="$HOME/Library/Logs/whispr-local.log"
PREFIX="$SUPPORT/cpython"
STOCK="$PREFIX/python/bin/python3"
VENV="$SUPPORT/venv"
mkdir -p "$SUPPORT" "$(dirname "$LOG")"
echo "---- launch $(date) ----" >> "$LOG"

/usr/bin/osascript -e 'display dialog "Whispr Local is setting up. The first launch can take a few minutes. Click OK and leave it alone until the bar appears." buttons {"OK"} default button 1 giving up after 3' >/dev/null 2>&1 || true

fail() {
  echo "FAIL: $1" >> "$LOG"
  /usr/bin/osascript -e "display alert \"Whispr Local did not open\" message \"$1\"" || echo "$1"
  exit 1
}

arch="$(uname -m)"
case "$arch" in
  arm64) asset="cpython-3.10.22+20261001-aarch64-apple-darwin-install_only.tar.gz" ;;
  *) asset="cpython-3.10.22+20261001-x86_64-apple-darwin-install_only.tar.gz" ;;
esac
url="https://github.com/astral-sh/python-build-standalone/releases/download/20261001/${asset}"

if ! "$STOCK" -V >> "$LOG" 2>&1; then
  work="$(mktemp -d)"
  echo "downloading $url" >> "$LOG"
  curl -L --fail --retry 3 -o "$work/python.tar.gz" "$url" >> "$LOG" 2>&1 || fail "Could not download Python. Check the network, then open the app again."
  rm -rf "$PREFIX"
  mkdir -p "$PREFIX"
  tar -xzf "$work/python.tar.gz" -C "$PREFIX" >> "$LOG" 2>&1 || fail "Could not unpack Python."
  rm -rf "$work" "$VENV"
  chmod 755 "$STOCK" || fail "Python was downloaded but the interpreter is missing."
  "$STOCK" -V >> "$LOG" 2>&1 || fail "The private Python does not start. See ~/Library/Logs/whispr-local.log"
fi

if [[ ! -x "$VENV/bin/python" ]] || ! "$VENV/bin/python" -c "import ApplicationServices" >> "$LOG" 2>&1; then
  "$STOCK" -m venv "$VENV" >> "$LOG" 2>&1 || true
  "$VENV/bin/python" -m pip install -r "$ROOT/requirements.txt" >> "$LOG" 2>&1 || fail "Could not install the dictation libraries. See ~/Library/Logs/whispr-local.log"
fi

cd "$ROOT" || fail "App resources are missing."
SITE="$(echo "$VENV"/lib/python3.*/site-packages)"
export PYTHONPATH="$SITE${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONNOUSERSITE=1
echo "starting $STOCK" >> "$LOG"
"$STOCK" "$ROOT/main.py" >> "$LOG" 2>&1
status=$?
if [[ "$status" != "0" ]]; then
  fail "The window closed with status $status. See ~/Library/Logs/whispr-local.log"
fi
