"""Rule-based cleanup so dictation reads like writing, with no network call.

This is the local stand-in for Wispr Flow's polish pass. It will not match a
cloud LLM, but it covers the cases that make raw Whisper output feel unfinished:
fillers, spoken punctuation, scratch-that, and short self-corrections.
"""

from __future__ import annotations

import re

_FILLER = re.compile(
    r"\b(?:u+m+|u+h+|e+r+m*|a+h+|h+m+|hmm+)\b"
    r"|\b(?:you know|i mean|sort of|kind of)\b",
    re.IGNORECASE,
)

_SPOKEN = [
    (re.compile(r"\bnew paragraph\b", re.I), "\n\n"),
    (re.compile(r"\bnew line\b", re.I), "\n"),
    (re.compile(r"\bquestion mark\b", re.I), "?"),
    (re.compile(r"\bexclamation (?:point|mark)\b", re.I), "!"),
    (re.compile(r"\b(?:period|full stop)\b", re.I), "."),
    (re.compile(r"\bcomma\b", re.I), ","),
    (re.compile(r"\bcolon\b", re.I), ":"),
    (re.compile(r"\bsemicolon\b", re.I), ";"),
    (re.compile(r"\b(?:dash|hyphen)\b", re.I), " - "),
    (re.compile(r"\bopen quote\b", re.I), ' "'),
    (re.compile(r"\bclose quote\b", re.I), '" '),
]

_NUMBER_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
}

# "meet at 5, actually 6" -> "meet at 6". One token, so we don't swallow the sentence.
_CORRECTION = re.compile(
    r"\b[\w']+\s*,?\s+(?:actually|no wait|wait no|i mean|sorry)\s+([\w']+)\b",
    re.IGNORECASE,
)

_SCRATCH = re.compile(
    r"(?:^|(?<=[.!?]\s)|(?<=\n))[^.!?\n]*?\bscratch that\b",
    re.IGNORECASE,
)


def clean(text: str, final: bool = True) -> str:
    """Turn a raw transcript into text you can send."""
    if not text or not text.strip():
        return ""

    out = text.strip()
    out = _SCRATCH.sub("", out)
    out = _apply_spoken_punctuation(out)
    out = _FILLER.sub(" ", out)
    out = _apply_corrections(out)
    out = _format_lists(out)
    out = _tidy(out)
    out = _capitalize(out, final=final)
    return out.strip()


def _apply_spoken_punctuation(text: str) -> str:
    out = text
    for pattern, replacement in _SPOKEN:
        out = pattern.sub(replacement, out)
    return out


def _apply_corrections(text: str) -> str:
    """Drop the span before a spoken correction and keep the replacement.

    "let's meet at 5 actually 6" -> "let's meet at 6"
    Runs a few passes so stacked corrections collapse.
    """
    out = text
    for _ in range(4):
        updated = _CORRECTION.sub(lambda m: m.group(1), out)
        if updated == out:
            break
        out = updated
    return out


def _format_lists(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        word = match.group(1).lower()
        number = _NUMBER_WORDS.get(word, word)
        return f"\n{number}. "

    out = re.sub(
        r"\b(?:number|item)\s+(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\b",
        repl,
        text,
        flags=re.IGNORECASE,
    )
    return out


def _tidy(text: str) -> str:
    out = text
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r" *\n *", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = re.sub(r"\s+([,.;:?!])", r"\1", out)
    out = re.sub(r"([,.;:?!])(?=[^\s\n\"'])", r"\1 ", out)
    out = re.sub(r"\(\s+", "(", out)
    out = re.sub(r"\s+\)", ")", out)
    out = re.sub(r'\"\s+', '"', out)
    out = re.sub(r"\s+\"", '"', out)
    # A spoken "period" already inserted a dot. Don't stack another one later.
    out = re.sub(r"([.!?])\s*[.!?]+", r"\1", out)
    return out.strip()


def _capitalize(text: str, final: bool = True) -> str:
    if not text:
        return text

    def cap_line(line: str) -> str:
        line = line.strip()
        if not line:
            return ""

        def repl(match: re.Match[str]) -> str:
            return match.group(1) + match.group(2).upper()

        line = line[0].upper() + line[1:]
        line = re.sub(r"([.!?]\s+)([a-z])", repl, line)
        return line

    lines = [_capitalize_list_item(part) if re.match(r"\d+\.\s", part) else cap_line(part) for part in text.split("\n")]
    out = "\n".join(lines).strip()
    if final and out and out[-1] not in ".!?\"'":
        out += "."
    return out


def _capitalize_list_item(item: str) -> str:
    match = re.match(r"(\d+\.\s*)(.*)", item.strip())
    if not match:
        return item.strip()
    body = match.group(2)
    if body:
        body = body[0].upper() + body[1:]
    return f"{match.group(1)}{body}"
