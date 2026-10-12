import pytest
from pathlib import Path

from app.retrieval.planner import QueryPlanner
from app.retrieval.lexical_retriever import LexicalRetriever
from app.retrieval.graph_retriever import GraphRetriever
from app.retrieval.evidence_validator import EvidenceValidator
from app.graph import get_graph_store

def test_query_planner():
    q = "How does the application handle a Groq API rate limit when an agent is playing a tournament?"
    plan = QueryPlanner.plan(q, "agent_chess")

    assert plan.repository_id == "agent_chess"
    assert "groq" in [t.lower() for t in plan.target_terms]
    assert plan.look_for_exceptions is True
    assert plan.look_for_retries is True
    assert plan.look_for_tournaments is True

def test_structural_retrieval_agent_chess():
    store = get_graph_store()
    # Check if agent_chess has been ingested
    stats = store.get_graph_statistics("agent_chess")
    if stats["total_nodes"] == 0:
        pytest.skip("Agent Chess not yet indexed in active store.")

    plan = QueryPlanner.plan(
        "How does the application handle a Groq API rate limit when an agent is playing a tournament?",
        "agent_chess"
    )

    retriever = GraphRetriever(store)
    result = retriever.retrieve(plan)

    assert len(result["nodes"]) > 0
    assert len(result["edges"]) > 0

    # Ensure relevant GroqAgent and Tournament symbols are in retrieved context
    qnames = [str(n.get("qualified_name") or n.get("name") or "") for n in result["nodes"]]
    assert any("groq" in q.lower() or "select_move" in q.lower() for q in qnames)

def test_evidence_validator_agent_chess():
    repo_root = Path(r"E:\MM Office\Agent Chess")
    evidence = EvidenceValidator.get_source_snippet(
        repo_root=repo_root,
        repo_id="agent_chess",
        rel_path="backend/app/agents/groq_agent.py",
        start_line=50,
        end_line=70,
        symbol_name="GroqChessAgent.select_move"
    )

    assert evidence is not None
    assert evidence.is_valid is True
    assert "def select_move" in evidence.snippet or "class GroqChessAgent" in evidence.snippet
    assert evidence.file_hash != ""
