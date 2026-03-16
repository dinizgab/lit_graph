import json
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

    client = MultiServerMCPClient(
        {
            "lit_graph": {
                "url": f"{MCP_SERVER_URL}",
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
        phil = await tools["get_book_philosophical_context"].ainvoke({
            "title": bib.title,
            "summaries": bib.summaries,
            "subjects": bib.subjects,
        })
        phil = parse_mcp_response(phil, BookPhilosophicalContext)
    except Exception:
        phil = {}

    try:
        english_query = llm_client.translate_to_english(query)
        raw = await tools["search_book_content"].ainvoke({
            "query": english_query,
            "gutenberg_id": bib.gutenberg_id,
        })
        
        if isinstance(raw, list) and raw and isinstance(raw[0], dict) and "text" in raw[0]:
            chunk_results = json.loads(raw[0]["text"])
        else:
            chunk_results = raw if isinstance(raw, list) else []
            
    except Exception:
        chunk_results = []

    retrieved_chunks = [
        item.get("text", "")
        for item in chunk_results
        if isinstance(item, dict) and item.get("text")
    ]

    sources = [
        {
            "source": "book",
            "title": bib.title,
            "id": bib.gutenberg_id,
            "excerpt": item.get("text", "")[:500].replace("\n", " ").strip(),
            "chunk_id": item.get("chunk_id"),
            "chunk_index": item.get("chunk_index"),
            "rank": item.get("rank"),
            "book_title": item.get("book_title"),
            "location": item.get("location"),
            "score": item.get("score"),
            "distance": item.get("distance"),
        }
        for item in chunk_results
        if isinstance(item, dict)
    ]

    return {
        "bibliographic_context": bib,
        "historical_context": hist,
        "philosophical_context": phil,
        "retrieved_chunks": retrieved_chunks,
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
            "chunk_id": s.get("chunk_id"),
            "chunk_index": s.get("chunk_index"),
            "rank": s.get("rank"),
            "book_title": s.get("book_title"),
            "location": s.get("location"),
            "score": s.get("score"),
            "distance": s.get("distance"),
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
                "chunk_id": s.get("chunk_id"),
                "chunk_index": s.get("chunk_index"),
                "rank": s.get("rank"),
                "book_title": s.get("book_title"),
                "location": s.get("location"),
                "score": s.get("score"),
                "distance": s.get("distance"),
            }
            for s in cast(list, state.get("retrieval_sources", []))
        ]
        
        draft_answer = generated_answer

    refs_block = "\n\n---\n**Referências:**\n"
    for i, c in enumerate(citations, 1):
        meta_parts = []
        if c.get("chunk_index") is not None:
            meta_parts.append(f"trecho={c['chunk_index']}")
        if c.get("score") is not None:
            meta_parts.append(f"relevância={c['score']:.2f}")

        meta_str = f" [{' | '.join(meta_parts)}]" if meta_parts else ""

        excerpt = c.get("excerpt", "")
        if excerpt:
            translated_excerpt = llm_client.translate_to_portuguese(excerpt)
            excerpt_line = f"\n> {translated_excerpt}\n"
        else:
            excerpt_line = ""

        refs_block += f"\n\n**[{i}] {c.get('title', '')}**{meta_str}{excerpt_line}"
    
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
        }

    if result.suggested_action == "revise":
        return {
            "self_check_passed": True,
            "final_answer": result.final_answer,
        }

    return {
        "self_check_passed": False,
        "self_check_attempts": attempts + 1,
    }


def output(state: LitGraphState) -> dict:
    final_answer = state.get("final_answer")
    draft_answer = state.get("draft_answer", "")

    if final_answer and str(final_answer).strip():
        return {"final_answer": final_answer}

    if draft_answer and str(draft_answer).strip():
        return {"final_answer": draft_answer}

    return {
        "final_answer": (
            "Não foi possível gerar uma resposta final. "
            "Tente reformular sua pergunta."
        )
    }


def refuse(state: LitGraphState) -> dict:
    msg = state.get("error") or (
        "Desculpe, só consigo responder perguntas sobre obras literárias clássicas "
        "do domínio público. Tente perguntar sobre um título específico!"
    )
    return {"final_answer": msg}