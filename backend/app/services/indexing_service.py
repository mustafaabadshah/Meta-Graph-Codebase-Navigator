import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import IndexingError
from app.parser.scanner import RepositoryScanner
from app.parser.ast_parser import AstParser
from app.parser.symbol_resolver import SymbolResolver
from app.parser.incremental import GraphDiffEngine, GraphDiffResult
from app.graph import get_graph_store
from app.services.repository_service import repository_service
from app.schemas.indexing import IndexStatusResponse, GraphDiffSummary

class IndexingService:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._tasks: Dict[str, asyncio.Task] = {}

    def get_status(self, repo_id: str) -> IndexStatusResponse:
        job = self._jobs.get(repo_id)
        if not job:
            return IndexStatusResponse(
                repository_id=repo_id,
                status="idle",
                progress_percentage=0.0
            )
        return IndexStatusResponse(**job)

    def get_graph_diff(self, repo_id: str) -> GraphDiffSummary:
        repo = repository_service.get_repository(repo_id)
        repo_path = Path(repo.path)
        scanner = RepositoryScanner(repo_path)
        files, _ = scanner.scan()
        diff_engine = GraphDiffEngine(repo_id, repo_path)
        diff_result, _, _ = diff_engine.compute_diff(files, force_full=False)
        return GraphDiffSummary(**diff_result.to_summary_dict())

    def get_effective_diff(self, repo_id: str) -> GraphDiffSummary:
        repo = repository_service.get_repository(repo_id)
        repo_path = Path(repo.path)
        scanner = RepositoryScanner(repo_path)
        files, _ = scanner.scan()
        diff_engine = GraphDiffEngine(repo_id, repo_path)
        diff_result = diff_engine.get_effective_diff(files)
        return GraphDiffSummary(**diff_result.to_summary_dict())

    async def start_indexing(self, repo_id: str, is_reindex: bool = False) -> IndexStatusResponse:
        current_job = self._jobs.get(repo_id)
        if current_job and current_job.get("status") == "running":
            return IndexStatusResponse(**current_job)

        repo = repository_service.get_repository(repo_id)
        repo_path = Path(repo.path)

        now_str = datetime.now(timezone.utc).isoformat()
        job_info = {
            "repository_id": repo_id,
            "status": "running",
            "progress_percentage": 0.0,
            "current_file": None,
            "scanned_files": 0,
            "indexed_files": 0,
            "failed_files": 0,
            "total_files": 0,
            "started_at": now_str,
            "completed_at": None,
            "error": None,
            "warnings": [],
            "diff": None
        }
        self._jobs[repo_id] = job_info

        # Launch async worker
        task = asyncio.create_task(self._run_indexing_worker(repo_id, repo_path, repo.name, is_reindex))
        self._tasks[repo_id] = task

        return IndexStatusResponse(**job_info)

    async def _run_indexing_worker(self, repo_id: str, repo_path: Path, repo_name: str, is_reindex: bool):
        job = self._jobs[repo_id]
        try:
            logger.info(f"Starting index job for repository {repo_id} at {repo_path} (is_reindex={is_reindex})")
            scanner = RepositoryScanner(repo_path)
            commit = scanner.get_git_commit()
            files, warnings = scanner.scan()

            job["total_files"] = len(files)
            job["scanned_files"] = len(files)
            job["warnings"] = warnings

            # 1. Compute Graph Diff
            diff_engine = GraphDiffEngine(repo_id, repo_path)
            force_full = not is_reindex and not bool(diff_engine.cached_hashes)
            diff_result, current_hashes, files_by_rel = diff_engine.compute_diff(files, force_full=force_full)
            
            job["diff"] = GraphDiffSummary(**diff_result.to_summary_dict())
            logger.info(f"Graph Diff for {repo_id}: {diff_result.summary_text} (incremental={diff_result.is_incremental})")

            parsed_files = []
            to_parse_rels = set(diff_result.added_files + diff_result.modified_files)

            # 2. Re-use cached AST for unchanged files (zero AST parse overhead)
            if diff_result.is_incremental:
                for rel in diff_result.unchanged_files:
                    cached_pf = diff_engine.load_cached_parsed_file(rel)
                    if cached_pf:
                        parsed_files.append(cached_pf)
                        job["indexed_files"] += 1
                    else:
                        to_parse_rels.add(rel)

            # 3. Only parse added and modified files with AstParser
            parse_list = sorted(list(to_parse_rels))
            total_to_parse = len(parse_list)

            for idx, rel in enumerate(parse_list):
                f_path = files_by_rel[rel]
                job["current_file"] = f_path.name
                job["progress_percentage"] = round(((idx + 1) / max(total_to_parse, 1)) * 80.0, 1)

                parsed = AstParser.parse_file(repo_id, repo_path, f_path)
                parsed_files.append(parsed)
                if parsed.file_node.parse_status == "ok":
                    job["indexed_files"] += 1
                else:
                    job["failed_files"] += 1

                # Yield control briefly so status polling remains snappy
                await asyncio.sleep(0.001)

            if total_to_parse == 0 and diff_result.is_incremental:
                job["progress_percentage"] = 80.0
                job["current_file"] = "All files unchanged. Reusing verified AST graph."

            job["progress_percentage"] = 85.0
            job["current_file"] = "Resolving cross-file symbols & calls..."

            # 4. Resolve symbols across complete union of parsed files
            resolver = SymbolResolver(repo_id, repo_name, str(repo_path), parsed_files)
            graph = resolver.resolve_all(commit_hash=commit, warnings=warnings)

            job["progress_percentage"] = 92.0
            job["current_file"] = "Ingesting graph nodes & edges..."

            # 5. Ingest incrementally via apply_graph_diff or full rebuild
            store = get_graph_store()
            if diff_result.is_incremental and hasattr(store, "apply_graph_diff"):
                store.apply_graph_diff(
                    repo_id=repo_id,
                    graph=graph,
                    added_files=diff_result.added_files,
                    modified_files=diff_result.modified_files,
                    deleted_files=diff_result.deleted_files
                )
            else:
                store.create_or_update_index(graph)

            # 6. Save updated state (hashes, serialized parsed files, and diff result)
            diff_engine.save_state(parsed_files, current_hashes, diff_result=diff_result)

            completed_at = datetime.now(timezone.utc).isoformat()
            job["status"] = "completed"
            job["progress_percentage"] = 100.0
            job["current_file"] = None
            job["completed_at"] = completed_at

            repository_service.update_repo_metadata(repo_id, {
                "indexed_at": completed_at,
                "commit_hash": commit,
                "file_count": len(files)
            })
            logger.info(
                f"Indexing completed successfully for {repo_id}: "
                f"{len(graph.files)} files, {len(graph.edges)} edges. "
                f"Graph Diff: {diff_result.summary_text}."
            )

        except Exception as e:
            logger.error(f"Indexing failed for {repo_id}: {e}", exc_info=True)
            job["status"] = "failed"
            job["error"] = str(e)
            job["completed_at"] = datetime.now(timezone.utc).isoformat()

indexing_service = IndexingService()
