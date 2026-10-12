import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import IndexingError
from app.parser.scanner import RepositoryScanner
from app.parser.ast_parser import AstParser
from app.parser.symbol_resolver import SymbolResolver
from app.parser.incremental import IncrementalTracker
from app.graph import get_graph_store
from app.services.repository_service import repository_service
from app.schemas.indexing import IndexStatusResponse

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
            "warnings": []
        }
        self._jobs[repo_id] = job_info

        # Launch async task
        task = asyncio.create_task(self._run_indexing_worker(repo_id, repo_path, repo.name, is_reindex))
        self._tasks[repo_id] = task

        return IndexStatusResponse(**job_info)

    async def _run_indexing_worker(self, repo_id: str, repo_path: Path, repo_name: str, is_reindex: bool):
        job = self._jobs[repo_id]
        try:
            logger.info(f"Starting index job for repository {repo_id} at {repo_path}")
            scanner = RepositoryScanner(repo_path)
            commit = scanner.get_git_commit()
            files, warnings = scanner.scan()

            job["total_files"] = len(files)
            job["scanned_files"] = len(files)
            job["warnings"] = warnings

            parsed_files = []
            for idx, f in enumerate(files):
                job["current_file"] = f.name
                job["progress_percentage"] = round(((idx + 1) / len(files)) * 80.0, 1)

                parsed = AstParser.parse_file(repo_id, repo_path, f)
                parsed_files.append(parsed)
                if parsed.file_node.parse_status == "ok":
                    job["indexed_files"] += 1
                else:
                    job["failed_files"] += 1
                
                # Yield control briefly so status polling remains snappy
                await asyncio.sleep(0.001)

            job["progress_percentage"] = 85.0
            job["current_file"] = "Resolving cross-file symbols & calls..."

            resolver = SymbolResolver(repo_id, repo_name, str(repo_path), parsed_files)
            graph = resolver.resolve_all(commit_hash=commit, warnings=warnings)

            job["progress_percentage"] = 92.0
            job["current_file"] = "Ingesting graph nodes & edges..."

            store = get_graph_store()
            store.create_or_update_index(graph)

            # Update cache tracker
            cache_file = settings.CACHE_DIR / f"{repo_id}_hashes.json"
            tracker = IncrementalTracker(cache_file)
            _, _, _, current_hashes = tracker.detect_changes(repo_path, files)
            tracker.save_cache(current_hashes)

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
            logger.info(f"Indexing completed successfully for {repo_id}: {len(graph.files)} files, {len(graph.edges)} edges.")

        except Exception as e:
            logger.error(f"Indexing failed for {repo_id}: {e}", exc_info=True)
            job["status"] = "failed"
            job["error"] = str(e)
            job["completed_at"] = datetime.now(timezone.utc).isoformat()

indexing_service = IndexingService()
