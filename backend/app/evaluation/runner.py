import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

from app.core.config import settings
from app.core.logging import logger
from app.evaluation.dataset import AGENT_CHESS_BENCHMARK, BenchmarkQuestion
from app.services.query_service import query_service
from app.schemas.query import QueryRequest

class EvaluationRunner:
    def __init__(self):
        self.eval_dir = settings.EVALUATIONS_DIR
        self.eval_dir.mkdir(parents=True, exist_ok=True)

    def list_evaluation_runs(self) -> List[Dict[str, Any]]:
        runs = []
        for f in self.eval_dir.glob("eval_*.json"):
            try:
                with open(f, "r", encoding="utf-8") as rf:
                    runs.append(json.load(rf))
            except Exception:
                pass
        # Sort newest first
        runs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return runs

    async def run_benchmark(self, repo_id: str = "agent_chess") -> Dict[str, Any]:
        run_id = f"eval_{int(time.time())}"
        start_time = datetime.now(timezone.utc).isoformat()

        results = []
        total_symbol_hits = 0
        total_symbol_expected = 0
        total_file_hits = 0
        total_file_expected = 0
        total_valid_citations = 0
        total_citations = 0
        total_latency_ms = 0

        for bq in AGENT_CHESS_BENCHMARK:
            q_start = time.perf_counter()
            try:
                req = QueryRequest(
                    repository_id=repo_id,
                    question=bq.question,
                    retrieval_depth=3,
                    detail_level="detailed"
                )
                resp = await query_service.execute_query(req)
                elapsed_ms = int((time.perf_counter() - q_start) * 1000)
                total_latency_ms += elapsed_ms

                # Check expected symbols
                retrieved_symbols = [s.get("name") or s.get("qualified_name") or "" for s in resp.retrieved_symbols]
                retrieved_symbols.extend([c.symbol or "" for c in resp.citations])
                retrieved_text = " ".join(retrieved_symbols).lower() + " " + resp.answer.lower()

                sym_hits = sum(1 for es in bq.expected_symbols if es.lower() in retrieved_text)
                total_symbol_hits += sym_hits
                total_symbol_expected += len(bq.expected_symbols)

                # Check expected files
                cited_files = [c.file.replace("\\", "/") for c in resp.citations]
                file_hits = sum(1 for ef in bq.expected_files if any(ef in cf for cf in cited_files))
                total_file_hits += file_hits
                total_file_expected += len(bq.expected_files)

                # Citation validity
                total_citations += len(resp.citations)
                valid_cites = sum(1 for c in resp.citations if c.start_line > 0 and c.end_line >= c.start_line)
                total_valid_citations += valid_cites

                results.append({
                    "question_id": bq.id,
                    "category": bq.category,
                    "question": bq.question,
                    "symbol_hit_rate": round(sym_hits / len(bq.expected_symbols), 2) if bq.expected_symbols else 1.0,
                    "file_hit_rate": round(file_hits / len(bq.expected_files), 2) if bq.expected_files else 1.0,
                    "citations_count": len(resp.citations),
                    "valid_citations": valid_cites,
                    "latency_ms": elapsed_ms,
                    "answer_snippet": resp.answer[:250] + "..."
                })
            except Exception as e:
                logger.error(f"Benchmark error on {bq.id}: {e}", exc_info=True)
                results.append({
                    "question_id": bq.id,
                    "category": bq.category,
                    "question": bq.question,
                    "error": str(e),
                    "symbol_hit_rate": 0.0,
                    "file_hit_rate": 0.0,
                    "citations_count": 0,
                    "valid_citations": 0,
                    "latency_ms": 0,
                    "answer_snippet": "Failed with error."
                })

        avg_sym_hit_rate = round(total_symbol_hits / max(1, total_symbol_expected) * 100, 1)
        avg_file_hit_rate = round(total_file_hits / max(1, total_file_expected) * 100, 1)
        citation_validity = round(total_valid_citations / max(1, total_citations) * 100, 1) if total_citations else 100.0
        avg_latency = round(total_latency_ms / max(1, len(AGENT_CHESS_BENCHMARK)))

        summary = {
            "run_id": run_id,
            "timestamp": start_time,
            "repository_id": repo_id,
            "total_questions": len(AGENT_CHESS_BENCHMARK),
            "symbol_retrieval_hit_rate_pct": avg_sym_hit_rate,
            "relevant_file_accuracy_pct": avg_file_hit_rate,
            "citation_validity_pct": citation_validity,
            "average_latency_ms": avg_latency,
            "results": results
        }

        # Persist run
        run_file = self.eval_dir / f"{run_id}.json"
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        return summary

evaluation_runner = EvaluationRunner()
