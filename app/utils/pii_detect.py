"""Local sensitive-data detection: regex rules, NER, and dictionary matching."""
import re
from typing import List, Optional

from app.core.config import get_settings
from app.core.constants import ENTITY_HANDLING, EntityType
from app.core.logger import get_logger

logger = get_logger(__name__)

# Lower number = higher priority when spans overlap.
_PRIORITY = {
    EntityType.API_KEY.value: 0,
    EntityType.CONTRACT_NUMBER.value: 1,
    EntityType.ACCOUNT_NUMBER.value: 2,
    EntityType.EMP_ID.value: 3,
    EntityType.CUSTOMER_ID.value: 3,
    EntityType.EMAIL.value: 4,
    EntityType.FINANCIAL_FIGURE.value: 5,
    EntityType.PHONE.value: 6,
    EntityType.PROJECT_NAME.value: 7,
    EntityType.CONFIDENTIAL_PHRASE.value: 8,
    EntityType.PERSON.value: 9,
}

_REGEX_RULES = [
    (EntityType.EMAIL.value,
     re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    (EntityType.API_KEY.value,
     re.compile(r"\b(?:sk-[A-Za-z0-9\-]{6,}|AKIA[0-9A-Z]{8,}|AIza[0-9A-Za-z\-_]{20,}"
                r"|ghp_[A-Za-z0-9]{20,}|xox[bp]-[A-Za-z0-9\-]{10,})\b")),
    (EntityType.EMP_ID.value, re.compile(r"\bEMP[-_]?\d{3,}\b", re.IGNORECASE)),
    (EntityType.CUSTOMER_ID.value,
     re.compile(r"\b(?:CUST|CUSTOMER)[-_]?\d{3,}\b", re.IGNORECASE)),
    (EntityType.CONTRACT_NUMBER.value,
     re.compile(r"\b(?:CTR|CONTRACT)[-_][0-9][0-9\-_]{2,}[0-9]\b", re.IGNORECASE)),
    (EntityType.ACCOUNT_NUMBER.value,
     re.compile(r"\b(?:ACCT|ACCOUNT)[-_]?\d{4,}\b", re.IGNORECASE)),
    (EntityType.FINANCIAL_FIGURE.value,
     re.compile(r"(?:USD|INR|EUR|GBP|\$|₹|€|£)\s?\d[\d,]*(?:\.\d+)?"
                r"|\b\d[\d,]*(?:\.\d+)?\s?(?:USD|INR|EUR|dollars|rupees)\b")),
    (EntityType.PROJECT_NAME.value,
     re.compile(r"\bProject\s+[A-Z][A-Za-z0-9]+\b")),
]

_PHONE_RE = re.compile(r"\+?\d[\d().\-\s]{7,16}\d")

_CONFIDENTIAL_PHRASES = [
    "strictly confidential",
    "company confidential",
    "internal only",
    "do not distribute",
    "do not share",
    "not for distribution",
    "trade secret",
    "confidential",
]

_spacy_nlp = None
_spacy_loaded = False


def _get_spacy():
    global _spacy_nlp, _spacy_loaded
    if _spacy_loaded:
        return _spacy_nlp
    _spacy_loaded = True
    try:
        import spacy

        _spacy_nlp = spacy.load(
            get_settings().spacy_model, disable=["lemmatizer", "tagger", "parser"]
        )
        logger.info("spaCy NER model loaded")
    except Exception as exc:
        logger.warning(
            "spaCy model unavailable (%s); using regex name fallback only", exc
        )
        _spacy_nlp = None
    return _spacy_nlp


# Capitalized two-word name regex. Always run alongside NER - spaCy's small
# model misses names, and for a privacy-first system over-masking is safer
# than leaking an undetected name.
_NAME_FALLBACK_RE = re.compile(r"\b[A-Z][a-z]{1,}\s[A-Z][a-z]{1,}\b")
_NAME_STOPWORDS = {"Project", "Internal", "Confidential", "Employee", "Service"}


def _make(start: int, end: int, text: str, entity_type: str, detector: str) -> dict:
    return {
        "start": start,
        "end": end,
        "text": text,
        "entity_type": entity_type,
        "handling": ENTITY_HANDLING.get(entity_type, "MASK"),
        "detector": detector,
    }


def _detect_persons(text: str) -> List[dict]:
    """Detect person names via NER and a capitalized-name regex.

    Both passes always run; overlapping duplicates are merged later by
    ``_resolve_overlaps``. This guards against names the small NER model
    misses (it does not catch every name).
    """
    spans: List[dict] = []

    nlp = _get_spacy()
    if nlp is not None:
        try:
            for ent in nlp(text).ents:
                if ent.label_ == "PERSON" and len(ent.text.strip()) > 2:
                    spans.append(
                        _make(ent.start_char, ent.end_char, ent.text,
                              EntityType.PERSON.value, "ner")
                    )
        except Exception as exc:
            logger.warning("NER pass failed (%s); using regex only", exc)

    for match in _NAME_FALLBACK_RE.finditer(text):
        if match.group().split()[0] in _NAME_STOPWORDS:
            continue
        spans.append(
            _make(match.start(), match.end(), match.group(),
                  EntityType.PERSON.value, "regex-name")
        )
    return spans


def _detect_phrases(text: str) -> List[dict]:
    spans: List[dict] = []
    lower = text.lower()
    for phrase in _CONFIDENTIAL_PHRASES:
        start = 0
        while True:
            idx = lower.find(phrase, start)
            if idx == -1:
                break
            spans.append(
                _make(idx, idx + len(phrase), text[idx:idx + len(phrase)],
                      EntityType.CONFIDENTIAL_PHRASE.value, "dictionary")
            )
            start = idx + len(phrase)
    return spans


def _resolve_overlaps(spans: List[dict]) -> List[dict]:
    """Greedily keep the highest-priority, longest spans; drop overlaps."""
    ranked = sorted(
        spans,
        key=lambda s: (_PRIORITY.get(s["entity_type"], 99),
                       -(s["end"] - s["start"])),
    )
    accepted: List[dict] = []
    for span in ranked:
        if any(span["start"] < a["end"] and a["start"] < span["end"]
               for a in accepted):
            continue
        accepted.append(span)
    return sorted(accepted, key=lambda s: s["start"])


def detect_entities(text: str, project_names: Optional[List[str]] = None) -> List[dict]:
    """Return non-overlapping sensitive spans sorted by position."""
    spans: List[dict] = []

    for entity_type, pattern in _REGEX_RULES:
        for match in pattern.finditer(text):
            spans.append(
                _make(match.start(), match.end(), match.group(),
                      entity_type, "regex")
            )

    for match in _PHONE_RE.finditer(text):
        digits = sum(ch.isdigit() for ch in match.group())
        if 8 <= digits <= 15:
            spans.append(
                _make(match.start(), match.end(), match.group(),
                      EntityType.PHONE.value, "regex")
            )

    for name in project_names or []:
        for match in re.finditer(re.escape(name), text):
            spans.append(
                _make(match.start(), match.end(), match.group(),
                      EntityType.PROJECT_NAME.value, "dictionary")
            )

    spans.extend(_detect_phrases(text))
    spans.extend(_detect_persons(text))
    return _resolve_overlaps(spans)
