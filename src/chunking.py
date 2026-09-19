from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    # Lookbehind keeps the terminator attached to the sentence it ends;
    # splitting on [.!?]\s+ would swallow it and leave every chunk truncated.
    _SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        sentences = [s.strip() for s in self._SENTENCE_BOUNDARY.split(text)]
        sentences = [s for s in sentences if s]

        step = self.max_sentences_per_chunk
        return [
            " ".join(sentences[start : start + step])
            for start in range(0, len(sentences), step)
        ]


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return [c for c in self._split(text, self.separators) if c.strip()]

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if not current_text:
            return []
        if len(current_text) <= self.chunk_size:
            return [current_text]

        # Out of separators (or asked to split on ""): nothing left but a hard cut.
        if not remaining_separators or remaining_separators[0] == "":
            return [
                current_text[i : i + self.chunk_size]
                for i in range(0, len(current_text), self.chunk_size)
            ]

        separator, rest = remaining_separators[0], remaining_separators[1:]
        chunks: list[str] = []
        buffer = ""

        for piece in current_text.split(separator):
            candidate = f"{buffer}{separator}{piece}" if buffer else piece

            # Merge upward: keep absorbing neighbours while they still fit.
            if len(candidate) <= self.chunk_size:
                buffer = candidate
                continue

            if buffer:
                chunks.append(buffer)
                buffer = ""

            if len(piece) <= self.chunk_size:
                buffer = piece
            else:
                # Recurse downward: this piece needs a finer separator.
                chunks.extend(self._split(piece, rest))

        if buffer:
            chunks.append(buffer)
        return chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    norm_a = math.sqrt(_dot(vec_a, vec_a))
    norm_b = math.sqrt(_dot(vec_b, vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return _dot(vec_a, vec_b) / (norm_a * norm_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results.

    compare() returns one entry per strategy:
        {"fixed_size": {...}, "by_sentences": {...}, "recursive": {...}}
    where each entry holds "count", "avg_length" and "chunks".
    """

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        # Overlap is scaled to chunk_size rather than left at the class default,
        # so a small chunk_size cannot produce a zero or negative stride.
        results = {
            "fixed_size": FixedSizeChunker(
                chunk_size=chunk_size, overlap=chunk_size // 10
            ).chunk(text),
            "by_sentences": SentenceChunker().chunk(text),
            "recursive": RecursiveChunker(chunk_size=chunk_size).chunk(text),
        }

        comparison = {}
        for name, chunks in results.items():
            count = len(chunks)
            comparison[name] = {
                "count": count,
                "avg_length": sum(len(c) for c in chunks) / count if count else 0.0,
                "chunks": chunks,
            }
        return comparison
