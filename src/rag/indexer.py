from pathlib import Path

from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import chromadb

EMBED_MODEL = "all-MiniLM-L6-v2"
CHROMA_DIR = "./chroma_db"
COLLECTION = "books"
CHUNK_SIZE = 800
OVERLAP = 100


def _get_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


def index_book(file_path: str | Path, book_title: str, gutenberg_id: int) -> int:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    text = path.read_text(encoding="utf-8")
    chunks = _chunk_text(text)

    embedder = SentenceTransformer(EMBED_MODEL)
    embeddings = embedder.encode(chunks, show_progress_bar=True).tolist()

    collection = _get_collection()

    existing = collection.get(where={"book_title": book_title})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    ids = [f"{book_title}::{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "book_title": book_title,
            "chunk_index": i,
            **({"gutenberg_id": gutenberg_id} if gutenberg_id is not None else {}),
        }
        for i in range(len(chunks))
    ]
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )

    print(f"[indexer] '{book_title}' → {len(chunks)} chunks indexados.")
    return len(chunks)


def index_all_books(books_dir: str | Path = "static/books") -> dict[str, int]:
    books_path = Path(books_dir)
    results = {}
    for txt_file in books_path.glob("*.txt"):
        title = txt_file.stem
        results[title] = index_book(txt_file, title, None)
    return results