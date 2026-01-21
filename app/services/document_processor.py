"""Document processing for text extraction and chunking."""

import hashlib
from io import BytesIO
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

from app.logging_config import get_logger

logger = get_logger("document_processor")


class DocumentProcessor:
    """Process documents into chunks for vector storage.

    Supports PDF, DOCX, and TXT files. Splits text into overlapping
    chunks for better retrieval.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_file(self, file_path: Path | str, content: bytes | None = None) -> list[dict]:
        """Process a file and return chunks with metadata.

        Args:
            file_path: Path to file (used for extension detection and naming)
            content: File content bytes (if None, reads from file_path)

        Returns:
            List of chunk dictionaries with doc_id, text, and metadata
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        if content is None:
            content = file_path.read_bytes()

        logger.debug("Processing file", extra={"doc_filename": file_path.name, "size": len(content)})

        if suffix == ".pdf":
            text = self._extract_pdf(content)
        elif suffix == ".docx":
            text = self._extract_docx(content)
        elif suffix == ".txt":
            text = self._extract_txt(content)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

        chunks = self._chunk_text(text)

        logger.info(
            "File processed",
            extra={"doc_filename": file_path.name, "chunks": len(chunks)},
        )

        return [
            {
                "doc_id": self._generate_chunk_id(file_path.name, i),
                "text": chunk,
                "metadata": {
                    "source": file_path.name,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            }
            for i, chunk in enumerate(chunks)
        ]

    def _extract_pdf(self, content: bytes) -> str:
        """Extract text from PDF."""
        reader = PdfReader(BytesIO(content))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n\n".join(text_parts)

    def _extract_docx(self, content: bytes) -> str:
        """Extract text from DOCX."""
        doc = DocxDocument(BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)

    def _extract_txt(self, content: bytes) -> str:
        """Extract text from TXT with encoding fallback."""
        # Try UTF-8 first, fall back to latin-1 which accepts any byte
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning("UTF-8 decode failed, falling back to latin-1")
            return content.decode("latin-1")

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        if not text.strip():
            return []

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < text_len:
                for sep in [". ", ".\n", "\n\n"]:
                    last_sep = text.rfind(sep, start + self.chunk_size // 2, end)
                    if last_sep != -1:
                        end = last_sep + len(sep)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.chunk_overlap

        return chunks

    def _generate_chunk_id(self, filename: str, chunk_index: int) -> str:
        """Generate unique ID for a chunk using SHA256."""
        content = f"{filename}_{chunk_index}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
