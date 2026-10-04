# whispr-local

A local macOS dictation app: hold Space, speak, release, and cleaned text lands in the focused text field. It uses a small native macOS pill and keeps microphone capture, Whisper, and text insertion local.

Audio never leaves the machine. There is no API key. Cleanup is rules, not a cloud model, so it handles fillers, spoken punctuation, "scratch that", short self-corrections, and numbered lists. It will not rewrite a paragraph the way Flow's LLM pass does.

## What you get

- Hold Space to start, speak, release to finish. Quick Space taps still type spaces normally.
- Clicking the pill remains available as a fallback.
- The final transcript is inserted when you release Space.
- Transcript is also copied to the clipboard.
- First-run download of a Whisper model, then fully offline.
- Config at `~/Library/Application Support/whispr-local/config.json`.

## Install

Needs Python 3.10+ and PortAudio.

```bash
brew install portaudio
cd whispr-local
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

That opens a small dark pill. Drag it anywhere. Click it to start or stop. Right-click the menu bar item to quit or open permission settings. Hold Space to dictate; the text is pasted after you release the key.

The Hugging Face warning on first launch is only the model download. No account is required. Later launches use the cached model.

## Install once, then forget the terminal

```bash
bash scripts/install_mac.sh
```

That installs the Python dependencies, builds a small `Whispr Local.app`, copies it to `~/Applications`, and starts it at login. The pill is the app. There is no Dock icon.

Microphone access is requested on first use. Global Space listening and auto-paste require Accessibility and Input Monitoring permission. Add **Whispr Local** and the Python executable shown in `~/Library/Logs/whispr-local.log` to both lists in System Settings → Privacy & Security. Use the menu bar item's permission links, then quit and reopen the app. If auto-paste is blocked, the transcript stays on the clipboard so you can paste manually while granting access.

Space hold-to-talk is enabled by default. The old Right Option setting is migrated to Space. Global key listening needs macOS permission; clicking the pill remains available if you do not enable it.

## Use

1. Click into a text field.
2. Hold Space for a moment and talk. Release Space to finish. A quick tap still inserts a normal space.
3. Wait for transcription and paste. The pill can still be clicked to start and stop manually.

Supported hotkey names: `space`, `alt_r`, `alt_l`, `ctrl_r`, `ctrl_l`, `shift_r`, `cmd_r`, `f13`, `f14`, `f15`. Fn is not visible to normal apps.

Try the cleanup pass without a mic:

```bash
python main.py --demo-cleanup "um let's meet at 5 actually 6 period"
```

## Models

`base.en` is the default: fast enough on a laptop CPU, fine for everyday speech. For better names and jargon, switch `model` to `small.en`. `tiny.en` is faster and sloppier.

## Not in this build

Personal dictionary, snippets, and an LLM polish pass. Those are the next layer once hold-to-talk feels solid. A local Ollama pass can sit in front of `paste_text` without sending audio anywhere.
