import json
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from src.models.models import BookBibliographicContext

CACHE_PATH = Path("static/data/book_cache.json")

_cache: dict[str, Any] | None = None


def _load_cache() -> dict[str, Any]:
    global _cache
    if _cache is None:
        if not CACHE_PATH.exists():
            raise FileNotFoundError(
                f"Cache não encontrado em {CACHE_PATH}. "
                "Execute: python -m ingest.build_book_cache"
            )
        _cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return _cache


def get_cached_titles() -> list[str]:
    cache = _load_cache()
    return [entry["title"] for entry in cache["by_id"].values()]


def lookup_by_id(gutenberg_id: int) -> BookBibliographicContext | None:
    cache = _load_cache()
    entry = cache["by_id"].get(str(gutenberg_id))
    if entry is None:
        return None
    return BookBibliographicContext.model_validate(entry)


def lookup_by_title(query: str, threshold: int = 60) -> BookBibliographicContext | None:
    cache = _load_cache()
    by_title: dict[str, int] = cache["by_title"]
    by_id: dict[str, dict] = cache["by_id"]

    normalized_query = query.lower().strip()

    if normalized_query in by_title:
        gid = by_title[normalized_query]
        entry = by_id.get(str(gid))
        if entry:
            return BookBibliographicContext.model_validate(entry)

    best_score = 0
    best_gid: int | None = None

    for title_key, gid in by_title.items():
        score = fuzz.token_sort_ratio(normalized_query, title_key)
        if score > best_score:
            best_score = score
            best_gid = gid

    if best_score >= threshold and best_gid is not None:
        entry = by_id.get(str(best_gid))
        if entry:
            return BookBibliographicContext.model_validate(entry)

    return None


def search_book_by_name_cached(
    query: str,
    llm_normalize_fn=None,
    fallback_fn=None,
) -> BookBibliographicContext:
    cached_titles = get_cached_titles()

    if llm_normalize_fn is not None:
        normalized = llm_normalize_fn(query, cache_titles=cached_titles)
        english_title = normalized.get("original_title", query)
        matched = normalized.get("matched_cache_title")
    else:
        english_title = query
        matched = None

    if matched:
        result = lookup_by_title(matched, threshold=0)
        if result is not None:
            return result

    result = lookup_by_title(english_title)
    if result is not None:
        return result

    if english_title.lower() != query.lower():
        result = lookup_by_title(query)
        if result is not None:
            return result

    if fallback_fn is not None:
        return fallback_fn(query)

    raise ValueError(
        f"Livro não encontrado no cache para: '{query}' "
        f"(buscado como: '{english_title}'). "
        "Execute ingest/build_book_cache.py para atualizar o cache."
    )


def cache_stats() -> dict[str, Any]:
    """Retorna estatísticas do cache carregado (útil para debug)."""
    cache = _load_cache()
    return {
        "generated_at": cache.get("generated_at"),
        "total_books": cache.get("total", 0),
        "total_title_keys": len(cache.get("by_title", {})),
        "failed_ids": cache.get("failed_ids", []),
        "cache_path": str(CACHE_PATH.resolve()),
    }