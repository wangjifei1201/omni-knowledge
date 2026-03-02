"""
Document parsing service
Handles: PDF, Word, Excel, PPT, images, audio
Pipeline: Upload -> Format detection -> Content extraction -> Quality check -> Smart chunking -> Vectorization -> Storage
"""

from dataclasses import dataclass, field
from enum import Enum


class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    LIST = "list"


@dataclass
class ParsedChunk:
    content: str = ""
    chunk_type: ChunkType = ChunkType.TEXT
    page_number: int = 0
    chapter: str = ""
    section: str = ""
    position: dict = field(default_factory=dict)  # {x, y, w, h}
    metadata: dict = field(default_factory=dict)
    token_count: int = 0


@dataclass
class ParsedDocument:
    doc_id: str = ""
    doc_name: str = ""
    page_count: int = 0
    chapters: list = field(default_factory=list)
    chunks: list[ParsedChunk] = field(default_factory=list)
    tables: list = field(default_factory=list)
    images: list = field(default_factory=list)


class DocumentParser:
    """Semantic-aware document parser"""

    def __init__(self):
        pass

    async def parse(self, file_path: str, file_type: str, doc_id: str) -> ParsedDocument:
        """Parse document based on file type"""
        parsers = {
            "pdf": self._parse_pdf,
            "docx": self._parse_word,
            "doc": self._parse_word,
            "xlsx": self._parse_excel,
            "xls": self._parse_excel,
            "txt": self._parse_text,
            "md": self._parse_text,
            "csv": self._parse_csv,
            "png": self._parse_image,
            "jpg": self._parse_image,
            "jpeg": self._parse_image,
        }

        parser_fn = parsers.get(file_type)
        if not parser_fn:
            raise ValueError(f"Unsupported file type: {file_type}")

        return await parser_fn(file_path, doc_id)

    async def _parse_pdf(self, file_path: str, doc_id: str) -> ParsedDocument:
        """Parse PDF with LlamaParse for best table recognition"""
        # TODO: Integrate LlamaParse for PDF parsing
        # - Extract text with positional info
        # - Detect and parse tables (merged cells handling)
        # - Extract images with OCR
        # - Identify chapter/section structure from headings
        return ParsedDocument(doc_id=doc_id)

    async def _parse_word(self, file_path: str, doc_id: str) -> ParsedDocument:
        """Parse Word documents using python-docx"""
        # TODO: Implement Word parsing
        # - Extract paragraphs with style info (headings, body)
        # - Extract tables preserving structure
        # - Extract embedded images
        return ParsedDocument(doc_id=doc_id)

    async def _parse_excel(self, file_path: str, doc_id: str) -> ParsedDocument:
        """Parse Excel with pandas"""
        # TODO: Implement Excel parsing
        # - Read all sheets
        # - Convert to structured table format
        # - Handle merged cells
        return ParsedDocument(doc_id=doc_id)

    async def _parse_text(self, file_path: str, doc_id: str) -> ParsedDocument:
        """Parse plain text / markdown"""
        # TODO: Implement text/markdown parsing
        return ParsedDocument(doc_id=doc_id)

    async def _parse_csv(self, file_path: str, doc_id: str) -> ParsedDocument:
        """Parse CSV files"""
        # TODO: Implement CSV parsing
        return ParsedDocument(doc_id=doc_id)

    async def _parse_image(self, file_path: str, doc_id: str) -> ParsedDocument:
        """Parse images with PaddleOCR"""
        # TODO: Integrate PaddleOCR
        return ParsedDocument(doc_id=doc_id)

    def smart_chunk(
        self,
        parsed_doc: ParsedDocument,
        max_chunk_size: int = 512,
        overlap: int = 50,
    ) -> list[ParsedChunk]:
        """
        Semantic-aware chunking strategy:
        - Split by chapter/section boundaries first
        - Keep tables as single chunks (don't split)
        - Long tables: whole embedding + row-level splits (with header)
        - Inject metadata into each chunk: {doc_name, chapter, page, chunk_type}
        """
        chunks = []

        for chunk in parsed_doc.chunks:
            if chunk.chunk_type == ChunkType.TABLE:
                # Tables are kept intact
                chunk.metadata.update({
                    "doc_name": parsed_doc.doc_name,
                    "doc_id": parsed_doc.doc_id,
                })
                chunks.append(chunk)
            else:
                # Text chunks: split by semantic boundaries
                text = chunk.content
                if len(text) <= max_chunk_size:
                    chunk.metadata.update({
                        "doc_name": parsed_doc.doc_name,
                        "doc_id": parsed_doc.doc_id,
                    })
                    chunks.append(chunk)
                else:
                    # Split long text preserving sentence boundaries
                    sub_chunks = self._split_by_sentences(
                        text, max_chunk_size, overlap
                    )
                    for sc in sub_chunks:
                        chunks.append(ParsedChunk(
                            content=sc,
                            chunk_type=chunk.chunk_type,
                            page_number=chunk.page_number,
                            chapter=chunk.chapter,
                            section=chunk.section,
                            position=chunk.position,
                            metadata={
                                "doc_name": parsed_doc.doc_name,
                                "doc_id": parsed_doc.doc_id,
                                **chunk.metadata,
                            },
                        ))

        return chunks

    def _split_by_sentences(
        self, text: str, max_size: int, overlap: int
    ) -> list[str]:
        """Split text by sentence boundaries with overlap"""
        import re
        sentences = re.split(r'(?<=[。！？.!?\n])', text)
        sentences = [s for s in sentences if s.strip()]

        chunks = []
        current = ""
        for sent in sentences:
            if len(current) + len(sent) > max_size and current:
                chunks.append(current)
                # Keep overlap
                overlap_text = current[-overlap:] if len(current) > overlap else current
                current = overlap_text + sent
            else:
                current += sent
        if current:
            chunks.append(current)

        return chunks


# Singleton
document_parser = DocumentParser()
