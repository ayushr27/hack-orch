"""One-time CLI to build the vector index from the corpus.

Usage:
    python -m index.build_index [--force]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Make sure we can import sibling packages when run from code/ dir
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from index.chunker import chunk_text

STORE_DIR = Path(__file__).resolve().parent / "store"
META_PATH = STORE_DIR / "meta.json"
EMBEDDINGS_PATH = STORE_DIR / "embeddings.npy"
CHUNKS_PATH = STORE_DIR / "chunks.jsonl"

TEXT_EXTENSIONS = {".md", ".txt", ".html"}
MIN_CHARS = 100


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str):
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def strip_html(html: str) -> str:
    parser = _HTMLStripper()
    parser.feed(html)
    return parser.get_text()


def _infer_company(path: Path) -> str:
    parts = path.parts
    data_idx = next((i for i, p in enumerate(parts) if p == "data"), None)
    if data_idx is not None and data_idx + 1 < len(parts):
        return parts[data_idx + 1].lower()
    return "unknown"


def _load_text(path: Path) -> str | None:
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
    if path.suffix == ".html":
        raw = strip_html(raw)
    if len(raw.strip()) < MIN_CHARS:
        return None
    return raw


def collect_chunks(data_dir: Path) -> list[dict]:
    chunks: list[dict] = []
    for path in sorted(data_dir.rglob("*")):
        if path.suffix not in TEXT_EXTENSIONS or not path.is_file():
            continue
        text = _load_text(path)
        if text is None:
            continue
        company = _infer_company(path)
        file_chunks = chunk_text(text, str(path), company)
        chunks.extend(file_chunks)
    return chunks


def build_index(force: bool = False) -> None:
    if STORE_DIR.exists() and META_PATH.exists() and not force:
        print("Index already exists. Use --force to rebuild.")
        return

    STORE_DIR.mkdir(parents=True, exist_ok=True)

    data_dir = Path(config.DATA_DIR).resolve()
    if not data_dir.exists():
        # Try relative to script location
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    if not data_dir.exists():
        print(f"ERROR: data directory not found at {data_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Collecting chunks from {data_dir} ...")
    chunks = collect_chunks(data_dir)
    print(f"  {len(chunks)} chunks collected")

    if not chunks:
        print("No chunks found. Check that data/ directory has .md/.txt/.html files.")
        sys.exit(1)

    print(f"Loading embedding model: {config.EMBEDDING_MODEL} ...")
    model = SentenceTransformer(config.EMBEDDING_MODEL)

    texts = [c["text"] for c in chunks]
    print(f"Embedding {len(texts)} chunks in batches of 64 ...")
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    embeddings = embeddings.astype(np.float32)

    np.save(EMBEDDINGS_PATH, embeddings)
    print(f"  saved embeddings: {embeddings.shape} → {EMBEDDINGS_PATH}")

    with open(CHUNKS_PATH, "w") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")
    print(f"  saved chunks → {CHUNKS_PATH}")

    per_company: dict[str, int] = {}
    for c in chunks:
        per_company[c["company"]] = per_company.get(c["company"], 0) + 1

    meta = {
        "total_chunks": len(chunks),
        "per_company_counts": per_company,
        "model_name": config.EMBEDDING_MODEL,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "embeddings_shape": list(embeddings.shape),
    }
    META_PATH.write_text(json.dumps(meta, indent=2))
    print(f"  saved meta → {META_PATH}")

    print("\n=== Index Stats ===")
    print(f"Total chunks : {meta['total_chunks']}")
    for company, count in sorted(per_company.items()):
        print(f"  {company:15s}: {count}")
    print(f"Embedding dim: {embeddings.shape[1]}")
    print(f"Built at     : {meta['built_at']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the support corpus vector index.")
    parser.add_argument("--force", action="store_true", help="Rebuild even if index exists.")
    args = parser.parse_args()
    build_index(force=args.force)
