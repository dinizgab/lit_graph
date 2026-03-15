import os
from typing import Any, cast

from langchain_mcp_adapters.client import MultiServerMCPClient

from src.graph.state import LitGraphState
from src.models.models import BookBibliographicContext, BookHistoricalContext, BookPhilosophicalContext, StudyChecklist, StudyGuideExtraction, StudyPlan
from src.utils import parse_mcp_response
from src.utils.llm_client import LLMClient


MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

llm_client = LLMClient()


def supervisor(state: LitGraphState) -> dict:
    query = state.get("user_query", "").lower()

    route = llm_client.decide_route(query)

    return {"intent": route}


async def retriever(state: LitGraphState) -> dict:
    query = state.get("book_title") or state.get("user_query", "")
    book_title = state.get("book_title")
    student_level = state.get("student_level", "curioso")

    client = MultiServerMCPClient(
        {
            "lit_graph": {
                "url": f"{MCP_SERVER_URL}/mcp",
                "transport": "streamable_http",
            }
        },
    )

    tools = {t.name: t for t in await client.get_tools()}

    try:
        bib = await tools["get_book_info"].ainvoke({"query": query})
        bib = parse_mcp_response(bib, BookBibliographicContext)
    except Exception as e:
        return {"error": str(e), "intent": "refuse"}

    try:
        hist = await tools["get_book_historical_context"].ainvoke({"query": query})
        hist = parse_mcp_response(hist, BookHistoricalContext)
    except Exception:
        hist = {}

    try:
        phil = await tools["get_book_philosophical_context"].ainvoke({"query": query})
        phil = parse_mcp_response(phil, BookPhilosophicalContext)
    except Exception:
        phil = {}

    # RAG — busca trechos reais dos livros indexados
    try:
        await tools["search_book_content"].ainvoke({
            "query": state.get("user_query", query),
            "book_title": book_title,
            "student_level": student_level,
        })
        from src.rag.retriever import retrieve_chunks
        chunks = retrieve_chunks(
            query=state.get("user_query", query),
            book_title=book_title,
            top_k=6,
        )
    except Exception:
        chunks = []

    sources = [
        {
            "source": "gutenberg",
            "title": bib.title,
            "id": bib.gutenberg_id,
            "excerpt": chunk[:300],
        }
        for chunk in chunks[:3]
    ]

    return {
        "bibliographic_context": bib,
        "historical_context": hist,
        "philosophical_context": phil,
        "retrieved_chunks": chunks,
        "retrieval_sources": sources,
    }


def automation(state: LitGraphState) -> dict:
    bibliographic_context = cast(BookBibliographicContext, state.get("bibliographic_context"))
    historical_context = cast(BookHistoricalContext, state.get("historical_context"))
    philosophical_context = cast(BookPhilosophicalContext, state.get("philosophical_context"))
    retrieved_chunks = cast(list[str], state.get("retrieved_chunks", []))
    student_level = cast(str, state.get("student_level", "curioso"))
    retrieval_sources = cast(list[dict[str, Any]], state.get("retrieval_sources", []))

    trace: list[str] = []

    plan: StudyPlan = llm_client.build_study_plan(
        bibliographic_context=bibliographic_context,
        historical_context=historical_context,
        philosophical_context=philosophical_context,
        retrieved_chunks=retrieved_chunks,
        student_level=student_level,
    )
    trace.append("build_study_plan")

    extraction: StudyGuideExtraction = llm_client.extract_study_guide_elements(
        bibliographic_context=bibliographic_context,
        historical_context=historical_context,
        philosophical_context=philosophical_context,
        retrieved_chunks=retrieved_chunks,
        student_level=student_level,
    )
    trace.append("extract_study_guide_elements")

    checklist: StudyChecklist = llm_client.build_revision_checklist(
        plan=plan,
        extraction=extraction,
        student_level=student_level,
    )
    trace.append("build_revision_checklist")

    draft = llm_client.render_structured_study_guide(
        bibliographic_context=bibliographic_context,
        plan=plan,
        extraction=extraction,
        checklist=checklist,
        student_level=student_level,
    )
    trace.append("render_structured_study_guide")

    citations = [
        {
            "source": s.get("source", ""),
            "title": s.get("title", ""),
            "id": s.get("id", ""),
            "excerpt": s.get("excerpt", ""),
        }
        for s in retrieval_sources
    ]

    return {
        "automation_plan": plan,
        "automation_extraction": extraction,
        "automation_checklist": checklist,
        "automation_trace": trace,
        "automation_steps_count": len(trace),
        "draft_answer": draft,
        "citations": citations,
    }


def safety(state: LitGraphState) -> dict:
    disclaimer = ""

    if cast(BookPhilosophicalContext, state.get("philosophical_context")).themes:
        disclaimer += (
            "As interpretações filosóficas são plausíveis com base nos temas "
            "da obra, mas não constituem consenso acadêmico. "
        )
    if cast(BookHistoricalContext, state.get("historical_context")).summary:
        disclaimer += (
            "O contexto histórico foi obtido da Wikipedia e pode conter "
            "imprecisões. Consulte fontes especializadas para pesquisa acadêmica."
        )

    return {"safety_disclaimer": disclaimer, "is_safe": True}


def answerer(state: LitGraphState) -> dict:
    intent = state.get("intent", "")
    citations = cast(list, state.get("citations", []))
    disclaimer = state.get("safety_disclaimer", "")
    draft_answer = state.get("draft_answer", "")

    if intent == "qa":
        generated_answer = llm_client.answer_question_with_context(
            user_query=cast(str, state.get("user_query", "")),
            book_title=cast(str, state.get("book_title", "")),
            bibliographic_context=cast(BookBibliographicContext, state.get("bibliographic_context")),
            historical_context=cast(BookHistoricalContext, state.get("historical_context")),
            philosophical_context=cast(BookPhilosophicalContext, state.get("philosophical_context")),
            retrieved_chunks=cast(list[str], state.get("retrieved_chunks", [])),
            student_level=cast(str, state.get("student_level", "curioso")),
        )

        citations = [
            {
                "source": s.get("source", ""),
                "title": s.get("title", ""),
                "id": s.get("id", ""),
                "excerpt": s.get("excerpt", ""),
            }
            for s in cast(list, state.get("retrieval_sources", []))
        ]
        draft_answer = generated_answer

    refs_block = ""
    if citations:
        refs_block = "\n\n---\n**Referências:**\n"
        for i, c in enumerate(citations, 1):
            excerpt = c.get("excerpt", "")
            excerpt_line = f"\nTrecho: {excerpt}" if excerpt else ""
            refs_block += (
                f"[{i}] {c.get('title', '')} — {c.get('source', '')} "
                f"(id: {c.get('id', '')}){excerpt_line}\n"
            )

    disclaimer_block = f"\n\n{disclaimer}" if disclaimer else ""

    final_draft = draft_answer + refs_block + disclaimer_block

    return {
        "draft_answer": final_draft,
        "citations": citations,
    }


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
        user_query=cast(str, state.get("user_query", "")),
        draft_answer=cast(str, draft),
        retrieved_chunks=cast(list, chunks),
        book_title=cast(str, state.get("book_title", "")),
        student_level=cast(str, state.get("student_level", "curioso")),
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