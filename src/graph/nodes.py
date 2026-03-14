import os
from typing import cast

from langchain_mcp_adapters.client import MultiServerMCPClient

from src.graph.state import LitGraphState
from src.utils.llm_client import LLMClient


MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

llm_client = LLMClient()


def supervisor(state: LitGraphState) -> dict:
    query = state["user_query"].lower()
    
    route = llm_client.decide_route(query)
    
    return {"intent": route}


async def retriever(state: LitGraphState) -> dict:
    query = state.get("book_title") or state.get("user_query", "")
    
    client = MultiServerMCPClient(
        {
            "lit_graph": {
                "url": MCP_SERVER_URL,
                "transport": "http",
            }
        }, # type: ignore
    )

    tools = {t.name: t for t in await client.get_tools()}

    try:
        bib = await tools["get_book_info"].ainvoke({"query": query})
    except Exception as e:
        return {"error": str(e), "intent": "refuse"}

    try:
        hist = await tools["get_book_historical_context"].ainvoke({"query": query})
    except Exception:
        hist = {}

    try:
        phil = await tools["get_book_philosophical_context"].ainvoke({"query": query})
    except Exception:
        phil = {}


    # TODO - Substituir aqui pela chamada do mcp para a funcao que faz RAG
    chunks = bib.get("summaries", [])[:3]
    sources = [{"source": "gutendex", "id": bib.get("gutenberg_id"), "title": bib.get("title")}]

    return {
        "bibliographic_context": bib,
        "historical_context": hist,
        "philosophical_context": phil,
        "retrieved_chunks": chunks,
        "retrieval_sources": sources,
    }


def automation(state: LitGraphState) -> dict:
    draft = llm_client.create_study_guide(
        bibliographic_context=state["bibliographic_context"],
        historical_context=state["historical_context"],
        philosophical_context=state["philosophical_context"],
        student_level=state["student_level"],
    )

    citations = [
        {"source": s["source"], "title": s.get("title", ""), "id": s.get("id")}
        for s in state["retrieval_sources"]
    ]

    return {
        "draft_answer": draft,
        "citations": citations,
    }
    
    
def safety(state: LitGraphState) -> dict:
    disclaimer = ""
 
    if state["philosophical_context"].themes:
        disclaimer += (
            "⚠️ As interpretações filosóficas são plausíveis com base nos temas "
            "da obra, mas não constituem consenso acadêmico. "
        )
    if state["historical_context"].summary:
        disclaimer += (
            "ℹ️ O contexto histórico foi obtido da Wikipedia e pode conter "
            "imprecisões. Consulte fontes especializadas para pesquisa acadêmica."
        )
 
    return {"safety_disclaimer": disclaimer, "is_safe": True}


def answerer(state: LitGraphState) -> dict:
    citations = state.get("citations") or []
 
    refs_block = "\n\n---\n**Referências:**\n"
    for i, c in enumerate(citations, 1):
        refs_block += f"[{i}] {c.get('title', '')} — {c.get('source', '')} (id: {c.get('id', '')})\n"
 
    disclaimer = state.get("safety_disclaimer", "")
    disclaimer_block = f"\n\n{disclaimer}" if disclaimer else ""
 
    answer = state.get("draft_answer", "") + refs_block + disclaimer_block
    return {"draft_answer": answer}


def self_check(state: LitGraphState) -> dict:
    draft = state.get("draft_answer", "")
    chunks = state.get("retrieved_chunks", [])
    attempts = state.get("self_check_attempts", 0)

    if not chunks:
        if attempts >= 1:
            return {
                "self_check_passed": False,
                "final_answer": (
                    "Não foi possível encontrar evidências suficientes. "
                    "Tente reformular sua pergunta."
                ),
            }
        return {
            "self_check_passed": False,
            "self_check_attempts": attempts + 1,
        }

    result = llm_client.self_check_answer(
        user_query=state.get("user_query", ""),
        draft_answer=draft,
        retrieved_chunks=chunks,
        book_title=state.get("book_title", ""),
        student_level=state.get("student_level", "curioso"),
    )

    if result.grounded and result.suggested_action == "accept":
        return {
            "self_check_passed": True,
            "final_answer": result.final_answer or draft,
        }

    if result.suggested_action == "revise":
        return {
            "self_check_passed": True,
            "final_answer": result.final_answer,
        }

    if attempts >= 1:
        return {
            "self_check_passed": False,
            "final_answer": (
                result.final_answer
                if result.final_answer
                else "Não foi possível validar a resposta com evidências suficientes. Tente reformular sua pergunta."
            ),
        }

    return {
        "self_check_passed": False,
        "self_check_attempts": attempts + 1,
    }
    
    
def output(state: LitGraphState) -> dict:
    return {"final_answer": state.get("draft_answer", "")}

 
def refuse(state: LitGraphState) -> dict:
    msg = state.get("error") or (
        "Desculpe, só consigo responder perguntas sobre obras literárias clássicas "
        "do domínio público. Tente perguntar sobre um título específico!"
    )
    return {"final_answer": msg}