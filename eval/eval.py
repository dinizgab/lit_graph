import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openai import AsyncOpenAI
from pydantic import BaseModel
from rich.console import Console
from rich.progress import track
from rich.table import Table

from ragas import EvaluationDataset, SingleTurnSample
from ragas.embeddings import OpenAIEmbeddings
from ragas.llms import llm_factory
from ragas.metrics.collections import (
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

from eval.dataset import LABELED_QUESTIONS
from src.graph.graph import build_graph
from src.graph.state import LitGraphState

console = Console()


class ExperimentResult(BaseModel):
    faithfulness: float | None = None
    answer_relevancy: float | None = None
    context_precision: float | None = None
    context_recall: float | None = None


async def run_single(
    graph: Any,
    question: str,
    student_level: str,
    book_title: str = "",
) -> dict:
    initial_state = LitGraphState(
        {
            "user_query": question,
            "book_title": book_title,
            "student_level": student_level,
            "self_check_attempts": 0,
            "enable_self_check": True,
        }
    )

    t0 = time.perf_counter()
    result = await graph.ainvoke(initial_state)
    latency = time.perf_counter() - t0

    answer = result.get("final_answer") or result.get("error", "")
    chunks = result.get("retrieved_chunks", [])

    if not isinstance(chunks, list):
        chunks = []

    return {
        "answer": str(answer),
        "contexts": [str(c) for c in chunks if c is not None],
        "latency_s": latency,
    }


def normalize_contexts(ctxs: Any) -> list[str]:
    if not isinstance(ctxs, list):
        return []
    cleaned = []
    for c in ctxs:
        if isinstance(c, str):
            c = c.strip()
            if c:
                cleaned.append(c)
    return cleaned


def build_eval_dataset(rows: list[dict]) -> EvaluationDataset:
    samples = []
    for r in rows:
        samples.append(
            SingleTurnSample(
                user_input=str(r.get("question", "")),
                response=str(r.get("answer", "")),
                retrieved_contexts=normalize_contexts(r.get("contexts", [])),
                reference=str(r.get("ground_truth", "")),
            )
        )
    return EvaluationDataset(samples=samples)


def safe_score_value(obj: Any) -> float | None:
    if obj is None:
        return None

    value = getattr(obj, "value", obj)

    if isinstance(value, bool):
        return float(value)

    if isinstance(value, (int, float)):
        return float(value)

    return None


def mean_metric(rows: list[dict], name: str) -> float | None:
    vals = [r[name] for r in rows if isinstance(r.get(name), (int, float))]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 6)


def print_results_table(
    scores: dict[str, float | None],
    rows: list[dict],
    metric_counts: dict[str, int],
) -> None:
    m_table = Table(
        title="Métricas RAGAS (médias)",
        show_header=True,
        header_style="bold cyan",
    )
    m_table.add_column("Métrica", style="cyan", min_width=22)
    m_table.add_column("Valor", justify="right", style="green")
    m_table.add_column("Barra", style="dim", min_width=12)
    m_table.add_column("N", justify="right", style="yellow", width=6)
    m_table.add_column("Interpretação", style="dim")

    interp = {
        "context_precision": "Chunks recuperados são relevantes?",
        "context_recall": "Contexto cobre o reference?",
        "faithfulness": "Resposta está ancorada nos chunks?",
        "answer_relevancy": "Resposta endereça a pergunta?",
    }

    for k, v in scores.items():
        if isinstance(v, float):
            filled = max(0, min(10, int(v * 10)))
            bar = "█" * filled + "░" * (10 - filled)
            m_table.add_row(
                k,
                f"{v:.4f}",
                bar,
                str(metric_counts.get(k, 0)),
                interp.get(k, ""),
            )
        else:
            m_table.add_row(
                k,
                "N/A",
                "—",
                str(metric_counts.get(k, 0)),
                interp.get(k, ""),
            )

    console.print(m_table)

    for sub in ("qa", "guide"):
        sub_rows = [r for r in rows if r.get("subset") == sub]
        if not sub_rows:
            continue

        s_table = Table(
            title=f"Latência — subset '{sub}' ({len(sub_rows)} perguntas)",
            show_header=True,
            header_style="bold yellow",
        )
        s_table.add_column("#", justify="right", style="dim", width=4)
        s_table.add_column("Pergunta", no_wrap=False, min_width=55)
        s_table.add_column("Lat (s)", justify="right", style="yellow", width=8)
        s_table.add_column("Chunks", justify="right", width=7)

        for i, r in enumerate(sub_rows, 1):
            q = str(r["question"])
            q = q[:72] + ("…" if len(q) > 72 else "")
            s_table.add_row(
                str(i),
                q,
                f"{float(r['latency_s']):.2f}",
                str(len(r.get("contexts", []))),
            )

        avg = sum(float(r["latency_s"]) for r in sub_rows) / len(sub_rows)
        s_table.add_row("—", "[bold]Média[/bold]", f"[bold]{avg:.2f}[/bold]", "—")
        console.print(s_table)


