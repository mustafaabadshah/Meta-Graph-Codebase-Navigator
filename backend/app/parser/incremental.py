import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from pydantic import BaseModel, Field

from app.utils.paths import normalize_posix_relpath
from app.utils.identifiers import compute_file_hash
from app.parser.models import ParsedFile
from app.core.config import settings
from app.core.logging import logger

class GraphDiffResult(BaseModel):
    """
    Detailed diff describing changed files between indexing runs.
    """
    repository_id: str
    is_incremental: bool = False
    has_changes: bool = False
    added_files: List[str] = Field(default_factory=list)      # Posix relative paths
    modified_files: List[str] = Field(default_factory=list)   # Posix relative paths
    deleted_files: List[str] = Field(default_factory=list)    # Posix relative paths
    unchanged_files: List[str] = Field(default_factory=list)  # Posix relative paths
    total_files: int = 0
    summary_text: str = ""

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "is_incremental": self.is_incremental,
            "has_changes": self.has_changes,
            "added_count": len(self.added_files),
            "modified_count": len(self.modified_files),
            "deleted_count": len(self.deleted_files),
            "unchanged_count": len(self.unchanged_files),
            "added_files": self.added_files,
            "modified_files": self.modified_files,
            "deleted_files": self.deleted_files,
            "unchanged_files": self.unchanged_files,
            "summary_text": self.summary_text
        }

