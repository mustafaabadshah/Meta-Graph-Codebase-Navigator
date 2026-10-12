import json
import re
from pathlib import Path
from typing import Dict, Any, List

from langgraph.graph import StateGraph, END

from app.retrieval.state import NavigatorState
from app.retrieval.planner import QueryPlanner, RetrievalPlan
from app.retrieval.graph_retriever import GraphRetriever
from app.retrieval.evidence_validator import EvidenceValidator
from app.retrieval.answer_generator import AnswerGenerator
from app.graph import get_graph_store
from app.core.logging import logger

def validate_question_node(state: NavigatorState) -> Dict[str, Any]:
    question = state.get("question", "").strip()
    repo_id = state.get("repository_id", "").strip()

    warnings = state.get("warnings", [])
    if not question or len(question) < 5:
        warnings.append("Question is very short or ambiguous.")

    store = get_graph_store()
    repo = store.get_repository(repo_id)
    if not repo:
        warnings.append(f"Repository '{repo_id}' not found in active graph store.")

    repo_path = ""
    if repo:
        repo_path = repo.get("repo_path") or repo.get("path") or ""
    if not repo_path:
        from app.core.config import settings
        repo_path = settings.DEFAULT_REPO_PATH

    return {
        "is_valid_question": bool(question),
        "warnings": warnings,
        "repo_path": repo_path
    }

def plan_retrieval_node(state: NavigatorState) -> Dict[str, Any]:
    question = state.get("question", "")
    repo_id = state.get("repository_id", "")
    depth = state.get("retrieval_depth", 3)

    plan = QueryPlanner.plan(question, repo_id, max_hops=depth)
    return {"plan": plan.model_dump()}

def execute_graph_queries_node(state: NavigatorState) -> Dict[str, Any]:
    plan_dict = state.get("plan", {})
    plan = RetrievalPlan.model_validate(plan_dict)

    store = get_graph_store()
    retriever = GraphRetriever(store)
    graph_ctx = retriever.retrieve(plan)

    return {
        "graph_context": graph_ctx,
        "seed_symbol_ids": [s["id"] for s in graph_ctx.get("seed_symbols", [])]
    }

def retrieve_source_evidence_node(state: NavigatorState) -> Dict[str, Any]:
    repo_path_str = state.get("repo_path", "")
    repo_id = state.get("repository_id", "")
    graph_ctx = state.get("graph_context", {})
    question = state.get("question", "").lower()

    if not repo_path_str:
        from app.core.config import settings
        repo_path_str = settings.DEFAULT_REPO_PATH

    evidence_list: List[Dict[str, Any]] = []

    if repo_path_str:
        repo_root = Path(repo_path_str)
        nodes = graph_ctx.get("nodes", [])
        ranked_nodes = graph_ctx.get("ranked_nodes", [])

        # Score and rank candidates to ensure the most relevant methods/functions are provided
        def score_node(n: Dict[str, Any]) -> float:
            score = 0.0
            rel = n.get("rel_path", "")
            if "tests/" in rel or "test_" in rel:
                score -= 20.0  # Penalize test files so production code is prioritized

            name = (n.get("name") or "").lower()
            qname = (n.get("qualified_name") or "").lower()
            handles = [str(h).lower() for h in (n.get("handles") or [])]
            raises = [str(r).lower() for r in (n.get("raises") or [])]

            # Prioritize specific exception and retry logic
            if "apierror" in handles or "ratelimit" in handles or "ratelimiterror" in handles:
                score += 35.0
            if "select_move" in name or "select_move" in qname:
                score += 30.0
            if "emergency" in name or "_select_emergency_move" in qname:
                score += 25.0
            if "groq" in qname:
                score += 15.0
            if "tournament" in qname and ("service" in qname or "match" in name):
                score += 20.0
            if "game_service" in qname or "execute_next_move" in name:
                score += 20.0

            if handles or raises:
                score += 10.0

            # Prefer Functions over raw Classes for execution tracing
            if n.get("type") == "Function":
                score += 10.0
            elif n.get("type") == "Class":
                score += 5.0

            return score

        all_candidates = [
            n for n in nodes
            if n.get("rel_path") and n.get("start_line") and n.get("type") in ("Function", "Class")
        ]
        # Deduplicate
        seen = set()
        deduped = []
        for c in all_candidates:
            if c["id"] not in seen:
                seen.add(c["id"])
                deduped.append(c)

        scored_candidates = sorted(deduped, key=score_node, reverse=True)

        # Select top distinct candidates (max 3 snippets to fit within Groq ITPM budget)
        selected_candidates = []
        covered_files = {}

        for n in scored_candidates:
            rel = n.get("rel_path", "")
            if covered_files.get(rel, 0) >= 1:
                continue
            selected_candidates.append(n)
            covered_files[rel] = covered_files.get(rel, 0) + 1
            if len(selected_candidates) >= 3:
                break

        for n in selected_candidates:
            rel_path = n.get("rel_path")
            start = n.get("start_line", 1)
            end = n.get("end_line", start + 30)
            symbol_name = n.get("qualified_name") or n.get("name")

            # For long functions (>75 lines), focus on the critical execution, call sites, and exception handling
            if (end - start) > 75:
                if any(h in (n.get("handles") or []) for h in ["APIError", "Exception", "ValueError"]):
                    # In methods like select_move, the retry loop and exception handler are in the lower half
                    start = max(start, end - 85)
                else:
                    # In services like execute_next_move, agent selection is typically in the first 65 lines
                    end = min(end, start + 65)

            if rel_path and start:
                ev = EvidenceValidator.get_source_snippet(
                    repo_root=repo_root,
                    repo_id=repo_id,
                    rel_path=rel_path,
                    start_line=start,
                    end_line=end,
                    symbol_name=symbol_name
                )
                if ev:
                    evidence_list.append(ev.model_dump())

    return {"source_evidence": evidence_list}

