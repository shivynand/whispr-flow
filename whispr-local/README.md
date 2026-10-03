# whispr-local

A local macOS clone of the Wispr Flow loop: hold a key, speak, release, and cleaned text lands in whatever text field is focused.

Audio never leaves the machine. There is no API key. Cleanup is rules, not a cloud model, so it handles fillers, spoken punctuation, "scratch that", short self-corrections, and numbered lists. It will not rewrite a paragraph the way Flow's LLM pass does.

## What you get

- Hold Right Option, speak, release. Text is pasted with Cmd+V.
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

That opens a small dark pill. Drag it anywhere. Click it to start, click again to paste. Right-click for quit and the Accessibility settings shortcut. Position is remembered.

The Hugging Face warning on first launch is only the model download. No account is required. Later launches use the cached model.

## Install once, then forget the terminal

```bash
bash scripts/install_mac.sh
```

That builds `Whispr Local.app`, copies it to `~/Applications`, and starts it at login. The pill is the app. There is no Dock icon.

Paste needs Accessibility or macOS returns error 1002 and the text only lands on the clipboard. Enable **Whispr Local** under System Settings → Privacy & Security → Accessibility, quit the app, and open it again from Applications. Click the pill, speak, click again. It switches back to the app you were typing in (Mail, Slack, the browser) and sends Cmd+V there.

The hotkey is optional. Input Monitoring is only for Right Option. Click-to-talk does not need it.

## Use

1. Click into a text field.
2. Click the pill (or hold Right Option, once the hotkey is trusted) and talk.
3. Click again, or release the key. Text is pasted and also left on the clipboard.

Supported hotkey names: `alt_r`, `alt_l`, `ctrl_r`, `ctrl_l`, `shift_r`, `cmd_r`, `f13`, `f14`, `f15`. Fn is not visible to normal apps.

Try the cleanup pass without a mic:

```bash
python main.py --demo-cleanup "um let's meet at 5 actually 6 period"
```

## Models

`base.en` is the default: fast enough on a laptop CPU, fine for everyday speech. For better names and jargon, switch `model` to `small.en`. `tiny.en` is faster and sloppier.

## Not in this build

Personal dictionary, snippets, and an LLM polish pass. Those are the next layer once hold-to-talk feels solid. A local Ollama pass can sit in front of `paste_text` without sending audio anywhere.
