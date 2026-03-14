from typing import Literal, TypedDict

from src.models.models import BookBibliographicContext, BookHistoricalContext, BookPhilosophicalContext


class LitGraphState(TypedDict, total=False):
    user_query: str
    book_title: str
    student_level: Literal["fundamental", "medio", "superior", "curioso"]
    
    intent: Literal["qa", "guide", "refuse", ""]
    
    retrieved_chunks: list[str]
    retrieval_sources: list[dict]
    
    bibliographic_context: BookBibliographicContext
    historical_context: BookHistoricalContext
    philosophical_context: BookPhilosophicalContext
    
    draft_answer: str
    citations: list[dict]
    
    self_check_passed: bool
    self_check_attempts: int
 
    final_answer: str
    error: str