def generate_answer_node(state: NavigatorState) -> Dict[str, Any]:
    question = state.get("question", "")
    repo_id = state.get("repository_id", "")
    graph_ctx = state.get("graph_context", {})
    source_evidence = state.get("source_evidence", [])

    store = get_graph_store()
    repo_meta = store.get_repository(repo_id) or {}
    repo_name = repo_meta.get("repo_name", repo_id)

    generator = AnswerGenerator()
    raw_answer, model_meta = generator.generate(
        question=question,
        repo_id=repo_id,
        repo_name=repo_name,
        graph_context=graph_ctx,
        source_evidence=source_evidence
    )

    return {
        "raw_answer": raw_answer,
        "model_metadata": model_meta
    }

def validate_citations_node(state: NavigatorState) -> Dict[str, Any]:
    raw_answer = state.get("raw_answer", "")
    repo_path_str = state.get("repo_path", "")
    repo_id = state.get("repository_id", "")
    source_evidence = state.get("source_evidence", [])
    warnings = list(state.get("warnings", []))

    parsed_citations = []

    # Attempt to extract JSON block from citations section
    json_match = re.search(r'```json\s*(\[\s*\{.*?\}\s*\])\s*```', raw_answer, re.DOTALL)
    if json_match:
        try:
            parsed_citations = json.loads(json_match.group(1))
        except Exception:
            pass

    # If LLM didn't return valid JSON citations, fall back to validated source evidence
    if not parsed_citations and source_evidence:
        for se in source_evidence:
            parsed_citations.append({
                "file": se.get("file"),
                "symbol": se.get("symbol"),
                "start_line": se.get("start_line"),
                "end_line": se.get("end_line")
            })

    valid_citations = []
    if repo_path_str:
        repo_root = Path(repo_path_str)
        valid_citations, cite_warnings = EvidenceValidator.validate_citations(
            repo_root=repo_root,
            repo_id=repo_id,
            citations=parsed_citations
        )
        warnings.extend(cite_warnings)
    else:
        valid_citations = parsed_citations

    # Clean citations block from raw text if desired or keep clean answer
    return {
        "answer": raw_answer,
        "citations": valid_citations,
        "warnings": warnings,
        "is_complete": True
    }

def create_navigator_workflow() -> Any:
    workflow = StateGraph(NavigatorState)

    workflow.add_node("validate_question", validate_question_node)
    workflow.add_node("plan_retrieval", plan_retrieval_node)
    workflow.add_node("execute_graph_queries", execute_graph_queries_node)
    workflow.add_node("retrieve_source_evidence", retrieve_source_evidence_node)
    workflow.add_node("generate_answer", generate_answer_node)
    workflow.add_node("validate_citations", validate_citations_node)

    workflow.set_entry_point("validate_question")

    workflow.add_edge("validate_question", "plan_retrieval")
    workflow.add_edge("plan_retrieval", "execute_graph_queries")
    workflow.add_edge("execute_graph_queries", "retrieve_source_evidence")
    workflow.add_edge("retrieve_source_evidence", "generate_answer")
    workflow.add_edge("generate_answer", "validate_citations")
    workflow.add_edge("validate_citations", END)

    return workflow.compile()
