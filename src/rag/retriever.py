from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import chromadb

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
        book_title: str | None = None,
        top_k: int = 6,
) -> list[str]:
    embedder = _get_embedder()
    query_embedding = embedder.encode([query]).tolist()

    collection = _get_collection()

    where_filter = {"book_title": book_title} if book_title else None

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where=where_filter,
        include=["documents", "distances"],
    )

    docs = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]

    filtered = [
        doc for doc, dist in zip(docs, distances)
        if dist <= 0.6 and doc and doc.strip()
    ]

    return filtered or docs