import json
from pathlib import Path
from typing import Dict, List, Optional, Any

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import RepositoryNotFoundError, RepositoryPathInvalidError
from app.utils.paths import validate_repo_path, resolve_safe_subpath
from app.utils.identifiers import make_repo_id
from app.parser.scanner import RepositoryScanner
from app.schemas.repository import RepositoryResponse, RepositoryValidationResponse

class RepositoryService:
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or settings.INDEXES_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.storage_dir / "repositories.json"
        self._ensure_default_repo()

    def _load_registry(self) -> Dict[str, Dict[str, Any]]:
        if self.registry_file.is_file():
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read repo registry: {e}")
        return {}

    def _save_registry(self, registry: Dict[str, Dict[str, Any]]):
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)

    def _ensure_default_repo(self):
        """Auto-registers DEFAULT_REPOSITORY_PATH if valid."""
        registry = self._load_registry()
        default_p = Path(settings.DEFAULT_REPOSITORY_PATH)
        if default_p.is_dir():
            repo_id = make_repo_id(str(default_p), "Agent Chess")
            if repo_id not in registry:
                registry[repo_id] = {
                    "id": repo_id,
                    "name": "Agent Chess",
                    "path": str(default_p.resolve()),
                    "is_valid": True,
                    "commit_hash": None,
                    "indexed_at": None,
                    "file_count": 0,
                    "warnings": []
                }
                self._save_registry(registry)

    def list_repositories(self) -> List[RepositoryResponse]:
        registry = self._load_registry()
        return [RepositoryResponse(**v) for v in registry.values()]

    def get_repository(self, repo_id: str) -> RepositoryResponse:
        registry = self._load_registry()
        if repo_id not in registry:
            raise RepositoryNotFoundError(f"Repository '{repo_id}' not found.")
        return RepositoryResponse(**registry[repo_id])

    def validate_path(self, path_str: str) -> RepositoryValidationResponse:
        try:
            p = validate_repo_path(path_str)
            scanner = RepositoryScanner(p)
            commit = scanner.get_git_commit()
            files, warnings = scanner.scan()

            return RepositoryValidationResponse(
                path=str(p),
                is_valid=True,
                exists=True,
                is_directory=True,
                is_git=commit is not None,
                commit_hash=commit,
                estimated_python_files=len(files),
                message=f"Valid repository: {len(files)} Python files discovered."
            )
        except Exception as e:
            return RepositoryValidationResponse(
                path=path_str,
                is_valid=False,
                exists=Path(path_str).exists(),
                is_directory=Path(path_str).is_dir() if Path(path_str).exists() else False,
                is_git=False,
                commit_hash=None,
                estimated_python_files=0,
                message=str(e)
            )

    def register_repository(self, path_str: str, name: Optional[str] = None) -> RepositoryResponse:
        val = self.validate_path(path_str)
        if not val.is_valid:
            raise RepositoryPathInvalidError(f"Cannot register repository: {val.message}")

        resolved_path = Path(val.path)
        repo_name = name or resolved_path.name
        repo_id = make_repo_id(str(resolved_path), repo_name)

        registry = self._load_registry()
        repo_data = {
            "id": repo_id,
            "name": repo_name,
            "path": str(resolved_path),
            "is_valid": True,
            "commit_hash": val.commit_hash,
            "indexed_at": None,
            "file_count": val.estimated_python_files,
            "warnings": []
        }
        registry[repo_id] = repo_data
        self._save_registry(registry)
        return RepositoryResponse(**repo_data)

    def update_repo_metadata(self, repo_id: str, updates: Dict[str, Any]):
        registry = self._load_registry()
        if repo_id in registry:
            registry[repo_id].update(updates)
            self._save_registry(registry)

    def delete_repository(self, repo_id: str):
        registry = self._load_registry()
        if repo_id in registry:
            del registry[repo_id]
            self._save_registry(registry)

repository_service = RepositoryService()
