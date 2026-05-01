"""Stage 2: Retrieval — cosine similarity search over pre-built index."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

_STORE_DIR_DEFAULT = Path(__file__).resolve().parent.parent / "index" / "store"


class Retriever:
    def __init__(self, store_dir: Path | None = None):
        if store_dir is None:
            store_dir = _STORE_DIR_DEFAULT
        store_dir = Path(store_dir)

        embeddings_path = store_dir / "embeddings.npy"
        chunks_path = store_dir / "chunks.jsonl"

        if not embeddings_path.exists():
            raise FileNotFoundError(
                f"Index not found at {store_dir}. Run: python -m index.build_index"
            )

        self._embeddings = np.load(embeddings_path)  # shape [N, D]
        with open(chunks_path) as f:
            self._chunks = [json.loads(line) for line in f]

        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(
            config.EMBEDDING_MODEL,
            local_files_only=True,  # use cached model, never try to reach HuggingFace
        )

    def search(self, query: str, company: str | None, k: int = 5) -> list[dict]:
        """Return top-k chunks sorted by cosine similarity (descending)."""
        query_emb = self._model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        )[0].astype(np.float32)

        if company:
            indices = [i for i, c in enumerate(self._chunks) if c["company"] == company.lower()]
        else:
            indices = list(range(len(self._chunks)))

        if not indices:
            return []

        subset = self._embeddings[indices]
        scores = subset @ query_emb  # cosine similarity (both normalized)

        top_local = np.argsort(scores)[::-1][: k]
        results = []
        for local_idx in top_local:
            global_idx = indices[local_idx]
            chunk = dict(self._chunks[global_idx])
            chunk["score"] = float(scores[local_idx])
            results.append(chunk)

        return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--company", default=None)
    args = parser.parse_args()

    retriever = Retriever()
    results = retriever.search(args.query, args.company, k=3)
    print(f"Top {len(results)} results for query={args.query!r} company={args.company!r}\n")
    for i, r in enumerate(results, 1):
        print(f"[{i}] score={r['score']:.4f}  title={r['title']!r}  source={r['source_path']}")
        print(f"     {r['text'][:200]}...")
        print()
