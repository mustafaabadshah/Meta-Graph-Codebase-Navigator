import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from app.utils.paths import normalize_posix_relpath
from app.utils.identifiers import compute_file_hash
from app.core.logging import logger

class IncrementalTracker:
    """
    Tracks file hashes across indexing runs to detect added, modified,
    and deleted Python files for incremental processing.
    """
    def __init__(self, cache_file_path: Path):
        self.cache_file_path = cache_file_path
        self.cached_hashes: Dict[str, str] = self._load_cache()

    def _load_cache(self) -> Dict[str, str]:
        if self.cache_file_path.is_file():
            try:
                with open(self.cache_file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read index cache at {self.cache_file_path}: {e}")
        return {}

    def save_cache(self, current_hashes: Dict[str, str]):
        try:
            self.cache_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file_path, "w", encoding="utf-8") as f:
                json.dump(current_hashes, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save index cache to {self.cache_file_path}: {e}")

    def detect_changes(
        self,
        repo_root: Path,
        current_files: List[Path]
    ) -> Tuple[List[Path], List[Path], List[str], Dict[str, str]]:
        """
        Compares current filesystem files against cached hashes.
        Returns:
            added_files: List[Path]
            modified_files: List[Path]
            deleted_rel_paths: List[str]
            current_hashes: Dict[str, str]
        """
        current_hashes: Dict[str, str] = {}
        added: List[Path] = []
        modified: List[Path] = []

        for p in current_files:
            rel = normalize_posix_relpath(repo_root, p)
            try:
                fhash = compute_file_hash(p.read_bytes())
                current_hashes[rel] = fhash

                if rel not in self.cached_hashes:
                    added.append(p)
                elif self.cached_hashes[rel] != fhash:
                    modified.append(p)
            except Exception as e:
                logger.warning(f"Error computing hash for {rel}: {e}")

        # Detect deleted
        current_rels = set(current_hashes.keys())
        deleted_rel_paths = [rel for rel in self.cached_hashes if rel not in current_rels]

        return added, modified, deleted_rel_paths, current_hashes
