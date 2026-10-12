import os
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional
import pathspec

from app.core.config import settings
from app.core.exceptions import RepositoryPathInvalidError
from app.core.logging import logger
from app.utils.paths import validate_repo_path, normalize_posix_relpath

DEFAULT_IGNORE_DIRS = {
    ".git", ".venv", "venv", "env", ".env", "node_modules",
    "__pycache__", "build", "dist", ".pytest_cache", ".ruff_cache",
    ".mypy_cache", ".tox", "site-packages", ".idea", ".vscode"
}

class RepositoryScanner:
    def __init__(
        self,
        repo_path: str | Path,
        max_files: int = settings.MAX_REPOSITORY_FILES,
        max_file_size_bytes: int = settings.MAX_FILE_SIZE_BYTES
    ):
        self.repo_path = validate_repo_path(repo_path)
        self.max_files = max_files
        self.max_file_size_bytes = max_file_size_bytes
        self.gitignore_spec = self._load_gitignore()

    def _load_gitignore(self) -> Optional[pathspec.PathSpec]:
        """Loads and compiles .gitignore if available in repo root."""
        gitignore_file = self.repo_path / ".gitignore"
        if gitignore_file.is_file():
            try:
                with open(gitignore_file, "r", encoding="utf-8", errors="ignore") as f:
                    patterns = f.read().splitlines()
                return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
            except Exception as e:
                logger.warning(f"Failed to parse .gitignore in {self.repo_path}: {e}")
        return None

    def get_git_commit(self) -> Optional[str]:
        """Attempts to retrieve the current git commit hash if in a git tree."""
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
        return None

    def scan(self) -> Tuple[List[Path], List[str]]:
        """
        Scans repository root for Python files respecting ignores and limits.
        Returns (valid_python_files, warnings).
        """
        valid_files: List[Path] = []
        warnings: List[str] = []
        visited_dirs = set()

        for root, dirs, files in os.walk(str(self.repo_path), followlinks=False):
            root_path = Path(root)
            
            # Prevent symlink cycles and directory escapes
            try:
                resolved_root = root_path.resolve()
                if resolved_root in visited_dirs:
                    continue
                visited_dirs.add(resolved_root)
                # Check root stays within repo
                resolved_root.relative_to(self.repo_path.resolve())
            except ValueError:
                warnings.append(f"Directory escaped repository root: {root_path}")
                dirs[:] = []
                continue

            # Filter ignored directories in-place
            dirs[:] = [
                d for d in dirs
                if d not in DEFAULT_IGNORE_DIRS and not d.startswith(".")
            ]

            for file_name in files:
                if not file_name.endswith(".py"):
                    continue

                file_path = root_path / file_name
                rel_posix = normalize_posix_relpath(self.repo_path, file_path)

                # Check gitignore
                if self.gitignore_spec and self.gitignore_spec.match_file(rel_posix):
                    continue

                # Check file size
                try:
                    stat = file_path.stat()
                    if stat.st_size > self.max_file_size_bytes:
                        warnings.append(
                            f"File exceeds max size ({stat.st_size} > {self.max_file_size_bytes} bytes): {rel_posix}"
                        )
                        continue
                except OSError as err:
                    warnings.append(f"Failed to stat file {rel_posix}: {err}")
                    continue

                valid_files.append(file_path)

                if len(valid_files) >= self.max_files:
                    warnings.append(
                        f"Scan limit reached ({self.max_files} files). Remaining files truncated."
                    )
                    return valid_files, warnings

        # Sort for deterministic processing
        valid_files.sort(key=lambda p: str(p))
        return valid_files, warnings
