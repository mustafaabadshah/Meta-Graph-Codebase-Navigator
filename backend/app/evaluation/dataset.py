from typing import List, Dict, Any
from pydantic import BaseModel, Field

class BenchmarkQuestion(BaseModel):
    id: str
    question: str
    repository_id: str
    category: str
    expected_symbols: List[str]
    expected_files: List[str]
    required_concepts: List[str]

AGENT_CHESS_BENCHMARK: List[BenchmarkQuestion] = [
    BenchmarkQuestion(
        id="q1_groq_rate_limit",
        question="How does the application handle a Groq API rate limit when an agent is playing a tournament? Trace the execution path, identify retry and exception-handling logic, explain what happens when retries are exhausted, and cite every relevant file, function, and line number.",
        repository_id="agent_chess",
        category="exception_handling_and_retries",
        expected_symbols=["GroqChessAgent.select_move", "APIError", "_select_emergency_move"],
        expected_files=["backend/app/agents/groq_agent.py"],
        required_concepts=["429", "backoff", "exponential", "fallback", "emergency"]
    ),
    BenchmarkQuestion(
        id="q2_move_validation",
        question="How does the chess move validation engine verify legal moves, and how does the agent recover when an illegal move is returned by the LLM?",
        repository_id="agent_chess",
        category="function_call_and_correction",
        expected_symbols=["validate_move", "GroqChessAgent.select_move"],
        expected_files=["backend/app/chess/validator.py", "backend/app/agents/groq_agent.py"],
        required_concepts=["validate_move", "correction", "legal", "illegal"]
    ),
    BenchmarkQuestion(
        id="q3_tournament_bracket",
        question="Explain how TournamentService sets up tournament bracket matches and transitions into game execution.",
        repository_id="agent_chess",
        category="multi_file_architecture",
        expected_symbols=["TournamentService", "game_service"],
        expected_files=["backend/app/services/tournament_service.py", "backend/app/services/game_service.py"],
        required_concepts=["bracket", "create_tournament", "game_service"]
    )
]