async def evaluate_sample(
    sample: SingleTurnSample,
    faithfulness_metric: Faithfulness,
    answer_relevancy_metric: AnswerRelevancy,
    context_precision_metric: ContextPrecision,
    context_recall_metric: ContextRecall,
) -> ExperimentResult:
    contexts = normalize_contexts(sample.retrieved_contexts)

    answer_relevancy_res = await answer_relevancy_metric.ascore(
        user_input=sample.user_input,
        response=sample.response,
    )

    faithfulness = None
    context_precision = None
    context_recall = None

    if contexts:
        faithfulness_res = await faithfulness_metric.ascore(
            user_input=sample.user_input,
            response=sample.response,
            retrieved_contexts=contexts,
        )

        context_precision_res = await context_precision_metric.ascore(
            user_input=sample.user_input,
            reference=sample.reference,
            retrieved_contexts=contexts,
        )

        context_recall_res = await context_recall_metric.ascore(
            user_input=sample.user_input,
            reference=sample.reference,
            retrieved_contexts=contexts,
        )

        faithfulness = safe_score_value(faithfulness_res)
        context_precision = safe_score_value(context_precision_res)
        context_recall = safe_score_value(context_recall_res)

    return ExperimentResult(
        faithfulness=faithfulness,
        answer_relevancy=safe_score_value(answer_relevancy_res),
        context_precision=context_precision,
        context_recall=context_recall,
    )


