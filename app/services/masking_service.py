"""Masking / tokenization service.

Replaces detected sensitive spans with stable, sanitized markers. Tokenized
values are deterministic within a document scope so the same raw value always
maps to the same token. Raw values are returned for encrypted storage by the
caller - they are never embedded in the sanitized text.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from app.core.constants import ENTITY_TOKEN_TIER, HandlingLabel, SensitivityTier
from app.core.security import short_hash


@dataclass
class TokenEntry:
    token_label: str
    raw_value: str
    entity_type: str
    release_tier: str


@dataclass
class MaskingResult:
    sanitized_text: str
    token_entries: List[TokenEntry] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)


def sanitize(text: str, detections: List[dict], doc_short: str) -> MaskingResult:
    """Apply handling labels to detected spans and return sanitized text."""
    detections = sorted(detections, key=lambda d: d["start"])
    pieces: List[str] = []
    cursor = 0

    counters: Dict[str, int] = {}
    value_to_label: Dict[Tuple[str, str], str] = {}
    entries: Dict[str, TokenEntry] = {}
    stats: Dict[str, int] = {}

    for det in detections:
        start, end = det["start"], det["end"]
        if start < cursor:  # defensive: skip residual overlaps
            continue
        pieces.append(text[cursor:start])

        entity_type = det["entity_type"]
        handling = det["handling"]
        raw = det["text"]
        stats[handling] = stats.get(handling, 0) + 1

        if handling == HandlingLabel.ALLOW.value:
            replacement = raw
        elif handling == HandlingLabel.DROP.value:
            replacement = "[[REMOVED]]"
        elif handling == HandlingLabel.MASK.value:
            replacement = f"[[REDACTED:{entity_type}]]"
        elif handling == HandlingLabel.HASH.value:
            replacement = f"[[HASH:{short_hash(raw, 8)}]]"
        else:  # TOKENIZE
            key = (entity_type, raw.strip().lower())
            label = value_to_label.get(key)
            if label is None:
                counters[entity_type] = counters.get(entity_type, 0) + 1
                label = f"{entity_type}_{doc_short}_{counters[entity_type]:03d}"
                value_to_label[key] = label
                entries[label] = TokenEntry(
                    token_label=label,
                    raw_value=raw,
                    entity_type=entity_type,
                    release_tier=ENTITY_TOKEN_TIER.get(
                        entity_type, SensitivityTier.CONFIDENTIAL.value
                    ),
                )
            replacement = f"[[{label}]]"

        pieces.append(replacement)
        cursor = end

    pieces.append(text[cursor:])
    return MaskingResult(
        sanitized_text="".join(pieces),
        token_entries=list(entries.values()),
        stats=stats,
    )
