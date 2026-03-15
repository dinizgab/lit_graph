import argparse
from pathlib import Path

from src.rag.gutenberg import  download_all, BOOKS_DIR, GUTENBERG_IDS
from src.rag.indexer import index_book


def load_ids_from_file(path: str) -> list[int]:
    lines = Path(path).read_text().splitlines()
    return [int(l.strip()) for l in lines if l.strip().isdigit()]


def main():
    parser = argparse.ArgumentParser(
        description="Baixa livros do Gutenberg e indexa no ChromaDB."
    )
    source = parser.add_mutually_exclusive_group(required=False)
    source.add_argument("--ids", nargs="+", type=int, help="IDs numéricos do Gutenberg (sobrescreve a lista padrão)")
    source.add_argument("--file", type=str, help="Arquivo .txt com um ID por linha (sobrescreve a lista padrão)")
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Só baixa os arquivos, sem indexar no ChromaDB",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Segundos entre downloads (padrão: 1.5)",
    )

    args = parser.parse_args()

    if args.ids:
        ids = args.ids
    elif args.file:
        ids = load_ids_from_file(args.file)
    else:
        ids = GUTENBERG_IDS
        print("(usando lista padrão de GUTENBERG_IDS)")
    print(f"\n→ {len(ids)} livros para processar: {ids}\n")

    downloaded = download_all(ids, books_dir=BOOKS_DIR, delay=args.delay)

    if args.no_index:
        print("\n✓ Download concluído. Indexação pulada (--no-index).")
        return

    print("\n→ Iniciando indexação no ChromaDB...\n")
    for gid, file_path in downloaded.items():
        book_title = file_path.stem
        try:
            n = index_book(file_path, book_title)
            print(f"  ✓ {book_title}: {n} chunks indexados")
        except Exception as e:
            print(f"  ✗ {book_title}: erro na indexação — {e}")

    print(f"\n✓ Concluído. {len(downloaded)} livros processados.")


if __name__ == "__main__":
    main()