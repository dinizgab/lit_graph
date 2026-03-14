from pydantic import BaseModel, Field
from typing import List, Literal


class Author(BaseModel):
    name: str
    birth_year: int | None = None
    death_year: int | None = None


class BookBibliographicContext(BaseModel):
    gutenberg_id: int = Field(alias="id")
    title: str
    authors: List[Author] = Field(default_factory=list)
    summaries: List[str] = Field(default_factory=list)
    subjects: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
    
    
class PhilosophicalTheme(BaseModel):
    theme: str
    explanation: str
    confidence: float


class BookPhilosophicalContext(BaseModel):
    work_title: str
    source: str
    themes: List[PhilosophicalTheme] = Field(default_factory=list)
    note: str


class BookHistoricalContext(BaseModel):
    work_title: str
    source: str
    summary: str
    historical_period: str | None = None
    cultural_context: str | None = None
    
    
class NormalizedTitle(BaseModel):
    original_title: str
    author_lastname: str | None = None
    
    
class UnsupportedClaim(BaseModel):
    claim_excerpt: str = Field(description="Trecho da resposta que parece não estar sustentado pelas evidências")
    reason: str = Field(description="Por que o trecho parece inadequado, inventado ou fraco")
    severity: Literal["low", "medium", "high"]


class SelfCheckResult(BaseModel):
    grounded: bool = Field(description="Se a resposta está adequadamente sustentada pelos trechos recuperados")
    confidence: float = Field(description="Confiança de 0 a 1 na avaliação")
    issues: List[UnsupportedClaim] = Field(default_factory=list)
    suggested_action: Literal["accept", "retry", "revise"] = Field(
        description="accept = pode seguir; retry = buscar novamente; revise = regenerar com as mesmas evidências"
    )
    final_answer: str = Field(
        description="Resposta final aprovada ou versão revisada da resposta, sempre em português"
    )