import argparse
from pathlib import Path

from src.rag.gutenberg import download_all, BOOKS_DIR, GUTENBERG_IDS
from src.rag.indexer import index_book


def load_ids_from_file(path: str) -> list[int]:
    lines = Path(path).read_text().splitlines()
    return [int(l.strip()) for l in lines if l.strip().isdigit()]


def main():
    parser = argparse.ArgumentParser(
        description="Baixa livros do Gutenberg e indexa no ChromaDB."
    )
    source = parser.add_mutually_exclusive_group(required=False)
    source.add_argument(
        "--ids",
        nargs="+",
        type=int,
        help="IDs numéricos do Gutenberg (sobrescreve a lista padrão)",
    )
    source.add_argument(
        "--file",
        type=str,
        help="Arquivo .txt com um ID por linha (sobrescreve a lista padrão)",
    )
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
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Pula a etapa de download (útil para indexar arquivos já baixados)",
    )

    args = parser.parse_args()

    if args.no_download:
        local_files = list(BOOKS_DIR.glob("*.txt"))
        if not local_files:
            print(f"Nenhum arquivo .txt encontrado em {BOOKS_DIR}. Abortando.")
            return

        if args.ids or args.file:
            ids = args.ids if args.ids else load_ids_from_file(args.file)
            id_set = {str(i) for i in ids}
            local_files = [f for f in local_files if f.stem in id_set]
            if not local_files:
                print(f"Nenhum arquivo local corresponde aos IDs {ids}. Abortando.")
                return

        downloaded = {}
        for f in local_files:
            prefix = f.stem.split("_")[0]
            gid = int(prefix) if prefix.isdigit() else None
            downloaded[gid] = f
            
        print(f"\n{len(downloaded)} arquivo(s) local(is) encontrado(s) em {BOOKS_DIR}\n")
    else:
        if args.ids:
            ids = args.ids
        elif args.file:
            ids = load_ids_from_file(args.file)
        else:
            ids = GUTENBERG_IDS
            print("(usando lista padrão de GUTENBERG_IDS)")
        print(f"\n{len(ids)} livros para processar: {ids}\n")

        downloaded = download_all(ids, books_dir=BOOKS_DIR, delay=args.delay)

    if args.no_index:
        print("\nDownload concluído. Indexação pulada (--no-index).")
        return

    print("\nIniciando indexação no ChromaDB...\n")
    for gid, file_path in downloaded.items():
        book_title = file_path.stem
        try:
            n = index_book(file_path, book_title, gid)
            print(f"  {book_title}: {n} chunks indexados")
        except Exception as e:
            print(f"  {book_title}: erro na indexação — {e}")

    print(f"\nConcluído. {len(downloaded)} livros processados.")


if __name__ == "__main__":
    main()