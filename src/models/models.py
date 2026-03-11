from pydantic import BaseModel, Field
from typing import List


class Author(BaseModel):
    name: str
    birth_year: int | None = None
    death_year: int | None = None


class BookBibliographicContext(BaseModel):
    gutenberg_id: int = Field(alias="id")
    title: str
    authors: List[Author] = []
    summaries: List[str] = []
    subjects: List[str] = []
    languages: List[str] = []

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
    
    
class NormalizedTitle(BaseModel):
    original_title: str
    author_lastname: str