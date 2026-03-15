from typing import Any, Dict, List

from langsmith import traceable
from openai import OpenAI
from src.models.models import BookBibliographicContext, BookHistoricalContext, BookPhilosophicalContext, NormalizedTitle, RouteDecision, SelfCheckResult, StudyChecklist, StudyGuideExtraction, StudyPlan


class LLMClient():
    def __init__(self, model: str = "gpt-5-mini-2025-08-07"):
        self.model = model
        self.client = OpenAI()
        
    @traceable(run_type="llm", name="normalize_title")
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
    
    @traceable(run_type="llm", name="decide_route")    
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
    
    
    @traceable(run_type="llm", name="self_check_answer")
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
    
    @traceable(run_type="llm", name="answer_question_with_context")
    def answer_question_with_context(
        self,
        user_query: str,
        book_title: str,
        bibliographic_context: BookBibliographicContext,
        historical_context: BookHistoricalContext,
        philosophical_context: BookPhilosophicalContext,
        retrieved_chunks: List[str],
        student_level: str = "curioso",
    ) -> str:
        authors = ", ".join(
            author.name for author in bibliographic_context.authors
        ) or "desconhecidos"

        themes = ", ".join(
            theme.theme for theme in philosophical_context.themes
        ) if philosophical_context.themes else "não disponíveis"

        evidence_block = "\n\n".join(
            f"[EVIDÊNCIA {idx + 1}]\n{chunk}"
            for idx, chunk in enumerate(retrieved_chunks[:8])
            if chunk and chunk.strip()
        )

        historical_summary = historical_context.summary if historical_context else ""
        historical_summary = historical_summary[:500] if historical_summary else ""

        prompt = f"""
            Você é um assistente de leitura de obras clássicas.

            Responda à pergunta do usuário usando exclusivamente o contexto e as evidências fornecidas.

            Regras:
            - Não invente fatos.
            - Se a evidência for insuficiente, diga isso claramente.
            - Priorize as evidências recuperadas.
            - Escreva em português.
            - Seja objetivo, mas útil.
            - Não use conhecimento externo.
            - Considere o nível do leitor: {student_level}.

            Pergunta do usuário:
            {user_query}

            Dados da obra:
            - Título: {book_title}
            - Autores: {authors}
            - Temas filosóficos plausíveis: {themes}
            - Contexto histórico resumido: {historical_summary}

            Evidências recuperadas:
            {evidence_block}
        """

        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Você responde perguntas sobre literatura clássica apenas com base "
                        "nas evidências fornecidas, mantendo fidelidade factual."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        if not response.output_text:
            raise ValueError("Falha ao gerar resposta para a pergunta do usuário.")

        return response.output_text.strip()
    
    def _build_context_block(
        self,
        bibliographic_context: BookBibliographicContext,
        historical_context: BookHistoricalContext,
        philosophical_context: BookPhilosophicalContext,
        retrieved_chunks: List[str],
    ) -> str:
        authors = ", ".join(
            author.name for author in bibliographic_context.authors
        ) or "desconhecidos"

        summaries = " | ".join(bibliographic_context.summaries[:2]) if bibliographic_context.summaries else "Não disponível"
        subjects = ", ".join(bibliographic_context.subjects[:8]) if bibliographic_context.subjects else "Não disponíveis"
        hist = historical_context.summary[:500] if historical_context and historical_context.summary else "Não disponível"
        themes = ", ".join(t.theme for t in philosophical_context.themes) if philosophical_context and philosophical_context.themes else "Não disponíveis"

        evidence_block = "\n\n".join(
            f"[EVIDÊNCIA {idx + 1}]\n{chunk}"
            for idx, chunk in enumerate(retrieved_chunks[:8])
            if chunk and chunk.strip()
        ) or "Sem evidências textuais disponíveis."

        return f"""
            Obra: {bibliographic_context.title}
            Autores: {authors}
            Resumos: {summaries}
            Assuntos: {subjects}
            Contexto histórico: {hist}
            Temas filosóficos plausíveis: {themes}

            Trechos recuperados:
            {evidence_block}
            """

    @traceable(run_type="llm", name="build_study_plan")
    def build_study_plan(
        self,
        bibliographic_context: BookBibliographicContext,
        historical_context: BookHistoricalContext,
        philosophical_context: BookPhilosophicalContext,
        retrieved_chunks: List[str],
        student_level: str,
    ) -> StudyPlan:
        context_block = self._build_context_block(
            bibliographic_context,
            historical_context,
            philosophical_context,
            retrieved_chunks,
        )

        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Você monta planos de leitura objetivos para literatura clássica, "
                        "adequados ao nível do estudante."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""
                    Monte um plano de estudo em etapas para o nível '{student_level}'.

                    Regras:
                    - Crie de 4 a 6 passos.
                    - Cada passo deve ter título e objetivo.
                    - O plano deve ser realista e sequencial.
                    - Use apenas o contexto fornecido.

                    Contexto:
                    {context_block}
                    """,
                },
            ],
            text_format=StudyPlan,
        )

        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("Falha ao gerar plano de estudo.")
        return parsed

    @traceable(run_type="llm", name="extract_study_guide_elements")
    def extract_study_guide_elements(
        self,
        bibliographic_context: BookBibliographicContext,
        historical_context: BookHistoricalContext,
        philosophical_context: BookPhilosophicalContext,
        retrieved_chunks: List[str],
        student_level: str,
    ) -> StudyGuideExtraction:
        context_block = self._build_context_block(
            bibliographic_context,
            historical_context,
            philosophical_context,
            retrieved_chunks,
        )

        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Você extrai elementos de guia de estudo a partir de evidências, "
                        "sem inventar fatos."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""
                    Extraia um guia estruturado para o nível '{student_level}'.

                    Retorne:
                    - narrative_summary
                    - characters
                    - themes
                    - key_passages
                    - review_questions

                    Regras:
                    - Use apenas o contexto fornecido.
                    - Cada personagem, tema e passagem deve incluir um evidence_excerpt curto.
                    - Se algo não estiver claro, seja conservador.

                    Contexto:
                    {context_block}
                    """,
                },
            ],
            text_format=StudyGuideExtraction,
        )

        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("Falha ao extrair elementos do guia.")
        return parsed

    @traceable(run_type="llm", name="build_revision_checklist")
    def build_revision_checklist(
        self,
        plan: StudyPlan,
        extraction: StudyGuideExtraction,
        student_level: str,
    ) -> StudyChecklist:
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Você transforma um plano de estudo em checklist de revisão objetivo."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""
                    Nível: {student_level}

                    Plano:
                    {plan.model_dump_json(indent=2)}

                    Extração:
                    {extraction.model_dump_json(indent=2)}

                    Crie uma checklist enxuta com 5 a 8 itens.
                    Cada item deve indicar o que revisar e por quê.
                    """,
                },
            ],
            text_format=StudyChecklist,
        )

        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("Falha ao gerar checklist.")
        return parsed

    @traceable(run_type="llm", name="render_structured_study_guide")
    def render_structured_study_guide(
        self,
        bibliographic_context: BookBibliographicContext,
        plan: StudyPlan,
        extraction: StudyGuideExtraction,
        checklist: StudyChecklist,
        student_level: str,
    ) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Você escreve um relatório final de estudo claro, estruturado e fiel "
                        "aos dados fornecidos."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""
            Monte um guia final em português para o nível '{student_level}'.

            Título da obra: {bibliographic_context.title}

            Use exatamente estas seções:
            1. Objetivo de leitura
            2. Plano de estudo
            3. Resumo narrativo
            4. Personagens principais
            5. Temas centrais
            6. Passagens-chave
            7. Perguntas de revisão
            8. Checklist final

            Dados:
            PLANO:
            {plan.model_dump_json(indent=2)}

            EXTRAÇÃO:
            {extraction.model_dump_json(indent=2)}

            CHECKLIST:
            {checklist.model_dump_json(indent=2)}

            Regras:
            - Não invente fatos.
            - Seja claro e didático.
            - Mantenha estrutura fixa.
            - Não mencione JSON.
            """,
                },
            ],
        )

        if not response.output_text:
            raise ValueError("Falha ao renderizar guia final.")

        return response.output_text.strip()