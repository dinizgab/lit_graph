from rapidfuzz import fuzz
import requests

from src.models.models import BookBibliographicContext
from src.utils.llm_client import LLMClient

llm_client = LLMClient()
GUTENDEX_URL = "https://gutendex.com/books/"

def search_books_gutendex(query: str) -> list[dict]:
    response = requests.get(GUTENDEX_URL, params={"search": query})

    if response.status_code != 200:
        raise ValueError(f"Erro ao buscar livro {query} no Gutendex")

    data = response.json()

    return data.get("results", [])


def pick_best_match(query: str, candidates: list[dict]) -> dict | None:
    if not candidates:
        return None
    
    scored = []
    for book in candidates:
        score = fuzz.token_sort_ratio(query.lower(), book["title"].lower())
        scored.append((score, book))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_book = scored[0]
    
    return best_book if best_score > 40 else None


def search_book_by_name(query: str) -> BookBibliographicContext:
    normalized = llm_client.normalize_title(query)
    search_term = f"{normalized['original_title']} {normalized['author_lastname']}"
    
    candidates = search_books_gutendex(search_term)
    
    if not candidates:
        candidates = search_books_gutendex(normalized["original_title"])
    
    best = pick_best_match(normalized["original_title"], candidates)
    
    if not best:
        raise ValueError(
            f"Nenhuma obra encontrada para: '{query}' "
            f"(buscado como: '{normalized['original_title']}')"
        )
    
    return BookBibliographicContext.model_validate(best)