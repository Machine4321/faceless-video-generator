"""
shadowvault/utils/text_utils.py
Text processing utilities for subtitle chunking and cleanup.
"""

from __future__ import annotations

import re


def clean_text(text: str) -> str:
    """Strip markdown artifacts and collapse whitespace."""
    text = re.sub(r"[\[\]#*`]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_words(text: str, words_per_chunk: int = 4) -> list[str]:
    """
    Split text into chunks of N words each.

    Parameters
    ----------
    text             : the full text to split
    words_per_chunk  : number of words per chunk

    Returns
    -------
    List of text chunks. Last chunk may have fewer words.
    """
    words = text.split()
    if not words:
        return []
    return [
        " ".join(words[i : i + words_per_chunk])
        for i in range(0, len(words), words_per_chunk)
    ]


def strip_json_fences(text: str) -> str:
    """Remove markdown code fences that Gemini sometimes wraps around JSON."""
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```[a-z]*\n?", "", clean)
        clean = re.sub(r"```$", "", clean).strip()
    return clean
