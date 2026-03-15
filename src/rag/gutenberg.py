"""
Downloader do Project Gutenberg.
- Baixa o texto de um livro pelo ID numérico
- Salva em data/books/{gutenberg_id}_{title}.txt
- Limpa o cabeçalho/rodapé padrão do Gutenberg antes de salvar
"""

import re
import time
from pathlib import Path

import requests

BOOKS_DIR = Path("data/books")

GUTENBERG_IDS = [
    1497, 1656, 1657, 1658, 1600, 1636, 1643, 1672, 1572, 1750,
    8438, 6762, 6763, 1974, 1173, 2412, 2413, 2414, 2415, 3296,
    45304, 3297, 1302, 48280, 17611, 41781, 42227, 37940, 37939,
    38032, 18269, 4039, 50319, 32970, 38241, 34283, 1998, 4363,
    52319, 51356, 19322, 37841, 2600, 1399, 1938, 4602, 20203,
    64908, 2554, 28054, 2638, 8117, 600, 36034,
]

GUTENBERG_MIRRORS = [
    "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt",
    "https://www.gutenberg.org/files/{id}/{id}-0.txt",
    "https://www.gutenberg.org/files/{id}/{id}.txt",
]

_START_MARKERS = [
    r"\*\*\* START OF THE PROJECT GUTENBERG EBOOK .+? \*\*\*",
    r"\*\*\* START OF THIS PROJECT GUTENBERG EBOOK .+? \*\*\*",
]
_END_MARKERS = [
    r"\*\*\* END OF THE PROJECT GUTENBERG EBOOK .+? \*\*\*",
    r"\*\*\* END OF THIS PROJECT GUTENBERG EBOOK .+? \*\*\*",
]


def _strip_gutenberg_boilerplate(text: str) -> str:
    for pattern in _START_MARKERS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            text = text[match.end():]
            break

    for pattern in _END_MARKERS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            text = text[: match.start()]
            break

    return text.strip()


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text[:60]


def download_book(gutenberg_id: int, books_dir: Path = BOOKS_DIR) -> Path:
    books_dir.mkdir(parents=True, exist_ok=True)

    text = None
    for url_template in GUTENBERG_MIRRORS:
        url = url_template.format(id=gutenberg_id)
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                text = response.text
                break
        except requests.RequestException:
            continue

    if not text:
        raise RuntimeError(
            f"Não foi possível baixar o livro ID {gutenberg_id}. "
            "Verifique o ID ou tente novamente mais tarde."
        )

    text = _strip_gutenberg_boilerplate(text)

    first_line = next((l.strip() for l in text.splitlines() if l.strip()), str(gutenberg_id))
    title = re.sub(r"^(title|by)[:\s]+", "", first_line, flags=re.IGNORECASE).strip()
    slug = _slugify(title) or str(gutenberg_id)

    file_path = books_dir / f"{gutenberg_id}_{slug}.txt"
    file_path.write_text(text, encoding="utf-8")

    print(f"[gutenberg] ID {gutenberg_id} → {file_path} ({len(text):,} chars)")
    return file_path


def download_all(
        gutenberg_ids: list[int],
        books_dir: Path = BOOKS_DIR,
        delay: float = 1.5,
) -> dict[int, Path]:
    results = {}
    for i, gid in enumerate(gutenberg_ids):
        existing = list(books_dir.glob(f"{gid}_*.txt"))
        if existing:
            print(f"[gutenberg] ID {gid} já existe em {existing[0]}, pulando.")
            results[gid] = existing[0]
            continue

        try:
            path = download_book(gid, books_dir)
            results[gid] = path
        except RuntimeError as e:
            print(f"[gutenberg] ERRO: {e}")

        if i < len(gutenberg_ids) - 1:
            time.sleep(delay)

    return results