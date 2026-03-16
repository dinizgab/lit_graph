import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datasets import Dataset
from ragas import aevaluate
from ragas.metrics.collections import (
    ContextPrecision,
    ContextRecall,
    Faithfulness,
    AnswerRelevancy,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from rich.console import Console
from rich.table import Table
from rich.progress import track

from src.graph.graph import build_graph
from src.graph.state import LitGraphState
from eval.dataset import LABELED_QUESTIONS


console = Console()

async def run_single(graph, question: str, student_level: str, book_title: str = "") -> dict:
    initial_state = LitGraphState({
        "user_query": question,
        "book_title": book_title,
        "student_level": student_level,  # type: ignore[arg-type]
        "self_check_attempts": 0,
        "enable_self_check": True,
    })
 
    t0 = time.perf_counter()
    result = await graph.ainvoke(initial_state)
    latency = time.perf_counter() - t0
 
    answer = result.get("final_answer") or result.get("error", "")
    chunks: list[str] = result.get("retrieved_chunks", [])
 
    return {
        "answer": answer,
        "contexts": chunks,
        "latency_s": latency,
    }


def build_ragas_dataset(rows: list[dict]) -> Dataset:
    return Dataset.from_dict({
        "question":     [r["question"]     for r in rows],
        "answer":       [r["answer"]       for r in rows],
        "contexts":     [r["contexts"]     for r in rows],
        "ground_truth": [r["ground_truth"] for r in rows],
    })


def print_results_table(scores: dict, rows: list[dict]) -> None:
    m_table = Table(
        title="Métricas RAGAS (médias)",
        show_header=True,
        header_style="bold cyan",
    )
    m_table.add_column("Métrica",       style="cyan", min_width=22)
    m_table.add_column("Valor",         justify="right", style="green")
    m_table.add_column("Barra",         style="dim", min_width=12)
    m_table.add_column("Interpretação", style="dim")

    INTERP = {
        "context_precision": "Chunks recuperados são relevantes?",
        "context_recall":    "Contexto cobre o ground truth?",
        "faithfulness":      "Resposta está ancorada nos chunks?",
        "answer_relevancy":  "Resposta endereça a pergunta?",
    }

    for k, v in scores.items():
        if isinstance(v, float):
            filled = int(v * 10)
            bar = "█" * filled + "░" * (10 - filled)
            m_table.add_row(k, f"{v:.4f}", bar, INTERP.get(k, ""))

    console.print(m_table)

    for sub in ("qa", "guide"):
        sub_rows = [r for r in rows if r["subset"] == sub]
        if not sub_rows:
            continue

        s_table = Table(
            title=f"⏱  Latência — subset '{sub}' ({len(sub_rows)} perguntas)",
            show_header=True,
            header_style="bold yellow",
        )
        s_table.add_column("#",       justify="right", style="dim", width=4)
        s_table.add_column("Pergunta", no_wrap=False, min_width=55)
        s_table.add_column("Lat (s)", justify="right", style="yellow", width=8)
        s_table.add_column("Chunks",  justify="right", width=7)

        for i, r in enumerate(sub_rows, 1):
            q = r["question"][:72] + ("…" if len(r["question"]) > 72 else "")
            s_table.add_row(str(i), q, f"{r['latency_s']:.2f}", str(len(r["contexts"])))

        avg = sum(r["latency_s"] for r in sub_rows) / len(sub_rows)
        s_table.add_row(
            "—", "[bold]Média[/bold]", f"[bold]{avg:.2f}[/bold]", "—"
        )
        console.print(s_table)


async def main(subset: str | None, output_path: str) -> None:
    console.rule("[bold blue]LitGraph — Avaliação RAG")
    console.print(
        "[dim]Corpus: Platão · Aristóteles · Agostinho · Tomás de Aquino · Anselmo · "
        "Pascal · Kierkegaard · Nietzsche · Tolstói · Dostoiévski[/dim]\n"
    )

    questions = LABELED_QUESTIONS
    if subset:
        questions = [q for q in LABELED_QUESTIONS if q["subset"] == subset]
        console.print(
            f"[dim]Filtrando subset='{subset}': {len(questions)} perguntas[/dim]\n"
        )
    else:
        console.print(f"[dim]Total de perguntas: {len(questions)}[/dim]\n")

    console.print("[dim]Inicializando o grafo LitGraph…[/dim]")
    graph = build_graph()

    rows: list[dict] = []
    for item in track(questions, description="Executando perguntas…"):
        result = await run_single(
            graph,
            question=item["question"],
            student_level=item["student_level"],
            book_title=item.get("book_title", ""),
        )
        rows.append({
            "question":      item["question"],
            "ground_truth":  item["ground_truth"],
            "answer":        result["answer"],
            "contexts":      result["contexts"],
            "latency_s":     result["latency_s"],
            "subset":        item["subset"],
            "student_level": item["student_level"],
            "book_title":    item.get("book_title", ""),
            "gutenberg_id":  item["gutenberg_id"],
        })

    console.print(f"\n[green]✓ {len(rows)} respostas coletadas.[/green]\n")

    dataset = build_ragas_dataset(rows)

    ragas_llm = LangchainLLMWrapper(
        ChatOpenAI(model="gpt-5-mini-2025-08-07", temperature=0)
    )
    ragas_embeddings = LangchainEmbeddingsWrapper(
        OpenAIEmbeddings(model="text-embedding-3-small")
    )

    console.print("[dim]Calculando métricas RAGAS (pode demorar alguns minutos)…[/dim]")
    metrics = [
        ContextPrecision(llm=ragas_llm),
        ContextRecall(llm=ragas_llm),
        Faithfulness(llm=ragas_llm),
        AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings),
    ]
    ragas_result = await aevaluate(
        dataset=dataset,
        metrics=metrics,
        raise_exceptions=False,
    )

    scores = ragas_result.to_pandas().mean(numeric_only=True).to_dict()

    print_results_table(scores, rows)

    output = {
        "evaluated_at":  datetime.utcnow().isoformat() + "Z",
        "subset_filter": subset,
        "n_questions":   len(rows),
        "metrics":       scores,
        "latency": {
            "mean_s": round(sum(r["latency_s"] for r in rows) / len(rows), 3),
            "min_s":  round(min(r["latency_s"] for r in rows), 3),
            "max_s":  round(max(r["latency_s"] for r in rows), 3),
        },
        "details": [
            {
                "question":       r["question"],
                "subset":         r["subset"],
                "student_level":  r["student_level"],
                "gutenberg_id":   r["gutenberg_id"],
                "latency_s":      round(r["latency_s"], 3),
                "n_chunks":       len(r["contexts"]),
                "answer_preview": r["answer"][:300],
            }
            for r in rows
        ],
    }

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    console.print(f"\n[bold green]Resultados salvos em:[/bold green] {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Avaliação RAG do LitGraph com RAGAS."
    )
    parser.add_argument(
        "--subset",
        choices=["qa", "guide"],
        default=None,
        help="Avaliar apenas 'qa' ou 'guide'. Omita para avaliar tudo.",
    )
    parser.add_argument(
        "--output",
        default="results/rag_eval.json",
        help="Caminho do arquivo JSON de saída (padrão: results/rag_eval.json).",
    )
    args = parser.parse_args()

    asyncio.run(main(subset=args.subset, output_path=args.output))