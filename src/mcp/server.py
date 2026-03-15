from dotenv import load_dotenv
load_dotenv()

import wikipedia
from wikipedia import DisambiguationError, PageError
from fastmcp import FastMCP
from src.models.models import BookBibliographicContext, BookHistoricalContext, BookPhilosophicalContext
from src.utils import search_book_by_name, LLMClient
from src.rag import retrieve_chunks

llm_client = LLMClient()

server = FastMCP(
    name="lit_graph",
    instructions=(
        "Este servidor fornece contexto estruturado sobre obras literárias "
        "clássicas do domínio público. Ele deve ser consultado quando for "
        "necessário obter informações sobre uma obra, seu autor ou seu contexto. "
        "Os dados retornados podem incluir metadados bibliográficos "
        "(autor, ano de publicação, idioma), contexto literário "
        "(gênero, movimento literário, temas e personagens), contexto histórico "
        "(período histórico e ambiente cultural da obra) e possíveis dimensões "
        "filosóficas relacionadas aos temas do texto."
    )
)


@server.tool()
def get_book_info(query: str) -> BookBibliographicContext:
    """
    Busca metadados bibliograficos de obra clássica pelo nome em qualquer idioma ou grafia.
    Dados como autores (nome, nascimento e morte), nome, temas, resumos e idiomas disponíveis.
    Exemplos: 'memórias do subsolo', 'guerra e paz', 'a divina comédia'.
    """
    return search_book_by_name(query)


@server.tool()
def get_book_historical_context(query: str) -> BookHistoricalContext:
    """
    Busca informações históricas sobre uma obra clássica pelo nome em qualquer idioma ou grafia.
    Dados como período histórico, ambiente cultural e contextos sociais da obra.
    Exemplos: 'memórias do subsolo', 'guerra e paz', 'a divina comédia'.
    """
    search_term = llm_client.normalize_title(query)["original_title"]

    wikipedia.set_lang("en")
    try:
        wikipedia_page = wikipedia.page(search_term, auto_suggest=False)
    except DisambiguationError as e:
        wikipedia_page = wikipedia.page(e.options[0], auto_suggest=False)
    except PageError:
        raise ValueError(f"Não foi possível encontrar contexto histórico para '{query}'.")

    return BookHistoricalContext(
        work_title=search_term,
        source="wikipedia",
        summary=wikipedia_page.summary,
    )


@server.tool()
def get_book_philosophical_context(query: str) -> BookPhilosophicalContext:
    """
    Gera temas filosóficos plausíveis associados à obra.
    """
    book = search_book_by_name(query)
    return llm_client.generate_philosophical_context(book.title, book.summaries, book.subjects)


@server.tool()
def search_book_content(
        query: str,
        book_title: str | None = None,
) -> list[str]:
    """
    Busca trechos relevantes nos livros indexados usando RAG.

    Usa embeddings locais para recuperar passagens do texto original
    mais relevantes para a query.

    Args:
        query: pergunta ou trecho a buscar (ex: 'O que motiva Raskolnikov?')
        book_title: título canônico para filtrar a busca (ex: '2554_crime_and_punishment').
                    Se omitido, busca em toda a base indexada.

    Exemplos:
        query='qual é o monólogo inicial do subsolo?', book_title='600_notes_from_underground'
        query='descreva a batalha de Borodino', book_title='2600_war_and_peace'
        query='o que significa o leopardo na obra?'
    """
    return retrieve_chunks(query=query, book_title=book_title, top_k=6)


if __name__ == "__main__":
    server.run(
        transport="http",
        host="127.0.0.1",
        port=8000,
    )