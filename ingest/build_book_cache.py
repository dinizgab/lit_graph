import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests
from rapidfuzz import fuzz

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.gutenberg import GUTENBERG_IDS

GUTENDEX_BOOK_URL = "https://gutendex.com/books/{id}/"
DEFAULT_OUTPUT = Path("static/data/book_cache.json")
ALLOWED_LANGUAGES = {"en", "pt"}


def _fetch_book(gutenberg_id: int, timeout: int = 30) -> dict[str, Any] | None:
    url = GUTENDEX_BOOK_URL.format(id=gutenberg_id)
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 404:
            print(f"  [{gutenberg_id}] 404 — ID não encontrado no Gutendex")
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"  [{gutenberg_id}] ERRO: {e}")
        return None


def _extract_entry(raw: dict[str, Any]) -> dict[str, Any]:
    languages = raw.get("languages", [])
    if not any(lang in ALLOWED_LANGUAGES for lang in languages):
        languages = raw.get("languages", [])

    authors = [
        {
            "name": a.get("name", ""),
            "birth_year": a.get("birth_year"),
            "death_year": a.get("death_year"),
        }
        for a in raw.get("authors", [])
    ]

    return {
        "id": raw["id"],
        "title": raw.get("title", ""),
        "authors": authors,
        "summaries": raw.get("summaries", []),
        "subjects": raw.get("subjects", []),
        "languages": languages,
    }


def _collect_title_keys(entry: dict[str, Any]) -> list[str]:
    keys = []
    title = entry.get("title", "").strip()
    if title:
        keys.append(title.lower())

    for sep in (" / ", " or ", "; "):
        if sep in title:
            for part in title.split(sep):
                part = part.strip().lower()
                if part:
                    keys.append(part)

    return list(dict.fromkeys(keys))


def build_cache(
    ids: list[int],
    output_path: Path,
    delay: float = 1.5,
) -> dict[str, Any]:
    print(f"\n[cache] Buscando {len(ids)} livros no Gutendex...")
    print(f"[cache] Saída: {output_path}\n")

    by_id: dict[str, dict] = {}
    by_title: dict[str, int] = {}
    failed: list[int] = []

    for i, gid in enumerate(ids):
        print(f"  [{i+1}/{len(ids)}] ID {gid} ...", end=" ", flush=True)
        raw = _fetch_book(gid)

        if raw is None:
            failed.append(gid)
            if i < len(ids) - 1:
                time.sleep(delay)
            continue

        languages = raw.get("languages", [])
        if not any(lang in ALLOWED_LANGUAGES for lang in languages):
            print(f"ignorado (idiomas: {languages})")
            if i < len(ids) - 1:
                time.sleep(delay)
            continue

        entry = _extract_entry(raw)
        str_id = str(gid)
        by_id[str_id] = entry

        for key in _collect_title_keys(entry):
            by_title[key] = gid

        print(f'OK — "{entry["title"]}" ({", ".join(entry["languages"])})')

        if i < len(ids) - 1:
            time.sleep(delay)

    cache = {
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "total": len(by_id),
        "failed_ids": failed,
        "by_id": by_id,
        "by_title": by_title,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n[cache]{len(by_id)} livros salvos em {output_path}")
    if failed:
        print(f"[cache]{len(failed)} IDs falharam: {failed}")

    return cache


def main() -> None:
    parser = argparse.ArgumentParser(description="Pré-cacheia metadados do Gutendex por ID.")
    parser.add_argument(
        "--ids", nargs="+", type=int, default=None,
        help="IDs específicos (padrão: usa GUTENBERG_IDS de src/rag/gutenberg.py)"
    )
    parser.add_argument(
        "--output", type=str, default=str(DEFAULT_OUTPUT),
        help=f"Caminho do JSON de saída (padrão: {DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        "--delay", type=float, default=1.5,
        help="Segundos entre requisições (padrão: 1.5)"
    )
    args = parser.parse_args()

    ids = args.ids if args.ids else GUTENBERG_IDS
    build_cache(ids=ids, output_path=Path(args.output), delay=args.delay)


if __name__ == "__main__":
    main()