"""
Smart Chunker Module
--------------------
Enforces character and boundary rules on extracted chunks while preserving
tabular row structure and document metadata.
Tabular chunks are kept intact to avoid losing column-row context.
"""

from typing import List
from src.parsers.base_parser import NormalizedChunk
from config import TEXT_CHUNK_SIZE_CHARS, TEXT_CHUNK_OVERLAP_CHARS

class SmartChunker:
    """Smart document chunking manager."""

    def __init__(self, max_chars: int = TEXT_CHUNK_SIZE_CHARS, overlap_chars: int = TEXT_CHUNK_OVERLAP_CHARS):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def process_chunks(self, raw_chunks: List[NormalizedChunk]) -> List[NormalizedChunk]:
        """
        Processes and validates chunk lengths, sub-splitting large text blocks
        while preserving structured table records.
        """
        final_chunks: List[NormalizedChunk] = []

        for chunk in raw_chunks:
            # Preserve tabular chunks and short slide chunks intact to protect row context
            if len(chunk.text) <= self.max_chars or chunk.metadata.get("section_type") == "tabular_data":
                final_chunks.append(chunk)
            else:
                # Sub-split long text blocks with overlap if necessary
                sub_texts = self._split_text(chunk.text)
                for idx, sub_text in enumerate(sub_texts):
                    meta = chunk.metadata.copy()
                    meta["sub_chunk_index"] = idx
                    final_chunks.append(NormalizedChunk(text=sub_text, metadata=meta))

        return final_chunks

    def _split_text(self, text: str) -> List[str]:
        """Sliding window text splitter with character overlap."""
        sub_texts = []
        start = 0
        text_len = len(text)
        while start < text_len:
            end = min(start + self.max_chars, text_len)
            sub_texts.append(text[start:end])
            if end == text_len:
                break
            start += (self.max_chars - self.overlap_chars)
        return sub_texts
