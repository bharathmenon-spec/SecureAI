"""Helpers for detecting token markers and raw PII leakage in model output."""
import re
from typing import List, Tuple

# Sanitized markers placed by the masking service, e.g. [[PERSON_ab12_001]].
TOKEN_MARKER_RE = re.compile(r"\[\[([^\[\]]+)\]\]")

_LEAK_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"\+?\d[\d().\-\s]{7,16}\d"),
    "api_key": re.compile(
        r"\b(?:sk-[A-Za-z0-9\-]{6,}|AKIA[0-9A-Z]{8,}|AIza[0-9A-Za-z\-_]{20,})\b"
    ),
}


def find_token_markers(text: str) -> List[str]:
    """Return the inner labels of every [[...]] marker in the text."""
    return TOKEN_MARKER_RE.findall(text)


def find_pii_leaks(text: str) -> List[dict]:
    """Detect raw PII (email/phone/key) that should never appear unmasked."""
    leaks: List[dict] = []
    for kind, pattern in _LEAK_PATTERNS.items():
        for match in pattern.finditer(text):
            if kind == "phone":
                digits = sum(ch.isdigit() for ch in match.group())
                if not 8 <= digits <= 15:
                    continue
            leaks.append({"type": kind, "value": match.group()})
    return leaks


def scrub_pii(text: str) -> Tuple[str, List[dict]]:
    """Replace any raw PII leak with a generic redaction marker."""
    leaks = find_pii_leaks(text)
    cleaned = text
    for kind, pattern in _LEAK_PATTERNS.items():
        if kind == "phone":
            def _repl(match):
                digits = sum(ch.isdigit() for ch in match.group())
                return "[redacted:phone]" if 8 <= digits <= 15 else match.group()

            cleaned = pattern.sub(_repl, cleaned)
        else:
            cleaned = pattern.sub(f"[redacted:{kind}]", cleaned)
    return cleaned, leaks
