import wikipedia

from dotenv import load_dotenv
load_dotenv()

from src.models.models import BookPhilosophicalContext
from src.utils import search_book_by_name
from src.utils.llm_client import LLMClient


llm_client = LLMClient()


def get_book_philosophical_context(query: str) -> BookPhilosophicalContext:
    """
    Gera temas filosóficos plausíveis associados à obra.
    """
    book = search_book_by_name(query)
    return llm_client.generate_philosophical_context(book.title, book.summaries, book.subjects)


res = get_book_philosophical_context("memorias do subsolo")
print(res)