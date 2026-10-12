import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class RetrievalPlan(BaseModel):
    raw_question: str
    repository_id: str
    target_terms: List[str] = Field(default_factory=list)
    candidate_symbols: List[str] = Field(default_factory=list)
    look_for_exceptions: bool = False
    look_for_retries: bool = False
    look_for_tournaments: bool = False
    max_hops: int = 3
    max_nodes: int = 50

class QueryPlanner:
    """
    Analyzes natural-language architectural questions to construct
    a bounded, structural retrieval plan.
    """
    EXCEPTION_KEYWORDS = {"error", "exception", "rate limit", "ratelimit", "429", "timeout", "retry", "exhaust", "fail", "fallback"}
    RETRY_KEYWORDS = {"retry", "backoff", "attempts", "exhausted", "loop", "wait", "rate limit", "ratelimit", "limit"}
    TOURNAMENT_KEYWORDS = {"tournament", "match", "game", "round", "bracket"}

    @classmethod
    def plan(cls, question: str, repository_id: str, max_hops: int = 3, max_nodes: int = 50) -> RetrievalPlan:
        q_lower = question.lower()

        # Extract potential identifiers: CamelCase, snake_case, dotted.names
        identifier_pattern = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+|[A-Z][a-zA-Z0-9]+|[a-z0-9_]{3,}')
        raw_tokens = identifier_pattern.findall(question)
        
        # Stopwords
        stopwords = {
            "how", "does", "the", "application", "handle", "when", "an", "agent",
            "is", "trace", "execution", "path", "identify", "and", "logic",
            "explain", "what", "happens", "cite", "every", "relevant", "file",
            "function", "line", "number", "numbers", "find", "show", "tell", "which",
            "where", "why", "who", "are", "with", "this", "that", "from", "into"
        }

        target_terms = [t for t in raw_tokens if t.lower() not in stopwords]

        look_for_exceptions = any(kw in q_lower for kw in cls.EXCEPTION_KEYWORDS)
        look_for_retries = any(kw in q_lower for kw in cls.RETRY_KEYWORDS)
        look_for_tournaments = any(kw in q_lower for kw in cls.TOURNAMENT_KEYWORDS)

        return RetrievalPlan(
            raw_question=question,
            repository_id=repository_id,
            target_terms=target_terms,
            candidate_symbols=target_terms,
            look_for_exceptions=look_for_exceptions,
            look_for_retries=look_for_retries,
            look_for_tournaments=look_for_tournaments,
            max_hops=max_hops,
            max_nodes=max_nodes
        )
