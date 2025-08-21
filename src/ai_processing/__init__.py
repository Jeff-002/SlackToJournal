"""AI processing module using Gemini 2.5 for content analysis."""

from .client import GeminiClient
from .service import AIProcessingService
from .schemas import AIRequest, AIResponse, WorkItem, JournalStructure
from .prompts import PromptTemplate, JournalPrompts

__all__ = [
    "GeminiClient",
    "AIProcessingService",
    "AIRequest",
    "AIResponse",
    "WorkItem",
    "JournalStructure",
    "PromptTemplate",
    "JournalPrompts"
]