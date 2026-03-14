import json
import requests
from rapidfuzz import fuzz

from src.models.models import BookBibliographicContext
from src.utils.llm_client import LLMClient

llm_client = LLMClient()
GUTENDEX_URL = "https://gutendex.com/books/"

def search_books_gutendex(query: str) -> list[dict]:
    try:
        response = requests.get(GUTENDEX_URL, params={"search": query}, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise ValueError(f"Erro ao buscar livro '{query}' no Gutendex: {e}") from e
    
    if response.status_code != 200:
        raise ValueError(f"Erro ao buscar livro {query} no Gutendex")

    data = response.json()

    return data.get("results", [])


def pick_best_match(query: str, candidates: list[dict]) -> dict | None:
    if not candidates:
        return None
    
    scored = []
    normalized_query = query.lower().strip()

    for book in candidates:
        title = book.get("title", "").lower().strip()
        score = fuzz.token_sort_ratio(normalized_query, title)
        scored.append((score, book))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_book = scored[0]

    return best_book if best_score >= 60 else None


def search_book_by_name(query: str) -> BookBibliographicContext:
    normalized = llm_client.normalize_title(query)
    original_title = normalized["original_title"]
    author_lastname = normalized.get("author_lastname")

    search_term = f"{original_title} {author_lastname}" if author_lastname else original_title
        
    candidates = search_books_gutendex(search_term)
    if not candidates and search_term != original_title:
        candidates = search_books_gutendex(original_title)
    
    best = pick_best_match(normalized["original_title"], candidates)
    
    if not best:
        raise ValueError(
            f"Nenhuma obra encontrada para: '{query}' "
            f"(buscado como: '{normalized['original_title']}')"
        )
    
    return BookBibliographicContext.model_validate(best)


def parse_mcp_response(raw, model_class):
    if isinstance(raw, list):
        content = raw[0]
        text = content.get("text") if isinstance(content, dict) else content
    elif isinstance(raw, str):
        text = raw
    else:
        return raw
    
    if text is None:
        raise ValueError("Cannot parse None as JSON")
    
    return model_class(**json.loads(text))