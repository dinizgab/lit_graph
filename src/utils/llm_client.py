from typing import List

from openai import OpenAI
from src.models.models import BookPhilosophicalContext, NormalizedTitle


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
                        "retorne os campos 'original_title' "
                        "(título em inglês ou no idioma original da obra) "
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