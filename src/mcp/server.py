from fastmcp import FastMCP
import wikipedia
from wikipedia import DisambiguationError, PageError

from src.models.models import BookBibliographicContext, BookHistoricalContext, BookPhilosophicalContext
from src.utils import search_book_by_name, LLMClient


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
    except  DisambiguationError as e:
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


# TODO -  Adicionar tool para fazer rag nos livros indexados aqui