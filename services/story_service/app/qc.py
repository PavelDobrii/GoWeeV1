from __future__ import annotations


def check_quality(text: str, forbidden: list[str]) -> bool:
    words = text.split()
    if not 200 <= len(words) <= 400:
        return False
    lowered = text.lower()
    return not any(word.lower() in lowered for word in forbidden)
