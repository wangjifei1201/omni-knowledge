"""
Document Chunking Strategy Engine
Provides multiple chunking strategies for splitting document text into chunks.
Strategies: character, paragraph, heading
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger


@dataclass
class ChunkResult:
    """Result of a single chunk"""

    content: str
    chunk_index: int
    token_count: int = 0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.token_count == 0:
            self.token_count = len(self.content)


# ──────────────────────────────────────────────
# Strategy definitions (used by frontend)
# ──────────────────────────────────────────────

STRATEGY_DEFINITIONS = [
    {
        "name": "character",
        "label": "字符拆分",
        "description": "按固定字符数切割文本，适合任意类型文档",
        "params": [
            {
                "key": "chunk_size",
                "label": "分段大小（字符数）",
                "type": "number",
                "default": 3000,
                "min": 1000,
                "max": 10000,
            },
            {
                "key": "overlap",
                "label": "重叠字符数",
                "type": "number",
                "default": 50,
                "min": 0,
                "max": 500,
            },
        ],
    },
    {
        "name": "paragraph",
        "label": "段落拆分",
        "description": "按自然段落分割，保持语义完整性，过长段落自动二次切割",
        "params": [
            {
                "key": "max_paragraph_size",
                "label": "段落最大字符数",
                "type": "number",
                "default": 3000,
                "min": 2000,
                "max": 10000,
            },
            {
                "key": "overlap",
                "label": "重叠字符数",
                "type": "number",
                "default": 50,
                "min": 0,
                "max": 500,
            },
        ],
    },
    {
        "name": "heading",
        "label": "标题拆分",
        "description": "识别标题/章节结构，按章节切分，保持文档结构",
        "params": [
            {
                "key": "max_section_size",
                "label": "章节最大字符数",
                "type": "number",
                "default": 3000,
                "min": 2000,
                "max": 10000,
            },
            {
                "key": "overlap",
                "label": "重叠字符数",
                "type": "number",
                "default": 50,
                "min": 0,
                "max": 500,
            },
        ],
    },
]


# ──────────────────────────────────────────────
# Strategy base class
# ──────────────────────────────────────────────


class ChunkingStrategyBase(ABC):
    """Abstract base for chunking strategies"""

    @abstractmethod
    def chunk(
        self,
        text: str,
        doc_id: str,
        doc_name: str,
        params: dict,
    ) -> list[ChunkResult]:
        """Split text into chunks according to the strategy"""
        ...


# ──────────────────────────────────────────────
# Character chunking
# ──────────────────────────────────────────────


class CharacterChunkingStrategy(ChunkingStrategyBase):
    """Split text by fixed character count with overlap"""

    def chunk(self, text: str, doc_id: str, doc_name: str, params: dict) -> list[ChunkResult]:
        chunk_size = params.get("chunk_size", 500)
        overlap = params.get("overlap", 50)

        if not text or not text.strip():
            return []

        text = text.strip()
        chunks: list[ChunkResult] = []
        start = 0
        idx = 0

        while start < len(text):
            end = start + chunk_size
            content = text[start:end]

            if content.strip():
                chunks.append(ChunkResult(content=content.strip(), chunk_index=idx))
                idx += 1

            # Move forward by (chunk_size - overlap)
            step = max(chunk_size - overlap, 1)
            start += step

        return chunks


# ──────────────────────────────────────────────
# Paragraph chunking
# ──────────────────────────────────────────────


class ParagraphChunkingStrategy(ChunkingStrategyBase):
    """Split text by natural paragraphs, merge short ones, split long ones"""

    # Sentence-ending patterns for Chinese and English
    _SENTENCE_ENDS = re.compile(r'(?<=[。！？.!?])\s*')

    def chunk(self, text: str, doc_id: str, doc_name: str, params: dict) -> list[ChunkResult]:
        max_size = params.get("max_paragraph_size", 1000)
        overlap = params.get("overlap", 50)

        if not text or not text.strip():
            return []

        text = text.strip()
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        chunks: list[ChunkResult] = []
        current = ""
        idx = 0

        for para in paragraphs:
            # If the paragraph itself exceeds max_size, split by sentences
            if len(para) > max_size:
                # Flush current buffer first
                if current:
                    chunks.append(ChunkResult(content=current, chunk_index=idx))
                    idx += 1
                    current = ""

                # Split long paragraph by sentences
                sentence_chunks = self._split_by_sentences(para, max_size, overlap)
                for sc in sentence_chunks:
                    chunks.append(ChunkResult(content=sc, chunk_index=idx))
                    idx += 1
                continue

            # Try to merge with current buffer
            candidate = (current + "\n\n" + para) if current else para
            if len(candidate) <= max_size:
                current = candidate
            else:
                # Current buffer is full, save it
                if current:
                    chunks.append(ChunkResult(content=current, chunk_index=idx))
                    idx += 1

                    # Overlap: take tail of current chunk
                    if overlap > 0 and len(current) > overlap:
                        current = current[-overlap:] + "\n\n" + para
                    else:
                        current = para
                else:
                    current = para

        # Flush remaining
        if current:
            chunks.append(ChunkResult(content=current, chunk_index=idx))

        return chunks

    def _split_by_sentences(self, text: str, max_size: int, overlap: int) -> list[str]:
        """Split a long paragraph by sentence boundaries"""
        sentences = self._SENTENCE_ENDS.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]

        results: list[str] = []
        current = ""

        for sent in sentences:
            candidate = (current + sent) if not current else (current + " " + sent)
            if len(candidate) <= max_size:
                current = candidate
            else:
                if current:
                    results.append(current)
                    # Overlap
                    if overlap > 0 and len(current) > overlap:
                        current = current[-overlap:] + " " + sent
                    else:
                        current = sent
                else:
                    # Single sentence exceeds max_size, force split
                    for i in range(0, len(sent), max_size - overlap):
                        results.append(sent[i : i + max_size])
                    current = ""

        if current:
            results.append(current)

        return results


# ──────────────────────────────────────────────
# Heading chunking
# ──────────────────────────────────────────────


class HeadingChunkingStrategy(ChunkingStrategyBase):
    """Split text by heading/title structure"""

    # Heading patterns ordered by priority
    _HEADING_PATTERNS = [
        # Markdown headings: # Title, ## Title, etc.
        re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE),
        # Numeric headings: 1. Title, 1.2 Title, 1.2.3 Title
        re.compile(r'^(\d+(?:\.\d+)*)[.\s]\s*(.+)$', re.MULTILINE),
        # Chinese ordinal: 一、Title, 二、Title
        re.compile(r'^([一二三四五六七八九十百]+)[、．.]\s*(.+)$', re.MULTILINE),
        # Parenthesized Chinese ordinal: （一）Title
        re.compile(r'^[（(]([一二三四五六七八九十百\d]+)[）)]\s*(.+)$', re.MULTILINE),
    ]

    def chunk(self, text: str, doc_id: str, doc_name: str, params: dict) -> list[ChunkResult]:
        max_size = params.get("max_section_size", 2000)
        overlap = params.get("overlap", 50)

        if not text or not text.strip():
            return []

        text = text.strip()

        # Find all heading positions
        headings = self._find_headings(text)

        if not headings:
            # No headings found, fallback to paragraph strategy
            logger.info("No headings found, falling back to paragraph strategy")
            fallback = ParagraphChunkingStrategy()
            return fallback.chunk(
                text,
                doc_id,
                doc_name,
                {"max_paragraph_size": max_size, "overlap": overlap},
            )

        # Split text into sections by heading positions
        sections = self._split_by_headings(text, headings)

        # Build chunks, splitting oversized sections
        chunks: list[ChunkResult] = []
        idx = 0

        for section_title, section_body in sections:
            full_section = f"{section_title}\n{section_body}" if section_title else section_body
            full_section = full_section.strip()

            if not full_section:
                continue

            if len(full_section) <= max_size:
                chunks.append(
                    ChunkResult(
                        content=full_section,
                        chunk_index=idx,
                        metadata={"heading": section_title},
                    )
                )
                idx += 1
            else:
                # Section too long, split by paragraphs while keeping heading
                sub_chunks = self._split_section(section_title, section_body, max_size, overlap)
                for sc in sub_chunks:
                    chunks.append(
                        ChunkResult(
                            content=sc,
                            chunk_index=idx,
                            metadata={"heading": section_title},
                        )
                    )
                    idx += 1

        return chunks

    def _find_headings(self, text: str) -> list[tuple[int, str]]:
        """Find all heading positions and text. Returns [(position, heading_text), ...]"""
        headings: list[tuple[int, str]] = []
        seen_positions = set()

        for pattern in self._HEADING_PATTERNS:
            for match in pattern.finditer(text):
                pos = match.start()
                if pos not in seen_positions:
                    headings.append((pos, match.group(0).strip()))
                    seen_positions.add(pos)

        # Sort by position
        headings.sort(key=lambda x: x[0])
        return headings

    def _split_by_headings(self, text: str, headings: list[tuple[int, str]]) -> list[tuple[str, str]]:
        """Split text into (heading_title, section_body) pairs"""
        sections: list[tuple[str, str]] = []

        # Content before first heading
        if headings and headings[0][0] > 0:
            pre_content = text[: headings[0][0]].strip()
            if pre_content:
                sections.append(("", pre_content))

        for i, (pos, heading_text) in enumerate(headings):
            # Section body is from end of heading line to start of next heading
            heading_end = pos + len(heading_text)
            # Skip any newline after heading
            while heading_end < len(text) and text[heading_end] in ('\n', '\r'):
                heading_end += 1

            if i + 1 < len(headings):
                body = text[heading_end : headings[i + 1][0]]
            else:
                body = text[heading_end:]

            sections.append((heading_text, body.strip()))

        return sections

    def _split_section(self, title: str, body: str, max_size: int, overlap: int) -> list[str]:
        """Split an oversized section into smaller chunks, preserving the heading"""
        prefix = f"{title}\n" if title else ""
        available = max_size - len(prefix)

        if available <= 0:
            available = max_size

        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
        results: list[str] = []
        current = ""

        for para in paragraphs:
            candidate = (current + "\n\n" + para) if current else para
            if len(candidate) <= available:
                current = candidate
            else:
                if current:
                    results.append(prefix + current)
                    if overlap > 0 and len(current) > overlap:
                        current = current[-overlap:] + "\n\n" + para
                    else:
                        current = para
                else:
                    # Single paragraph exceeds available size
                    for i in range(0, len(para), available - overlap):
                        results.append(prefix + para[i : i + available])
                    current = ""

        if current:
            results.append(prefix + current)

        return results


# ──────────────────────────────────────────────
# Chunking Engine
# ──────────────────────────────────────────────


class ChunkingEngine:
    """Unified chunking engine that dispatches to the appropriate strategy"""

    _strategies: dict[str, ChunkingStrategyBase] = {
        "character": CharacterChunkingStrategy(),
        "paragraph": ParagraphChunkingStrategy(),
        "heading": HeadingChunkingStrategy(),
    }

    def chunk_document(
        self,
        text: str,
        doc_id: str,
        doc_name: str,
        strategy: str = "paragraph",
        params: Optional[dict] = None,
    ) -> list[ChunkResult]:
        """
        Split document text into chunks using the specified strategy.

        Args:
            text: Full document text
            doc_id: Document ID
            doc_name: Document name
            strategy: Strategy name (character/paragraph/heading)
            params: Strategy-specific parameters

        Returns:
            List of ChunkResult
        """
        if params is None:
            params = {}

        impl = self._strategies.get(strategy)
        if impl is None:
            logger.warning(f"Unknown strategy '{strategy}', falling back to paragraph")
            impl = self._strategies["paragraph"]

        logger.info(f"Chunking doc '{doc_name}' with strategy='{strategy}', params={params}")
        chunks = impl.chunk(text, doc_id, doc_name, params)
        logger.info(f"Generated {len(chunks)} chunks for doc '{doc_name}'")
        return chunks

    @staticmethod
    def get_strategy_definitions() -> list[dict]:
        """Return strategy definitions for frontend"""
        return STRATEGY_DEFINITIONS


# Singleton
chunking_engine = ChunkingEngine()
