import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from app.core.config import settings
from app.core.logging import logger
from app.schemas.query import QueryRequest, QueryResponse, CitationItem
from app.retrieval.workflow import create_navigator_workflow
from app.graph import get_graph_store

class QueryService:
    def __init__(self):
        self.workflow = create_navigator_workflow()
        self.history_file = settings.CACHE_DIR / "query_history.json"
        self._ensure_history_file()

    def _ensure_history_file(self):
        settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if not self.history_file.is_file():
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _save_to_history(self, record: Dict[str, Any]):
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            history.insert(0, record)
            # Keep last 50 queries
            history = history[:50]
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to record query history: {e}")

    def get_query_history(self) -> List[Dict[str, Any]]:
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    async def execute_query(self, req: QueryRequest) -> QueryResponse:
        inputs = {
            "question": req.question,
            "repository_id": req.repository_id,
            "retrieval_depth": req.retrieval_depth,
            "detail_level": req.detail_level
        }

        # Run compiled LangGraph state workflow
        res = self.workflow.invoke(inputs)

        answer_text = res.get("answer", "")
        raw_citations = res.get("citations", [])
        graph_ctx = res.get("graph_context", {})

        citations = [
            CitationItem(
                repository=c.get("repository", req.repository_id),
                file=c.get("file", ""),
                symbol=c.get("symbol"),
                start_line=c.get("start_line", 1),
                end_line=c.get("end_line", 1),
                evidence_type=c.get("evidence_type", "verified_source")
            )
            for c in raw_citations
        ]

        # Extract bounded subgraph for React Flow rendering
        subgraph_nodes = graph_ctx.get("nodes", [])[:40]
        subgraph_edges = graph_ctx.get("edges", [])[:60]

        response = QueryResponse(
            repository_id=req.repository_id,
            question=req.question,
            answer=answer_text,
            citations=citations,
            retrieved_symbols=graph_ctx.get("seed_symbols", []),
            graph_subgraph={
                "nodes": subgraph_nodes,
                "edges": subgraph_edges
            },
            execution_flow=res.get("execution_flow", []),
            warnings=res.get("warnings", []),
            model_metadata=res.get("model_metadata", {})
        )

        # Log query to history
        self._save_to_history({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "repository_id": req.repository_id,
            "question": req.question,
            "citations_count": len(citations),
            "model": response.model_metadata.get("model", "unknown"),
            "latency_ms": response.model_metadata.get("latency_ms", 0)
        })

        return response

query_service = QueryService()
