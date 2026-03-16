from typing import Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from chromadb import Where

from src.rag.indexer import CHROMA_DIR, COLLECTION, EMBED_MODEL

_embedder: SentenceTransformer | None = None


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def _get_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve_chunks(
        query: str,
        gutenberg_id: int,
        top_k: int = 6,
) -> list[dict[str, Any]]:
    embedder = _get_embedder()
    query_embedding = embedder.encode([query]).tolist()

    collection = _get_collection()

    where_filter: Where | None = (
        {"gutenberg_id": {"$eq": gutenberg_id}} if gutenberg_id else None
    )
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )
    
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    ids = results.get("ids", [[]])[0]

    rows: list[dict[str, Any]] = []

    for idx, (doc, meta, dist, chunk_id) in enumerate(zip(docs, metas, distances, ids), start=1):
        if not doc or not str(doc).strip():
            continue

        meta = meta or {}
        distance = float(dist) if dist is not None else None
        score = None if distance is None else max(0.0, 1.0 - distance)

        rows.append(
            {
                "text": doc,
                "chunk_id": chunk_id,
                "chunk_index": meta.get("chunk_index"),
                "rank": idx,
                "book_title": meta.get("book_title"),
                "location": (
                    f"chunk_{meta.get('chunk_index')}"
                    if meta.get("chunk_index") is not None
                    else None
                ),
                "score": score,
                "distance": distance,
            }
        )

    filtered = [
        row for row in rows
        if row.get("distance") is not None and row["distance"] <= 0.6
    ]

    return filtered or rows