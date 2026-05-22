"""Sentence splitting, windowed chunking, and keyword helpers."""
import re
from typing import List, Set

STOPWORDS: Set[str] = {
    "the", "a", "an", "and", "or", "but", "if", "then", "of", "to", "in", "on",
    "for", "with", "as", "is", "are", "was", "were", "be", "been", "by", "at",
    "this", "that", "these", "those", "it", "its", "from", "into", "about",
    "what", "which", "who", "how", "why", "when", "where", "can", "could",
    "would", "should", "will", "shall", "do", "does", "did", "has", "have",
    "had", "i", "you", "we", "they", "he", "she", "their", "our", "your",
}

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[A-Za-z0-9_]+")


def split_sentences(text: str) -> List[str]:
    sentences: List[str] = []
    for block in text.split("\n"):
        block = block.strip()
        if not block:
            continue
        for sentence in _SENTENCE_RE.split(block):
            sentence = sentence.strip()
            if sentence:
                sentences.append(sentence)
    return sentences


def word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[dict]:
    """Split text into sentence-aware overlapping windows.

    Returns dicts of {text, token_count}. token_count is an approximate word
    count used purely for retrieval-side budgeting.
    """
    sentences = split_sentences(text)
    if not sentences:
        return []

    chunks: List[dict] = []
    current: List[str] = []
    current_words = 0

    for sentence in sentences:
        words = word_count(sentence)
        if current and current_words + words > chunk_size:
            body = " ".join(current)
            chunks.append({"text": body, "token_count": current_words})
            carry: List[str] = []
            carried = 0
            for prev in reversed(current):
                carried += word_count(prev)
                carry.insert(0, prev)
                if carried >= overlap:
                    break
            current = carry
            current_words = sum(word_count(s) for s in current)
        current.append(sentence)
        current_words += words

    if current:
        chunks.append({"text": " ".join(current), "token_count": current_words})
    return chunks


def keyword_set(text: str) -> Set[str]:
    return {
        word
        for word in _WORD_RE.findall(text.lower())
        if word not in STOPWORDS and len(word) > 2
    }


def keyword_overlap(query: str, text: str) -> float:
    """Fraction of query keywords present in ``text`` (0.0 - 1.0)."""
    query_words = keyword_set(query)
    if not query_words:
        return 0.0
    return len(query_words & keyword_set(text)) / len(query_words)