async def main(
    subset: str | None,
    output_path: str,
    skip_generation: bool = False,
    generated_input: str | None = None,
) -> None:
    console.rule("[bold blue]LitGraph — Avaliação RAG")
    console.print(
        "[dim]Corpus: Platão · Aristóteles · Agostinho · Tomás de Aquino · "
        "Anselmo · Pascal · Kierkegaard · Nietzsche · Tolstói · Dostoiévski[/dim]\n"
    )

    questions = LABELED_QUESTIONS
    if subset:
        questions = [q for q in LABELED_QUESTIONS if q["subset"] == subset]
        console.print(
            f"[dim]Filtrando subset='{subset}': {len(questions)} perguntas[/dim]\n"
        )
    else:
        console.print(f"[dim]Total de perguntas: {len(questions)}[/dim]\n")

    rows: list[dict] = []

    if skip_generation:
        if not generated_input:
            raise ValueError(
                "Ao usar --skip-generation, informe --generated-input com o caminho do JSON."
            )

        generated_path = Path(generated_input)
        if not generated_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {generated_path}")

        console.print(
            f"[dim]Pulando geração e carregando respostas de:[/dim] {generated_path}"
        )
        payload = json.loads(generated_path.read_text(encoding="utf-8"))
        rows = payload.get("data", [])

        if not isinstance(rows, list) or not rows:
            raise ValueError(
                f"O arquivo {generated_path} não contém uma lista válida em 'data'."
            )

        if subset:
            rows = [r for r in rows if r.get("subset") == subset]
            console.print(
                f"[dim]Após filtro subset='{subset}': {len(rows)} respostas carregadas[/dim]\n"
            )

        if not rows:
            raise ValueError(
                "Nenhuma resposta disponível para avaliação após os filtros."
            )

        console.print(f"[green]✓ {len(rows)} respostas carregadas do disco.[/green]\n")

    else:
        console.print("[dim]Inicializando o grafo LitGraph…[/dim]")
        graph = build_graph()

        for item in track(questions, description="Executando perguntas…"):
            result = await run_single(
                graph,
                question=item["question"],
                student_level=item["student_level"],
                book_title=item.get("book_title", ""),
            )
            rows.append(
                {
                    "question": item["question"],
                    "ground_truth": item["ground_truth"],
                    "answer": result["answer"],
                    "contexts": result["contexts"],
                    "latency_s": result["latency_s"],
                    "subset": item["subset"],
                    "student_level": item["student_level"],
                    "book_title": item.get("book_title", ""),
                    "gutenberg_id": item["gutenberg_id"],
                }
            )

        console.print(f"\n[green]✓ {len(rows)} respostas coletadas.[/green]\n")

        generated_dir = Path("static/data/generated_data")
        generated_dir.mkdir(parents=True, exist_ok=True)

        generated_path = generated_dir / (
            f"generated_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        )
        generated_payload = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "n_examples": len(rows),
            "data": rows,
        }
        generated_path.write_text(
            json.dumps(generated_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        console.print(
            f"[bold cyan]Dados gerados salvos em:[/bold cyan] {generated_path}"
        )

    dataset = build_eval_dataset(rows)

    client = AsyncOpenAI()
    llm = llm_factory("gpt-4o-mini", client=client)
    embeddings = OpenAIEmbeddings(
        client=client,
        model="text-embedding-3-small",
    )

    faithfulness_metric = Faithfulness(llm=llm)
    answer_relevancy_metric = AnswerRelevancy(llm=llm, embeddings=embeddings)
    context_precision_metric = ContextPrecision(llm=llm)
    context_recall_metric = ContextRecall(llm=llm)

    console.print("[dim]Calculando métricas RAGAS…[/dim]")

    result_rows: list[dict] = []
    for idx, sample in enumerate(track(dataset.samples, description="Avaliando samples…"), 1):
        try:
            out = await evaluate_sample(
                sample=sample,
                faithfulness_metric=faithfulness_metric,
                answer_relevancy_metric=answer_relevancy_metric,
                context_precision_metric=context_precision_metric,
                context_recall_metric=context_recall_metric,
            )
            result_rows.append(
                {
                    "faithfulness": out.faithfulness,
                    "answer_relevancy": out.answer_relevancy,
                    "context_precision": out.context_precision,
                    "context_recall": out.context_recall,
                }
            )
        except Exception as e:
            console.print(
                f"[red]Erro ao avaliar sample #{idx}:[/red] {type(e).__name__}: {e}"
            )
            result_rows.append(
                {
                    "faithfulness": None,
                    "answer_relevancy": None,
                    "context_precision": None,
                    "context_recall": None,
                }
            )

    scores = {
        "faithfulness": mean_metric(result_rows, "faithfulness"),
        "answer_relevancy": mean_metric(result_rows, "answer_relevancy"),
        "context_precision": mean_metric(result_rows, "context_precision"),
        "context_recall": mean_metric(result_rows, "context_recall"),
    }

    metric_counts = {
        "faithfulness": sum(
            isinstance(r.get("faithfulness"), (int, float)) for r in result_rows
        ),
        "answer_relevancy": sum(
            isinstance(r.get("answer_relevancy"), (int, float)) for r in result_rows
        ),
        "context_precision": sum(
            isinstance(r.get("context_precision"), (int, float)) for r in result_rows
        ),
        "context_recall": sum(
            isinstance(r.get("context_recall"), (int, float)) for r in result_rows
        ),
    }

    print_results_table(scores, rows, metric_counts)

    output = {
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "subset_filter": subset,
        "skip_generation": skip_generation,
        "generated_input": generated_input,
        "n_questions": len(rows),
        "metrics": scores,
        "metric_counts": metric_counts,
        "latency": {
            "mean_s": round(sum(float(r["latency_s"]) for r in rows) / len(rows), 3),
            "min_s": round(min(float(r["latency_s"]) for r in rows), 3),
            "max_s": round(max(float(r["latency_s"]) for r in rows), 3),
        },
        "details": [
            {
                "question": r["question"],
                "subset": r["subset"],
                "student_level": r["student_level"],
                "gutenberg_id": r["gutenberg_id"],
                "latency_s": round(float(r["latency_s"]), 3),
                "n_chunks": len(normalize_contexts(r.get("contexts", []))),
                "answer_preview": str(r["answer"])[:300],
                "has_context": bool(normalize_contexts(r.get("contexts", []))),
            }
            for r in rows
        ],
    }

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    console.print(f"\n[bold green]Resultados salvos em:[/bold green] {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Avaliação RAG do LitGraph com RAGAS 0.4."
    )
    parser.add_argument(
        "--subset",
        choices=["qa", "guide"],
        default=None,
        help="Avaliar apenas 'qa' ou 'guide'.",
    )
    parser.add_argument(
        "--output",
        default="results/rag_eval.json",
        help="Caminho do JSON de saída.",
    )
    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help="Pula a geração e reutiliza um JSON salvo.",
    )
    parser.add_argument(
        "--generated-input",
        default=None,
        help="Caminho do JSON com respostas previamente geradas.",
    )

    args = parser.parse_args()

    asyncio.run(
        main(
            subset=args.subset,
            output_path=args.output,
            skip_generation=args.skip_generation,
            generated_input=args.generated_input,
        )
    )