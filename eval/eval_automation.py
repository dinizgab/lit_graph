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

from rich.console import Console
from rich.progress import track
from rich.table import Table

from eval.dataset import LABELED_QUESTIONS
from src.graph.graph import build_graph
from src.graph.state import LitGraphState

console = Console()

EXPECTED_STEPS = {
    "build_study_plan",
    "extract_study_guide_elements",
    "build_revision_checklist",
    "render_structured_study_guide",
}

ERROR_PHRASES = [
    "desculpe",
    "só consigo responder",
    "não foi possível",
    "error calling tool",
    "sem resposta",
]


def _is_error_output(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in ERROR_PHRASES)


async def run_automation_task(
    graph: Any,
    question: str,
    book_title: str,
    student_level: str,
) -> dict:
    initial_state = LitGraphState({
        "user_query": question,
        "book_title": book_title,
        "student_level": student_level,
        "self_check_attempts": 0,
        "enable_self_check": True,
    })

    t0 = time.perf_counter()
    try:
        result = await graph.ainvoke(initial_state)
        latency = time.perf_counter() - t0
        error = None
    except Exception as e:
        latency = time.perf_counter() - t0
        return {
            "success": False,
            "steps_count": 0,
            "steps_ok": [],
            "missing_steps": list(EXPECTED_STEPS),
            "has_output": False,
            "latency_s": round(latency, 3),
            "error": f"{type(e).__name__}: {e}",
            "answer_preview": "",
        }

    trace: list[str] = result.get("automation_trace") or []
    steps_count: int = result.get("automation_steps_count") or len(trace)
    final_answer: str = result.get("final_answer") or result.get("error") or ""

    steps_ok = [s for s in trace if s in EXPECTED_STEPS]
    missing_steps = sorted(EXPECTED_STEPS - set(trace))
    has_output = bool(final_answer) and not _is_error_output(final_answer)

    success = len(missing_steps) == 0 and has_output

    return {
        "success": success,
        "steps_count": steps_count,
        "steps_ok": steps_ok,
        "missing_steps": missing_steps,
        "has_output": has_output,
        "latency_s": round(latency, 3),
        "error": None if not result.get("error") else result["error"],
        "answer_preview": final_answer[:300],
    }


def print_automation_table(tasks: list[dict], results: list[dict]) -> None:
    table = Table(
        title="Avaliação de Automação — subset 'guide'",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("#", width=3)
    table.add_column("Tarefa", min_width=40)
    table.add_column("Nível", width=10)
    table.add_column("Sucesso", width=8)
    table.add_column("Steps", width=6, justify="right")
    table.add_column("Lat (s)", width=8, justify="right")
    table.add_column("Etapas faltando", min_width=20, style="dim")

    for i, (task, res) in enumerate(zip(tasks, results), 1):
        success_icon = "[green]✓[/green]" if res["success"] else "[red]✗[/red]"
        missing = ", ".join(res["missing_steps"]) if res["missing_steps"] else "—"
        table.add_row(
            str(i),
            task["question"][:60],
            task["student_level"],
            success_icon,
            str(res["steps_count"]),
            f"{res['latency_s']:.2f}",
            missing,
        )

    console.print(table)

    n = len(results)
    n_success = sum(1 for r in results if r["success"])
    avg_steps = sum(r["steps_count"] for r in results) / n if n else 0
    avg_lat = sum(r["latency_s"] for r in results) / n if n else 0

    summary = Table(title="Resumo", show_header=True, header_style="bold cyan")
    summary.add_column("Métrica", style="cyan", min_width=30)
    summary.add_column("Valor", justify="right", style="green")
    summary.add_column("Interpretação", style="dim")

    summary.add_row(
        "taxa_de_sucesso",
        f"{n_success}/{n} ({100 * n_success / n:.0f}%)" if n else "N/A",
        "Tarefas com todas as 4 etapas + output válido",
    )
    summary.add_row(
        "steps_médios",
        f"{avg_steps:.1f}",
        "Etapas completadas por execução (máx: 4)",
    )
    summary.add_row(
        "latência_média_s",
        f"{avg_lat:.2f}",
        "Tempo médio de execução por tarefa",
    )

    console.print(summary)


async def main(output_path: str) -> None:
    console.rule("[bold blue]LitGraph — Avaliação de Automação")

    guide_tasks = [q for q in LABELED_QUESTIONS if q["subset"] == "guide"]
    console.print(f"[dim]{len(guide_tasks)} tarefas no subset 'guide'[/dim]\n")

    console.print("[dim]Inicializando o grafo LitGraph…[/dim]")
    graph = build_graph()

    results = []
    for task in track(guide_tasks, description="Executando tarefas de automação…"):
        res = await run_automation_task(
            graph=graph,
            question=task["question"],
            book_title=task.get("book_title", ""),
            student_level=task["student_level"],
        )
        results.append(res)

    console.print(f"\n[green]✓ {len(results)} tarefas executadas.[/green]\n")

    print_automation_table(guide_tasks, results)

    # Monta output JSON
    n = len(results)
    n_success = sum(1 for r in results if r["success"])
    avg_steps = round(sum(r["steps_count"] for r in results) / n, 2) if n else 0
    avg_lat = round(sum(r["latency_s"] for r in results) / n, 3) if n else 0

    output = {
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "n_tasks": n,
        "metrics": {
            "success_rate": round(n_success / n, 4) if n else 0,
            "n_success": n_success,
            "avg_steps": avg_steps,
            "avg_latency_s": avg_lat,
            "min_latency_s": round(min(r["latency_s"] for r in results), 3) if results else 0,
            "max_latency_s": round(max(r["latency_s"] for r in results), 3) if results else 0,
        },
        "details": [
            {
                "question": task["question"],
                "book_title": task.get("book_title", ""),
                "student_level": task["student_level"],
                "gutenberg_id": task.get("gutenberg_id"),
                **res,
            }
            for task, res in zip(guide_tasks, results)
        ],
    }

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"\n[bold green]Resultado salvo em:[/bold green] {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Avaliação do workflow de automação do LitGraph.")
    parser.add_argument(
        "--output",
        default="result/automation_eval_0001.json",
        help="Caminho do JSON de saída.",
    )
    args = parser.parse_args()
    asyncio.run(main(output_path=args.output)) 