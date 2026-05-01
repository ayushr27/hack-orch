"""Markdown-aware text chunker for the support corpus."""

import re
import uuid
from pathlib import Path


CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

_HEADING_RE = re.compile(r"^#{1,3} .+", re.MULTILINE)


def _split_on_headings(text: str) -> list[str]:
    """Split markdown text at H1/H2/H3 headings, keeping the heading with its section."""
    parts = []
    positions = [m.start() for m in _HEADING_RE.finditer(text)]
    if not positions:
        return [text]
    if positions[0] > 0:
        parts.append(text[: positions[0]])
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        parts.append(text[pos:end])
    return [p for p in parts if p.strip()]


def _split_on_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]


def _split_on_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _build_chunks(sections: list[str], chunk_size: int, overlap: int) -> list[str]:
    """Merge sections into target-sized chunks with overlap."""
    chunks: list[str] = []
    current = ""
    for section in sections:
        if len(current) + len(section) + 1 <= chunk_size:
            current = (current + "\n\n" + section).strip() if current else section
        else:
            if current:
                chunks.append(current)
            overlap_text = current[-overlap:] if len(current) > overlap else current
            current = (overlap_text + "\n\n" + section).strip() if overlap_text else section
    if current:
        chunks.append(current)
    return chunks


def _extract_title(text: str, source_path: str) -> str:
    m = re.search(r"^#{1,3} (.+)", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return Path(source_path).stem.replace("-", " ").replace("_", " ").title()


def chunk_text(text: str, source_path: str, company: str) -> list[dict]:
    """
    Split text into overlapping chunks and return list of chunk dicts.

    Each dict: {id, company, source_path, title, text, char_start, char_end}
    """
    title = _extract_title(text, source_path)
    sections = _split_on_headings(text)

    fine_sections: list[str] = []
    for section in sections:
        if len(section) <= CHUNK_SIZE:
            fine_sections.append(section)
        else:
            paras = _split_on_paragraphs(section)
            for para in paras:
                if len(para) <= CHUNK_SIZE:
                    fine_sections.append(para)
                else:
                    fine_sections.extend(_split_on_sentences(para))

    raw_chunks = _build_chunks(fine_sections, CHUNK_SIZE, CHUNK_OVERLAP)

    result = []
    char_pos = 0
    for chunk_text_content in raw_chunks:
        chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_path}:{char_pos}"))
        start = char_pos
        end = char_pos + len(chunk_text_content)
        result.append(
            {
                "id": chunk_id,
                "company": company,
                "source_path": source_path,
                "title": title,
                "text": chunk_text_content,
                "char_start": start,
                "char_end": end,
            }
        )
        char_pos = end + 1

    return result