class GraphDiffEngine:
    """
    High-Performance Graph Diff & Incremental Indexing Engine:
    Tracks file hashes and serialized parsed ASTs across runs.
    Eliminates redundant AST parsing for unchanged files and enables
    incremental graph updates without rebuilding the knowledge graph from scratch.
    """
    def __init__(self, repo_id: str, repo_root: Path, cache_dir: Optional[Path] = None):
        self.repo_id = repo_id
        self.repo_root = repo_root
        self.cache_dir = cache_dir or settings.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.hashes_file = self.cache_dir / f"{repo_id}_hashes.json"
        self.parsed_cache_file = self.cache_dir / f"{repo_id}_parsed.json"
        self.last_diff_file = self.cache_dir / f"{repo_id}_last_diff.json"

        self.cached_hashes: Dict[str, str] = self._load_json(self.hashes_file)
        self.cached_parsed: Dict[str, dict] = self._load_json(self.parsed_cache_file)
        self.cached_last_diff: Dict[str, Any] = self._load_json(self.last_diff_file)

    def _load_json(self, path: Path) -> Dict[str, Any]:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed loading cache file at {path}: {e}")
        return {}

    def compute_diff(self, current_files: List[Path], force_full: bool = False) -> Tuple[GraphDiffResult, Dict[str, str], Dict[str, Path]]:
        """
        Calculates Graph Diff by comparing disk file hashes against cached hashes.
        Returns:
            diff_result: GraphDiffResult
            current_hashes: Dict[str, str] (rel_path -> hash)
            files_by_rel: Dict[str, Path] (rel_path -> Path)
        """
        current_hashes: Dict[str, str] = {}
        files_by_rel: Dict[str, Path] = {}
        added: List[str] = []
        modified: List[str] = []
        unchanged: List[str] = []

        for p in current_files:
            rel = normalize_posix_relpath(self.repo_root, p)
            files_by_rel[rel] = p
            try:
                fhash = compute_file_hash(p.read_bytes())
                current_hashes[rel] = fhash

                if force_full or not self.cached_hashes:
                    added.append(rel)
                elif rel not in self.cached_hashes:
                    added.append(rel)
                elif self.cached_hashes[rel] != fhash:
                    modified.append(rel)
                else:
                    unchanged.append(rel)
            except Exception as e:
                logger.warning(f"Error computing hash for {rel}: {e}")
                modified.append(rel)

        # Detect deleted files (in previous cache but no longer on disk)
        current_rel_set = set(current_hashes.keys())
        deleted: List[str] = [rel for rel in self.cached_hashes.keys() if rel not in current_rel_set] if not force_full else []

        is_incremental = not force_full and bool(self.cached_hashes)
        has_changes = bool(added or modified or deleted)

        summary_parts = []
        if added:
            summary_parts.append(f"{len(added)} added")
        if modified:
            summary_parts.append(f"{len(modified)} modified")
        if deleted:
            summary_parts.append(f"{len(deleted)} deleted")
        if unchanged:
            summary_parts.append(f"{len(unchanged)} unchanged")

        summary_text = ", ".join(summary_parts) if summary_parts else "No files detected"

        diff_result = GraphDiffResult(
            repository_id=self.repo_id,
            is_incremental=is_incremental,
            has_changes=has_changes,
            added_files=added,
            modified_files=modified,
            deleted_files=deleted,
            unchanged_files=unchanged,
            total_files=len(current_files),
            summary_text=summary_text
        )

        return diff_result, current_hashes, files_by_rel

    def load_cached_parsed_file(self, rel_path: str) -> Optional[ParsedFile]:
        """
        Deserializes a cached ParsedFile without executing AST parsing.
        """
        data = self.cached_parsed.get(rel_path)
        if not data:
            return None
        try:
            return ParsedFile.model_validate(data)
        except Exception as e:
            logger.warning(f"Failed deserializing cached ParsedFile for {rel_path}: {e}")
            return None

    def save_state(
        self,
        parsed_files: List[ParsedFile],
        current_hashes: Dict[str, str],
        diff_result: Optional[GraphDiffResult] = None
    ):
        """
        Persists updated file hashes and serialized ParsedFiles to disk.
        """
        try:
            # 1. Save hashes
            with open(self.hashes_file, "w", encoding="utf-8") as f:
                json.dump(current_hashes, f, indent=2)

            # 2. Save serialized ParsedFiles dictionary
            parsed_dump: Dict[str, dict] = {}
            for pf in parsed_files:
                rel = pf.file_node.rel_path
                parsed_dump[rel] = pf.model_dump()

            with open(self.parsed_cache_file, "w", encoding="utf-8") as f:
                json.dump(parsed_dump, f)

            # 3. Save last indexing diff summary if provided
            if diff_result is not None:
                summary_data = diff_result.to_summary_dict()
                summary_data["repository_id"] = self.repo_id
                with open(self.last_diff_file, "w", encoding="utf-8") as f:
                    json.dump(summary_data, f, indent=2)
                self.cached_last_diff = summary_data

            self.cached_hashes = current_hashes
            self.cached_parsed = parsed_dump
            logger.info(f"GraphDiffEngine saved state for {self.repo_id} ({len(current_hashes)} files cached).")
        except Exception as e:
            logger.error(f"Failed saving GraphDiffEngine state for {self.repo_id}: {e}")

    def get_effective_diff(self, current_files: List[Path]) -> GraphDiffResult:
        """
        Returns the current pending diff if changes exist;
        otherwise falls back to the most recent recorded indexing diff.
        """
        diff_result, _, _ = self.compute_diff(current_files, force_full=False)
        if diff_result.has_changes:
            return diff_result
        if self.cached_last_diff and bool(self.cached_last_diff.get("added_files") or self.cached_last_diff.get("modified_files")):
            return GraphDiffResult(
                repository_id=self.repo_id,
                is_incremental=self.cached_last_diff.get("is_incremental", False),
                has_changes=self.cached_last_diff.get("has_changes", False),
                added_files=self.cached_last_diff.get("added_files", []),
                modified_files=self.cached_last_diff.get("modified_files", []),
                deleted_files=self.cached_last_diff.get("deleted_files", []),
                unchanged_files=self.cached_last_diff.get("unchanged_files", []),
                total_files=len(current_files),
                summary_text=self.cached_last_diff.get("summary_text", "")
            )
        return diff_result

    def clear_cache(self):
        """Purges cache files for full rebuild."""
        try:
            if self.hashes_file.is_file():
                self.hashes_file.unlink()
            if self.parsed_cache_file.is_file():
                self.parsed_cache_file.unlink()
            if self.last_diff_file.is_file():
                self.last_diff_file.unlink()
            self.cached_hashes = {}
            self.cached_parsed = {}
            self.cached_last_diff = {}
        except Exception as e:
            logger.warning(f"Failed clearing cache for {self.repo_id}: {e}")

class IncrementalTracker:
    """
    Backwards-compatible tracker wrapping GraphDiffEngine.
    """
    def __init__(self, cache_file_path: Path):
        self.cache_file_path = cache_file_path
        self.repo_id = cache_file_path.stem.replace("_hashes", "")
        self.engine = GraphDiffEngine(self.repo_id, cache_file_path.parent, cache_file_path.parent)

    @property
    def cached_hashes(self) -> Dict[str, str]:
        return self.engine.cached_hashes

    def save_cache(self, current_hashes: Dict[str, str]):
        with open(self.cache_file_path, "w", encoding="utf-8") as f:
            json.dump(current_hashes, f, indent=2)

    def detect_changes(
        self,
        repo_root: Path,
        current_files: List[Path]
    ) -> Tuple[List[Path], List[Path], List[str], Dict[str, str]]:
        self.engine.repo_root = repo_root
        diff, hashes, files_by_rel = self.engine.compute_diff(current_files, force_full=False)
        added_paths = [files_by_rel[rel] for rel in diff.added_files if rel in files_by_rel]
        modified_paths = [files_by_rel[rel] for rel in diff.modified_files if rel in files_by_rel]
        return added_paths, modified_paths, diff.deleted_files, hashes
