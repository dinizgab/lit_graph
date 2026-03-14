from typing import Any, Dict, List

from openai import OpenAI
from src.models.models import BookBibliographicContext, BookHistoricalContext, BookPhilosophicalContext, NormalizedTitle, RouteDecision, SelfCheckResult


class LLMClient():
    def __init__(self, model: str = "gpt-5.4"):
        self.model = model
        self.client = OpenAI()
    
    def normalize_title(self, query: str) -> dict:
        response = self.client.responses.parse(
            model="gpt-5.4",
            input=[
                {
                    "role": "system",
                    "content": (
                        "Você é um especialista em literatura clássica. "
                        "Dado um título de obra literária em qualquer idioma, "
                        "retorne os campos 'original_title' (título em inglês)"
                        "e 'author_lastname' (sobrenome do autor em inglês)."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Obra: {query}",
                },
            ],
            text_format=NormalizedTitle,
        )
        
        parsed = response.output_parsed

        if parsed is None:
            raise ValueError("Falha ao estruturar resposta do modelo.")
        
        return parsed.model_dump()
    
    def generate_philosophical_context(self, title: str, summaries: List[str], subjects: list[str]) -> BookPhilosophicalContext:
        payload = {
            "title": title,
            "summary": summaries[0] if summaries else "",
            "subjects": subjects,
        }
    
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Você é um especialista em filosofia e literatura. "
                        "Dada uma obra literária, identifique de 3 a 5 temas filosóficos plausíveis, "
                        "explique brevemente cada um e atribua um confidence de 0 a 1. "
                        "Não trate interpretações como fatos históricos. "
                        "As interpretações devem ser plausíveis com base no resumo e nos temas."
                    ),
                },
                {
                    "role": "user",
                    "content": str(payload),
                },
            ],
            text_format=BookPhilosophicalContext,
        )

        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("Falha ao gerar contexto filosófico.")

        return parsed
    
    
    def decide_route(self, query: str) -> str:
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente de roteamento para um sistema de perguntas e respostas sobre livros. "
                        "Dada uma consulta do usuário, decida se ela deve ser tratada como 'qa' (pergunta direta), "
                        "'guide' (pedido de orientação sobre como abordar a obra) ou 'refuse' (consulta fora do escopo)."
                        "Responda apenas com uma das três opções, sem explicações adicionais."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Consulta: {query}",
                },
            ],
            text_format=RouteDecision,
        )

        route = response.output_parsed
        if route is None:
            raise ValueError("Falha ao decidir rota para a consulta.")
        
        return route.intent
    
    
    def create_study_guide(
        self,
        bibliographic_context: BookBibliographicContext,
        historical_context: BookHistoricalContext,
        philosophical_context: BookPhilosophicalContext,
        student_level: str,
    ) -> str:
        authors = ", ".join(
            author.name if author.name else "desconhecido"
            for author in (bibliographic_context.authors if bibliographic_context.authors else [])
        ) or "desconhecidos"

        summaries = bibliographic_context.summaries 
        summary_text = " | ".join(summaries[:2]) if summaries else "Não disponível"

        subjects = bibliographic_context.subjects if bibliographic_context.subjects else []
        subject_text = ", ".join(subjects[:5]) if subjects else "Não disponíveis"

        historical_summary = historical_context.summary if historical_context.summary else "Não disponível"
        historical_summary = historical_summary[:400] if historical_summary else "Não disponível"

        themes = [theme.theme for theme in philosophical_context.themes] if philosophical_context.themes else []
        themes_text = ", ".join(themes) if themes else "Não disponíveis"

        context_block = f"""
            Obra: {bibliographic_context.title if bibliographic_context.title else 'desconhecida'}
            Autores: {authors}
            Resumos: {summary_text}
            Temas: {subject_text}
            Contexto histórico: {historical_summary}
            Temas filosóficos: {themes_text}
            """

        prompt = f"""
            Você é um especialista em literatura clássica.

            Com base exclusivamente no contexto abaixo, gere um guia de estudo para nível
            '{student_level}' com as seções:

            1. Resumo narrativo (3-5 parágrafos)
            2. Personagens principais (nome + papel + traço central)
            3. Temas centrais (3-5 temas com explicação)
            4. Trechos/passagens-chave (com indicação de onde encontrar)
            5. Perguntas de revisão (5 perguntas abertas)

            Regras:
            - Não invente fatos que não estejam apoiados no contexto.
            - Quando houver incerteza, sinalize isso claramente.
            - Escreva em português.
            - Ao final de cada seção, indique brevemente de quais fontes do contexto a informação veio
            (ex.: gutendex, wikipedia, contexto histórico, contexto filosófico).

            Contexto:
            {context_block}
        """

        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Você produz guias de estudo claros, fiéis ao contexto fornecido "
                        "e apropriados ao nível do estudante."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        if not response.output_text:
            raise ValueError("Falha ao gerar guia de estudo.")

        return response.output_text.strip()
    
    
    def self_check_answer(
        self,
        user_query: str,
        draft_answer: str,
        retrieved_chunks: List[str],
        book_title: str = "",
        student_level: str = "curioso",
    ) -> SelfCheckResult:
        if not retrieved_chunks:
            return SelfCheckResult(
                grounded=False,
                confidence=0.0,
                issues=[],
                suggested_action="retry",
                final_answer=(
                    "Não foi possível encontrar evidências suficientes para responder com segurança. "
                    "Tente reformular sua pergunta."
                ),
            )

        evidence_block = "\n\n".join(
            f"[EVIDÊNCIA {idx + 1}]\n{chunk}"
            for idx, chunk in enumerate(retrieved_chunks[:8])
            if chunk and chunk.strip()
        )

        prompt = f"""
        Avalie se a resposta abaixo está adequadamente sustentada pelas evidências fornecidas.

        Regras:
        - Considere como sustentado apenas o que puder ser inferido de forma razoável a partir das evidências.
        - Marque como problemático qualquer trecho inventado, específico demais, ou não suportado.
        - Se a resposta estiver boa, retorne grounded=true e suggested_action='accept'.
        - Se a resposta estiver parcialmente boa, mas precisar pequenos ajustes, retorne suggested_action='revise'
        e produza em final_answer uma versão corrigida e mais fiel às evidências.
        - Se a resposta estiver fraca ou sem base suficiente, retorne suggested_action='retry'.
        - Não use conhecimento externo. Julgue apenas com base nas evidências.
        - Escreva tudo em português.

        Metadados:
        - Pergunta do usuário: {user_query}
        - Título da obra: {book_title}
        - Nível do aluno: {student_level}

        Resposta gerada:
        {draft_answer}

        Evidências recuperadas:
        {evidence_block}
        """

        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Você é um verificador rigoroso de grounding em um sistema RAG literário. "
                        "Sua função é validar se a resposta está sustentada pelas evidências recuperadas, "
                        "sem usar conhecimento externo."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            text_format=SelfCheckResult,
        )

        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("Falha ao executar self-check da resposta.")

        return parsed